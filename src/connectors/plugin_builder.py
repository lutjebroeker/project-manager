"""Plugin Builder — laat het systeem zelf nieuwe connectoren en agents bouwen.

Wanneer je zegt "koppel Home Assistant" of "monitor mijn Proxmox server",
dan kan dit systeem:
1. Uitzoeken welke API/MCP daarvoor nodig is
2. De connector code genereren
3. Het als plugin registreren
4. De MCP server herladen met de nieuwe tool

Plugins worden opgeslagen in data/plugins/ en automatisch geladen bij start.
"""

import json
import importlib
import importlib.util
import sys
from datetime import datetime
from pathlib import Path

from src.memory.store import MemoryStore
from src.config import settings


# Plugin manifest structuur
PLUGIN_MANIFEST_TEMPLATE = {
    "name": "",
    "description": "",
    "version": "0.1.0",
    "author": "auto-generated",
    "type": "connector",  # connector | agent | tool
    "status": "draft",  # draft | active | disabled
    "created_at": "",
    "config": {},  # Plugin-specifieke configuratie (URLs, tokens, etc.)
    "dependencies": [],  # Extra pip packages
}


class PluginBuilder:
    """Bouwt en beheert plugins dynamisch."""

    def __init__(self, memory: MemoryStore):
        self.memory = memory
        self.plugins_dir = Path("data/plugins")
        self.plugins_dir.mkdir(parents=True, exist_ok=True)
        self._loaded_plugins: dict = {}

    def list_plugins(self) -> list[dict]:
        """Lijst van alle geïnstalleerde plugins."""
        plugins = []
        for manifest_path in self.plugins_dir.glob("*/manifest.json"):
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["path"] = str(manifest_path.parent)
            plugins.append(manifest)
        return plugins

    def get_plugin(self, name: str) -> dict | None:
        """Haal een specifieke plugin op."""
        plugin_dir = self.plugins_dir / name
        manifest_path = plugin_dir / "manifest.json"
        if not manifest_path.exists():
            return None
        return json.loads(manifest_path.read_text(encoding="utf-8"))

    def create_plugin_scaffold(
        self,
        name: str,
        description: str,
        plugin_type: str = "connector",
        config: dict | None = None,
    ) -> dict:
        """Maak de basis structuur voor een nieuwe plugin.

        Dit maakt:
        - data/plugins/{name}/manifest.json
        - data/plugins/{name}/connector.py (of agent.py)
        - data/plugins/{name}/__init__.py
        """
        plugin_dir = self.plugins_dir / name
        plugin_dir.mkdir(parents=True, exist_ok=True)

        # Manifest
        manifest = {
            **PLUGIN_MANIFEST_TEMPLATE,
            "name": name,
            "description": description,
            "type": plugin_type,
            "status": "draft",
            "created_at": datetime.now().isoformat(),
            "config": config or {},
        }
        (plugin_dir / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        # __init__.py
        (plugin_dir / "__init__.py").write_text("", encoding="utf-8")

        return manifest

    def save_plugin_code(self, name: str, filename: str, code: str) -> str:
        """Sla gegenereerde code op voor een plugin."""
        plugin_dir = self.plugins_dir / name
        if not plugin_dir.exists():
            raise ValueError(f"Plugin '{name}' bestaat niet. Maak eerst een scaffold.")

        file_path = plugin_dir / filename
        file_path.write_text(code, encoding="utf-8")
        return str(file_path)

    def activate_plugin(self, name: str) -> bool:
        """Activeer een plugin (status: active)."""
        plugin_dir = self.plugins_dir / name
        manifest_path = plugin_dir / "manifest.json"
        if not manifest_path.exists():
            return False

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["status"] = "active"
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return True

    def disable_plugin(self, name: str) -> bool:
        """Deactiveer een plugin."""
        plugin_dir = self.plugins_dir / name
        manifest_path = plugin_dir / "manifest.json"
        if not manifest_path.exists():
            return False

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["status"] = "disabled"
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return True

    def load_plugin(self, name: str):
        """Laad een plugin module dynamisch."""
        plugin_dir = self.plugins_dir / name
        manifest_path = plugin_dir / "manifest.json"
        if not manifest_path.exists():
            raise ValueError(f"Plugin '{name}' niet gevonden")

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest["status"] != "active":
            raise ValueError(f"Plugin '{name}' is niet actief (status: {manifest['status']})")

        # Zoek het hoofd Python bestand
        main_file = plugin_dir / "connector.py"
        if not main_file.exists():
            main_file = plugin_dir / "agent.py"
        if not main_file.exists():
            main_file = plugin_dir / "tool.py"
        if not main_file.exists():
            raise ValueError(f"Geen connector.py, agent.py of tool.py gevonden in {plugin_dir}")

        # Dynamisch laden
        spec = importlib.util.spec_from_file_location(f"plugins.{name}", main_file)
        module = importlib.util.module_from_spec(spec)
        sys.modules[f"plugins.{name}"] = module
        spec.loader.exec_module(module)

        self._loaded_plugins[name] = {
            "manifest": manifest,
            "module": module,
        }

        return module

    def load_all_active(self) -> list[str]:
        """Laad alle actieve plugins."""
        loaded = []
        for manifest_path in self.plugins_dir.glob("*/manifest.json"):
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if manifest["status"] == "active":
                try:
                    self.load_plugin(manifest["name"])
                    loaded.append(manifest["name"])
                except Exception as e:
                    self.memory.log_action(
                        agent="plugin_builder",
                        action="load_error",
                        input_data=manifest["name"],
                        output_data=str(e),
                        status="error",
                    )
        return loaded

    def get_mcp_tools_from_plugins(self) -> list[dict]:
        """Haal MCP tool definities op uit geladen plugins.

        Elke plugin kan een `get_mcp_tools()` functie exporteren
        die een lijst van MCP tool dicts teruggeeft.
        """
        all_tools = []
        for name, plugin in self._loaded_plugins.items():
            module = plugin["module"]
            if hasattr(module, "get_mcp_tools"):
                try:
                    tools = module.get_mcp_tools(plugin["manifest"].get("config", {}))
                    all_tools.extend(tools)
                except Exception as e:
                    self.memory.log_action(
                        agent="plugin_builder",
                        action="tools_error",
                        input_data=name,
                        output_data=str(e),
                        status="error",
                    )
        return all_tools

    def get_build_prompt(self, request: str) -> str:
        """Genereer een prompt waarmee een agent de plugin code kan bouwen.

        Dit is de instructie die naar Claude gaat om de connector te schrijven.
        """
        existing_plugins = self.list_plugins()
        existing_names = [p["name"] for p in existing_plugins]

        return f"""Bouw een nieuwe plugin connector voor het AI Business Agent platform.

## Verzoek van de gebruiker:
{request}

## Bestaande plugins:
{json.dumps(existing_names, ensure_ascii=False)}

## Plugin structuur:
Elke plugin heeft:
1. `manifest.json` — metadata en configuratie
2. `connector.py` — de hoofdlogica
3. Optioneel: `get_mcp_tools(config)` functie die MCP tools exporteert

## connector.py template:
```python
\"\"\"[Naam] connector voor AI Business Agent.\"\"\"

import json
from datetime import datetime


class [Naam]Connector:
    \"\"\"Verbindt met [service].\"\"\"

    def __init__(self, config: dict):
        self.base_url = config.get("url", "")
        self.token = config.get("token", "")

    async def status(self) -> dict:
        \"\"\"Haal de huidige status op.\"\"\"
        # Implementatie hier
        pass

    # ... meer methodes


def get_mcp_tools(config: dict) -> list[dict]:
    \"\"\"Exporteer MCP tools voor deze connector.\"\"\"
    connector = [Naam]Connector(config)
    return [
        {{
            "name": "[naam]_status",
            "description": "Haal [service] status op",
            "handler": connector.status,
            "input_schema": {{"type": "object", "properties": {{}}}},
        }},
    ]
```

## Regels:
- Gebruik httpx voor HTTP calls (al geïnstalleerd)
- Geen hardcoded credentials — alles via config dict
- Exporteer altijd `get_mcp_tools(config)` zodat de tools via MCP beschikbaar zijn
- Schrijf Nederlandse docstrings
- Foutafhandeling: return duidelijke error messages, geen crashes
- Houd het simpel — begin met basis functionaliteit

## Output:
Geef terug:
1. De plugin naam (lowercase, met hyphens)
2. Een korte beschrijving
3. Welke config keys nodig zijn (url, token, etc.)
4. De volledige connector.py code
"""
