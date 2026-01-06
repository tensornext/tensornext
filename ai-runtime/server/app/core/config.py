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

    class Config:
        env_file = ".env"
        case_sensitive = False

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        use_mock = os.getenv("USE_MOCK_MODEL", "").lower()
        if use_mock in ("true", "1", "yes"):
            object.__setattr__(self, "use_mock_model", True)


settings = Settings()

