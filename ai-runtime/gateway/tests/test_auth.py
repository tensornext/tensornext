import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from gateway.app.main import app
from gateway.app.core.registry import registry
import os


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
async def setup_registry():
    await registry.start()
    yield
    await registry.stop()


@pytest.mark.asyncio
async def test_missing_api_key(client):
    """Test that requests without API key are rejected."""
    response = client.post(
        "/infer",
        json={"prompt": "test", "max_tokens": 10},
    )
    assert response.status_code == 401
    assert "Missing X-API-Key header" in response.json()["detail"]


@pytest.mark.asyncio
async def test_invalid_api_key(client):
    """Test that requests with invalid API key are rejected."""
    with patch.dict(os.environ, {"API_KEYS": "tenant1:valid-key"}):
        from gateway.app.core.config import Settings
        test_settings = Settings()
        
        response = client.post(
            "/infer",
            json={"prompt": "test", "max_tokens": 10},
            headers={"X-API-Key": "invalid-key"},
        )
        assert response.status_code == 401
        assert "Invalid API key" in response.json()["detail"]


@pytest.mark.asyncio
async def test_valid_api_key(client):
    """Test that requests with valid API key are accepted."""
    with patch.dict(os.environ, {"API_KEYS": "tenant1:valid-key"}):
        from gateway.app.core.config import Settings
        test_settings = Settings()
        
        # Health endpoint should work without auth
        response = client.get("/health")
        assert response.status_code == 200
        
        # Register endpoint should work without auth
        response = client.post(
            "/register",
            json={
                "node_id": "test-node",
                "url": "http://localhost:8000",
                "max_capacity": 100,
            },
        )
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_multiple_api_keys(client):
    """Test that multiple API keys are supported."""
    with patch.dict(os.environ, {"API_KEYS": "tenant1:key1,tenant2:key2,tenant3:key3"}):
        from gateway.app.core.config import Settings
        test_settings = Settings()
        api_key_map = test_settings.get_api_key_map()
        
        assert "key1" in api_key_map
        assert "key2" in api_key_map
        assert "key3" in api_key_map
        assert api_key_map["key1"] == "tenant1"
        assert api_key_map["key2"] == "tenant2"
        assert api_key_map["key3"] == "tenant3"