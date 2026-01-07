import pytest
import time
from fastapi.testclient import TestClient
from unittest.mock import patch
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
async def test_rate_limit_enforcement(client, mock_node):
    """Test that rate limiting enforces per-tenant limits."""
    await mock_node()
    
    # Set low rate limit for testing
    with patch.dict(os.environ, {"TENANT_RATE_LIMIT": "5", "API_KEYS": "tenant1:test-key"}):
        from gateway.app.core.config import Settings
        test_settings = Settings()
        
        # Mock successful node response
        from unittest.mock import AsyncMock, patch
        mock_response_data = {
            "api_version": "v1",
            "text": "test",
            "request_id": "test-123",
        }
        
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_response_data
            mock_response.raise_for_status = lambda: None
            mock_post.return_value = mock_response
            
            # Make requests up to limit
            for i in range(test_settings.tenant_rate_limit):
                response = client.post(
                    "/infer",
                    json={"prompt": "test", "max_tokens": 10},
                    headers={"X-API-Key": "test-key"},
                )
                assert response.status_code == 200
            
            # Next request should be rate limited
            response = client.post(
                "/infer",
                json={"prompt": "test", "max_tokens": 10},
                headers={"X-API-Key": "test-key"},
            )
            assert response.status_code == 429
            assert "Rate limit exceeded" in response.json()["detail"]


@pytest.mark.asyncio
async def test_rate_limit_per_tenant(client, mock_node):
    """Test that rate limits are per-tenant."""
    await mock_node()
    
    with patch.dict(os.environ, {"TENANT_RATE_LIMIT": "3", "API_KEYS": "tenant1:key1,tenant2:key2"}):
        from gateway.app.core.config import Settings
        test_settings = Settings()
        
        from unittest.mock import AsyncMock, patch
        mock_response_data = {
            "api_version": "v1",
            "text": "test",
            "request_id": "test-123",
        }
        
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_response_data
            mock_response.raise_for_status = lambda: None
            mock_post.return_value = mock_response
            
            # Exhaust tenant1's limit
            for _ in range(test_settings.tenant_rate_limit):
                response = client.post(
                    "/infer",
                    json={"prompt": "test", "max_tokens": 10},
                    headers={"X-API-Key": "key1"},
                )
                assert response.status_code == 200
            
            # Tenant2 should still be able to make requests
            response = client.post(
                "/infer",
                json={"prompt": "test", "max_tokens": 10},
                headers={"X-API-Key": "key2"},
            )
            assert response.status_code == 200


@pytest.mark.asyncio
async def test_rate_limit_health_endpoint_bypassed(client):
    """Test that health endpoint bypasses rate limiting."""
    response = client.get("/health")
    assert response.status_code == 200
    
    # Make many health requests - should not be rate limited
    for _ in range(100):
        response = client.get("/health")
        assert response.status_code == 200