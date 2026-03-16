"""Compatibility layer — importeer `tool` decorator ongeacht of claude_agent_sdk beschikbaar is.

Bij claude_sdk provider: de echte decorator wordt gebruikt voor MCP tools.
Bij andere providers: de decorator is een no-op marker die metadata bewaart.
"""

try:
    from claude_agent_sdk import tool
except ImportError:
    # Fallback: een simpele decorator die functie metadata bewaart
    # zodat agents gedefinieerd kunnen worden zonder de SDK
    def tool(name: str, description: str, parameters: dict):
        """No-op tool decorator wanneer claude_agent_sdk niet beschikbaar is."""
        def decorator(func):
            func._tool_name = name
            func._tool_description = description
            func._tool_parameters = parameters
            return func
        return decorator
