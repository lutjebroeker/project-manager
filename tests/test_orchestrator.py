"""Tests voor Orchestrator."""

import pytest

from src.orchestrator import Orchestrator


class FakeAgent:
    def __init__(self, name="test", description="Test agent"):
        self.name = name
        self.description = description
        self._last_prompt = None

    async def run(self, prompt):
        self._last_prompt = prompt
        return f"Result from {self.name}: {prompt}"


class TestOrchestrator:
    def test_register_and_list(self):
        orch = Orchestrator()
        orch.register(FakeAgent("marketing", "Marketing agent"))
        orch.register(FakeAgent("sales", "Sales agent"))

        agents = orch.list_agents()
        assert len(agents) == 2
        names = [a["name"] for a in agents]
        assert "marketing" in names
        assert "sales" in names

    def test_get_agent(self):
        orch = Orchestrator()
        agent = FakeAgent("marketing")
        orch.register(agent)
        assert orch.get_agent("marketing") is agent

    def test_get_unknown_agent_raises(self):
        orch = Orchestrator()
        with pytest.raises(ValueError, match="not found"):
            orch.get_agent("nonexistent")

    @pytest.mark.asyncio
    async def test_run_routes_to_agent(self):
        orch = Orchestrator()
        agent = FakeAgent("marketing")
        orch.register(agent)

        result = await orch.run("marketing", "schrijf een post")
        assert "marketing" in result
        assert "schrijf een post" in result
        assert agent._last_prompt == "schrijf een post"
