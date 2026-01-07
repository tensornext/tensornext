import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from gateway.app.main import app
from gateway.app.core.registry import registry
from gateway.app.core.circuit_breaker import circuit_breaker
import os


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
async def setup_registry():
    await registry.start()
    yield
    await registry.stop()
    circuit_breaker._circuits.clear()


@pytest.fixture
def mock_node():
    """Register a mock node for testing."""
    async def _register():
        await registry.register_node("test-node", "http://localhost:8000", 100)
    return _register


@pytest.mark.asyncio
async def test_circuit_breaker_opens_on_failures(client, mock_node):
    """Test that circuit breaker opens after threshold failures."""
    await mock_node()
    
    with patch.dict(os.environ, {"API_KEYS": "tenant1:test-key"}):
        from gateway.app.core.config import Settings
        test_settings = Settings()
        
        # Simulate failures
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_post.side_effect = Exception("Connection error")
            
            # Make requests that will fail
            failure_threshold = 5
            for i in range(failure_threshold):
                try:
                    response = client.post(
                        "/infer",
                        json={"prompt": "test", "max_tokens": 10},
                        headers={"X-API-Key": "test-key"},
                    )
                except:
                    pass
            
            # Circuit breaker should be open
            assert not circuit_breaker.is_available("test-node")


@pytest.mark.asyncio
async def test_retry_on_node_failure(client, mock_node):
    """Test that gateway retries on node failure."""
    await mock_node()
    await registry.register_node("test-node-2", "http://localhost:8001", 100)
    
    with patch.dict(os.environ, {"API_KEYS": "tenant1:test-key", "MAX_RETRIES": "1"}):
        from gateway.app.core.config import Settings
        test_settings = Settings()
        
        call_count = 0
        
        def mock_post_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First call fails
                raise Exception("Node error")
            # Second call succeeds
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "api_version": "v1",
                "text": "success",
                "request_id": "test-123",
            }
            mock_response.raise_for_status = lambda: None
            return mock_response
        
        with patch("httpx.AsyncClient.post", side_effect=mock_post_side_effect):
            response = client.post(
                "/infer",
                json={"prompt": "test", "max_tokens": 10},
                headers={"X-API-Key": "test-key"},
            )
            # Should succeed after retry
            assert response.status_code == 200
            assert call_count == 2


@pytest.mark.asyncio
async def test_timeout_handling(client, mock_node):
    """Test that timeouts are handled correctly."""
    await mock_node()
    
    with patch.dict(os.environ, {"API_KEYS": "tenant1:test-key", "GATEWAY_TIMEOUT_MS": "1000"}):
        from gateway.app.core.config import Settings
        test_settings = Settings()
        
        import httpx
        
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_post.side_effect = httpx.TimeoutException("Request timeout")
            
            response = client.post(
                "/infer",
                json={"prompt": "test", "max_tokens": 10},
                headers={"X-API-Key": "test-key"},
            )
            assert response.status_code == 504
            assert "timeout" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_circuit_breaker_recovery(client, mock_node):
    """Test that circuit breaker recovers after timeout."""
    await mock_node()
    
    # Open circuit breaker
    for _ in range(5):
        circuit_breaker.record_failure("test-node")
    
    assert not circuit_breaker.is_available("test-node")
    
    # Record success should close it
    circuit_breaker.record_success("test-node")
    assert circuit_breaker.is_available("test-node")