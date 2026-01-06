import pytest
from gateway.app.core.router import Router
from gateway.app.core.registry import NodeRegistry


@pytest.mark.asyncio
async def test_select_node_least_loaded():
    registry = NodeRegistry()
    router = Router(registry)
    await registry.start()

    try:
        await registry.register_node("node1", "http://localhost:8000", 100)
        await registry.register_node("node2", "http://localhost:8001", 50)

        node = await router.select_node()
        assert node is not None
        assert node.node_id == "node1"
        assert node.get_available_capacity() == 100

        await registry.increment_node_load("node1")
        await registry.increment_node_load("node1")

        node = await router.select_node()
        assert node is not None
        assert node.node_id == "node1"
        assert node.get_available_capacity() == 98

        for _ in range(50):
            await registry.increment_node_load("node1")

        node = await router.select_node()
        assert node is not None
        assert node.node_id == "node2"
    finally:
        await registry.stop()


@pytest.mark.asyncio
async def test_select_node_no_healthy():
    registry = NodeRegistry()
    router = Router(registry)
    await registry.start()

    try:
        node = await router.select_node()
        assert node is None

        await registry.register_node("node1", "http://localhost:8000", 100)
        node1 = await registry.get_node("node1")
        assert node1 is not None
        node1.healthy = False

        node = await router.select_node()
        assert node is None
    finally:
        await registry.stop()


@pytest.mark.asyncio
async def test_select_node_deterministic():
    registry = NodeRegistry()
    router = Router(registry)
    await registry.start()

    try:
        await registry.register_node("node1", "http://localhost:8000", 100)
        await registry.register_node("node2", "http://localhost:8001", 100)

        node1 = await router.select_node()
        node2 = await router.select_node()

        assert node1 is not None
        assert node2 is not None
        assert node1.node_id == node2.node_id
    finally:
        await registry.stop()
