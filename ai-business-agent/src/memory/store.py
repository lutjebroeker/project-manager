import json
import sqlite3
from datetime import datetime
from pathlib import Path

from src.memory.models import SCHEMA


class MemoryStore:
    def __init__(self, db_path: str = "data/agent_memory.db"):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(db_path)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)

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

    def log_action(
        self, agent: str, action: str, input_data: str = "", output_data: str = "", status: str = "success"
    ) -> None:
        self.db.execute(
            "INSERT INTO agent_log (agent, action, input, output, status) VALUES (?, ?, ?, ?, ?)",
            (agent, action, input_data, output_data, status),
        )
        self.db.commit()

    def get_recent_logs(self, agent: str, limit: int = 20) -> list[dict]:
        rows = self.db.execute(
            "SELECT * FROM agent_log WHERE agent = ? ORDER BY created_at DESC LIMIT ?",
            (agent, limit),
        ).fetchall()
        return [dict(r) for r in rows]
