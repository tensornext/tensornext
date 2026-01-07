import pytest
import asyncio
import time
from gateway.app.core.registry import NodeRegistry, NodeInfo


@pytest.mark.asyncio
async def test_register_node():
    registry = NodeRegistry()
    await registry.start()

    try:
        await registry.register_node("node1", "http://localhost:8000", 100)
        node = await registry.get_node("node1")
        assert node is not None
        assert node.node_id == "node1"
        assert node.url == "http://localhost:8000"
        assert node.max_capacity == 100
        assert node.healthy is True
    finally:
        await registry.stop()


@pytest.mark.asyncio
async def test_heartbeat_update():
    registry = NodeRegistry()
    await registry.start()

    try:
        await registry.register_node("node1", "http://localhost:8000", 100)
        node1 = await registry.get_node("node1")
        assert node1 is not None
        initial_time = node1.last_heartbeat

        await asyncio.sleep(0.1)
        updated = await registry.update_heartbeat("node1")
        assert updated is not None
        assert updated.last_heartbeat > initial_time
    finally:
        await registry.stop()


@pytest.mark.asyncio
async def test_get_healthy_nodes():
    registry = NodeRegistry()
    await registry.start()

    try:
        await registry.register_node("node1", "http://localhost:8000", 100)
        await registry.register_node("node2", "http://localhost:8001", 50)

        healthy = await registry.get_healthy_nodes()
        assert len(healthy) == 2

        node1 = await registry.get_node("node1")
        assert node1 is not None
        node1.healthy = False

        healthy = await registry.get_healthy_nodes()
        assert len(healthy) == 1
        assert healthy[0].node_id == "node2"
    finally:
        await registry.stop()


@pytest.mark.asyncio
async def test_load_tracking():
    registry = NodeRegistry()
    await registry.start()

    try:
        await registry.register_node("node1", "http://localhost:8000", 100)
        node = await registry.get_node("node1")
        assert node is not None
        assert node.current_load == 0
        assert node.get_available_capacity() == 100

        await registry.increment_node_load("node1")
        node = await registry.get_node("node1")
        assert node.current_load == 1
        assert node.get_available_capacity() == 99

        await registry.decrement_node_load("node1")
        node = await registry.get_node("node1")
        assert node.current_load == 0
        assert node.get_available_capacity() == 100
    finally:
        await registry.stop()


@pytest.mark.asyncio
async def test_node_eviction(monkeypatch):
    registry = NodeRegistry()
    from gateway.app.core import config
    original_timeout = config.settings.node_eviction_timeout_sec
    monkeypatch.setattr(config.settings, "node_eviction_timeout_sec", 0.5)
    await registry.start()

    try:
        await registry.register_node("node1", "http://localhost:8000", 100)
        node = await registry.get_node("node1")
        assert node is not None

        await asyncio.sleep(0.6)
        await registry._evict_stale_nodes()

        node = await registry.get_node("node1")
        assert node is not None
        assert node.healthy is False

        node.last_heartbeat = time.time() - 1.5
        await registry._evict_stale_nodes()

        node = await registry.get_node("node1")
        assert node is None
        monkeypatch.setattr(config.settings, "node_eviction_timeout_sec", original_timeout)
    finally:
        await registry.stop()
