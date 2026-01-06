from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    app_name: str = "AI Runtime Server"
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"
    model_path: Optional[str] = None
    model_name: Optional[str] = None

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()

