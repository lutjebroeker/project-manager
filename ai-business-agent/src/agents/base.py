"""Base agent class wrapping Claude Agent SDK with versioning and learning."""

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
    """Base class for all business automation agents.

    Learning loop:
    1. Agent draait met system prompt + geleerde voorkeuren
    2. Output wordt gelogd (log_id teruggegeven)
    3. Gebruiker geeft feedback via API (rating + comment)
    4. Bij voldoende feedback: agent analyseert patronen
    5. Nieuwe voorkeuren worden opgeslagen en in prompt geïnjecteerd
    6. Prompt versie wordt bijgehouden voor rollback
    """

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
        # Registreer initiële prompt versie als die er nog niet is
        self._ensure_prompt_version()

    def _ensure_prompt_version(self) -> None:
        """Zorg dat er een prompt versie in de DB staat."""
        active = self.memory.get_active_prompt(self.name)
        if not active:
            self.memory.save_prompt_version(
                self.name, self.system_prompt, "Initiële versie"
            )

    def _build_system_prompt(self) -> str:
        """Combine agent system prompt with business context and learned preferences."""
        # Gebruik de actieve prompt versie uit DB (kan afwijken van code)
        active = self.memory.get_active_prompt(self.name)
        base_prompt = active["system_prompt"] if active else self.system_prompt

        ctx = json.dumps(self.business_context, ensure_ascii=False, indent=2)

        # Haal geleerde voorkeuren op
        preferences = self.memory.get_active_preferences(self.name)
        prefs_section = ""
        if preferences:
            prefs_lines = []
            for p in preferences:
                confidence_label = (
                    "sterk" if p["confidence"] >= 0.8
                    else "gemiddeld" if p["confidence"] >= 0.5
                    else "zwak"
                )
                prefs_lines.append(
                    f"- [{p['category']}] {p['preference']} (vertrouwen: {confidence_label})"
                )
            prefs_section = (
                "\n\n## Geleerde Voorkeuren\n"
                "Op basis van eerdere feedback heb je het volgende geleerd. "
                "Pas dit toe tenzij de gebruiker expliciet iets anders vraagt:\n"
                + "\n".join(prefs_lines)
            )

        # Haal recente feedback samen voor context
        feedback_section = ""
        negative = self.memory.get_negative_feedback(self.name, limit=3)
        if negative:
            avoid_lines = []
            for fb in negative:
                if fb["comment"]:
                    avoid_lines.append(f"- Vermijd: {fb['comment']}")
            if avoid_lines:
                feedback_section = (
                    "\n\n## Recente Correcties\n"
                    "Deze feedback is recent ontvangen — houd hier rekening mee:\n"
                    + "\n".join(avoid_lines)
                )

        return f"""{base_prompt}

## Business Context
{ctx}

## Instructies
- Schrijf altijd in het Nederlands tenzij anders gevraagd.
- Wees professioneel maar toegankelijk.
- Gebruik de business context om relevante, gepersonaliseerde output te genereren.
{prefs_section}{feedback_section}"""

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

        # Log the action — return log_id zodat feedback gekoppeld kan worden
        log_id = self.memory.log_action(
            agent=self.name,
            action="run",
            input_data=prompt[:500],
            output_data=result_text[:1000],
        )

        return result_text

    async def run_with_tracking(self, prompt: str, max_turns: int = 10) -> dict:
        """Run the agent and return result + log_id voor feedback tracking."""
        result = await self.run(prompt, max_turns)
        # Haal het laatste log_id op
        logs = self.memory.get_recent_logs(self.name, limit=1)
        log_id = logs[0]["id"] if logs else None
        return {"result": result, "log_id": log_id}

    async def learn_from_feedback(self) -> str:
        """Analyseer feedback en leer nieuwe voorkeuren.

        Dit is de kern van het zelflerende systeem:
        1. Haal positieve en negatieve feedback op
        2. Laat Claude de patronen analyseren
        3. Sla geleerde voorkeuren op
        4. Update confidence scores van bestaande voorkeuren
        """
        positive = self.memory.get_positive_feedback(self.name, limit=20)
        negative = self.memory.get_negative_feedback(self.name, limit=20)
        current_prefs = self.memory.get_active_preferences(self.name)

        if not positive and not negative:
            return "Nog geen feedback om van te leren."

        # Bouw een analyse prompt
        pos_examples = "\n".join(
            f"- Input: {fb['input'][:200]}\n  Output: {fb['output'][:200]}\n  Comment: {fb.get('comment', 'geen')}"
            for fb in positive
        ) or "Geen positieve feedback."

        neg_examples = "\n".join(
            f"- Input: {fb['input'][:200]}\n  Output: {fb['output'][:200]}\n  Comment: {fb.get('comment', 'geen')}"
            for fb in negative
        ) or "Geen negatieve feedback."

        current_prefs_text = "\n".join(
            f"- [{p['category']}] {p['preference']} (confidence: {p['confidence']})"
            for p in current_prefs
        ) or "Nog geen geleerde voorkeuren."

        analysis_prompt = f"""Analyseer de volgende feedback op mijn output en extraheer concrete voorkeuren.

## Positieve feedback (dit was goed):
{pos_examples}

## Negatieve feedback (dit moet beter):
{neg_examples}

## Huidige geleerde voorkeuren:
{current_prefs_text}

## Opdracht:
Geef je analyse als JSON array met objecten:
```json
[
  {{
    "category": "stijl|structuur|inhoud|toon|format",
    "preference": "Concrete, actionable voorkeur in het Nederlands",
    "confidence": 0.5-1.0
  }}
]
```

Regels:
- Max 5 nieuwe voorkeuren per analyse
- Wees specifiek, niet generiek ("Gebruik bullet points voor opsommingen" > "Schrijf beter")
- Alleen voorkeuren die duidelijk uit de feedback volgen
- Update confidence: hoger als meerdere feedbacks hetzelfde patroon tonen
- Als een bestaande voorkeur niet meer klopt op basis van feedback, geef confidence 0.0
- Return ALLEEN de JSON array, geen extra tekst
"""

        # Draai een tijdelijke agent voor de analyse
        options = ClaudeAgentOptions(
            allowed_tools=[],
            system_prompt="Je bent een feedback analyst. Je analyseert patronen in feedback en extraheert concrete voorkeuren. Antwoord ALLEEN met een JSON array.",
            max_turns=1,
            model=self.model,
            permission_mode="bypassPermissions",
        )

        result_text = ""
        async with ClaudeSDKClient(options=options) as client:
            await client.query(analysis_prompt)
            async for message in client.receive_response():
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            result_text += block.text
                elif isinstance(message, ResultMessage):
                    result_text = message.result or result_text

        # Parse de JSON response
        try:
            # Strip markdown code block als die er omheen zit
            clean = result_text.strip()
            if clean.startswith("```"):
                clean = clean.split("\n", 1)[1].rsplit("```", 1)[0]
            new_prefs = json.loads(clean)
        except (json.JSONDecodeError, IndexError):
            return f"Kon feedback analyse niet parsen. Raw output: {result_text[:500]}"

        # Sla nieuwe voorkeuren op
        saved = []
        for pref in new_prefs:
            if not isinstance(pref, dict):
                continue
            category = pref.get("category", "algemeen")
            preference = pref.get("preference", "")
            confidence = pref.get("confidence", 0.5)

            if not preference:
                continue

            # Als confidence 0 is, deactiveer bestaande matching preference
            if confidence <= 0.1:
                for existing in current_prefs:
                    if existing["category"] == category and existing["preference"] == preference:
                        self.memory.deactivate_preference(existing["id"])
                continue

            self.memory.save_preference(
                agent=self.name,
                category=category,
                preference=preference,
                confidence=min(confidence, 1.0),
            )
            saved.append(f"[{category}] {preference} ({confidence})")

        if saved:
            summary = "Geleerde voorkeuren opgeslagen:\n" + "\n".join(f"- {s}" for s in saved)
        else:
            summary = "Geen nieuwe voorkeuren geëxtraheerd uit de feedback."

        self.memory.log_action(
            agent=self.name,
            action="learn",
            input_data=f"pos={len(positive)}, neg={len(negative)}",
            output_data=summary[:1000],
        )

        return summary

    async def update_system_prompt(self, new_prompt: str, reason: str) -> int:
        """Update de system prompt en sla als nieuwe versie op."""
        version = self.memory.save_prompt_version(self.name, new_prompt, reason)
        return version

    def get_version_info(self) -> dict:
        """Haal versie info op voor deze agent."""
        active = self.memory.get_active_prompt(self.name)
        history = self.memory.get_prompt_history(self.name)
        stats = self.memory.get_feedback_stats(self.name)
        prefs = self.memory.get_active_preferences(self.name)

        return {
            "agent": self.name,
            "active_version": active["version"] if active else None,
            "total_versions": len(history),
            "feedback_stats": stats,
            "learned_preferences": len(prefs),
            "version_history": history,
        }

    def run_sync(self, prompt: str, max_turns: int = 10) -> str:
        """Synchronous wrapper for run()."""
        return anyio.from_thread.run(self.run, prompt, max_turns)
