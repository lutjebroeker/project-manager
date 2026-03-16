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


# --- Feedback & Learning ---


class FeedbackRequest(BaseModel):
    log_id: int
    rating: int  # -1 (slecht), 0 (neutraal), 1 (goed)
    comment: str = ""
    tags: list[str] | None = None


class UpdatePromptRequest(BaseModel):
    new_prompt: str
    reason: str


@router.post("/agent/{agent_name}/feedback")
async def add_feedback(agent_name: str, request: FeedbackRequest):
    """Geef feedback op een agent output. Dit voedt het zelflerende systeem."""
    if request.rating not in (-1, 0, 1):
        raise HTTPException(status_code=400, detail="Rating moet -1, 0, of 1 zijn")
    feedback_id = memory.add_feedback(
        log_id=request.log_id,
        agent=agent_name,
        rating=request.rating,
        comment=request.comment,
        tags=request.tags,
    )
    return {"feedback_id": feedback_id, "message": "Feedback opgeslagen"}


@router.post("/agent/{agent_name}/learn")
async def trigger_learning(agent_name: str):
    """Trigger de learning loop: analyseer feedback en leer voorkeuren."""
    try:
        agent = orchestrator.get_agent(agent_name)
        result = await agent.learn_from_feedback()
        return {"agent": agent_name, "result": result}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/agent/{agent_name}/feedback/stats")
async def get_feedback_stats(agent_name: str):
    """Haal feedback statistieken op."""
    stats = memory.get_feedback_stats(agent_name)
    return {"agent": agent_name, "stats": stats}


@router.get("/agent/{agent_name}/feedback")
async def get_feedback(agent_name: str, limit: int = 20):
    """Haal recente feedback op."""
    feedback = memory.get_recent_feedback(agent_name, limit=limit)
    return {"agent": agent_name, "feedback": feedback}


@router.get("/agent/{agent_name}/preferences")
async def get_preferences(agent_name: str):
    """Haal geleerde voorkeuren op."""
    prefs = memory.get_active_preferences(agent_name)
    return {"agent": agent_name, "preferences": prefs}


@router.delete("/agent/{agent_name}/preferences/{pref_id}")
async def deactivate_preference(agent_name: str, pref_id: int):
    """Deactiveer een geleerde voorkeur (als die niet klopt)."""
    memory.deactivate_preference(pref_id)
    return {"message": f"Voorkeur {pref_id} gedeactiveerd"}


# --- Versioning ---


@router.get("/agent/{agent_name}/versions")
async def get_versions(agent_name: str):
    """Haal prompt versie geschiedenis op."""
    try:
        agent = orchestrator.get_agent(agent_name)
        return agent.get_version_info()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/agent/{agent_name}/versions/{version}")
async def get_prompt_version(agent_name: str, version: int):
    """Haal een specifieke prompt versie op (inclusief de prompt tekst)."""
    history = memory.get_prompt_history(agent_name)
    for v in history:
        if v["version"] == version:
            return v
    raise HTTPException(status_code=404, detail=f"Versie {version} niet gevonden")


@router.post("/agent/{agent_name}/versions/rollback/{version}")
async def rollback_version(agent_name: str, version: int):
    """Rollback naar een eerdere prompt versie."""
    success = memory.rollback_prompt(agent_name, version)
    if not success:
        raise HTTPException(status_code=404, detail=f"Versie {version} niet gevonden")
    return {"message": f"Agent '{agent_name}' teruggezet naar versie {version}"}


@router.post("/agent/{agent_name}/versions/update")
async def update_prompt(agent_name: str, request: UpdatePromptRequest):
    """Update de system prompt (maakt automatisch een nieuwe versie aan)."""
    try:
        agent = orchestrator.get_agent(agent_name)
        version = await agent.update_system_prompt(request.new_prompt, request.reason)
        return {"agent": agent_name, "new_version": version, "reason": request.reason}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# --- Tracking endpoint (run + log_id voor feedback) ---


@router.post("/agent/{agent_name}/run-tracked")
async def run_agent_tracked(agent_name: str, request: PromptRequest):
    """Run een agent en return ook het log_id voor feedback koppeling."""
    try:
        agent = orchestrator.get_agent(agent_name)
        result = await agent.run_with_tracking(request.prompt, request.max_turns)
        return {"agent": agent_name, **result}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


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
