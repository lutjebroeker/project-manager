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

    # LLM Provider config — instelbaar, niet meer gebonden aan één provider
    # Opties: "claude_sdk" (default), "anthropic", "openai", "ollama"
    llm_provider: str = "claude_sdk"
    llm_model: str = ""  # Leeg = provider default
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    openai_base_url: str = ""  # Voor OpenRouter, Together, etc.
    ollama_base_url: str = "http://localhost:11434"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()


def load_business_context() -> dict:
    path = Path(settings.business_context_path)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}
