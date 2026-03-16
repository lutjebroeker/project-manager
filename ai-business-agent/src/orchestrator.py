"""Central orchestrator for managing and routing to agents."""

from src.memory.store import MemoryStore
from src.config import settings


class Orchestrator:
    """Routes requests to the appropriate agent."""

    def __init__(self):
        self.memory = MemoryStore(settings.database_path)
        self._agents: dict = {}

    def register(self, agent_instance) -> None:
        """Register an agent instance."""
        self._agents[agent_instance.name] = agent_instance

    def get_agent(self, name: str):
        """Get a registered agent by name."""
        if name not in self._agents:
            raise ValueError(
                f"Agent '{name}' not found. Available: {list(self._agents.keys())}"
            )
        return self._agents[name]

    def list_agents(self) -> list[dict]:
        """List all registered agents."""
        return [
            {"name": a.name, "description": a.description}
            for a in self._agents.values()
        ]

    async def run(self, agent_name: str, prompt: str) -> str:
        """Run a specific agent with a prompt."""
        agent = self.get_agent(agent_name)
        return await agent.run(prompt)
