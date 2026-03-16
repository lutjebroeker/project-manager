"""Anthropic provider — direct via de anthropic Python SDK (pay-per-token)."""

from src.providers.base import LLMProvider, LLMResponse


class AnthropicProvider(LLMProvider):
    """Gebruikt de Anthropic API direct. Vereist ANTHROPIC_API_KEY."""

    name = "anthropic"
    default_model = "claude-sonnet-4-6"

    def __init__(self, api_key: str):
        try:
            import anthropic
        except ImportError:
            raise ImportError(
                "anthropic package niet geïnstalleerd. "
                "Run: pip install anthropic"
            )
        self.client = anthropic.AsyncAnthropic(api_key=api_key)

    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str | None = None,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        model = model or self.default_model
        response = await self.client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        text = "".join(
            block.text for block in response.content if block.type == "text"
        )
        return LLMResponse(
            text=text,
            model=model,
            usage={
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            },
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
        """Multi-turn tool calling loop via Anthropic API."""
        model = model or self.default_model

        # Converteer OpenAI-format tools naar Anthropic format
        anthropic_tools = []
        for t in tools:
            fn = t.get("function", t)
            anthropic_tools.append({
                "name": fn["name"],
                "description": fn.get("description", ""),
                "input_schema": fn.get("parameters", {"type": "object", "properties": {}}),
            })

        messages = [{"role": "user", "content": user_prompt}]
        total_usage = {"input_tokens": 0, "output_tokens": 0}
        result_text = ""

        for _turn in range(max_turns):
            response = await self.client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=system_prompt,
                messages=messages,
                tools=anthropic_tools if anthropic_tools else None,
            )

            total_usage["input_tokens"] += response.usage.input_tokens
            total_usage["output_tokens"] += response.usage.output_tokens

            # Verzamel text output
            for block in response.content:
                if block.type == "text":
                    result_text += block.text

            # Als er geen tool_use is, zijn we klaar
            if response.stop_reason != "tool_use":
                break

            # Voeg assistant bericht toe aan conversatie
            messages.append({"role": "assistant", "content": response.content})

            # Verzamel tool results (placeholder — caller moet tool execution implementeren)
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": "[Tool execution niet beschikbaar in deze provider mode]",
                    })
            messages.append({"role": "user", "content": tool_results})

        return LLMResponse(text=result_text, model=model, usage=total_usage)

    def supports_tools(self) -> bool:
        return True
