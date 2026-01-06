import pytest
from fastapi.testclient import TestClient
from gateway.app.main import app
from gateway.app.core.registry import registry
import asyncio


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
async def setup_registry():
    await registry.start()
    yield
    await registry.stop()


@pytest.mark.asyncio
async def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_register_node(client):
    response = client.post(
        "/register",
        json={
            "node_id": "test-node",
            "url": "http://localhost:8000",
            "max_capacity": 100,
        },
    )
    assert response.status_code == 200
    assert response.json() == {"status": "registered"}

    node = await registry.get_node("test-node")
    assert node is not None
    assert node.node_id == "test-node"
    assert node.url == "http://localhost:8000"
    assert node.max_capacity == 100


@pytest.mark.asyncio
async def test_heartbeat(client):
    await registry.register_node("test-node", "http://localhost:8000", 100)
    node = await registry.get_node("test-node")
    assert node is not None
    initial_time = node.last_heartbeat

    await asyncio.sleep(0.1)
    response = client.post("/heartbeat/test-node")
    assert response.status_code == 200

    node = await registry.get_node("test-node")
    assert node.last_heartbeat > initial_time


@pytest.mark.asyncio
async def test_heartbeat_not_found(client):
    response = client.post("/heartbeat/nonexistent")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_infer_no_nodes(client):
    response = client.post(
        "/infer",
        json={"prompt": "test", "max_tokens": 10, "temperature": 0.7},
    )
    assert response.status_code == 503
    assert "No inference nodes available" in response.json()["detail"]
