"""Tests voor KnowledgeBase — het centrale kennissysteem."""

import json
import os
import tempfile

import pytest

from src.memory.store import MemoryStore
from src.learning.knowledge_base import KnowledgeBase


@pytest.fixture
def tmp_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    os.unlink(path)


@pytest.fixture
def memory(tmp_db):
    return MemoryStore(tmp_db)


@pytest.fixture
def kb(memory, tmp_path):
    """KnowledgeBase met een temp CLAUDE.md locatie."""
    claude_md = tmp_path / "CLAUDE.md"
    return KnowledgeBase(memory, claude_md_path=str(claude_md))


# --- Cross-agent kennis ---


class TestSharedKnowledge:
    def test_share_and_retrieve(self, kb):
        kb.share_knowledge("sales", "schrijfstijl", "Korte emails", 0.8)
        prefs = kb.get_shared_knowledge()
        assert len(prefs) == 1
        assert prefs[0]["preference"] == "Korte emails"

    def test_filter_by_category(self, kb):
        kb.share_knowledge("sales", "schrijfstijl", "Kort", 0.8)
        kb.share_knowledge("marketing", "tone_of_voice", "Informeel", 0.7)

        stijl = kb.get_shared_knowledge("schrijfstijl")
        assert len(stijl) == 1
        assert stijl[0]["preference"] == "Kort"

    def test_knowledge_for_agent_includes_global(self, kb, memory):
        # Agent-specifiek
        memory.save_preference("marketing", "format", "Bullet points", 0.9)
        # Globaal
        kb.share_knowledge("sales", "schrijfstijl", "Kort", 0.8)

        all_knowledge = kb.get_knowledge_for_agent("marketing")
        assert len(all_knowledge) == 2

    def test_empty_shared_knowledge(self, kb):
        assert kb.get_shared_knowledge() == []


# --- Klant kennis ---


class TestClientKnowledge:
    def test_remember_and_recall_client(self, kb):
        kb.remember_client("Acme", {"budget": "20k", "contact": "Jan"})
        info = kb.recall_client("Acme")
        assert info["budget"] == "20k"
        assert info["contact"] == "Jan"
        assert "_updated_at" in info

    def test_update_client_preserves_existing(self, kb):
        kb.remember_client("Acme", {"budget": "20k", "contact": "Jan"})
        kb.remember_client("Acme", {"status": "actief"})

        info = kb.recall_client("Acme")
        assert info["budget"] == "20k"  # Bewaard
        assert info["status"] == "actief"  # Toegevoegd

    def test_update_client_overwrites_key(self, kb):
        kb.remember_client("Acme", {"budget": "20k"})
        kb.remember_client("Acme", {"budget": "30k"})
        assert kb.recall_client("Acme")["budget"] == "30k"

    def test_recall_unknown_client(self, kb):
        assert kb.recall_client("Onbekend") == {}

    def test_list_clients(self, kb):
        kb.remember_client("Acme", {"budget": "20k"})
        kb.remember_client("BetaCorp", {"budget": "10k"})
        clients = kb.list_clients()
        assert set(clients) == {"Acme", "BetaCorp"}

    def test_list_clients_empty(self, kb):
        assert kb.list_clients() == []


# --- Auto-learn triggers ---


class TestAutoLearn:
    def test_should_not_learn_without_feedback(self, kb):
        assert kb.should_auto_learn("marketing") is False

    def test_should_learn_after_threshold(self, kb, memory):
        # Geef 5 feedback items (default threshold)
        for _ in range(5):
            log_id = memory.log_action("marketing", "run", "in", "out")
            memory.add_feedback(log_id, "marketing", 1, "goed")

        assert kb.should_auto_learn("marketing") is True

    def test_should_not_learn_below_threshold(self, kb, memory):
        for _ in range(3):
            log_id = memory.log_action("marketing", "run")
            memory.add_feedback(log_id, "marketing", 1)

        assert kb.should_auto_learn("marketing") is False


# --- CLAUDE.md sync ---


class TestClaudeMdSync:
    def test_sync_creates_file(self, kb):
        kb.share_knowledge("sales", "schrijfstijl", "Kort en bondig", 0.8)
        result = kb.sync_to_claude_md()
        assert "gesynct" in result
        assert kb.claude_md_path.exists()

    def test_sync_contains_preferences(self, kb):
        kb.share_knowledge("sales", "schrijfstijl", "Kort en bondig", 0.8)
        kb.sync_to_claude_md()

        content = kb.claude_md_path.read_text(encoding="utf-8")
        assert "Kort en bondig" in content
        assert "Geleerde Voorkeuren" in content

    def test_sync_contains_clients(self, kb):
        kb.remember_client("TestBV", {"budget": "15k"})
        kb.sync_to_claude_md()

        content = kb.claude_md_path.read_text(encoding="utf-8")
        assert "TestBV" in content
        assert "15k" in content

    def test_sync_preserves_existing_content(self, kb):
        # Schrijf iets bestaands
        kb.claude_md_path.write_text("# Mijn Project\n\nBestaande content.\n")

        kb.share_knowledge("test", "format", "Markdown gebruiken", 0.9)
        kb.sync_to_claude_md()

        content = kb.claude_md_path.read_text(encoding="utf-8")
        assert "Mijn Project" in content
        assert "Bestaande content" in content
        assert "Markdown gebruiken" in content

    def test_sync_replaces_on_resync(self, kb):
        kb.share_knowledge("test", "stijl", "Versie 1", 0.8)
        kb.sync_to_claude_md()

        kb.share_knowledge("test", "stijl", "Versie 2", 0.9)
        kb.sync_to_claude_md()

        content = kb.claude_md_path.read_text(encoding="utf-8")
        # Beide versies staan erin (preferences worden niet verwijderd)
        assert "Versie 2" in content

    def test_sync_status(self, kb):
        status = kb.get_sync_status()
        assert "claude_md_path" in status
        assert "global_preferences" in status
        assert "known_clients" in status
        assert "agents" in status
        assert "marketing" in status["agents"]
