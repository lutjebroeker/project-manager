"""Tests voor Plugin Builder."""

import json
import os
import tempfile

import pytest

from src.memory.store import MemoryStore
from src.connectors.plugin_builder import PluginBuilder


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
def builder(memory, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    pb = PluginBuilder(memory)
    pb.plugins_dir = tmp_path / "plugins"
    pb.plugins_dir.mkdir()
    return pb


class TestPluginScaffold:
    def test_create_scaffold(self, builder):
        manifest = builder.create_plugin_scaffold(
            "home-assistant", "Koppelt Home Assistant", config={"url": "http://localhost:8123"}
        )
        assert manifest["name"] == "home-assistant"
        assert manifest["status"] == "draft"
        assert manifest["config"]["url"] == "http://localhost:8123"

    def test_scaffold_creates_files(self, builder):
        builder.create_plugin_scaffold("test-plugin", "Test")
        plugin_dir = builder.plugins_dir / "test-plugin"
        assert (plugin_dir / "manifest.json").exists()
        assert (plugin_dir / "__init__.py").exists()

    def test_list_plugins(self, builder):
        builder.create_plugin_scaffold("plugin-a", "Plugin A")
        builder.create_plugin_scaffold("plugin-b", "Plugin B")
        plugins = builder.list_plugins()
        assert len(plugins) == 2
        names = [p["name"] for p in plugins]
        assert "plugin-a" in names
        assert "plugin-b" in names

    def test_list_empty(self, builder):
        assert builder.list_plugins() == []

    def test_get_plugin(self, builder):
        builder.create_plugin_scaffold("my-plugin", "My Plugin")
        plugin = builder.get_plugin("my-plugin")
        assert plugin["name"] == "my-plugin"

    def test_get_nonexistent(self, builder):
        assert builder.get_plugin("nope") is None


class TestPluginCode:
    def test_save_code(self, builder):
        builder.create_plugin_scaffold("test", "Test")
        path = builder.save_plugin_code("test", "connector.py", "print('hello')")
        assert os.path.exists(path)
        with open(path) as f:
            assert f.read() == "print('hello')"

    def test_save_code_nonexistent_plugin(self, builder):
        with pytest.raises(ValueError, match="bestaat niet"):
            builder.save_plugin_code("nope", "connector.py", "code")


class TestPluginActivation:
    def test_activate(self, builder):
        builder.create_plugin_scaffold("test", "Test")
        assert builder.activate_plugin("test") is True

        plugin = builder.get_plugin("test")
        assert plugin["status"] == "active"

    def test_disable(self, builder):
        builder.create_plugin_scaffold("test", "Test")
        builder.activate_plugin("test")
        assert builder.disable_plugin("test") is True

        plugin = builder.get_plugin("test")
        assert plugin["status"] == "disabled"

    def test_activate_nonexistent(self, builder):
        assert builder.activate_plugin("nope") is False

    def test_disable_nonexistent(self, builder):
        assert builder.disable_plugin("nope") is False


class TestPluginLoading:
    def test_load_active_plugin(self, builder):
        builder.create_plugin_scaffold("test", "Test")
        builder.save_plugin_code("test", "connector.py", "VALUE = 42\n")
        builder.activate_plugin("test")

        module = builder.load_plugin("test")
        assert module.VALUE == 42

    def test_load_inactive_raises(self, builder):
        builder.create_plugin_scaffold("test", "Test")
        builder.save_plugin_code("test", "connector.py", "VALUE = 1\n")
        # Status is 'draft', niet 'active'
        with pytest.raises(ValueError, match="niet actief"):
            builder.load_plugin("test")

    def test_load_missing_code_raises(self, builder):
        builder.create_plugin_scaffold("test", "Test")
        builder.activate_plugin("test")
        with pytest.raises(ValueError, match="connector.py"):
            builder.load_plugin("test")

    def test_load_all_active(self, builder):
        builder.create_plugin_scaffold("a", "A")
        builder.save_plugin_code("a", "connector.py", "NAME = 'a'\n")
        builder.activate_plugin("a")

        builder.create_plugin_scaffold("b", "B")  # draft, niet active

        loaded = builder.load_all_active()
        assert loaded == ["a"]

    def test_get_mcp_tools_from_plugins(self, builder):
        builder.create_plugin_scaffold("test", "Test")
        builder.save_plugin_code(
            "test", "connector.py",
            "def get_mcp_tools(config):\n    return [{'name': 'test_tool', 'config': config}]\n"
        )
        builder.activate_plugin("test")
        builder.load_plugin("test")

        tools = builder.get_mcp_tools_from_plugins()
        assert len(tools) == 1
        assert tools[0]["name"] == "test_tool"


class TestBuildPrompt:
    def test_prompt_includes_request(self, builder):
        prompt = builder.get_build_prompt("Koppel Home Assistant")
        assert "Home Assistant" in prompt
        assert "connector.py" in prompt.lower()
