"""OpenAI-compatible provider — werkt met OpenAI, Azure OpenAI, en elke OpenAI-compatible API."""

import json

from src.providers.base import LLMProvider, LLMResponse


class OpenAIProvider(LLMProvider):
    """OpenAI-compatible provider. Werkt ook met OpenRouter, Together, etc.

    Set base_url om een alternatieve provider te gebruiken:
    - OpenAI: https://api.openai.com/v1 (default)
    - OpenRouter: https://openrouter.ai/api/v1
    - Together: https://api.together.xyz/v1
    - Lokale vLLM: http://localhost:8000/v1
    """

    name = "openai"
    default_model = "gpt-4o"

    def __init__(self, api_key: str, base_url: str | None = None):
        try:
            import openai
        except ImportError:
            raise ImportError(
                "openai package niet geïnstalleerd. "
                "Run: pip install openai"
            )
        kwargs = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        self.client = openai.AsyncOpenAI(**kwargs)

    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str | None = None,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        model = model or self.default_model
        response = await self.client.chat.completions.create(
            model=model,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        choice = response.choices[0]
        usage = {}
        if response.usage:
            usage = {
                "input_tokens": response.usage.prompt_tokens,
                "output_tokens": response.usage.completion_tokens,
            }
        return LLMResponse(
            text=choice.message.content or "",
            model=model,
            usage=usage,
        )

    async def complete_with_tools(
        self,
        system_prompt: str,
        user_prompt: str,
        tools: list[dict],
        model: str | None = None,
        max_tokens: int = 4096,
        max_turns: int = 10,
    ) -> LLMResponse:
        """Multi-turn tool calling loop via OpenAI-compatible API."""
        model = model or self.default_model

        # Tools moeten al in OpenAI format zijn
        openai_tools = []
        for t in tools:
            if "function" in t:
                openai_tools.append(t)
            else:
                openai_tools.append({"type": "function", "function": t})

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        total_usage = {"input_tokens": 0, "output_tokens": 0}
        result_text = ""

        for _turn in range(max_turns):
            kwargs = {
                "model": model,
                "max_tokens": max_tokens,
                "messages": messages,
            }
            if openai_tools:
                kwargs["tools"] = openai_tools

            response = await self.client.chat.completions.create(**kwargs)
            choice = response.choices[0]

            if response.usage:
                total_usage["input_tokens"] += response.usage.prompt_tokens
                total_usage["output_tokens"] += response.usage.completion_tokens

            if choice.message.content:
                result_text += choice.message.content

            # Als er geen tool calls zijn, klaar
            if not choice.message.tool_calls:
                break

            # Voeg assistant bericht toe
            messages.append(choice.message)

            # Placeholder tool results
            for tc in choice.message.tool_calls:
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": "[Tool execution niet beschikbaar in deze provider mode]",
                })

        return LLMResponse(text=result_text, model=model, usage=total_usage)

    def supports_tools(self) -> bool:
        return True
