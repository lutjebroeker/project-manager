"""Ollama provider — draai LLMs lokaal, volledig gratis."""

from src.providers.base import LLMProvider, LLMResponse


class OllamaProvider(LLMProvider):
    """Lokale LLMs via Ollama. Geen API key nodig, geen kosten.

    Vereist: Ollama draaiend op je machine (https://ollama.ai)
    Goede modellen: llama3.1, mistral, mixtral, qwen2.5
    """

    name = "ollama"
    default_model = "llama3.1"

    def __init__(self, base_url: str = "http://localhost:11434"):
        try:
            import httpx
        except ImportError:
            raise ImportError("httpx package niet geïnstalleerd.")
        self.base_url = base_url.rstrip("/")
        self._httpx = httpx

    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str | None = None,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        model = model or self.default_model

        async with self._httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "stream": False,
                    "options": {"num_predict": max_tokens},
                },
            )
            response.raise_for_status()
            data = response.json()

        text = data.get("message", {}).get("content", "")
        usage = {}
        if "eval_count" in data:
            usage = {
                "input_tokens": data.get("prompt_eval_count", 0),
                "output_tokens": data.get("eval_count", 0),
            }
        return LLMResponse(text=text, model=model, usage=usage)

    async def complete_with_tools(
        self,
        system_prompt: str,
        user_prompt: str,
        tools: list[dict],
        model: str | None = None,
        max_tokens: int = 4096,
        max_turns: int = 10,
    ) -> LLMResponse:
        """Ollama heeft beperkte tool support — we emuleren via prompt engineering."""
        import json

        tool_descriptions = []
        for t in tools:
            fn = t.get("function", t)
            tool_descriptions.append(
                f"- {fn['name']}: {fn.get('description', '')}"
            )

        enhanced_prompt = (
            f"{user_prompt}\n\n"
            f"Je hebt deze tools beschikbaar:\n"
            + "\n".join(tool_descriptions)
            + "\n\nBeschrijf welke tools je zou gebruiken en geef je antwoord."
        )
        return await self.complete(system_prompt, enhanced_prompt, model, max_tokens)

    def supports_tools(self) -> bool:
        return False
