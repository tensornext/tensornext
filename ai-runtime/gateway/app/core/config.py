from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    app_name: str = "AI Runtime Gateway"
    host: str = "0.0.0.0"
    port: int = 8001
    log_level: str = "INFO"
    request_timeout_sec: int = 30
    node_eviction_timeout_sec: int = 10
    heartbeat_interval_sec: int = 5

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


settings = Settings()
