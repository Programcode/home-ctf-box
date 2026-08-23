"""Docker harness: build, start, solve from inside the lab network.

The lab network is internal (default-deny egress), so nothing on it is
reachable from the host and the room cannot reach out. Solvers execute
in a purpose-built attacker container attached to the same network,
which is exactly how learner workstations work in production.
"""

from __future__ import annotations

import json
import logging
import os
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import docker
from openrange.content.loader import load_room
from openrange.content.models import RoomBundle
from openrange.content.solver import derive_flag

logger = logging.getLogger(__name__)

NETWORK_PREFIX = "openrange-test"
ATTACKER_IMAGE = "openrange/harness-attacker:latest"

_DRIVER_TEMPLATE = """
import dataclasses
import importlib.util
import json

spec = importlib.util.spec_from_file_location("room_solver", "/bundle/solver/solver.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

from openrange.content.solver import SolveContext  # noqa: E402

with open("/work/expected.json") as fh:
    expected = json.load(fh)

ctx = SolveContext(base_urls={"target": "http://target:%(port)d"}, expected_flags=expected)
result = mod.solve(ctx)
print("@@RESULT@@" + json.dumps(dataclasses.asdict(result)))
"""


@dataclass(slots=True)
class HarnessResult:
    slug: str
    solved: bool
    detail: str


class HarnessError(Exception):
    pass


def _ensure_attacker_image(client: docker.DockerClient) -> object:
    try:
        return client.images.get(ATTACKER_IMAGE)
    except Exception as exc:  # image absent on first run; build below
        logger.debug("attacker image not present yet (%s)", exc.__class__.__name__)
    root = Path(__file__).resolve().parents[6]
    logger.info("building harness attacker image")
    image, _logs = client.images.build(
        path=str(root),
        dockerfile="packages/content-sdk/harness-attacker/Dockerfile",
        tag=ATTACKER_IMAGE,
        rm=True,
    )
    return image


@dataclass(slots=True)
class RoomEnv:
    bundle: RoomBundle
    base_urls: dict[str, str]
    expected_flags: dict[str, str]
    instance_id: str
    _client: Any
    _container: Any
    _attacker: Any

    def wait_healthy(self) -> None:
        hc = self.bundle.spec.target.healthcheck
        deadline = time.monotonic() + max(hc.timeout_seconds, 10)
        while time.monotonic() < deadline:
            self._container.reload()
            if self._container.status == "exited":
                logs = self._container.logs(tail=40).decode(errors="replace")
                raise HarnessError(f"container exited during startup:\n{logs}")
            if self._probe():
                return
            time.sleep(0.5)
        raise HarnessError("healthcheck did not pass in time")

    def _probe(self) -> bool:
        hc = self.bundle.spec.target.healthcheck
        port = self.bundle.spec.target.ports[0]
        if hc.tcp_port is not None:
            code = (
                "import socket,sys;"
                f"s=socket.create_connection(('127.0.0.1',{hc.tcp_port}),2);sys.exit(0)"
            )
            result = self._container.exec_run(["python3", "-c", code])
            if result.exit_code == 0:
                return True
            if result.exit_code in (126, 127):
                # Target has no python3 (e.g. Debian-slim SSH boxes).
                bash = f"exec 3<>/dev/tcp/127.0.0.1/{hc.tcp_port}"
                return bool(self._container.exec_run(["bash", "-c", bash]).exit_code == 0)
            return False
        path = hc.http_path or "/healthz"
        code = (
            "import urllib.request,sys;"
            f"urllib.request.urlopen('http://127.0.0.1:{port}{path}',timeout=2);"
            "sys.exit(0)"
        )
        result = self._container.exec_run(["python3", "-c", code])
        if result.exit_code == 0:
            return True
        if result.exit_code in (126, 127):
            for probe_cmd in (
                ["curl", "-fsS", f"http://127.0.0.1:{port}{path}"],
                ["wget", "-qO-", f"http://127.0.0.1:{port}{path}"],
            ):
                if self._container.exec_run(probe_cmd).exit_code == 0:
                    return True
            return False
        return False

    def restart(self) -> None:
        """Reset proof: fresh process must serve fresh state."""
        self._container.restart(timeout=10)
        self.wait_healthy()

    def run_solver(self, solver_path: Path) -> dict[str, dict[str, object]]:
        driver = _DRIVER_TEMPLATE % {"port": self.bundle.spec.target.ports[0]}
        payload_dir = "/work"
        self._attacker.put_archive(
            payload_dir,
            _tar_bytes(
                [
                    ("expected.json", json.dumps(self.expected_flags)),
                    ("_driver.py", driver),
                ]
            ),
        )
        exit_code, output = self._attacker.exec_run(
            ["python3", "/work/_driver.py"],
            workdir="/work",
        )
        text = output.decode(errors="replace")
        marker = text.rfind("@@RESULT@@")
        if exit_code not in (0, None) or marker == -1:
            raise HarnessError(f"solver crashed inside attacker container:\n{text[-1500:]}")
        payload = json.loads(text[marker + len("@@RESULT@@") :].strip().splitlines()[-1])
        return {r["task_id"]: r for r in payload["results"]}


