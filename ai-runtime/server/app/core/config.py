from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    app_name: str = "AI Runtime Server"
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"
    model_path: Optional[str] = None
    model_name: Optional[str] = None
    use_mock_model: bool = False
    max_concurrent_requests: int = 2
    batch_max_size: int = 8
    batch_max_latency_ms: int = 50
    max_in_flight_requests: int = 100
    gateway_url: Optional[str] = None
    node_id: Optional[str] = None
    heartbeat_interval_sec: int = 5
    node_max_capacity: int = 100

    class Config:
        env_file = ".env"
        case_sensitive = False

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        use_mock = os.getenv("USE_MOCK_MODEL", "").lower()
        if use_mock in ("true", "1", "yes"):
            object.__setattr__(self, "use_mock_model", True)
        batch_size = os.getenv("BATCH_MAX_SIZE")
        if batch_size:
            object.__setattr__(self, "batch_max_size", int(batch_size))
        batch_latency = os.getenv("BATCH_MAX_LATENCY_MS")
        if batch_latency:
            object.__setattr__(self, "batch_max_latency_ms", int(batch_latency))
        max_in_flight = os.getenv("MAX_IN_FLIGHT_REQUESTS")
        if max_in_flight:
            object.__setattr__(self, "max_in_flight_requests", int(max_in_flight))
        gateway_url = os.getenv("GATEWAY_URL")
        if gateway_url:
            object.__setattr__(self, "gateway_url", gateway_url)
        node_id = os.getenv("NODE_ID")
        if node_id:
            object.__setattr__(self, "node_id", node_id)
        heartbeat = os.getenv("HEARTBEAT_INTERVAL_SEC")
        if heartbeat:
            object.__setattr__(self, "heartbeat_interval_sec", int(heartbeat))
        capacity = os.getenv("NODE_MAX_CAPACITY")
        if capacity:
            object.__setattr__(self, "node_max_capacity", int(capacity))


settings = Settings()

