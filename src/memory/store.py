import json
import sqlite3
from datetime import datetime
from pathlib import Path

from src.memory.models import SCHEMA


class MemoryStore:
    def __init__(self, db_path: str = "data/agent_memory.db"):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(db_path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.executescript(SCHEMA)

    # --- Key/Value geheugen ---

    def remember(self, agent: str, key: str, value: str) -> None:
        existing = self.db.execute(
            "SELECT id FROM agent_memory WHERE agent = ? AND key = ?",
            (agent, key),
        ).fetchone()
        if existing:
            self.db.execute(
                "UPDATE agent_memory SET value = ?, updated_at = ? WHERE id = ?",
                (value, datetime.now().isoformat(), existing["id"]),
            )
        else:
            self.db.execute(
                "INSERT INTO agent_memory (agent, key, value) VALUES (?, ?, ?)",
                (agent, key, value),
            )
        self.db.commit()

    def recall(self, agent: str, key: str) -> str | None:
        row = self.db.execute(
            "SELECT value FROM agent_memory WHERE agent = ? AND key = ?",
            (agent, key),
        ).fetchone()
        return row["value"] if row else None

    def recall_all(self, agent: str) -> dict[str, str]:
        rows = self.db.execute(
            "SELECT key, value FROM agent_memory WHERE agent = ?", (agent,)
        ).fetchall()
        return {r["key"]: r["value"] for r in rows}

    # --- Action logging ---

    def log_action(
        self, agent: str, action: str, input_data: str = "", output_data: str = "", status: str = "success"
    ) -> int:
        """Log een actie en return het log ID (voor feedback koppeling)."""
        cursor = self.db.execute(
            "INSERT INTO agent_log (agent, action, input, output, status) VALUES (?, ?, ?, ?, ?)",
            (agent, action, input_data, output_data, status),
        )
        self.db.commit()
        return cursor.lastrowid

    def get_recent_logs(self, agent: str, limit: int = 20) -> list[dict]:
        rows = self.db.execute(
            "SELECT * FROM agent_log WHERE agent = ? ORDER BY created_at DESC LIMIT ?",
            (agent, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    # --- Prompt versioning ---

    def save_prompt_version(
        self, agent: str, system_prompt: str, change_reason: str = ""
    ) -> int:
        """Sla een nieuwe prompt versie op. Returns versienummer."""
        # Bepaal volgende versienummer
        row = self.db.execute(
            "SELECT MAX(version) as max_v FROM prompt_versions WHERE agent = ?",
            (agent,),
        ).fetchone()
        next_version = (row["max_v"] or 0) + 1

        # Deactiveer oude versies
        self.db.execute(
            "UPDATE prompt_versions SET is_active = 0 WHERE agent = ?",
            (agent,),
        )

        # Sla nieuwe versie op
        self.db.execute(
            "INSERT INTO prompt_versions (agent, version, system_prompt, change_reason) "
            "VALUES (?, ?, ?, ?)",
            (agent, next_version, system_prompt, change_reason),
        )
        self.db.commit()
        return next_version

    def get_active_prompt(self, agent: str) -> dict | None:
        """Haal de actieve prompt versie op."""
        row = self.db.execute(
            "SELECT * FROM prompt_versions WHERE agent = ? AND is_active = 1 "
            "ORDER BY version DESC LIMIT 1",
            (agent,),
        ).fetchone()
        return dict(row) if row else None

    def get_prompt_history(self, agent: str) -> list[dict]:
        """Haal alle prompt versies op voor een agent."""
        rows = self.db.execute(
            "SELECT id, agent, version, change_reason, is_active, performance_score, created_at "
            "FROM prompt_versions WHERE agent = ? ORDER BY version DESC",
            (agent,),
        ).fetchall()
        return [dict(r) for r in rows]

    def rollback_prompt(self, agent: str, version: int) -> bool:
        """Activeer een eerdere prompt versie."""
        row = self.db.execute(
            "SELECT id FROM prompt_versions WHERE agent = ? AND version = ?",
            (agent, version),
        ).fetchone()
        if not row:
            return False

        self.db.execute(
            "UPDATE prompt_versions SET is_active = 0 WHERE agent = ?", (agent,)
        )
        self.db.execute(
            "UPDATE prompt_versions SET is_active = 1 WHERE agent = ? AND version = ?",
            (agent, version),
        )
        self.db.commit()
        return True

    def update_prompt_score(self, agent: str, version: int, score: float) -> None:
        """Update de performance score van een prompt versie."""
        self.db.execute(
            "UPDATE prompt_versions SET performance_score = ? WHERE agent = ? AND version = ?",
            (score, agent, version),
        )
        self.db.commit()

    # --- Feedback systeem ---

    def add_feedback(
        self,
        log_id: int,
        agent: str,
        rating: int,
        comment: str = "",
        tags: list[str] | None = None,
    ) -> int:
        """Voeg feedback toe op een agent output. Rating: -1 (slecht), 0 (neutraal), 1 (goed)."""
        # Haal huidige prompt versie op
        active = self.get_active_prompt(agent)
        prompt_version = active["version"] if active else None

        tags_json = json.dumps(tags) if tags else None
        cursor = self.db.execute(
            "INSERT INTO feedback (log_id, agent, rating, comment, tags, prompt_version) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (log_id, agent, rating, comment, tags_json, prompt_version),
        )
        self.db.commit()
        return cursor.lastrowid

    def get_feedback_stats(self, agent: str) -> dict:
        """Haal feedback statistieken op voor een agent."""
        rows = self.db.execute(
            "SELECT rating, COUNT(*) as count FROM feedback WHERE agent = ? GROUP BY rating",
            (agent,),
        ).fetchall()

        stats = {"positive": 0, "neutral": 0, "negative": 0, "total": 0}
        for row in rows:
            if row["rating"] == 1:
                stats["positive"] = row["count"]
            elif row["rating"] == 0:
                stats["neutral"] = row["count"]
            elif row["rating"] == -1:
                stats["negative"] = row["count"]
            stats["total"] += row["count"]

        if stats["total"] > 0:
            stats["satisfaction_rate"] = round(stats["positive"] / stats["total"] * 100, 1)
        else:
            stats["satisfaction_rate"] = None

        return stats

    def get_recent_feedback(self, agent: str, limit: int = 20) -> list[dict]:
        """Haal recente feedback op met de bijbehorende log entries."""
        rows = self.db.execute(
            "SELECT f.*, l.action, l.input, l.output "
            "FROM feedback f "
            "JOIN agent_log l ON f.log_id = l.id "
            "WHERE f.agent = ? "
            "ORDER BY f.created_at DESC LIMIT ?",
            (agent, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_negative_feedback(self, agent: str, limit: int = 10) -> list[dict]:
        """Haal negatieve feedback op — input voor learning."""
        rows = self.db.execute(
            "SELECT f.*, l.action, l.input, l.output "
            "FROM feedback f "
            "JOIN agent_log l ON f.log_id = l.id "
            "WHERE f.agent = ? AND f.rating = -1 "
            "ORDER BY f.created_at DESC LIMIT ?",
            (agent, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_positive_feedback(self, agent: str, limit: int = 10) -> list[dict]:
        """Haal positieve feedback op — bevestiging van goede patronen."""
        rows = self.db.execute(
            "SELECT f.*, l.action, l.input, l.output "
            "FROM feedback f "
            "JOIN agent_log l ON f.log_id = l.id "
            "WHERE f.agent = ? AND f.rating = 1 "
            "ORDER BY f.created_at DESC LIMIT ?",
            (agent, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    # --- Learned preferences ---

    def save_preference(
        self,
        agent: str,
        category: str,
        preference: str,
        confidence: float = 0.5,
        source_feedback_ids: list[int] | None = None,
    ) -> int:
        """Sla een geleerde voorkeur op."""
        sources = json.dumps(source_feedback_ids) if source_feedback_ids else None
        cursor = self.db.execute(
            "INSERT INTO learned_preferences "
            "(agent, category, preference, confidence, source_feedback_ids) "
            "VALUES (?, ?, ?, ?, ?)",
            (agent, category, preference, confidence, sources),
        )
        self.db.commit()
        return cursor.lastrowid

    def get_active_preferences(self, agent: str) -> list[dict]:
        """Haal alle actieve geleerde voorkeuren op."""
        rows = self.db.execute(
            "SELECT * FROM learned_preferences WHERE agent = ? AND is_active = 1 "
            "ORDER BY confidence DESC",
            (agent,),
        ).fetchall()
        return [dict(r) for r in rows]

    def update_preference_confidence(self, pref_id: int, confidence: float) -> None:
        """Update de confidence score van een voorkeur."""
        self.db.execute(
            "UPDATE learned_preferences SET confidence = ?, updated_at = ? WHERE id = ?",
            (confidence, datetime.now().isoformat(), pref_id),
        )
        self.db.commit()

    def deactivate_preference(self, pref_id: int) -> None:
        """Deactiveer een voorkeur (bijv. als deze niet meer klopt)."""
        self.db.execute(
            "UPDATE learned_preferences SET is_active = 0, updated_at = ? WHERE id = ?",
            (datetime.now().isoformat(), pref_id),
        )
        self.db.commit()