def _tar_bytes(entries: list[tuple[str, str]]):
    import io
    import tarfile

    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tar:
        for arcname, content in entries:
            data = content.encode()
            info = tarfile.TarInfo(arcname)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return buf.getvalue()


@contextmanager
def room_environment(bundle_dir: Path) -> Iterator[RoomEnv]:
    """Builds the room target and an attacker container on an internal net."""
    client = docker.from_env()
    bundle, manifest = load_room(bundle_dir)
    run_id = f"{bundle.metadata.slug}-{uuid.uuid4().hex[:8]}"
    network_name = f"{NETWORK_PREFIX}-{run_id}"
    image_tag = f"openrange/test-{bundle.metadata.slug}:{bundle.metadata.version}"

    network = client.networks.create(network_name, driver="bridge", internal=True)
    container = None
    attacker = None
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
            if len(expected) == 1:
                env[bundle.spec.target.flag_env] = next(iter(expected.values()))
            else:
                for task_id, flag in expected.items():
                    suffix = task_id.upper().replace("-", "_")
                    env[f"{bundle.spec.target.flag_env}_{suffix}"] = flag

        elevated = bundle.spec.target.privilege_profile == "elevated"
        container_kwargs: dict[str, object] = dict(
            detach=True,
            name=f"target-{run_id}",
            hostname="target",
            network=network_name,
            environment=env,
            nano_cpus=int(1.5 * 1e9),
            mem_limit="512m",
            pids_limit=256,
        )
        if elevated:
            # Bounded set for setuid-dependent services (sshd privsep, sudo,
            # SUID). no-new-privileges must stay off or elevation is a no-op.
            container_kwargs["cap_add"] = [
                "CHOWN",
                "DAC_OVERRIDE",
                "FOWNER",
                "SETGID",
                "SETUID",
                "NET_BIND_SERVICE",
                "SYS_CHROOT",
            ]
        else:
            container_kwargs["cap_drop"] = ["ALL"]
            container_kwargs["security_opt"] = ["no-new-privileges:true"]
        container = client.containers.run(image.id, **container_kwargs)  # type: ignore[arg-type]

        attacker_image = _ensure_attacker_image(client)
        repo_root = Path(__file__).resolve().parents[6]
        attacker = client.containers.run(
            attacker_image.id,
            detach=True,
            name=f"attacker-{run_id}",
            network=network_name,
            volumes={str(repo_root / "content"): {"bind": "/content", "mode": "ro"}},
            working_dir="/work",
            command=["sleep", "infinity"],
            nano_cpus=int(0.5 * 1e9),
            mem_limit="256m",
            cap_drop=["ALL"],
            security_opt=["no-new-privileges:true"],
        )
        # Re-mount this specific bundle read-only into the attacker.
        attacker.exec_run(["mkdir", "-p", "/bundle"])
        put_dir(attacker, bundle_dir, "/bundle")

        yield RoomEnv(
            bundle=bundle,
            base_urls={"target": f"http://target:{bundle.spec.target.ports[0]}"},
            expected_flags=expected,
            instance_id=run_id,
            _client=client,
            _container=container,
            _attacker=attacker,
        )
    finally:
        for c in (container, attacker):
            if c is not None:
                try:
                    c.remove(force=True)
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


def put_dir(container: Any, src: Path, dest: str) -> None:
    import tarfile

    buf_io = __import__("io").BytesIO()
    with tarfile.open(fileobj=buf_io, mode="w") as tar:
        for path in sorted(src.rglob("*")):
            if "__pycache__" in str(path):
                continue
            tar.add(path, arcname=path.relative_to(src))
    buf_io.seek(0)
    container.put_archive(dest, buf_io)


def solve_room(bundle_dir: Path) -> HarnessResult:
    """Full gate: healthy start → intended-path solve → reset → re-solve."""
    slug = bundle_dir.name
    try:
        with room_environment(bundle_dir) as env:
            env.wait_healthy()
            first = env.run_solver(bundle_dir / "solver" / "solver.py")
            failed = [tid for tid, r in first.items() if not r.get("ok")]
            if failed:
                return HarnessResult(slug, False, f"first pass failed tasks: {failed}")
            env.restart()
            second = env.run_solver(bundle_dir / "solver" / "solver.py")
            failed = [tid for tid, r in second.items() if not r.get("ok")]
            if failed:
                return HarnessResult(slug, False, f"post-reset pass failed tasks: {failed}")
            captured = {tid: r.get("captured") or "" for tid, r in first.items()}
            mismatches = [t for t, f in env.expected_flags.items() if captured.get(t) != f]
            if mismatches:
                return HarnessResult(slug, False, f"flags do not match derivation for {mismatches}")
            return HarnessResult(
                slug, True, "solved on both passes with matching per-session flags"
            )
    except Exception as exc:
        return HarnessResult(slug, False, f"{type(exc).__name__}: {exc}")
