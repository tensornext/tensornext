import pytest
import asyncio
from fastapi.testclient import TestClient
from gateway.app.main import app as gateway_app
from gateway.app.core.registry import registry
import httpx
from unittest.mock import AsyncMock, patch


@pytest.fixture
def gateway_client():
    return TestClient(gateway_app)


@pytest.fixture(autouse=True)
async def setup_registry():
    await registry.start()
    yield
    await registry.stop()
    registry._nodes.clear()


@pytest.mark.asyncio
async def test_routing_to_node(gateway_client):
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_response = httpx.Response(
            200,
            json={
                "api_version": "v1",
                "text": "test response",
                "request_id": "test-id",
            },
        )
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        await registry.register_node(
            "node1", "http://localhost:8000", max_capacity=100
        )

        response = gateway_client.post(
            "/infer",
            json={"prompt": "test", "max_tokens": 10, "temperature": 0.7},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["text"] == "test response"
        assert data["request_id"] == "test-id"


@pytest.mark.asyncio
async def test_timeout_handling(gateway_client):
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        await registry.register_node(
            "node1", "http://localhost:8000", max_capacity=100
        )

        response = gateway_client.post(
            "/infer",
            json={"prompt": "test", "max_tokens": 10, "temperature": 0.7},
        )

        assert response.status_code == 504
        assert "timeout" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_node_failure_handling(gateway_client):
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_response = httpx.Response(500, text="Internal Server Error")
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.raise_for_status = AsyncMock(
            side_effect=httpx.HTTPStatusError(
                "Server Error", request=None, response=mock_response
            )
        )
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        await registry.register_node(
            "node1", "http://localhost:8000", max_capacity=100
        )

        response = gateway_client.post(
            "/infer",
            json={"prompt": "test", "max_tokens": 10, "temperature": 0.7},
        )

        assert response.status_code == 500


@pytest.mark.asyncio
async def test_load_balancing(gateway_client):
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_response = httpx.Response(
            200,
            json={
                "api_version": "v1",
                "text": "test",
                "request_id": "test-id",
            },
        )
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        await registry.register_node("node1", "http://localhost:8000", 100)
        await registry.register_node("node2", "http://localhost:8001", 50)

        node1 = await registry.get_node("node1")
        assert node1 is not None

        for _ in range(60):
            await registry.increment_node_load("node1")

        response = gateway_client.post(
            "/infer",
            json={"prompt": "test", "max_tokens": 10, "temperature": 0.7},
        )

        assert response.status_code == 200
        node2 = await registry.get_node("node2")
        assert node2 is not None
        assert node2.current_load > 0
