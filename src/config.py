import json
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    anthropic_api_key: str = ""
    host: str = "0.0.0.0"
    port: int = 8000
    database_path: str = "data/agent_memory.db"
    business_context_path: str = "data/business_context.json"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()


def load_business_context() -> dict:
    path = Path(settings.business_context_path)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}
