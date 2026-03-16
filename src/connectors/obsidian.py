"""Obsidian vault connector — indexeert projecten, notities en werkwijze.

Leest je Obsidian vault en extraheert:
- Projectnotities (status, besluiten, aanpak)
- Werkwijze documenten (hoe je dingen aanpakt)
- Klant informatie
- Persoonlijke voorkeuren en denkpatronen
- Templates en standaard aanpakken

Dit wordt geïndexeerd in de KnowledgeBase zodat alle agents
(en Claude via MCP) jouw context kennen.
"""

import json
import re
from datetime import datetime
from pathlib import Path

import yaml

from src.memory.store import MemoryStore


class ObsidianConnector:
    """Leest en indexeert een Obsidian vault."""

    def __init__(self, vault_path: str, memory: MemoryStore):
        self.vault_path = Path(vault_path)
        self.memory = memory

        if not self.vault_path.exists():
            raise ValueError(f"Vault pad bestaat niet: {vault_path}")

    def scan_vault(self) -> dict:
        """Scan de hele vault en geef een overzicht."""
        md_files = list(self.vault_path.rglob("*.md"))

        # Categoriseer bestanden
        stats = {
            "total_files": len(md_files),
            "folders": set(),
            "projects": [],
            "templates": [],
            "daily_notes": [],
            "other": [],
        }

        for f in md_files:
            rel = f.relative_to(self.vault_path)
            parts = rel.parts

            # Track folders
            if len(parts) > 1:
                stats["folders"].add(parts[0])

            name = f.stem.lower()
            folder = parts[0].lower() if len(parts) > 1 else ""

            if any(kw in folder for kw in ["project", "klant", "client"]):
                stats["projects"].append(str(rel))
            elif any(kw in folder for kw in ["template", "sjabloon"]):
                stats["templates"].append(str(rel))
            elif re.match(r"\d{4}-\d{2}-\d{2}", name):
                stats["daily_notes"].append(str(rel))
            else:
                stats["other"].append(str(rel))

        stats["folders"] = sorted(stats["folders"])
        return stats

    def read_note(self, relative_path: str) -> dict:
        """Lees een notitie en parse frontmatter + content."""
        full_path = self.vault_path / relative_path
        if not full_path.exists():
            return {"error": f"Bestand niet gevonden: {relative_path}"}

        text = full_path.read_text(encoding="utf-8")
        frontmatter = {}
        content = text

        # Parse YAML frontmatter
        if text.startswith("---"):
            parts = text.split("---", 2)
            if len(parts) >= 3:
                try:
                    frontmatter = yaml.safe_load(parts[1]) or {}
                except yaml.YAMLError:
                    pass
                content = parts[2].strip()

        # Extract links en tags
        links = re.findall(r"\[\[([^\]]+)\]\]", content)
        tags = re.findall(r"#([a-zA-Z0-9_/]+)", content)

        return {
            "path": relative_path,
            "frontmatter": frontmatter,
            "content": content,
            "links": links,
            "tags": tags,
            "word_count": len(content.split()),
        }

    def search_vault(self, query: str, max_results: int = 10) -> list[dict]:
        """Zoek in de vault op tekst."""
        results = []
        query_lower = query.lower()

        for md_file in self.vault_path.rglob("*.md"):
            try:
                text = md_file.read_text(encoding="utf-8")
                if query_lower in text.lower():
                    # Vind de relevante passages
                    lines = text.split("\n")
                    snippets = []
                    for i, line in enumerate(lines):
                        if query_lower in line.lower():
                            start = max(0, i - 1)
                            end = min(len(lines), i + 2)
                            snippets.append("\n".join(lines[start:end]))

                    rel_path = str(md_file.relative_to(self.vault_path))
                    results.append({
                        "path": rel_path,
                        "snippets": snippets[:3],
                        "match_count": text.lower().count(query_lower),
                    })

                    if len(results) >= max_results:
                        break
            except (UnicodeDecodeError, PermissionError):
                continue

        results.sort(key=lambda x: x["match_count"], reverse=True)
        return results

    def index_projects(self) -> list[dict]:
        """Indexeer alle projectnotities en sla op als klant/project kennis."""
        scan = self.scan_vault()
        indexed = []

        for project_path in scan["projects"]:
            note = self.read_note(project_path)
            if "error" in note:
                continue

            # Extraheer project info uit frontmatter en content
            fm = note["frontmatter"]
            project_info = {
                "source": f"obsidian:{project_path}",
                "tags": note["tags"],
                "status": fm.get("status", "onbekend"),
                "indexed_at": datetime.now().isoformat(),
            }

            # Zoek klant naam in frontmatter of bestandsnaam
            client = fm.get("klant") or fm.get("client") or fm.get("bedrijf")
            if not client:
                # Probeer uit pad of titel
                stem = Path(project_path).stem
                project_info["project_name"] = stem

            if client:
                # Sla op als klantkennis
                self.memory.remember(
                    "global",
                    f"client:{client}",
                    json.dumps(project_info, ensure_ascii=False),
                )

            # Sla project notitie op als doorzoekbare kennis
            summary = note["content"][:500]
            self.memory.remember(
                "global",
                f"project:{Path(project_path).stem}",
                json.dumps({
                    **project_info,
                    "summary": summary,
                    "client": client,
                }, ensure_ascii=False),
            )

            indexed.append({
                "path": project_path,
                "client": client,
                "status": project_info["status"],
                "tags": note["tags"],
            })

        return indexed

    def extract_working_style(self) -> list[dict]:
        """Analyseer de vault om werkwijze en denkpatronen te herkennen.

        Zoekt naar:
        - Notities over werkwijze, processen, aanpak
        - Terugkerende patronen in project notities
        - Templates (die laten zien hoe je dingen aanpakt)
        - Persoonlijke regels/principes
        """
        patterns = []

        # Zoek naar werkwijze-gerelateerde notities
        keywords = [
            "werkwijze", "proces", "aanpak", "workflow", "principes",
            "regels", "standaard", "checklist", "how-to", "methode",
            "framework", "template", "sop", "procedure",
        ]

        for keyword in keywords:
            results = self.search_vault(keyword, max_results=5)
            for result in results:
                note = self.read_note(result["path"])
                if "error" in note:
                    continue

                patterns.append({
                    "source": result["path"],
                    "keyword": keyword,
                    "content": note["content"][:1000],
                    "tags": note["tags"],
                    "frontmatter": note["frontmatter"],
                })

        return patterns

    def index_all(self) -> dict:
        """Volledige indexering van de vault. Sla alles op in het kennissysteem."""
        scan = self.scan_vault()
        projects = self.index_projects()

        # Sla vault metadata op
        self.memory.remember(
            "global",
            "obsidian:vault_info",
            json.dumps({
                "path": str(self.vault_path),
                "total_files": scan["total_files"],
                "folders": scan["folders"],
                "project_count": len(projects),
                "indexed_at": datetime.now().isoformat(),
            }, ensure_ascii=False),
        )

        return {
            "vault_path": str(self.vault_path),
            "total_files": scan["total_files"],
            "folders": scan["folders"],
            "projects_indexed": len(projects),
            "projects": projects,
        }
