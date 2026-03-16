"""Tests voor de FastAPI routes — draait zonder Claude SDK."""

import json
import os
import tempfile
from unittest.mock import patch, AsyncMock

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def mock_settings(tmp_path):
    """Override settings zodat we temp database gebruiken."""
    db_path = str(tmp_path / "test.db")
    biz_path = str(tmp_path / "business_context.json")

    # Maak een minimal business context
    with open(biz_path, "w") as f:
        json.dump({"bedrijf": "Test BV"}, f)

    with patch.dict(os.environ, {
        "DATABASE_PATH": db_path,
        "BUSINESS_CONTEXT_PATH": biz_path,
        "OBSIDIAN_VAULT_PATH": "",
        "LLM_PROVIDER": "ollama",
        "API_TOKEN": "test-token-123",
    }):
        # Force re-import with new settings
        import importlib
        import src.config
        importlib.reload(src.config)

        # Reset cached auth token zodat de nieuwe API_TOKEN wordt opgepikt
        import src.api.auth
        src.api.auth._token = None
        importlib.reload(src.api.auth)

        import src.api.routes
        importlib.reload(src.api.routes)

        from src.main import app
        client = TestClient(app, headers={"Authorization": "Bearer test-token-123"})
        yield client


class TestHealthEndpoint:
    def test_root(self, mock_settings):
        client = mock_settings
        resp = client.get("/")
        assert resp.status_code == 200
        assert resp.json()["name"] == "AI Business Agent"

    def test_status(self, mock_settings):
        client = mock_settings
        resp = client.get("/api/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "agents" in data
        assert "knowledge" in data


class TestKnowledgeEndpoints:
    def test_share_knowledge(self, mock_settings):
        client = mock_settings
        resp = client.post("/api/knowledge/share", json={
            "source_agent": "marketing",
            "category": "schrijfstijl",
            "knowledge": "Korte zinnen",
            "confidence": 0.8,
        })
        assert resp.status_code == 200

    def test_get_shared_knowledge(self, mock_settings):
        client = mock_settings
        # Eerst opslaan
        client.post("/api/knowledge/share", json={
            "source_agent": "test",
            "category": "format",
            "knowledge": "Gebruik markdown",
            "confidence": 0.9,
        })
        # Dan ophalen
        resp = client.get("/api/knowledge/shared")
        assert resp.status_code == 200

    def test_remember_client(self, mock_settings):
        client = mock_settings
        resp = client.post("/api/knowledge/client", json={
            "client_name": "Acme",
            "facts": {"budget": "20k", "contact": "Jan"},
        })
        assert resp.status_code == 200

    def test_get_client(self, mock_settings):
        client = mock_settings
        # Opslaan
        client.post("/api/knowledge/client", json={
            "client_name": "Acme",
            "facts": {"budget": "20k"},
        })
        # Ophalen
        resp = client.get("/api/knowledge/client/Acme")
        assert resp.status_code == 200
        assert resp.json()["knowledge"]["budget"] == "20k"

    def test_get_unknown_client_404(self, mock_settings):
        client = mock_settings
        resp = client.get("/api/knowledge/client/NietBestaand")
        assert resp.status_code == 404

    def test_list_clients(self, mock_settings):
        client = mock_settings
        client.post("/api/knowledge/client", json={
            "client_name": "A", "facts": {"x": "1"},
        })
        client.post("/api/knowledge/client", json={
            "client_name": "B", "facts": {"x": "2"},
        })
        resp = client.get("/api/knowledge/clients")
        assert resp.status_code == 200
        assert len(resp.json()["clients"]) == 2


class TestPluginEndpoints:
    def test_list_plugins_empty(self, mock_settings):
        client = mock_settings
        resp = client.get("/api/plugins")
        assert resp.status_code == 200
        assert resp.json()["plugins"] == []
