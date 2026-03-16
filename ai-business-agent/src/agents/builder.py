"""Builder agent — bouwt nieuwe plugins, connectoren en agents op verzoek.

Dit is de meta-agent: het kan het platform zelf uitbreiden.
Zeg "koppel Home Assistant" en deze agent:
1. Zoekt uit welke API/integratie nodig is
2. Genereert de connector code
3. Registreert het als plugin
4. Maakt de MCP tools beschikbaar
"""

import json

from claude_agent_sdk import tool

from src.agents.base import BaseAgent
from src.connectors.plugin_builder import PluginBuilder


class BuilderAgent(BaseAgent):
    name = "builder"
    description = "Bouwt nieuwe plugins, connectoren en agents. Breidt het platform zelf uit."

    system_prompt = """Je bent een software engineer die plugins bouwt voor het AI Business Agent platform.

Je taken:
1. **Nieuwe connectoren** — Bouw connectoren voor externe services (Home Assistant, UniFi, Proxmox, etc.)
2. **Nieuwe agents** — Maak nieuwe gespecialiseerde agents als dat nodig is
3. **Plugin beheer** — Activeer, deactiveer, en update plugins

Regels:
- Gebruik altijd httpx voor HTTP calls (async)
- Credentials nooit hardcoden — altijd via config
- Elke connector moet `get_mcp_tools(config)` exporteren
- Begin simpel: eerst basis status/monitoring, later uitbreiden
- Schrijf duidelijke docstrings in het Nederlands
- Test je code mentaal door — geen syntax errors
- Vraag om benodigde config (URL, tokens) als je die niet hebt
"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.plugin_builder = PluginBuilder(self.memory)

    def _get_tools(self) -> list:
        """Builder-specific tools."""

        @tool(
            "list_plugins",
            "Bekijk alle geïnstalleerde plugins",
            {},
        )
        async def list_plugins(args):
            plugins = self.plugin_builder.list_plugins()
            if not plugins:
                return {"content": [{"type": "text", "text": "Geen plugins geïnstalleerd."}]}
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(plugins, ensure_ascii=False, indent=2),
                    }
                ]
            }

        @tool(
            "create_plugin",
            "Maak een nieuwe plugin scaffold",
            {"name": str, "description": str, "plugin_type": str, "config": dict},
        )
        async def create_plugin(args):
            manifest = self.plugin_builder.create_plugin_scaffold(
                name=args["name"],
                description=args["description"],
                plugin_type=args.get("plugin_type", "connector"),
                config=args.get("config", {}),
            )
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Plugin scaffold aangemaakt: {args['name']}\n"
                        f"Manifest: {json.dumps(manifest, ensure_ascii=False, indent=2)}",
                    }
                ]
            }

        @tool(
            "save_plugin_code",
            "Sla gegenereerde code op voor een plugin",
            {"plugin_name": str, "filename": str, "code": str},
        )
        async def save_plugin_code(args):
            path = self.plugin_builder.save_plugin_code(
                args["plugin_name"], args["filename"], args["code"]
            )
            return {
                "content": [
                    {"type": "text", "text": f"Code opgeslagen: {path}"}
                ]
            }

        @tool(
            "activate_plugin",
            "Activeer een plugin zodat deze geladen wordt",
            {"name": str},
        )
        async def activate_plugin(args):
            success = self.plugin_builder.activate_plugin(args["name"])
            if success:
                return {"content": [{"type": "text", "text": f"Plugin '{args['name']}' geactiveerd."}]}
            return {"content": [{"type": "text", "text": f"Plugin '{args['name']}' niet gevonden."}]}

        @tool(
            "disable_plugin",
            "Deactiveer een plugin",
            {"name": str},
        )
        async def disable_plugin(args):
            success = self.plugin_builder.disable_plugin(args["name"])
            if success:
                return {"content": [{"type": "text", "text": f"Plugin '{args['name']}' uitgeschakeld."}]}
            return {"content": [{"type": "text", "text": f"Plugin '{args['name']}' niet gevonden."}]}

        @tool(
            "get_build_instructions",
            "Haal de bouw-instructies op voor een bepaald type connector",
            {"request": str},
        )
        async def get_build_instructions(args):
            prompt = self.plugin_builder.get_build_prompt(args["request"])
            return {"content": [{"type": "text", "text": prompt}]}

        return [
            list_plugins, create_plugin, save_plugin_code,
            activate_plugin, disable_plugin, get_build_instructions,
        ]

    async def build_plugin(self, request: str) -> str:
        """Bouw een nieuwe plugin op basis van een verzoek in natuurlijke taal.

        Voorbeeld: "Koppel Home Assistant op http://192.168.1.100:8123"
        """
        prompt = (
            f"De gebruiker vraagt: {request}\n\n"
            "Stappen:\n"
            "1. Gebruik get_build_instructions om de plugin template te krijgen\n"
            "2. Bepaal de plugin naam, beschrijving, en benodigde config\n"
            "3. Gebruik create_plugin om de scaffold aan te maken\n"
            "4. Schrijf de connector code met get_mcp_tools() functie\n"
            "5. Gebruik save_plugin_code om de code op te slaan\n"
            "6. Activeer de plugin met activate_plugin\n\n"
            "Belangrijk:\n"
            "- Gebruik httpx voor alle HTTP calls\n"
            "- Alle credentials via config dict, niet hardcoden\n"
            "- Begin met basis functionaliteit (status check, lijst ophalen)\n"
            "- Exporteer MCP tools zodat Claude de service kan gebruiken\n"
            "- Als je info mist (URL, token), geef dan aan wat de gebruiker moet invullen"
        )
        return await self.run(prompt, max_turns=15)

    async def extend_plugin(self, plugin_name: str, request: str) -> str:
        """Breid een bestaande plugin uit met nieuwe functionaliteit."""
        plugin = self.plugin_builder.get_plugin(plugin_name)
        if not plugin:
            return f"Plugin '{plugin_name}' niet gevonden."

        prompt = (
            f"Breid de plugin '{plugin_name}' uit.\n\n"
            f"Huidige plugin info: {json.dumps(plugin, ensure_ascii=False, indent=2)}\n\n"
            f"Verzoek: {request}\n\n"
            "Lees de huidige code, voeg de gevraagde functionaliteit toe, "
            "en sla de bijgewerkte code op via save_plugin_code."
        )
        return await self.run(prompt, max_turns=15)
