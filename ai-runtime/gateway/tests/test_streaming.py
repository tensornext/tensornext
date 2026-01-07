import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
import json
from gateway.app.main import app
from gateway.app.core.registry import registry
from gateway.app.core.config import settings
import os


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
async def setup_registry():
    await registry.start()
    yield
    await registry.stop()


@pytest.fixture
def mock_node():
    """Register a mock node for testing."""
    async def _register():
        await registry.register_node("test-node", "http://localhost:8000", 100)
    return _register


@pytest.mark.asyncio
async def test_streaming_disabled_by_default(client, mock_node):
    """Test that streaming endpoint returns 503 when not enabled."""
    await mock_node()
    
    with patch.dict(os.environ, {"ENABLE_STREAMING": "false"}):
        # Reload settings
        from gateway.app.core.config import Settings
        test_settings = Settings()
        if not test_settings.enable_streaming:
            response = client.post(
                "/infer/stream",
                json={"prompt": "test", "max_tokens": 10},
                headers={"X-API-Key": "test-key"},
            )
            assert response.status_code == 503
            assert "Streaming is not enabled" in response.json()["detail"]


@pytest.mark.asyncio
async def test_streaming_with_mock_node(client, mock_node):
    """Test streaming endpoint with mocked node response."""
    await mock_node()
    
    # Mock httpx response for streaming
    mock_response_data = {
        "api_version": "v1",
        "text": "test response",
        "request_id": "test-123",
    }
    
    async def mock_stream():
        sse_data = json.dumps(mock_response_data)
        yield f"data: {sse_data}\n\n".encode()
        yield "data: [DONE]\n\n".encode()
    
    with patch.dict(os.environ, {"ENABLE_STREAMING": "true", "API_KEYS": "tenant1:test-key"}):
        from gateway.app.core.config import Settings
        test_settings = Settings()
        
        if test_settings.enable_streaming:
            with patch("httpx.AsyncClient.post") as mock_post:
                mock_response = AsyncMock()
                mock_response.status_code = 200
                mock_response.headers = {"content-type": "text/event-stream"}
                mock_response.aiter_bytes = mock_stream
                mock_response.raise_for_status = lambda: None
                mock_post.return_value = mock_response
                
                response = client.post(
                    "/infer/stream",
                    json={"prompt": "test", "max_tokens": 10},
                    headers={"X-API-Key": "test-key"},
                )
                
                assert response.status_code == 200
                assert response.headers["content-type"] == "text/event-stream"


@pytest.mark.asyncio
async def test_non_streaming_unchanged(client, mock_node):
    """Test that non-streaming endpoint remains unchanged."""
    await mock_node()
    
    mock_response_data = {
        "api_version": "v1",
        "text": "test response",
        "request_id": "test-123",
    }
    
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = lambda: None
        mock_post.return_value = mock_response
        
        response = client.post(
            "/infer",
            json={"prompt": "test", "max_tokens": 10},
            headers={"X-API-Key": "test-key"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["text"] == "test response"
        assert data["api_version"] == "v1"