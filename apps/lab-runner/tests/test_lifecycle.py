"""Instance lifecycle: create, inspect, restart, delete, build-context path."""

from __future__ import annotations

import base64
import io
import tarfile
import uuid
from collections.abc import Callable, Coroutine
from typing import Any

import docker
import pytest
from docker.errors import ImageNotFound, NotFound

pytestmark = pytest.mark.integration

CreateInstanceFactory = Callable[..., Coroutine[Any, Any, tuple[str, dict[str, Any]]]]

PROBE = [
    "python3",
    "-c",
    "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8000/healthz')",
]


def _assert_hardening(container: Any) -> None:
    host_config = container.attrs["HostConfig"]
    assert host_config["CapDrop"] == ["ALL"]
    assert host_config["SecurityOpt"] == ["no-new-privileges:true"]
    assert host_config["NanoCpus"] == 500_000_000
    assert host_config["Memory"] == 256 * 1024 * 1024
    assert host_config["PidsLimit"] == 128
    assert host_config["PortBindings"] == {}
    assert host_config["AutoRemove"] is False
    labels = container.labels
    assert labels["openrange.managed"] == "true"
    assert labels["openrange.instance.id"]
    assert labels["openrange.created-at"]
    assert labels["room"] == "integration"


async def test_create_ready_and_probe(
    create_instance: CreateInstanceFactory,
    docker_client: docker.DockerClient,
) -> None:
    instance_id, body = await create_instance()
    assert body["state"] == "ready"
    network_name = f"lab-{instance_id}"
    assert body["network"] == network_name
    assert body["targets"] == [{"name": "target", "url": f"tcp://{network_name}:8000"}]

    container = docker_client.containers.get(f"lab-{instance_id}")
    _assert_hardening(container)
    network = docker_client.networks.get(network_name)
    assert network.attrs["Internal"] is True
    assert network.attrs["Driver"] == "bridge"

    exit_code, _output = container.exec_run(PROBE)
    assert exit_code == 0


async def test_get_instance_reports_ready(
    create_instance: CreateInstanceFactory,
    runner_client,
) -> None:
    instance_id, _body = await create_instance()
    response = await runner_client.request("GET", f"/v1/instances/{instance_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "ready"
    assert body["started_at"]
    assert body["labels"]["openrange.instance.id"] == instance_id
    assert body["labels"]["openrange.managed"] == "true"


async def test_get_unknown_instance_reports_missing(runner_client) -> None:
    response = await runner_client.request("GET", f"/v1/instances/{uuid.uuid4()}")
    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "missing"
    assert body["started_at"] is None
    assert body["labels"] == {}


async def test_restart_resets_container(
    create_instance: CreateInstanceFactory,
    runner_client,
    docker_client: docker.DockerClient,
) -> None:
    instance_id, _body = await create_instance()
    name = f"lab-{instance_id}"
    before = docker_client.containers.get(name).attrs["State"]["StartedAt"]

    response = await runner_client.request("POST", f"/v1/instances/{instance_id}/restart")
    assert response.status_code == 200
    assert response.json() == {"state": "ready"}

    container = docker_client.containers.get(name)
    assert container.attrs["State"]["StartedAt"] > before
    exit_code, _output = container.exec_run(PROBE)
    assert exit_code == 0


async def test_restart_unknown_instance_is_404_problem(runner_client) -> None:
    response = await runner_client.request("POST", f"/v1/instances/{uuid.uuid4()}/restart")
    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/problem+json")


async def test_delete_is_idempotent_and_cleans_up(
    create_instance: CreateInstanceFactory,
    runner_client,
    docker_client: docker.DockerClient,
) -> None:
    instance_id, _body = await create_instance()

    first = await runner_client.request("DELETE", f"/v1/instances/{instance_id}")
    second = await runner_client.request("DELETE", f"/v1/instances/{instance_id}")
    assert first.status_code == 204
    assert second.status_code == 204

    with pytest.raises(NotFound):
        docker_client.containers.get(f"lab-{instance_id}")
    remaining = docker_client.networks.list(
        filters={"label": f"openrange.instance.id={instance_id}"}
    )
    assert remaining == []


async def test_create_from_build_context(
    make_payload,
    runner_client,
    docker_client: docker.DockerClient,
) -> None:
    payload = make_payload(image=None, build_context_tar_gz_base64=_context_archive())
    response = await runner_client.request("POST", "/v1/instances", payload)
    assert response.status_code == 201, response.text
    instance_id = payload["instance_id"]

    tag = f"openrange/lab-{instance_id}:latest"
    image = docker_client.images.get(tag)
    assert image.labels["openrange.instance.id"] == instance_id

    delete = await runner_client.request("DELETE", f"/v1/instances/{instance_id}")
    assert delete.status_code == 204
    with pytest.raises(ImageNotFound):
        docker_client.images.get(tag)


def _context_archive() -> str:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        app_py = (
            b"from flask import Flask\n"
            b"app = Flask(__name__)\n"
            b"@app.get('/healthz')\n"
            b"def healthz():\n"
            b"    return 'ok'\n"
            b"if __name__ == '__main__':\n"
            b"    app.run(host='0.0.0.0', port=8000)\n"
        )
        for name, data in (
            ("app.py", app_py),
            (
                "Dockerfile",
                b"FROM python:3.12-alpine\n"
                b"RUN pip install --no-cache-dir 'flask>=3,<4'\n"
                b"COPY app.py /srv/app.py\n"
                b'CMD ["python3", "/srv/app.py"]\n',
            ),
        ):
            info = tarfile.TarInfo(name=name)
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))
    return base64.b64encode(buffer.getvalue()).decode()
