"""Claude Agent SDK provider — de originele, voor wie Claude Code Max heeft.

Dit is de meest capabele provider: ondersteunt MCP tools, file access,
web search, en alle Claude Code features. Maar vereist een Max abonnement.
"""

from src.providers.base import LLMProvider, LLMResponse


class ClaudeSDKProvider(LLMProvider):
    """Wrapt de Claude Agent SDK (vereist Claude Code CLI + Max abo).

    Dit is de enige provider die native MCP server support heeft.
    Andere providers gebruiken direct function/tool calling.
    """

    name = "claude_sdk"
    default_model = "claude-sonnet-4-6"

    def __init__(self):
        try:
            from claude_agent_sdk import (
                ClaudeSDKClient,
                ClaudeAgentOptions,
                AssistantMessage,
                ResultMessage,
                TextBlock,
            )
        except ImportError:
            raise ImportError(
                "claude-agent-sdk niet geïnstalleerd. "
                "Run: pip install claude-agent-sdk"
            )
        self._sdk = {
            "ClaudeSDKClient": ClaudeSDKClient,
            "ClaudeAgentOptions": ClaudeAgentOptions,
            "AssistantMessage": AssistantMessage,
            "ResultMessage": ResultMessage,
            "TextBlock": TextBlock,
        }

    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str | None = None,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        model = model or self.default_model
        options = self._sdk["ClaudeAgentOptions"](
            allowed_tools=[],
            system_prompt=system_prompt,
            max_turns=1,
            model=model,
            permission_mode="bypassPermissions",
        )

        result_text = ""
        async with self._sdk["ClaudeSDKClient"](options=options) as client:
            await client.query(user_prompt)
            async for message in client.receive_response():
                if isinstance(message, self._sdk["AssistantMessage"]):
                    for block in message.content:
                        if isinstance(block, self._sdk["TextBlock"]):
                            result_text += block.text
                elif isinstance(message, self._sdk["ResultMessage"]):
                    result_text = message.result or result_text

        return LLMResponse(text=result_text, model=model)

    async def complete_with_tools(
        self,
        system_prompt: str,
        user_prompt: str,
        tools: list[dict],
        model: str | None = None,
        max_tokens: int = 4096,
        max_turns: int = 10,
    ) -> LLMResponse:
        """Full SDK run met tools — dit is de krachtigste modus."""
        model = model or self.default_model
        options = self._sdk["ClaudeAgentOptions"](
            allowed_tools=["Read", "WebSearch", "WebFetch"],
            system_prompt=system_prompt,
            max_turns=max_turns,
            model=model,
            permission_mode="bypassPermissions",
        )

        result_text = ""
        async with self._sdk["ClaudeSDKClient"](options=options) as client:
            await client.query(user_prompt)
            async for message in client.receive_response():
                if isinstance(message, self._sdk["AssistantMessage"]):
                    for block in message.content:
                        if isinstance(block, self._sdk["TextBlock"]):
                            result_text += block.text
                elif isinstance(message, self._sdk["ResultMessage"]):
                    result_text = message.result or result_text

        return LLMResponse(text=result_text, model=model)

    def supports_tools(self) -> bool:
        return True
