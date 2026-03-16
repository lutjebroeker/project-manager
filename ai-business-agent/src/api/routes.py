"""API routes for agent interaction."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.orchestrator import Orchestrator
from src.agents.marketing import MarketingAgent
from src.memory.store import MemoryStore
from src.config import settings

router = APIRouter()

# Initialize orchestrator and agents
memory = MemoryStore(settings.database_path)
orchestrator = Orchestrator()
orchestrator.register(MarketingAgent(memory=memory))


class PromptRequest(BaseModel):
    prompt: str
    max_turns: int = 10


class TopicRequest(BaseModel):
    topic: str | None = None


class ContentPlanRequest(BaseModel):
    weeks: int = 1


# --- Generic agent endpoint ---


@router.post("/agent/{agent_name}/run")
async def run_agent(agent_name: str, request: PromptRequest):
    try:
        result = await orchestrator.run(agent_name, request.prompt)
        return {"agent": agent_name, "result": result}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/agents")
async def list_agents():
    return {"agents": orchestrator.list_agents()}


# --- Marketing shortcuts ---


@router.post("/agent/marketing/linkedin-post")
async def generate_linkedin_post(request: TopicRequest):
    agent = orchestrator.get_agent("marketing")
    result = await agent.generate_linkedin_post(request.topic)
    return {"result": result}


@router.post("/agent/marketing/blog-outline")
async def generate_blog_outline(request: TopicRequest):
    if not request.topic:
        raise HTTPException(status_code=400, detail="Topic is required")
    agent = orchestrator.get_agent("marketing")
    result = await agent.generate_blog_outline(request.topic)
    return {"result": result}


@router.post("/agent/marketing/content-plan")
async def generate_content_plan(request: ContentPlanRequest):
    agent = orchestrator.get_agent("marketing")
    result = await agent.generate_content_plan(request.weeks)
    return {"result": result}


# --- Status & logs ---


@router.get("/agent/{agent_name}/logs")
async def get_agent_logs(agent_name: str, limit: int = 20):
    logs = memory.get_recent_logs(agent_name, limit=limit)
    return {"agent": agent_name, "logs": logs}


@router.get("/status")
async def health():
    return {
        "status": "ok",
        "agents": orchestrator.list_agents(),
    }
