"""Base LLM provider interface — alle providers implementeren dit."""

from dataclasses import dataclass, field


@dataclass
class LLMResponse:
    """Gestandaardiseerd antwoord van elke LLM provider."""

    text: str
    model: str
    usage: dict = field(default_factory=dict)  # tokens in/out indien beschikbaar


class LLMProvider:
    """Abstract base class voor LLM providers.

    Elke provider (Anthropic, OpenAI, Ollama) implementeert:
    - complete(): simpele text completion
    - complete_with_tools(): completion met tool/function calling
    """

    name: str = "base"

    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str | None = None,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """Eenvoudige text completion zonder tools."""
        raise NotImplementedError

    async def complete_with_tools(
        self,
        system_prompt: str,
        user_prompt: str,
        tools: list[dict],
        model: str | None = None,
        max_tokens: int = 4096,
        max_turns: int = 10,
    ) -> LLMResponse:
        """Completion met tool/function calling (multi-turn loop).

        tools: lijst van tool definities in OpenAI-compatible format:
        [{"type": "function", "function": {"name": ..., "description": ..., "parameters": ...}}]

        Providers die geen native tool calling ondersteunen kunnen dit
        emuleren via prompt engineering.
        """
        raise NotImplementedError

    def supports_tools(self) -> bool:
        """Of deze provider native tool calling ondersteunt."""
        return False
