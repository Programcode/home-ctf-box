"""Docker lifecycle operations for lab instances.

The runner is the only OpenRange component allowed to touch the Docker
socket; everything here is scoped to objects carrying openrange.* labels.
"""

from __future__ import annotations

import base64
import binascii
import io
import tarfile
import tempfile
import time
from datetime import UTC, datetime
from typing import Any, cast

import docker
from docker.errors import BuildError, DockerException, ImageNotFound, NotFound
from docker.models.containers import Container
from docker.models.networks import Network
from openrange.runner.models import (
    CreateInstanceRequest,
    CreateInstanceResponse,
    GetInstanceResponse,
    InstanceTarget,
    ReconcileResponse,
    RestartInstanceResponse,
)
from openrange.runner.problems import RunnerError

MANAGED_LABEL = "openrange.managed"
INSTANCE_LABEL = "openrange.instance.id"
CREATED_AT_LABEL = "openrange.created-at"
TARGET_PORT_LABEL = "openrange.target.port"

HEALTHCHECK_TIMEOUT_SECONDS = 30.0
HEALTHCHECK_INTERVAL_SECONDS = 0.5
STOP_TIMEOUT_SECONDS = 10


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _labels(obj: Any) -> dict[str, str]:
    return {str(key): str(value) for key, value in dict(obj).items()}


def _probe_command(port: int) -> list[str]:
    return [
        "python3",
        "-c",
        f"import urllib.request;urllib.request.urlopen("
        f"'http://127.0.0.1:{port}/healthz', timeout=2)",
    ]


