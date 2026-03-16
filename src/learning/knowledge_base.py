"""Centraal kennissysteem — verbindt alle agents, synct naar CLAUDE.md, en leert automatisch.

Dit is het brein van het platform:
- Cross-agent kennis: wat sales leert over een klant, weet finance ook
- Globale voorkeuren: schrijfstijl, toon, format regels gelden voor iedereen
- CLAUDE.md sync: geleerde voorkeuren worden geschreven naar CLAUDE.md
  zodat je hele Claude Code omgeving meegroeit
- Auto-learn: na voldoende feedback wordt learning automatisch getriggerd
"""

import json
from datetime import datetime
from pathlib import Path

from src.memory.store import MemoryStore


class KnowledgeBase:
    """Centraal kennissysteem dat alle agents verbindt."""

    # Categorieën voor globale kennis
    GLOBAL_CATEGORIES = {
        "schrijfstijl": "Hoe teksten geschreven moeten worden",
        "klant_kennis": "Wat we weten over specifieke klanten",
        "tone_of_voice": "Toon en stijl in communicatie",
        "format": "Hoe output geformateerd moet worden",
        "werkwijze": "Hoe we werken, processen, afspraken",
        "domein_kennis": "Inhoudelijke kennis over ons vakgebied",
    }

    def __init__(self, memory: MemoryStore, claude_md_path: str | None = None):
        self.memory = memory
        self.claude_md_path = Path(claude_md_path) if claude_md_path else self._find_claude_md()
        self._ensure_global_agent()

    def _find_claude_md(self) -> Path:
        """Zoek of maak het CLAUDE.md pad."""
        # Zoek in project root
        candidates = [
            Path.cwd() / "CLAUDE.md",
            Path.cwd().parent / "CLAUDE.md",
            Path.home() / ".claude" / "CLAUDE.md",
        ]
        for p in candidates:
            if p.exists():
                return p
        # Default: project root
        return Path.cwd() / "CLAUDE.md"

    def _ensure_global_agent(self) -> None:
        """Zorg dat er een 'global' agent entry bestaat voor gedeelde kennis."""
        active = self.memory.get_active_prompt("global")
        if not active:
            self.memory.save_prompt_version(
                "global",
                "Globale kennis en voorkeuren die gelden voor alle agents.",
                "Initiële versie",
            )

    # --- Cross-agent kennis ---

    def share_knowledge(
        self,
        source_agent: str,
        category: str,
        knowledge: str,
        confidence: float = 0.7,
    ) -> int:
        """Deel kennis vanuit één agent naar het globale niveau.

        Voorbeeld: Sales leert dat een klant voorkeur heeft voor korte emails
        → wordt gedeeld zodat marketing en finance dit ook weten.
        """
        return self.memory.save_preference(
            agent="global",
            category=category,
            preference=knowledge,
            confidence=confidence,
            source_feedback_ids=None,
        )

    def get_shared_knowledge(self, category: str | None = None) -> list[dict]:
        """Haal gedeelde kennis op, optioneel per categorie."""
        prefs = self.memory.get_active_preferences("global")
        if category:
            prefs = [p for p in prefs if p["category"] == category]
        return prefs

    def get_knowledge_for_agent(self, agent_name: str) -> list[dict]:
        """Haal zowel agent-specifieke als globale kennis op."""
        agent_prefs = self.memory.get_active_preferences(agent_name)
        global_prefs = self.memory.get_active_preferences("global")
        return agent_prefs + global_prefs

    # --- Klant kennis ---

    def remember_client(self, client_name: str, facts: dict) -> None:
        """Sla klantkennis op die alle agents kunnen gebruiken."""
        existing_raw = self.memory.recall("global", f"client:{client_name}")
        existing = json.loads(existing_raw) if existing_raw else {}
        existing.update(facts)
        existing["_updated_at"] = datetime.now().isoformat()
        self.memory.remember(
            "global", f"client:{client_name}", json.dumps(existing, ensure_ascii=False)
        )

    def recall_client(self, client_name: str) -> dict:
        """Haal alle bekende info over een klant op."""
        raw = self.memory.recall("global", f"client:{client_name}")
        return json.loads(raw) if raw else {}

    def list_clients(self) -> list[str]:
        """Lijst van alle bekende klanten."""
        all_keys = self.memory.recall_all("global")
        return [
            k.replace("client:", "")
            for k in all_keys
            if k.startswith("client:")
        ]

    # --- Auto-learn triggers ---

    def should_auto_learn(self, agent_name: str, threshold: int = 5) -> bool:
        """Check of er genoeg nieuwe feedback is om automatisch te leren."""
        stats = self.memory.get_feedback_stats(agent_name)
        if stats["total"] == 0:
            return False

        # Haal het laatste learn moment op
        logs = self.memory.get_recent_logs(agent_name, limit=50)
        last_learn = None
        for log in logs:
            if log["action"] == "learn":
                last_learn = log["created_at"]
                break

        if not last_learn:
            # Nog nooit geleerd — leer als er genoeg feedback is
            return stats["total"] >= threshold

        # Tel feedback sinds laatste learn
        recent_feedback = self.memory.get_recent_feedback(agent_name, limit=100)
        new_count = sum(
            1 for fb in recent_feedback
            if fb["created_at"] > last_learn
        )

        return new_count >= threshold

    # --- CLAUDE.md sync ---

    def sync_to_claude_md(self) -> str:
        """Schrijf alle geleerde kennis naar CLAUDE.md.

        Dit zorgt dat je Claude Code omgeving (niet alleen dit platform)
        de geleerde voorkeuren toepast. CLAUDE.md wordt gelezen door
        elke Claude Code sessie.
        """
        sections = []

        # Header
        sections.append("# Geleerde Voorkeuren & Kennis\n")
        sections.append(
            "> Auto-gegenereerd door AI Business Agent. "
            "Laatste sync: " + datetime.now().strftime("%Y-%m-%d %H:%M") + "\n"
            "> Niet handmatig bewerken — wijzigingen worden overschreven bij volgende sync.\n"
        )

        # Globale voorkeuren
        global_prefs = self.memory.get_active_preferences("global")
        if global_prefs:
            sections.append("## Globale Voorkeuren\n")
            by_category: dict[str, list] = {}
            for p in global_prefs:
                cat = p["category"]
                by_category.setdefault(cat, []).append(p)

            for cat, prefs in sorted(by_category.items()):
                cat_label = self.GLOBAL_CATEGORIES.get(cat, cat)
                sections.append(f"### {cat_label}\n")
                for p in prefs:
                    marker = "+" if p["confidence"] >= 0.7 else "~"
                    sections.append(f"- [{marker}] {p['preference']}")
                sections.append("")

        # Per-agent voorkeuren
        agents = ["marketing", "sales", "finance", "planning"]
        for agent_name in agents:
            prefs = self.memory.get_active_preferences(agent_name)
            if prefs:
                sections.append(f"## {agent_name.title()} Agent\n")
                for p in prefs:
                    sections.append(f"- [{p['category']}] {p['preference']}")
                sections.append("")

        # Klant kennis
        clients = self.list_clients()
        if clients:
            sections.append("## Klant Kennis\n")
            for client in clients:
                info = self.recall_client(client)
                sections.append(f"### {client}\n")
                for k, v in info.items():
                    if not k.startswith("_"):
                        sections.append(f"- **{k}**: {v}")
                sections.append("")

        content = "\n".join(sections)

        # Schrijf naar CLAUDE.md
        # Bewaar eventuele handmatige secties die er al in staan
        if self.claude_md_path.exists():
            existing = self.claude_md_path.read_text(encoding="utf-8")
            marker_start = "# Geleerde Voorkeuren & Kennis"
            marker_end = "# --- Einde Geleerde Voorkeuren ---"

            if marker_start in existing:
                # Vervang alleen het geleerde gedeelte
                before = existing.split(marker_start)[0].rstrip()
                after_parts = existing.split(marker_end)
                after = after_parts[1] if len(after_parts) > 1 else ""
                content_with_markers = f"{content}\n{marker_end}\n"
                full_content = f"{before}\n\n{content_with_markers}{after}".strip() + "\n"
            else:
                # Voeg toe aan het einde
                full_content = f"{existing.rstrip()}\n\n{content}\n{marker_end}\n"
        else:
            full_content = f"{content}\n# --- Einde Geleerde Voorkeuren ---\n"

        self.claude_md_path.write_text(full_content, encoding="utf-8")

        return f"CLAUDE.md gesynct naar {self.claude_md_path} ({len(global_prefs)} globale voorkeuren, {len(clients)} klanten)"

    def get_sync_status(self) -> dict:
        """Check de huidige sync status."""
        global_prefs = self.memory.get_active_preferences("global")
        clients = self.list_clients()

        claude_md_exists = self.claude_md_path.exists()
        claude_md_age = None
        if claude_md_exists:
            mtime = self.claude_md_path.stat().st_mtime
            claude_md_age = (datetime.now().timestamp() - mtime) / 3600  # uren

        agent_stats = {}
        for agent_name in ["marketing", "sales", "finance", "planning"]:
            prefs = self.memory.get_active_preferences(agent_name)
            feedback = self.memory.get_feedback_stats(agent_name)
            agent_stats[agent_name] = {
                "preferences": len(prefs),
                "feedback": feedback,
                "should_learn": self.should_auto_learn(agent_name),
            }

        return {
            "claude_md_path": str(self.claude_md_path),
            "claude_md_exists": claude_md_exists,
            "claude_md_hours_since_sync": round(claude_md_age, 1) if claude_md_age else None,
            "global_preferences": len(global_prefs),
            "known_clients": len(clients),
            "agents": agent_stats,
        }
