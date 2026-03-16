"""Base agent class wrapping Claude Agent SDK."""

import json
from pathlib import Path

import anyio
from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    AssistantMessage,
    ResultMessage,
    TextBlock,
    tool,
    create_sdk_mcp_server,
)

from src.config import load_business_context, settings
from src.memory.store import MemoryStore


class BaseAgent:
    """Base class for all business automation agents."""

    name: str = "base"
    description: str = "Base agent"
    system_prompt: str = ""

    # Default model — Max abonnement ondersteunt alle modellen
    model: str = "claude-sonnet-4-6"  # Goede balans snelheid/kwaliteit

    def __init__(self, memory: MemoryStore | None = None, model: str | None = None):
        self.memory = memory or MemoryStore(settings.database_path)
        self.business_context = load_business_context()
        if model:
            self.model = model

    def _build_system_prompt(self) -> str:
        """Combine agent system prompt with business context."""
        ctx = json.dumps(self.business_context, ensure_ascii=False, indent=2)
        return f"""{self.system_prompt}

## Business Context
{ctx}

## Instructies
- Schrijf altijd in het Nederlands tenzij anders gevraagd.
- Wees professioneel maar toegankelijk.
- Gebruik de business context om relevante, gepersonaliseerde output te genereren.
"""

    def _get_tools(self) -> list:
        """Override in subclasses to provide custom MCP tools."""
        return []

    def _get_allowed_tools(self) -> list[str]:
        """Built-in tools this agent can use."""
        return ["Read", "WebSearch", "WebFetch"]

    async def run(self, prompt: str, max_turns: int = 10) -> str:
        """Run the agent with a prompt and return the result."""
        custom_tools = self._get_tools()

        options_kwargs = {
            "allowed_tools": self._get_allowed_tools(),
            "system_prompt": self._build_system_prompt(),
            "max_turns": max_turns,
            "model": self.model,
            "permission_mode": "bypassPermissions",
        }

        if custom_tools:
            server = create_sdk_mcp_server(
                f"{self.name}-tools", tools=custom_tools
            )
            options_kwargs["mcp_servers"] = {self.name: server}

        options = ClaudeAgentOptions(**options_kwargs)
        result_text = ""

        async with ClaudeSDKClient(options=options) as client:
            await client.query(prompt)
            async for message in client.receive_response():
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            result_text += block.text
                elif isinstance(message, ResultMessage):
                    result_text = message.result or result_text

        # Log the action
        self.memory.log_action(
            agent=self.name,
            action="run",
            input_data=prompt[:500],
            output_data=result_text[:1000],
        )

        return result_text

    def run_sync(self, prompt: str, max_turns: int = 10) -> str:
        """Synchronous wrapper for run()."""
        return anyio.from_thread.run(self.run, prompt, max_turns)
