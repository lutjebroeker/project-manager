"""Tests voor Obsidian connector."""

import os
import tempfile

import pytest

from src.memory.store import MemoryStore
from src.connectors.obsidian import ObsidianConnector


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
def vault(tmp_path):
    """Maak een fake Obsidian vault structuur."""
    # Projecten
    projects = tmp_path / "Projects"
    projects.mkdir()
    (projects / "Acme Website.md").write_text(
        "---\nklant: Acme BV\nstatus: actief\n---\n\n# Acme Website\n\nWebsite redesign project.\n\n#project #web",
        encoding="utf-8",
    )
    (projects / "Beta App.md").write_text(
        "---\nclient: Beta Corp\nstatus: afgerond\n---\n\n# Beta App\n\nMobiele app ontwikkeling.\n\n#project #app",
        encoding="utf-8",
    )

    # Werkwijze notities
    werkwijze = tmp_path / "Werkwijze"
    werkwijze.mkdir()
    (werkwijze / "Offerte Process.md").write_text(
        "# Offerte Proces\n\nMijn standaard aanpak voor offertes:\n1. Intake gesprek\n2. Analyse\n3. Offerte schrijven\n\n#werkwijze #proces",
        encoding="utf-8",
    )

    # Daily notes
    daily = tmp_path / "Daily"
    daily.mkdir()
    (daily / "2025-01-15.md").write_text(
        "# 2025-01-15\n\nVandaag gewerkt aan Acme project.\n\n- Meeting met Jan\n- Design review",
        encoding="utf-8",
    )

    # Templates
    templates = tmp_path / "Templates"
    templates.mkdir()
    (templates / "Project Template.md").write_text(
        "---\nklant: \nstatus: nieuw\n---\n\n# {{title}}\n\n## Scope\n\n## Timeline",
        encoding="utf-8",
    )

    # Losse notitie
    (tmp_path / "Ideeën.md").write_text(
        "# Ideeën\n\n- AI automatisering voor klanten\n- Workshop framework\n",
        encoding="utf-8",
    )

    return tmp_path


@pytest.fixture
def connector(vault, memory):
    return ObsidianConnector(str(vault), memory)


class TestVaultScan:
    def test_scan_finds_all_files(self, connector):
        scan = connector.scan_vault()
        assert scan["total_files"] == 6

    def test_scan_categorizes_projects(self, connector):
        scan = connector.scan_vault()
        assert len(scan["projects"]) == 2

    def test_scan_categorizes_templates(self, connector):
        scan = connector.scan_vault()
        assert len(scan["templates"]) == 1

    def test_scan_categorizes_daily_notes(self, connector):
        scan = connector.scan_vault()
        assert len(scan["daily_notes"]) == 1

    def test_scan_lists_folders(self, connector):
        scan = connector.scan_vault()
        assert "Projects" in scan["folders"]
        assert "Werkwijze" in scan["folders"]


class TestReadNote:
    def test_read_with_frontmatter(self, connector):
        note = connector.read_note("Projects/Acme Website.md")
        assert note["frontmatter"]["klant"] == "Acme BV"
        assert note["frontmatter"]["status"] == "actief"
        assert "Website redesign" in note["content"]

    def test_read_extracts_tags(self, connector):
        note = connector.read_note("Projects/Acme Website.md")
        assert "project" in note["tags"]
        assert "web" in note["tags"]

    def test_read_counts_words(self, connector):
        note = connector.read_note("Projects/Acme Website.md")
        assert note["word_count"] > 0

    def test_read_nonexistent(self, connector):
        note = connector.read_note("does_not_exist.md")
        assert "error" in note

    def test_read_without_frontmatter(self, connector):
        note = connector.read_note("Ideeën.md")
        assert note["frontmatter"] == {}
        assert "AI automatisering" in note["content"]


class TestSearch:
    def test_search_finds_content(self, connector):
        results = connector.search_vault("Acme")
        assert len(results) >= 1
        paths = [r["path"] for r in results]
        assert any("Acme" in p for p in paths)

    def test_search_returns_snippets(self, connector):
        results = connector.search_vault("Acme")
        assert results[0]["snippets"]

    def test_search_counts_matches(self, connector):
        results = connector.search_vault("Acme")
        assert results[0]["match_count"] >= 1

    def test_search_no_results(self, connector):
        results = connector.search_vault("xyznonexistent")
        assert results == []

    def test_search_max_results(self, connector):
        results = connector.search_vault("project", max_results=1)
        assert len(results) <= 1

    def test_search_case_insensitive(self, connector):
        results = connector.search_vault("acme")
        assert len(results) >= 1


class TestIndexing:
    def test_index_projects(self, connector):
        indexed = connector.index_projects()
        assert len(indexed) == 2

    def test_index_extracts_client(self, connector):
        indexed = connector.index_projects()
        clients = [p["client"] for p in indexed]
        assert "Acme BV" in clients
        assert "Beta Corp" in clients

    def test_index_extracts_status(self, connector):
        indexed = connector.index_projects()
        statuses = {p["client"]: p["status"] for p in indexed}
        assert statuses["Acme BV"] == "actief"
        assert statuses["Beta Corp"] == "afgerond"

    def test_index_stores_in_memory(self, connector, memory):
        connector.index_projects()
        raw = memory.recall("global", "project:Acme Website")
        assert raw is not None
        data = __import__("json").loads(raw)
        assert data["client"] == "Acme BV"

    def test_index_all(self, connector):
        result = connector.index_all()
        assert result["total_files"] == 6
        assert result["projects_indexed"] == 2

    def test_index_stores_vault_info(self, connector, memory):
        connector.index_all()
        raw = memory.recall("global", "obsidian:vault_info")
        assert raw is not None


class TestWorkingStyle:
    def test_extract_finds_werkwijze(self, connector):
        patterns = connector.extract_working_style()
        assert len(patterns) >= 1
        keywords = [p["keyword"] for p in patterns]
        assert any(kw in ["werkwijze", "aanpak", "proces"] for kw in keywords)


class TestInvalidVault:
    def test_nonexistent_vault_raises(self, memory):
        with pytest.raises(ValueError, match="bestaat niet"):
            ObsidianConnector("/nonexistent/path", memory)
