"""Reconcile removes managed orphans, keeps known instances and bystanders."""

from __future__ import annotations

import uuid
from collections.abc import Callable, Coroutine
from datetime import UTC, datetime
from typing import Any

import docker
import pytest
from docker.errors import NotFound

pytestmark = pytest.mark.integration

CreateInstanceFactory = Callable[..., Coroutine[Any, Any, tuple[str, dict[str, Any]]]]


def _labels(instance_id: str) -> dict[str, str]:
    return {
        "openrange.managed": "true",
        "openrange.instance.id": instance_id,
        "openrange.created-at": datetime.now(UTC).isoformat(),
    }


async def test_reconcile_removes_orphans_keeps_known(
    create_instance: CreateInstanceFactory,
    runner_client,
    docker_client: docker.DockerClient,
    lab_image: str,
) -> None:
    instance_id, _body = await create_instance()

    orphan_net_id = str(uuid.uuid4())
    orphan_net = docker_client.networks.create(
        f"lab-orphan-net-{orphan_net_id[:8]}",
        driver="bridge",
        internal=True,
        labels=_labels(orphan_net_id),
    )
    orphan_ctr_name = f"lab-orphan-ctr-{orphan_net_id[:8]}"
    docker_client.containers.create(
        lab_image,
        name=orphan_ctr_name,
        detach=True,
        network=orphan_net.name,
        labels=_labels(str(uuid.uuid4())),
    )

    bystander = docker_client.networks.create(f"bystander-{uuid.uuid4().hex[:8]}", driver="bridge")
    try:
        response = await runner_client.request(
            "POST", "/v1/reconcile", {"known_instance_ids": [instance_id]}
        )
    finally:
        bystander.remove()

    assert response.status_code == 200
    removed = response.json()
    assert orphan_ctr_name in removed["removed_containers"]
    assert orphan_net.name in removed["removed_networks"]

    known_container = docker_client.containers.get(f"lab-{instance_id}")
    assert known_container.status == "running"
    assert docker_client.networks.get(f"lab-{instance_id}")

    with pytest.raises(NotFound):
        docker_client.containers.get(orphan_ctr_name)
    assert orphan_net.name is not None
    with pytest.raises(NotFound):
        docker_client.networks.get(orphan_net.name)


async def test_reconcile_with_empty_known_set_clears_managed_objects(
    runner_client,
    docker_client: docker.DockerClient,
    lab_image: str,
) -> None:
    orphan_net = docker_client.networks.create(
        f"lab-sweep-{uuid.uuid4().hex[:8]}",
        driver="bridge",
        labels=_labels(str(uuid.uuid4())),
    )
    orphan_name = f"lab-sweep-ctr-{uuid.uuid4().hex[:8]}"
    docker_client.containers.create(
        lab_image, name=orphan_name, detach=True, labels=_labels(str(uuid.uuid4()))
    )

    response = await runner_client.request("POST", "/v1/reconcile", {"known_instance_ids": []})

    assert response.status_code == 200
    removed = response.json()
    assert orphan_name in removed["removed_containers"]
    assert orphan_net.name in removed["removed_networks"]
