import json
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    host: str = "0.0.0.0"
    port: int = 8000
    database_path: str = "data/agent_memory.db"
    business_context_path: str = "data/business_context.json"
    obsidian_vault_path: str = ""
    api_token: str = ""  # Auto-gegenereerd als leeg
    # Claude Agent SDK gebruikt Claude Code CLI auth (Max abonnement)
    # Geen API key nodig — zorg dat `claude login` is gedaan

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()


def load_business_context() -> dict:
    path = Path(settings.business_context_path)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}
