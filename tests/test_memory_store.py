"""Tests voor MemoryStore — het fundament van alles."""

import json
import os
import tempfile

import pytest

from src.memory.store import MemoryStore


@pytest.fixture
def memory():
    """Geeft een verse MemoryStore met temp database."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    store = MemoryStore(path)
    yield store
    store.db.close()
    os.unlink(path)


# --- Key/Value geheugen ---


class TestKeyValueMemory:
    def test_remember_and_recall(self, memory):
        memory.remember("marketing", "style", "kort en bondig")
        assert memory.recall("marketing", "style") == "kort en bondig"

    def test_recall_nonexistent(self, memory):
        assert memory.recall("marketing", "nope") is None

    def test_remember_overwrites(self, memory):
        memory.remember("sales", "tone", "formeel")
        memory.remember("sales", "tone", "informeel")
        assert memory.recall("sales", "tone") == "informeel"

    def test_recall_all(self, memory):
        memory.remember("finance", "rate", "125")
        memory.remember("finance", "currency", "EUR")
        all_data = memory.recall_all("finance")
        assert all_data == {"rate": "125", "currency": "EUR"}

    def test_recall_all_empty(self, memory):
        assert memory.recall_all("nobody") == {}

    def test_agents_are_isolated(self, memory):
        memory.remember("agent_a", "key", "value_a")
        memory.remember("agent_b", "key", "value_b")
        assert memory.recall("agent_a", "key") == "value_a"
        assert memory.recall("agent_b", "key") == "value_b"


# --- Action logging ---


class TestActionLogging:
    def test_log_action_returns_id(self, memory):
        log_id = memory.log_action("marketing", "run", "input", "output")
        assert isinstance(log_id, int)
        assert log_id > 0

    def test_get_recent_logs(self, memory):
        memory.log_action("marketing", "run", "i1", "o1")
        memory.log_action("marketing", "run", "i2", "o2")
        memory.log_action("sales", "run", "i3", "o3")

        logs = memory.get_recent_logs("marketing")
        assert len(logs) == 2
        # Meest recent eerst
        assert logs[0]["input"] == "i2"

    def test_get_recent_logs_limit(self, memory):
        for i in range(10):
            memory.log_action("test", "run", f"i{i}", f"o{i}")
        logs = memory.get_recent_logs("test", limit=3)
        assert len(logs) == 3

    def test_log_action_status(self, memory):
        log_id = memory.log_action("test", "run", status="error")
        logs = memory.get_recent_logs("test")
        assert logs[0]["status"] == "error"


# --- Prompt versioning ---


class TestPromptVersioning:
    def test_save_and_get_active(self, memory):
        memory.save_prompt_version("marketing", "prompt v1", "initial")
        active = memory.get_active_prompt("marketing")
        assert active is not None
        assert active["version"] == 1
        assert active["system_prompt"] == "prompt v1"

    def test_versions_increment(self, memory):
        v1 = memory.save_prompt_version("marketing", "v1", "first")
        v2 = memory.save_prompt_version("marketing", "v2", "second")
        assert v1 == 1
        assert v2 == 2

    def test_only_latest_is_active(self, memory):
        memory.save_prompt_version("marketing", "v1", "first")
        memory.save_prompt_version("marketing", "v2", "second")
        active = memory.get_active_prompt("marketing")
        assert active["version"] == 2
        assert active["system_prompt"] == "v2"

    def test_rollback(self, memory):
        memory.save_prompt_version("marketing", "v1", "first")
        memory.save_prompt_version("marketing", "v2", "second")

        success = memory.rollback_prompt("marketing", 1)
        assert success is True

        active = memory.get_active_prompt("marketing")
        assert active["version"] == 1

    def test_rollback_nonexistent(self, memory):
        assert memory.rollback_prompt("marketing", 99) is False

    def test_prompt_history(self, memory):
        memory.save_prompt_version("marketing", "v1", "first")
        memory.save_prompt_version("marketing", "v2", "second")
        history = memory.get_prompt_history("marketing")
        assert len(history) == 2
        # Nieuwste eerst
        assert history[0]["version"] == 2

    def test_update_prompt_score(self, memory):
        memory.save_prompt_version("marketing", "v1", "test")
        memory.update_prompt_score("marketing", 1, 0.85)
        active = memory.get_active_prompt("marketing")
        assert active["performance_score"] == 0.85


# --- Feedback systeem ---


class TestFeedback:
    def test_add_and_get_feedback(self, memory):
        log_id = memory.log_action("marketing", "run", "prompt", "output")
        fb_id = memory.add_feedback(log_id, "marketing", 1, "goed gedaan!")
        assert isinstance(fb_id, int)

        recent = memory.get_recent_feedback("marketing")
        assert len(recent) == 1
        assert recent[0]["rating"] == 1
        assert recent[0]["comment"] == "goed gedaan!"

    def test_feedback_stats(self, memory):
        for rating in [1, 1, 1, -1, 0]:
            log_id = memory.log_action("marketing", "run")
            memory.add_feedback(log_id, "marketing", rating)

        stats = memory.get_feedback_stats("marketing")
        assert stats["positive"] == 3
        assert stats["negative"] == 1
        assert stats["neutral"] == 1
        assert stats["total"] == 5
        assert stats["satisfaction_rate"] == 60.0

    def test_feedback_stats_empty(self, memory):
        stats = memory.get_feedback_stats("nobody")
        assert stats["total"] == 0
        assert stats["satisfaction_rate"] is None

    def test_negative_feedback(self, memory):
        log1 = memory.log_action("test", "run", "p1", "bad output")
        log2 = memory.log_action("test", "run", "p2", "good output")
        memory.add_feedback(log1, "test", -1, "te lang")
        memory.add_feedback(log2, "test", 1, "perfect")

        neg = memory.get_negative_feedback("test")
        assert len(neg) == 1
        assert neg[0]["comment"] == "te lang"

    def test_positive_feedback(self, memory):
        log1 = memory.log_action("test", "run", "p1", "good")
        memory.add_feedback(log1, "test", 1, "top")

        pos = memory.get_positive_feedback("test")
        assert len(pos) == 1
        assert pos[0]["comment"] == "top"

    def test_feedback_with_tags(self, memory):
        log_id = memory.log_action("test", "run")
        memory.add_feedback(log_id, "test", 1, tags=["stijl", "format"])

        recent = memory.get_recent_feedback("test")
        assert json.loads(recent[0]["tags"]) == ["stijl", "format"]


# --- Learned preferences ---


class TestPreferences:
    def test_save_and_get_preference(self, memory):
        pref_id = memory.save_preference("marketing", "stijl", "Korte zinnen", 0.8)
        assert isinstance(pref_id, int)

        prefs = memory.get_active_preferences("marketing")
        assert len(prefs) == 1
        assert prefs[0]["category"] == "stijl"
        assert prefs[0]["preference"] == "Korte zinnen"
        assert prefs[0]["confidence"] == 0.8

    def test_preferences_sorted_by_confidence(self, memory):
        memory.save_preference("test", "stijl", "low conf", 0.3)
        memory.save_preference("test", "stijl", "high conf", 0.9)
        memory.save_preference("test", "stijl", "mid conf", 0.6)

        prefs = memory.get_active_preferences("test")
        confidences = [p["confidence"] for p in prefs]
        assert confidences == [0.9, 0.6, 0.3]

    def test_update_confidence(self, memory):
        pref_id = memory.save_preference("test", "stijl", "test", 0.5)
        memory.update_preference_confidence(pref_id, 0.95)

        prefs = memory.get_active_preferences("test")
        assert prefs[0]["confidence"] == 0.95

    def test_deactivate_preference(self, memory):
        pref_id = memory.save_preference("test", "stijl", "old rule", 0.8)
        memory.deactivate_preference(pref_id)

        prefs = memory.get_active_preferences("test")
        assert len(prefs) == 0
