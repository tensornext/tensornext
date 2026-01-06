import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from server.app.core.registry_client import RegistryClient
from server.app.core.config import settings


@pytest.mark.asyncio
async def test_register_success():
    client = RegistryClient()
    client._gateway_url = "http://localhost:8001"
    client._node_id = "test-node"
    client._node_url = "http://localhost:8000"

    with patch("httpx.AsyncClient") as mock_client:
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=mock_response
        )

        result = await client.register()
        assert result is True


@pytest.mark.asyncio
async def test_register_missing_config():
    client = RegistryClient()
    client._gateway_url = None
    client._node_id = None
    client._node_url = None

    result = await client.register()
    assert result is False


@pytest.mark.asyncio
async def test_heartbeat_loop():
    client = RegistryClient()
    client._gateway_url = "http://localhost:8001"
    client._node_id = "test-node"
    client._running = True

    with patch("httpx.AsyncClient") as mock_client:
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=mock_response
        )

        task = asyncio.create_task(client._heartbeat_loop())
        await asyncio.sleep(0.1)
        client._running = False
        task.cancel()

        try:
            await task
        except asyncio.CancelledError:
            pass


@pytest.mark.asyncio
async def test_start_stop_heartbeat():
    client = RegistryClient()
    client._gateway_url = "http://localhost:8001"
    client._node_id = "test-node"

    with patch("httpx.AsyncClient") as mock_client:
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=mock_response
        )

        await client.start_heartbeat()
        assert client._heartbeat_task is not None

        await client.stop_heartbeat()
        assert client._heartbeat_task is None
