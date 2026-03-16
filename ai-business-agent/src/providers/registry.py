"""Provider registry — selecteer je LLM provider via config.

Configuratie via .env:
    LLM_PROVIDER=anthropic          # anthropic, openai, ollama, claude_sdk
    LLM_MODEL=claude-sonnet-4-6     # model naam (provider-specifiek)
    ANTHROPIC_API_KEY=sk-ant-...    # voor anthropic provider
    OPENAI_API_KEY=sk-...           # voor openai provider
    OPENAI_BASE_URL=                # optioneel, voor OpenRouter/Together/etc.
    OLLAMA_BASE_URL=http://localhost:11434  # voor ollama provider
"""

import os

from src.providers.base import LLMProvider


def get_provider(provider_name: str | None = None) -> LLMProvider:
    """Maak een provider instance op basis van naam of env var.

    Prioriteit:
    1. Expliciete provider_name parameter
    2. LLM_PROVIDER env var
    3. Fallback: claude_sdk (backwards compatible)
    """
    name = provider_name or os.getenv("LLM_PROVIDER", "claude_sdk")
    name = name.lower().strip()

    if name == "anthropic":
        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        if not api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY niet gezet. "
                "Voeg toe aan .env of exporteer als environment variable."
            )
        from src.providers.anthropic_provider import AnthropicProvider
        return AnthropicProvider(api_key=api_key)

    elif name == "openai":
        api_key = os.getenv("OPENAI_API_KEY", "")
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY niet gezet. "
                "Voeg toe aan .env of exporteer als environment variable."
            )
        base_url = os.getenv("OPENAI_BASE_URL") or None
        from src.providers.openai_provider import OpenAIProvider
        return OpenAIProvider(api_key=api_key, base_url=base_url)

    elif name == "ollama":
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        from src.providers.ollama_provider import OllamaProvider
        return OllamaProvider(base_url=base_url)

    elif name == "claude_sdk":
        from src.providers.claude_sdk_provider import ClaudeSDKProvider
        return ClaudeSDKProvider()

    else:
        raise ValueError(
            f"Onbekende LLM provider: '{name}'. "
            f"Kies uit: {', '.join(get_available_providers())}"
        )


def get_available_providers() -> list[str]:
    """Lijst van beschikbare provider namen."""
    return ["anthropic", "openai", "ollama", "claude_sdk"]


def get_default_model(provider_name: str | None = None) -> str:
    """Haal het default model op voor een provider, of uit env."""
    env_model = os.getenv("LLM_MODEL")
    if env_model:
        return env_model

    name = provider_name or os.getenv("LLM_PROVIDER", "claude_sdk")
    defaults = {
        "anthropic": "claude-sonnet-4-6",
        "openai": "gpt-4o",
        "ollama": "llama3.1",
        "claude_sdk": "claude-sonnet-4-6",
    }
    return defaults.get(name, "claude-sonnet-4-6")