class LabDocker:
    """Owns every Docker interaction for lab instances."""

    def __init__(self) -> None:
        self._client: docker.DockerClient | None = None

    @property
    def client(self) -> docker.DockerClient:
        if self._client is None:
            self._client = docker.from_env()
        return self._client

    def ping(self) -> bool:
        try:
            self.client.ping()
        except DockerException:
            return False
        return True

    # ------------------------------------------------------------------ create

    def create_instance(self, request: CreateInstanceRequest) -> CreateInstanceResponse:
        instance_id = request.instance_id
        network_name = f"lab-{instance_id}"
        base_labels = {
            MANAGED_LABEL: "true",
            INSTANCE_LABEL: instance_id,
            CREATED_AT_LABEL: _now_iso(),
        }
        self.client.networks.create(
            network_name, driver="bridge", internal=True, labels=base_labels
        )
        built_image = False
        image_ref: str | None = request.image
        try:
            context = request.build_context_tar_gz_base64
            if context is not None:
                image_ref = self._build_image(instance_id, context)
                built_image = True
            elif image_ref is not None:
                self._ensure_image(image_ref)
            else:  # unreachable: CreateInstanceRequest enforces exactly one source
                raise RunnerError(500, "Internal Server Error", "no image source resolved")
            container = self.client.containers.create(
                image=image_ref,
                name=f"lab-{instance_id}",
                detach=True,
                environment=request.env,
                nano_cpus=int(request.cpus * 1_000_000_000),
                mem_limit=request.mem_mb * 1024 * 1024,
                pids_limit=request.pids_limit,
                cap_drop=["ALL"],
                security_opt=["no-new-privileges:true"],
                network=network_name,
                labels=base_labels | request.labels | {TARGET_PORT_LABEL: str(request.ports[0])},
            )
        except RunnerError:
            self._cleanup_partial(instance_id, remove_container=False, remove_image=built_image)
            raise
        except (DockerException, OSError) as exc:
            self._cleanup_partial(instance_id, remove_container=False, remove_image=built_image)
            raise RunnerError(
                502, "Lab runtime error", f"failed to create instance {instance_id}: {exc}"
            ) from exc
        try:
            container.start()
            self._wait_healthy(container, request.ports[0])
        except RunnerError:
            self._cleanup_partial(instance_id, remove_container=True, remove_image=built_image)
            raise
        except (DockerException, OSError) as exc:
            self._cleanup_partial(instance_id, remove_container=True, remove_image=built_image)
            raise RunnerError(
                502, "Lab runtime error", f"instance {instance_id} failed during startup: {exc}"
            ) from exc
        return _creation_response(instance_id, request.ports)

    def _build_image(self, instance_id: str, context_base64: str) -> str:
        tag = f"openrange/lab-{instance_id}:latest"
        try:
            raw_context = base64.b64decode(context_base64, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise RunnerError(400, "Invalid build context", "payload is not valid base64") from exc
        with tempfile.TemporaryDirectory(prefix="openrange-build-") as tmp_dir:
            try:
                with tarfile.open(fileobj=io.BytesIO(raw_context), mode="r:gz") as archive:
                    archive.extractall(tmp_dir, filter="data")
            except (tarfile.TarError, EOFError) as exc:
                raise RunnerError(
                    400, "Invalid build context", "payload is not a valid tar.gz archive"
                ) from exc
            try:
                self.client.images.build(
                    path=tmp_dir,
                    tag=tag,
                    rm=True,
                    labels={
                        MANAGED_LABEL: "true",
                        INSTANCE_LABEL: instance_id,
                        CREATED_AT_LABEL: _now_iso(),
                    },
                )
            except BuildError as exc:
                reason = getattr(exc, "msg", None) or "docker build failed"
                raise RunnerError(400, "Image build failed", str(reason)) from exc
            except DockerException as exc:
                raise RunnerError(502, "Lab runtime error", f"docker build failed: {exc}") from exc
        return tag

    def _ensure_image(self, image_ref: str) -> None:
        try:
            self.client.images.get(image_ref)
            return
        except ImageNotFound:
            pass
        try:
            self.client.images.pull(image_ref)
        except ImageNotFound as exc:
            raise RunnerError(
                400, "Image not found", f"{image_ref} does not exist in the registry"
            ) from exc
        except DockerException as exc:
            raise RunnerError(
                502, "Lab runtime error", f"failed to pull {image_ref}: {exc}"
            ) from exc

    def _wait_healthy(self, container: Container, port: int) -> None:
        deadline = time.monotonic() + HEALTHCHECK_TIMEOUT_SECONDS
        command = _probe_command(port)
        while True:
            container.reload()
            status = cast("str", container.status)
            if status != "running":
                raise RunnerError(
                    502,
                    "Instance failed to become ready",
                    f"container exited before healthcheck passed (status={status})",
                )
            result = container.exec_run(command)
            if cast("int | None", result.exit_code) == 0:
                return
            if time.monotonic() >= deadline:
                raise RunnerError(
                    502,
                    "Instance failed to become ready",
                    f"healthcheck on port {port} did not pass within "
                    f"{int(HEALTHCHECK_TIMEOUT_SECONDS)}s",
                )
            time.sleep(HEALTHCHECK_INTERVAL_SECONDS)

    # -------------------------------------------------------------- read state

    def get_instance(self, instance_id: str) -> GetInstanceResponse:
        containers = self._containers_for(instance_id)
        if not containers:
            return GetInstanceResponse(state="missing")
        container = containers[0]
        container.reload()
        status = cast("str", container.status)
        attrs = cast("dict[str, Any]", container.attrs)
        started_at_raw = cast("Any", attrs.get("State", {})).get("StartedAt")
        if status == "running":
            port = self._target_port(container)
            healthy = port is not None and self._probe_once(container, port)
            state = "ready" if healthy else "starting"
        elif status in {"exited", "dead"}:
            state = "stopped"
        else:
            state = "starting"
        return GetInstanceResponse(
            state=state,  # type: ignore[arg-type]
            started_at=cast("str | None", started_at_raw),
            labels=_labels(container.labels),
        )

    def _target_port(self, container: Container) -> int | None:
        labels = _labels(container.labels)
        labeled = labels.get(TARGET_PORT_LABEL)
        if labeled is not None:
            try:
                return int(labeled)
            except ValueError:
                pass
        attrs = cast("dict[str, Any]", container.attrs)
        exposed = cast("dict[str, Any]", attrs.get("Config", {}).get("ExposedPorts", {}) or {})
        ports = [key.split("/")[0] for key in exposed]
        if len(ports) == 1:
            try:
                return int(ports[0])
            except ValueError:
                return None
        return None

    def _probe_once(self, container: Container, port: int) -> bool:
        try:
            result = container.exec_run(_probe_command(port))
        except (DockerException, OSError):
            return False
        return cast("int | None", result.exit_code) == 0

    # ----------------------------------------------------------------- restart

    def restart_instance(self, instance_id: str) -> RestartInstanceResponse:
        containers = self._containers_for(instance_id)
        if not containers:
            raise RunnerError(404, "Not Found", f"no such instance: {instance_id}")
        container = containers[0]
        try:
            container.restart(timeout=STOP_TIMEOUT_SECONDS)
        except (DockerException, OSError) as exc:
            raise RunnerError(
                502, "Lab runtime error", f"failed to restart {instance_id}: {exc}"
            ) from exc
        port = self._target_port(container)
        if port is not None:
            self._wait_healthy(container, port)
        return RestartInstanceResponse(state="ready")

    # ------------------------------------------------------------------ delete

    def delete_instance(self, instance_id: str) -> None:
        for container in self._containers_for(instance_id):
            try:
                container.stop(timeout=STOP_TIMEOUT_SECONDS)
            except (NotFound, DockerException, OSError):
                pass
            try:
                container.remove(force=True)
            except NotFound:
                pass
            except (DockerException, OSError) as exc:
                raise RunnerError(
                    502, "Lab runtime error", f"failed to remove container for {instance_id}: {exc}"
                ) from exc
        for network in self._networks_for(instance_id):
            try:
                network.remove()
            except NotFound:
                pass
            except (DockerException, OSError) as exc:
                raise RunnerError(
                    502, "Lab runtime error", f"failed to remove network for {instance_id}: {exc}"
                ) from exc
        self._remove_built_image(instance_id)

    def _remove_built_image(self, instance_id: str) -> None:
        ref = f"openrange/lab-{instance_id}:latest"
        try:
            image = self.client.images.get(ref)
        except (ImageNotFound, NotFound):
            return
        if _labels(image.labels).get(INSTANCE_LABEL) == instance_id:
            try:
                self.client.images.remove(ref, force=True)
            except (ImageNotFound, NotFound):
                pass

    def _cleanup_partial(
        self, instance_id: str, *, remove_container: bool, remove_image: bool
    ) -> None:
        """Best-effort removal after a failed create; never masks the original error."""
        if remove_container:
            for container in self._containers_for(instance_id):
                try:
                    container.remove(force=True)
                except (NotFound, DockerException, OSError):
                    pass
        for network in self._networks_for(instance_id):
            try:
                network.remove()
            except (NotFound, DockerException, OSError):
                pass
        if remove_image:
            self._remove_built_image(instance_id)

    # --------------------------------------------------------------- reconcile

    def reconcile(self, known_instance_ids: list[str]) -> ReconcileResponse:
        known = set(known_instance_ids)
        removed_containers: list[str] = []
        removed_networks: list[str] = []
        managed = f"{MANAGED_LABEL}=true"
        for container in self.client.containers.list(all=True, filters={"label": managed}):
            if _labels(container.labels).get(INSTANCE_LABEL) not in known:
                name = cast("str", container.name)
                container.remove(force=True)
                removed_containers.append(name)
        for network in self.client.networks.list(filters={"label": managed}):
            network_labels = _labels(cast("dict[str, Any]", network.attrs).get("Labels"))
            if network_labels.get(INSTANCE_LABEL) not in known:
                name = cast("str", network.name)
                network.remove()
                removed_networks.append(name)
        return ReconcileResponse(
            removed_containers=removed_containers, removed_networks=removed_networks
        )

    # ----------------------------------------------------------------- lookups

    def _containers_for(self, instance_id: str) -> list[Container]:
        return cast(
            "list[Container]",
            self.client.containers.list(
                all=True, filters={"label": f"{INSTANCE_LABEL}={instance_id}"}
            ),
        )

    def _networks_for(self, instance_id: str) -> list[Network]:
        return cast(
            "list[Network]",
            self.client.networks.list(filters={"label": f"{INSTANCE_LABEL}={instance_id}"}),
        )


def _creation_response(instance_id: str, ports: list[int]) -> CreateInstanceResponse:
    network_name = f"lab-{instance_id}"
    targets = [
        InstanceTarget(
            name="target" if index == 0 else f"target-{index}",
            url=f"tcp://{network_name}:{port}",
        )
        for index, port in enumerate(ports)
    ]
    return CreateInstanceResponse(state="ready", network=network_name, targets=targets)
