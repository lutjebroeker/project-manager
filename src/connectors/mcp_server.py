"""MCP Server — maakt het kennissysteem beschikbaar voor Claude overal.

Dit is de brug tussen jouw platform en Claude in:
- Claude Desktop app
- Claude Web (claude.ai met Max)
- Claude Code CLI
- Elke MCP-compatible client

Claude kan via deze server:
- Jouw werkwijze en voorkeuren opvragen
- Klantinfo ophalen voordat het iets schrijft
- Projectcontext uit Obsidian lezen
- Feedback geven op eerdere output
- Agents aansturen (offerte maken, content genereren, etc.)
"""

import json
from pathlib import Path

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from src.memory.store import MemoryStore
from src.learning.knowledge_base import KnowledgeBase
from src.connectors.obsidian import ObsidianConnector
from src.connectors.plugin_builder import PluginBuilder
from src.config import settings


def create_mcp_server(
    vault_path: str | None = None,
    db_path: str | None = None,
) -> Server:
    """Maak een MCP server met alle tools."""

    server = Server("ai-business-agent")
    memory = MemoryStore(db_path or settings.database_path)
    kb = KnowledgeBase(memory)
    plugins = PluginBuilder(memory)
    plugins.load_all_active()

    obsidian = None
    if vault_path and Path(vault_path).exists():
        obsidian = ObsidianConnector(vault_path, memory)

    # --- Tool definities ---

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        tools = [
            # Kennis ophalen
            Tool(
                name="get_my_preferences",
                description=(
                    "Haal mijn persoonlijke voorkeuren en werkwijze op. "
                    "Gebruik dit ALTIJD aan het begin van een gesprek om te weten "
                    "hoe ik dingen aanpak, welke stijl ik prefereer, etc."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "category": {
                            "type": "string",
                            "description": "Optioneel: filter op categorie (schrijfstijl, tone_of_voice, format, werkwijze, domein_kennis)",
                        },
                    },
                },
            ),
            Tool(
                name="get_client_info",
                description=(
                    "Haal alle bekende informatie op over een klant. "
                    "Gebruik dit voordat je iets schrijft voor of over een klant."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "client_name": {
                            "type": "string",
                            "description": "Naam van de klant/bedrijf",
                        },
                    },
                    "required": ["client_name"],
                },
            ),
            Tool(
                name="list_clients",
                description="Toon alle bekende klanten",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="remember_about_client",
                description=(
                    "Sla nieuwe informatie op over een klant zodat alle toekomstige "
                    "gesprekken deze context hebben."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "client_name": {
                            "type": "string",
                            "description": "Naam van de klant",
                        },
                        "facts": {
                            "type": "object",
                            "description": "Key-value pairs met info (bijv. {\"budget\": \"20k\", \"voorkeur\": \"korte emails\"})",
                        },
                    },
                    "required": ["client_name", "facts"],
                },
            ),
            Tool(
                name="learn_preference",
                description=(
                    "Sla een nieuwe voorkeur op die ik heb aangegeven. "
                    "Bijv. als ik zeg 'ik wil altijd bullet points' of "
                    "'gebruik nooit emoji's', sla dat dan op."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "category": {
                            "type": "string",
                            "enum": ["schrijfstijl", "tone_of_voice", "format", "werkwijze", "domein_kennis"],
                            "description": "Categorie van de voorkeur",
                        },
                        "preference": {
                            "type": "string",
                            "description": "De voorkeur in duidelijke tekst",
                        },
                        "confidence": {
                            "type": "number",
                            "description": "Hoe zeker (0.5-1.0). Expliciet aangegeven = 0.9, afgeleid = 0.6",
                            "default": 0.8,
                        },
                    },
                    "required": ["category", "preference"],
                },
            ),
            Tool(
                name="get_project_context",
                description=(
                    "Haal projectcontext op. Zoekt in opgeslagen projecten "
                    "en optioneel in de Obsidian vault."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_name": {
                            "type": "string",
                            "description": "Naam van het project",
                        },
                    },
                    "required": ["project_name"],
                },
            ),
            Tool(
                name="give_feedback",
                description=(
                    "Geef feedback op een eerdere output. "
                    "Gebruik dit als ik aangeef dat iets goed of slecht was."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "agent": {
                            "type": "string",
                            "description": "Welke agent (marketing, sales, finance, planning)",
                        },
                        "rating": {
                            "type": "integer",
                            "enum": [-1, 0, 1],
                            "description": "-1=slecht, 0=neutraal, 1=goed",
                        },
                        "comment": {
                            "type": "string",
                            "description": "Wat was goed/slecht en waarom",
                        },
                    },
                    "required": ["agent", "rating"],
                },
            ),
            Tool(
                name="run_agent",
                description=(
                    "Stuur een opdracht naar een van de business agents. "
                    "Beschikbaar: marketing (content), sales (offertes/emails), "
                    "finance (facturen/uren), planning (taken/planning)."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "agent": {
                            "type": "string",
                            "enum": ["marketing", "sales", "finance", "planning"],
                            "description": "Welke agent",
                        },
                        "prompt": {
                            "type": "string",
                            "description": "De opdracht voor de agent",
                        },
                    },
                    "required": ["agent", "prompt"],
                },
            ),
            Tool(
                name="get_knowledge_status",
                description="Toon het overzicht van het kennissysteem: voorkeuren, feedback, sync status",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="build_plugin",
                description=(
                    "Bouw een nieuwe connector/plugin voor een externe service. "
                    "Bijv: 'Koppel Home Assistant', 'Monitor UniFi netwerk', 'Verbind met Proxmox'. "
                    "Het systeem bouwt automatisch de code en MCP tools."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "request": {
                            "type": "string",
                            "description": "Wat je wilt koppelen, inclusief URL/details als je die hebt",
                        },
                    },
                    "required": ["request"],
                },
            ),
            Tool(
                name="list_plugins",
                description="Toon alle geïnstalleerde plugins en hun status",
                inputSchema={"type": "object", "properties": {}},
            ),
        ]

        # Obsidian-specifieke tools
        if obsidian:
            tools.extend([
                Tool(
                    name="search_obsidian",
                    description="Zoek in mijn Obsidian vault naar notities, projecten, of informatie",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Zoekterm",
                            },
                            "max_results": {
                                "type": "integer",
                                "description": "Max aantal resultaten",
                                "default": 5,
                            },
                        },
                        "required": ["query"],
                    },
                ),
                Tool(
                    name="read_obsidian_note",
                    description="Lees een specifieke notitie uit mijn Obsidian vault",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "Relatief pad naar de notitie (bijv. 'Projects/Acme.md')",
                            },
                        },
                        "required": ["path"],
                    },
                ),
                Tool(
                    name="index_obsidian",
                    description="Herindexeer de Obsidian vault — haalt projecten, klanten en werkwijze op",
                    inputSchema={"type": "object", "properties": {}},
                ),
            ])

        return tools

    # --- Tool handlers ---

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:

        if name == "get_my_preferences":
            category = arguments.get("category")
            all_prefs = kb.get_shared_knowledge(category)
            if not all_prefs:
                return [TextContent(
                    type="text",
                    text="Nog geen voorkeuren geleerd. Geef feedback of vertel me je voorkeuren zodat ik ze kan opslaan.",
                )]
            by_cat: dict[str, list] = {}
            for p in all_prefs:
                by_cat.setdefault(p["category"], []).append(p["preference"])
            lines = []
            for cat, prefs in sorted(by_cat.items()):
                lines.append(f"\n## {cat}")
                for pref in prefs:
                    lines.append(f"- {pref}")
            return [TextContent(type="text", text="\n".join(lines))]

        elif name == "get_client_info":
            client = arguments["client_name"]
            info = kb.recall_client(client)
            if not info:
                return [TextContent(type="text", text=f"Geen informatie bekend over '{client}'.")]
            return [TextContent(
                type="text",
                text=json.dumps(info, ensure_ascii=False, indent=2),
            )]

        elif name == "list_clients":
            clients = kb.list_clients()
            if not clients:
                return [TextContent(type="text", text="Nog geen klanten bekend.")]
            return [TextContent(type="text", text="Bekende klanten:\n" + "\n".join(f"- {c}" for c in clients))]

        elif name == "remember_about_client":
            kb.remember_client(arguments["client_name"], arguments["facts"])
            kb.sync_to_claude_md()
            return [TextContent(
                type="text",
                text=f"Opgeslagen over {arguments['client_name']}: {json.dumps(arguments['facts'], ensure_ascii=False)}",
            )]

        elif name == "learn_preference":
            confidence = arguments.get("confidence", 0.8)
            kb.share_knowledge(
                source_agent="mcp_direct",
                category=arguments["category"],
                knowledge=arguments["preference"],
                confidence=confidence,
            )
            kb.sync_to_claude_md()
            return [TextContent(
                type="text",
                text=f"Voorkeur opgeslagen: [{arguments['category']}] {arguments['preference']}",
            )]

        elif name == "get_project_context":
            project = arguments["project_name"]
            # Zoek in memory
            raw = memory.recall("global", f"project:{project}")
            info = json.loads(raw) if raw else None

            # Zoek ook in obsidian als beschikbaar
            obsidian_results = []
            if obsidian:
                obsidian_results = obsidian.search_vault(project, max_results=3)

            parts = []
            if info:
                parts.append(f"**Opgeslagen projectinfo:**\n{json.dumps(info, ensure_ascii=False, indent=2)}")
            if obsidian_results:
                parts.append("**Obsidian notities:**")
                for r in obsidian_results:
                    note = obsidian.read_note(r["path"])
                    parts.append(f"\n### {r['path']}\n{note.get('content', '')[:500]}")
            if not parts:
                return [TextContent(type="text", text=f"Geen info gevonden over project '{project}'.")]
            return [TextContent(type="text", text="\n\n".join(parts))]

        elif name == "give_feedback":
            # Haal het laatste log_id op voor deze agent
            logs = memory.get_recent_logs(arguments["agent"], limit=1)
            if not logs:
                return [TextContent(type="text", text="Geen recente output gevonden om feedback op te geven.")]
            log_id = logs[0]["id"]
            memory.add_feedback(
                log_id=log_id,
                agent=arguments["agent"],
                rating=arguments["rating"],
                comment=arguments.get("comment", ""),
            )
            rating_text = {-1: "negatief", 0: "neutraal", 1: "positief"}
            return [TextContent(
                type="text",
                text=f"Feedback opgeslagen: {rating_text[arguments['rating']]} voor {arguments['agent']}. "
                f"Comment: {arguments.get('comment', 'geen')}",
            )]

        elif name == "run_agent":
            # Import hier om circular imports te voorkomen
            from src.orchestrator import Orchestrator
            from src.agents.marketing import MarketingAgent
            from src.agents.sales import SalesAgent
            from src.agents.finance import FinanceAgent
            from src.agents.planning import PlanningAgent

            orch = Orchestrator()
            orch.register(MarketingAgent(memory=memory))
            orch.register(SalesAgent(memory=memory))
            orch.register(FinanceAgent(memory=memory))
            orch.register(PlanningAgent(memory=memory))

            result = await orch.run(arguments["agent"], arguments["prompt"])
            return [TextContent(type="text", text=result)]

        elif name == "get_knowledge_status":
            status = kb.get_sync_status()
            status["plugins"] = plugins.list_plugins()
            return [TextContent(
                type="text",
                text=json.dumps(status, ensure_ascii=False, indent=2),
            )]

        elif name == "build_plugin":
            from src.agents.builder import BuilderAgent
            builder = BuilderAgent(memory=memory)
            result = await builder.build_plugin(arguments["request"])
            return [TextContent(type="text", text=result)]

        elif name == "list_plugins":
            plugin_list = plugins.list_plugins()
            if not plugin_list:
                return [TextContent(type="text", text="Geen plugins geïnstalleerd.")]
            return [TextContent(
                type="text",
                text=json.dumps(plugin_list, ensure_ascii=False, indent=2),
            )]

        # Obsidian tools
        elif name == "search_obsidian" and obsidian:
            results = obsidian.search_vault(
                arguments["query"],
                arguments.get("max_results", 5),
            )
            if not results:
                return [TextContent(type="text", text=f"Niets gevonden voor '{arguments['query']}'.")]
            parts = []
            for r in results:
                parts.append(f"**{r['path']}** ({r['match_count']} matches)")
                for snippet in r["snippets"][:2]:
                    parts.append(f"```\n{snippet}\n```")
            return [TextContent(type="text", text="\n\n".join(parts))]

        elif name == "read_obsidian_note" and obsidian:
            note = obsidian.read_note(arguments["path"])
            if "error" in note:
                return [TextContent(type="text", text=note["error"])]
            parts = [f"# {arguments['path']}"]
            if note["frontmatter"]:
                parts.append(f"**Frontmatter:** {json.dumps(note['frontmatter'], ensure_ascii=False)}")
            if note["tags"]:
                parts.append(f"**Tags:** {', '.join(note['tags'])}")
            parts.append(f"\n{note['content']}")
            return [TextContent(type="text", text="\n".join(parts))]

        elif name == "index_obsidian" and obsidian:
            result = obsidian.index_all()
            kb.sync_to_claude_md()
            return [TextContent(
                type="text",
                text=f"Vault geïndexeerd: {result['total_files']} bestanden, "
                f"{result['projects_indexed']} projecten. CLAUDE.md gesynct.",
            )]

        return [TextContent(type="text", text=f"Onbekende tool: {name}")]

    return server


async def run_mcp_server(vault_path: str | None = None, db_path: str | None = None):
    """Start de MCP server via stdio (voor Claude Desktop/Web)."""
    server = create_mcp_server(vault_path=vault_path, db_path=db_path)
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())
