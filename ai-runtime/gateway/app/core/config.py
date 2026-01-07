from pydantic_settings import BaseSettings
from typing import Optional, Dict
import os


class Settings(BaseSettings):
    app_name: str = "AI Runtime Gateway"
    host: str = "0.0.0.0"
    port: int = 8001
    log_level: str = "INFO"
    request_timeout_sec: int = 30
    node_eviction_timeout_sec: int = 10
    heartbeat_interval_sec: int = 5
    
    # Step-4 features
    enable_streaming: bool = False
    api_keys: str = ""
    tenant_rate_limit: int = 100
    gateway_timeout_ms: int = 30000
    max_retries: int = 1

    class Config:
        env_file = ".env"
        case_sensitive = False

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        timeout = os.getenv("REQUEST_TIMEOUT_SEC")
        if timeout:
            object.__setattr__(self, "request_timeout_sec", int(timeout))
        eviction = os.getenv("NODE_EVICTION_TIMEOUT_SEC")
        if eviction:
            object.__setattr__(self, "node_eviction_timeout_sec", int(eviction))
        heartbeat = os.getenv("HEARTBEAT_INTERVAL_SEC")
        if heartbeat:
            object.__setattr__(self, "heartbeat_interval_sec", int(heartbeat))
        
        # Step-4 env vars
        streaming = os.getenv("ENABLE_STREAMING", "").lower()
        if streaming:
            object.__setattr__(self, "enable_streaming", streaming in ("true", "1", "yes"))
        
        api_keys_env = os.getenv("API_KEYS", "")
        if api_keys_env:
            object.__setattr__(self, "api_keys", api_keys_env)
        
        rate_limit = os.getenv("TENANT_RATE_LIMIT")
        if rate_limit:
            object.__setattr__(self, "tenant_rate_limit", int(rate_limit))
        
        gateway_timeout = os.getenv("GATEWAY_TIMEOUT_MS")
        if gateway_timeout:
            object.__setattr__(self, "gateway_timeout_ms", int(gateway_timeout))
        
        retries = os.getenv("MAX_RETRIES")
        if retries:
            object.__setattr__(self, "max_retries", int(retries))
    
    def get_api_key_map(self) -> Dict[str, str]:
        """Parse API_KEYS env var into tenant_id -> api_key mapping."""
        if not self.api_keys:
            return {}
        result: Dict[str, str] = {}
        for pair in self.api_keys.split(","):
            pair = pair.strip()
            if ":" in pair:
                tenant_id, api_key = pair.split(":", 1)
                result[api_key.strip()] = tenant_id.strip()
        return result


settings = Settings()
