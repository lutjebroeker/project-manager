"""Tests voor de provider-agnostische LLM layer."""

import os
import json
import tempfile
from unittest.mock import patch, AsyncMock, MagicMock

import pytest

from src.providers.base import LLMProvider, LLMResponse
from src.providers.registry import get_provider, get_available_providers, get_default_model


class TestLLMResponse:
    def test_basic_response(self):
        resp = LLMResponse(text="Hello", model="test-model")
        assert resp.text == "Hello"
        assert resp.model == "test-model"
        assert resp.usage == {}

    def test_response_with_usage(self):
        resp = LLMResponse(
            text="Hello",
            model="test",
            usage={"input_tokens": 10, "output_tokens": 20},
        )
        assert resp.usage["input_tokens"] == 10
        assert resp.usage["output_tokens"] == 20


class TestLLMProviderBase:
    def test_base_class_raises(self):
        provider = LLMProvider()
        assert provider.name == "base"
        assert provider.supports_tools() is False

    @pytest.mark.asyncio
    async def test_complete_not_implemented(self):
        provider = LLMProvider()
        with pytest.raises(NotImplementedError):
            await provider.complete("system", "user")

    @pytest.mark.asyncio
    async def test_complete_with_tools_not_implemented(self):
        provider = LLMProvider()
        with pytest.raises(NotImplementedError):
            await provider.complete_with_tools("system", "user", [])


class TestProviderRegistry:
    def test_available_providers(self):
        providers = get_available_providers()
        assert "anthropic" in providers
        assert "openai" in providers
        assert "ollama" in providers
        assert "claude_sdk" in providers

    def test_get_default_model_from_env(self):
        with patch.dict(os.environ, {"LLM_MODEL": "my-custom-model"}):
            assert get_default_model() == "my-custom-model"

    def test_get_default_model_per_provider(self):
        with patch.dict(os.environ, {}, clear=False):
            # Verwijder LLM_MODEL als het er is
            env = os.environ.copy()
            env.pop("LLM_MODEL", None)
            with patch.dict(os.environ, env, clear=True):
                assert get_default_model("anthropic") == "claude-sonnet-4-6"
                assert get_default_model("openai") == "gpt-4o"
                assert get_default_model("ollama") == "llama3.1"

    def test_unknown_provider_raises(self):
        with pytest.raises(ValueError, match="Onbekende LLM provider"):
            get_provider("nonexistent")

    def test_get_anthropic_provider_without_key_raises(self):
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": ""}, clear=False):
            with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
                get_provider("anthropic")

    def test_get_openai_provider_without_key_raises(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": ""}, clear=False):
            with pytest.raises(ValueError, match="OPENAI_API_KEY"):
                get_provider("openai")

    def test_default_provider_from_env(self):
        """LLM_PROVIDER env var bepaalt de default provider."""
        with patch.dict(os.environ, {"LLM_PROVIDER": "ollama"}):
            provider = get_provider()
            assert provider.name == "ollama"

    def test_ollama_provider_no_key_needed(self):
        """Ollama heeft geen API key nodig."""
        provider = get_provider("ollama")
        assert provider.name == "ollama"


class TestOllamaProvider:
    def test_init_default_url(self):
        from src.providers.ollama_provider import OllamaProvider
        provider = OllamaProvider()
        assert provider.base_url == "http://localhost:11434"

    def test_init_custom_url(self):
        from src.providers.ollama_provider import OllamaProvider
        provider = OllamaProvider(base_url="http://myserver:11434/")
        assert provider.base_url == "http://myserver:11434"

    def test_does_not_support_tools(self):
        from src.providers.ollama_provider import OllamaProvider
        provider = OllamaProvider()
        assert provider.supports_tools() is False


class TestAnthropicProvider:
    def test_supports_tools(self):
        """Anthropic provider moet tools ondersteunen."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test-key"}):
            # Mock de anthropic import
            mock_anthropic = MagicMock()
            with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
                from src.providers.anthropic_provider import AnthropicProvider
                provider = AnthropicProvider(api_key="sk-test-key")
                assert provider.supports_tools() is True
                assert provider.name == "anthropic"


class TestOpenAIProvider:
    def test_supports_tools(self):
        """OpenAI provider moet tools ondersteunen."""
        mock_openai = MagicMock()
        with patch.dict("sys.modules", {"openai": mock_openai}):
            from src.providers.openai_provider import OpenAIProvider
            provider = OpenAIProvider(api_key="sk-test-key")
            assert provider.supports_tools() is True
            assert provider.name == "openai"

    def test_custom_base_url(self):
        """OpenAI provider moet custom base_url accepteren (voor OpenRouter etc)."""
        mock_openai = MagicMock()
        with patch.dict("sys.modules", {"openai": mock_openai}):
            from src.providers.openai_provider import OpenAIProvider
            provider = OpenAIProvider(
                api_key="sk-test",
                base_url="https://openrouter.ai/api/v1",
            )
            assert provider.name == "openai"


class TestCompatToolDecorator:
    def test_compat_tool_without_sdk(self):
        """Tool decorator moet werken zonder claude_agent_sdk."""
        from src.agents.compat import tool

        @tool("test_tool", "Een test tool", {"param": str})
        async def my_tool(args):
            return args

        # De functie moet nog steeds callable zijn
        assert callable(my_tool)


class TestBaseAgentWithProvider:
    """Test dat BaseAgent correct met providers werkt."""

    @pytest.fixture
    def tmp_db(self, tmp_path):
        return str(tmp_path / "test.db")

    @pytest.fixture
    def mock_env(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        biz_path = str(tmp_path / "biz.json")
        with open(biz_path, "w") as f:
            json.dump({"bedrijf": "Test"}, f)
        return {
            "DATABASE_PATH": db_path,
            "BUSINESS_CONTEXT_PATH": biz_path,
            "LLM_PROVIDER": "ollama",
            "OBSIDIAN_VAULT_PATH": "",
        }

    def test_agent_with_ollama_provider(self, mock_env):
        with patch.dict(os.environ, mock_env):
            import importlib
            import src.config
            importlib.reload(src.config)

            from src.agents.base import BaseAgent
            agent = BaseAgent(provider="ollama")
            assert agent.provider.name == "ollama"
            assert agent.model == "llama3.1"

    def test_agent_with_explicit_model(self, mock_env):
        with patch.dict(os.environ, mock_env):
            import importlib
            import src.config
            importlib.reload(src.config)

            from src.agents.base import BaseAgent
            agent = BaseAgent(provider="ollama", model="mistral")
            assert agent.model == "mistral"

    def test_agent_version_info_includes_provider(self, mock_env):
        with patch.dict(os.environ, mock_env):
            import importlib
            import src.config
            importlib.reload(src.config)

            from src.agents.base import BaseAgent
            agent = BaseAgent(provider="ollama")
            info = agent.get_version_info()
            assert info["provider"] == "ollama"
            assert info["model"] == "llama3.1"
