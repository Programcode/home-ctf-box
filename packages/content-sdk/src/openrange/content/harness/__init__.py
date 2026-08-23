"""Docker harness: build, start, healthcheck, solve, reset-proof, teardown.

This is what `make test-solvers` and CI run for every room. It never
publishes ports beyond a random loopback port during the run, and every
resource is destroyed afterwards.
"""

from __future__ import annotations

import importlib.util
import logging
import os
import socket
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import docker
import httpx
from openrange.content.loader import load_room
from openrange.content.models import RoomBundle
from openrange.content.solver import SolveContext, derive_flag

logger = logging.getLogger(__name__)

NETWORK_PREFIX = "openrange-test"


@dataclass(slots=True)
class HarnessResult:
    slug: str
    solved: bool
    detail: str


class HarnessError(Exception):
    pass


@dataclass(slots=True)
class RoomEnv:
    bundle: RoomBundle
    base_urls: dict[str, str]
    expected_flags: dict[str, str]
    instance_id: str
    _client: Any
    _container: Any

    def wait_healthy(self) -> None:
        hc = self.bundle.spec.target.healthcheck
        deadline = time.monotonic() + max(hc.timeout_seconds, 10)
        last_error = ""
        while time.monotonic() < deadline:
            self._container.reload()
            if self._container.status == "exited":
                logs = self._container.logs(tail=40).decode(errors="replace")
                raise HarnessError(f"container exited during startup:\n{logs}")
            try:
                url = self.base_urls["target"]
                if hc.http_path:
                    res = httpx.get(url.rstrip("/") + hc.http_path, timeout=2)
                    if res.status_code < 500:
                        return
                elif hc.tcp_port is not None:
                    host_part = url.split("//")[1]
                    host, port = host_part.split(":")
                    with socket.create_connection((host, int(port)), timeout=2):
                        return
            except Exception as exc:
                last_error = str(exc)
            time.sleep(0.5)
        raise HarnessError(f"healthcheck did not pass in time: {last_error}")

    def restart(self) -> None:
        """Reset proof: a fresh process must serve fresh state."""
        self._container.restart(timeout=10)
        self.wait_healthy()

    def solve_context(self) -> SolveContext:
        return SolveContext(
            base_urls=self.base_urls,
            expected_flags=self.expected_flags,
        )


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _load_solver(solver_path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(f"solver_{uuid.uuid4().hex}", solver_path)
    if spec is None or spec.loader is None:
        raise HarnessError(f"cannot load {solver_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not hasattr(module, "solve"):
        raise HarnessError("solver.py must define solve(ctx)")
    return module


@contextmanager
def room_environment(bundle_dir: Path) -> Iterator[RoomEnv]:
    """Builds and starts a room target on an isolated bridge network."""
    client = docker.from_env()
    bundle, manifest = load_room(bundle_dir)
    run_id = f"{bundle.metadata.slug}-{uuid.uuid4().hex[:8]}"
    network_name = f"{NETWORK_PREFIX}-{run_id}"
    image_tag = f"openrange/test-{bundle.metadata.slug}:{bundle.metadata.version}"

    network = client.networks.create(network_name, driver="bridge")
    container = None
    image = None
    try:
        context_dir = (manifest.parent / bundle.spec.target.build_context).resolve()
        logger.info("building %s", image_tag)
        image, _logs = client.images.build(path=str(context_dir), tag=image_tag, rm=True)

        master_key = os.environ.get("OPENRANGE_FLAG_MASTER_KEY", "").encode() or b"harness-key"
        expected = {
            task.id: derive_flag(
                master_key,
                instance_id=run_id,
                content_slug=bundle.metadata.slug,
                task_id=task.id,
            )
            for task in bundle.spec.tasks
        }

        env: dict[str, str] = {}
        if bundle.spec.target.flag_delivery == "env":
            joined = "|".join(expected.values())
            # Single-task rooms get the bare flag; multi-task rooms get an
            # ordered list so the target can expose per-task flags.
            env[bundle.spec.target.flag_env] = (
                next(iter(expected.values())) if len(expected) == 1 else joined
            )

        port = _free_port()
        container = client.containers.run(
            str(image.id),
            detach=True,
            name=f"{network_name}-target",
            network=network_name,
            environment=env,
            ports={f"{bundle.spec.target.ports[0]}/tcp": ("127.0.0.1", port)},
            nano_cpus=int(1.5 * 1e9),
            mem_limit="512m",
            pids_limit=256,
            security_opt=["no-new-privileges:true"],
            cap_drop=["ALL"],
        )
        yield RoomEnv(
            bundle=bundle,
            base_urls={"target": f"http://127.0.0.1:{port}"},
            expected_flags=expected,
            instance_id=run_id,
            _client=client,
            _container=container,
        )
    finally:
        if container is not None:
            try:
                container.remove(force=True)
            except Exception:  # noqa: S110 - best-effort teardown
                pass
        try:
            network.remove()
        except Exception:  # noqa: S110 - best-effort teardown
            pass
        if image is not None:
            try:
                client.images.remove(image.id, force=True)
            except Exception:  # noqa: S110 - best-effort teardown
                pass


def solve_room(bundle_dir: Path) -> HarnessResult:
    """Full gate: healthy start → intended-path solve → reset → re-solve."""
    slug = bundle_dir.name
    try:
        with room_environment(bundle_dir) as env:
            solver = _load_solver(bundle_dir / "solver" / "solver.py")
            env.wait_healthy()
            ctx = env.solve_context()
            first = solver.solve(ctx)
            if not first.ok:
                failed = [r.task_id for r in first.results if not r.ok]
                return HarnessResult(slug, False, f"first pass failed tasks: {failed}")
            env.restart()
            second = solver.solve(env.solve_context())
            if not second.ok:
                failed = [r.task_id for r in second.results if not r.ok]
                return HarnessResult(slug, False, f"post-reset pass failed tasks: {failed}")
            captured = {r.task_id: r.captured or "" for r in first.results}
            mismatches = [
                tid for tid, flag in env.expected_flags.items() if captured.get(tid) != flag
            ]
            if mismatches:
                return HarnessResult(
                    slug,
                    False,
                    f"captured flags do not match derived flags for {mismatches}",
                )
            return HarnessResult(
                slug, True, "solved on both passes with matching per-session flags"
            )
    except HarnessError as exc:
        return HarnessResult(slug, False, str(exc))
