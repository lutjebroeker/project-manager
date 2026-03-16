"""API routes for agent interaction."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.orchestrator import Orchestrator
from src.agents.marketing import MarketingAgent
from src.agents.sales import SalesAgent
from src.agents.finance import FinanceAgent
from src.agents.planning import PlanningAgent
from src.memory.store import MemoryStore
from src.config import settings

router = APIRouter()

# Initialize orchestrator and agents
memory = MemoryStore(settings.database_path)
orchestrator = Orchestrator()
orchestrator.register(MarketingAgent(memory=memory))
orchestrator.register(SalesAgent(memory=memory))
orchestrator.register(FinanceAgent(memory=memory))
orchestrator.register(PlanningAgent(memory=memory))


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


# --- Sales shortcuts ---


class QuoteRequest(BaseModel):
    client_name: str
    client_need: str
    service_type: str | None = None


class FollowUpRequest(BaseModel):
    client_name: str
    context: str
    follow_up_type: str = "after_meeting"


class ColdEmailRequest(BaseModel):
    client_name: str
    company: str
    context: str


class LeadQualifyRequest(BaseModel):
    company: str
    info: str


@router.post("/agent/sales/quote")
async def generate_quote(request: QuoteRequest):
    agent = orchestrator.get_agent("sales")
    result = await agent.generate_quote(
        request.client_name, request.client_need, request.service_type
    )
    return {"result": result}


@router.post("/agent/sales/follow-up")
async def generate_follow_up(request: FollowUpRequest):
    agent = orchestrator.get_agent("sales")
    result = await agent.generate_follow_up(
        request.client_name, request.context, request.follow_up_type
    )
    return {"result": result}


@router.post("/agent/sales/cold-email")
async def generate_cold_email(request: ColdEmailRequest):
    agent = orchestrator.get_agent("sales")
    result = await agent.generate_cold_email(
        request.client_name, request.company, request.context
    )
    return {"result": result}


@router.post("/agent/sales/qualify-lead")
async def qualify_lead(request: LeadQualifyRequest):
    agent = orchestrator.get_agent("sales")
    result = await agent.qualify_lead(request.company, request.info)
    return {"result": result}


@router.get("/agent/sales/leads")
async def get_leads():
    import json
    existing = memory.recall("sales", "leads")
    leads = json.loads(existing) if existing else []
    return {"leads": leads}


# --- Finance shortcuts ---


class InvoiceRequest(BaseModel):
    client_name: str
    description: str
    hours: float | None = None
    fixed_amount: float | None = None
    service_type: str = "AI Implementatie"


class TimeLogRequest(BaseModel):
    client: str
    hours: float
    description: str
    project: str = "Algemeen"


class FinanceReportRequest(BaseModel):
    period: str = "current_month"


@router.post("/agent/finance/invoice")
async def generate_invoice(request: InvoiceRequest):
    agent = orchestrator.get_agent("finance")
    result = await agent.generate_invoice(
        request.client_name,
        request.description,
        request.hours,
        request.fixed_amount,
        request.service_type,
    )
    return {"result": result}


@router.post("/agent/finance/log-hours")
async def log_hours(request: TimeLogRequest):
    agent = orchestrator.get_agent("finance")
    result = await agent.log_time(
        request.client, request.hours, request.description, request.project
    )
    return {"result": result}


@router.post("/agent/finance/report")
async def financial_report(request: FinanceReportRequest):
    agent = orchestrator.get_agent("finance")
    result = await agent.financial_report(request.period)
    return {"result": result}


@router.get("/agent/finance/invoices")
async def get_invoices():
    import json
    existing = memory.recall("finance", "invoices")
    invoices = json.loads(existing) if existing else []
    return {"invoices": invoices}


@router.get("/agent/finance/hours")
async def get_hours(client: str | None = None, month: str | None = None):
    import json
    existing = memory.recall("finance", "hours_log")
    hours_log = json.loads(existing) if existing else []
    if client:
        hours_log = [h for h in hours_log if h["client"].lower() == client.lower()]
    if month:
        hours_log = [h for h in hours_log if h["date"].startswith(month)]
    total = sum(h["hours"] for h in hours_log)
    return {"hours": hours_log, "total_hours": total}


# --- Planning shortcuts ---


class WeekPlanRequest(BaseModel):
    goals: str | None = None


class DayPlanRequest(BaseModel):
    focus: str | None = None


class AddTasksRequest(BaseModel):
    tasks: str


@router.post("/agent/planning/week-plan")
async def create_week_plan(request: WeekPlanRequest):
    agent = orchestrator.get_agent("planning")
    result = await agent.create_week_plan(request.goals)
    return {"result": result}


@router.post("/agent/planning/day-plan")
async def create_day_plan(request: DayPlanRequest):
    agent = orchestrator.get_agent("planning")
    result = await agent.create_day_plan(request.focus)
    return {"result": result}


@router.post("/agent/planning/add-tasks")
async def add_tasks(request: AddTasksRequest):
    agent = orchestrator.get_agent("planning")
    result = await agent.add_tasks(request.tasks)
    return {"result": result}


@router.post("/agent/planning/prioritize")
async def prioritize_tasks():
    agent = orchestrator.get_agent("planning")
    result = await agent.prioritize()
    return {"result": result}


@router.get("/agent/planning/tasks")
async def get_tasks(status: str | None = None, project: str | None = None):
    import json
    existing = memory.recall("planning", "tasks")
    tasks = json.loads(existing) if existing else []
    if status:
        tasks = [t for t in tasks if t["status"] == status]
    if project:
        tasks = [t for t in tasks if t["project"].lower() == project.lower()]
    return {"tasks": tasks}


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
