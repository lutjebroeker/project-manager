"""Webhook endpoints voor n8n en andere automation tools.

Deze endpoints zijn geoptimaliseerd voor n8n HTTP Request nodes:
- Simpele JSON input/output
- Consistente response structuur
- Webhook signatures voor beveiliging (optioneel)
"""

import hashlib
import hmac
from typing import Any

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from src.orchestrator import Orchestrator
from src.agents.marketing import MarketingAgent
from src.agents.sales import SalesAgent
from src.agents.finance import FinanceAgent
from src.agents.planning import PlanningAgent
from src.memory.store import MemoryStore
from src.config import settings

webhook_router = APIRouter(prefix="/webhook", tags=["webhooks"])

# Shared orchestrator
memory = MemoryStore(settings.database_path)
orchestrator = Orchestrator()
orchestrator.register(MarketingAgent(memory=memory))
orchestrator.register(SalesAgent(memory=memory))
orchestrator.register(FinanceAgent(memory=memory))
orchestrator.register(PlanningAgent(memory=memory))


class WebhookPayload(BaseModel):
    """Universeel webhook payload formaat voor n8n."""

    agent: str
    action: str
    data: dict[str, Any] = {}


class WebhookResponse(BaseModel):
    """Consistente response structuur."""

    success: bool
    agent: str
    action: str
    result: str
    error: str | None = None


# --- Universeel webhook endpoint ---


@webhook_router.post("/run", response_model=WebhookResponse)
async def webhook_run(payload: WebhookPayload):
    """Universeel webhook endpoint — stuurt elke actie naar de juiste agent.

    n8n voorbeeld payload:
    {
        "agent": "sales",
        "action": "quote",
        "data": {
            "client_name": "Acme B.V.",
            "client_need": "AI chatbot voor klantenservice"
        }
    }
    """
    try:
        result = await _route_action(payload.agent, payload.action, payload.data)
        return WebhookResponse(
            success=True,
            agent=payload.agent,
            action=payload.action,
            result=result,
        )
    except ValueError as e:
        return WebhookResponse(
            success=False,
            agent=payload.agent,
            action=payload.action,
            result="",
            error=str(e),
        )
    except Exception as e:
        return WebhookResponse(
            success=False,
            agent=payload.agent,
            action=payload.action,
            result="",
            error=f"Internal error: {str(e)}",
        )


# --- Shortcut webhooks per agent (voor simpelere n8n flows) ---


@webhook_router.post("/marketing/{action}", response_model=WebhookResponse)
async def webhook_marketing(action: str, data: dict[str, Any] = {}):
    """Marketing webhook — /webhook/marketing/linkedin-post"""
    try:
        result = await _route_action("marketing", action, data)
        return WebhookResponse(success=True, agent="marketing", action=action, result=result)
    except Exception as e:
        return WebhookResponse(success=False, agent="marketing", action=action, result="", error=str(e))


@webhook_router.post("/sales/{action}", response_model=WebhookResponse)
async def webhook_sales(action: str, data: dict[str, Any] = {}):
    """Sales webhook — /webhook/sales/quote"""
    try:
        result = await _route_action("sales", action, data)
        return WebhookResponse(success=True, agent="sales", action=action, result=result)
    except Exception as e:
        return WebhookResponse(success=False, agent="sales", action=action, result="", error=str(e))


@webhook_router.post("/finance/{action}", response_model=WebhookResponse)
async def webhook_finance(action: str, data: dict[str, Any] = {}):
    """Finance webhook — /webhook/finance/invoice"""
    try:
        result = await _route_action("finance", action, data)
        return WebhookResponse(success=True, agent="finance", action=action, result=result)
    except Exception as e:
        return WebhookResponse(success=False, agent="finance", action=action, result="", error=str(e))


@webhook_router.post("/planning/{action}", response_model=WebhookResponse)
async def webhook_planning(action: str, data: dict[str, Any] = {}):
    """Planning webhook — /webhook/planning/week-plan"""
    try:
        result = await _route_action("planning", action, data)
        return WebhookResponse(success=True, agent="planning", action=action, result=result)
    except Exception as e:
        return WebhookResponse(success=False, agent="planning", action=action, result="", error=str(e))


# --- Action router ---


async def _route_action(agent_name: str, action: str, data: dict) -> str:
    """Route een actie naar de juiste agent method."""
    agent = orchestrator.get_agent(agent_name)

    # Marketing actions
    if agent_name == "marketing":
        actions = {
            "linkedin-post": lambda: agent.generate_linkedin_post(data.get("topic")),
            "blog-outline": lambda: agent.generate_blog_outline(data.get("topic", "AI trends")),
            "content-plan": lambda: agent.generate_content_plan(data.get("weeks", 1)),
            "run": lambda: agent.run(data.get("prompt", "")),
        }

    # Sales actions
    elif agent_name == "sales":
        actions = {
            "quote": lambda: agent.generate_quote(
                data.get("client_name", ""),
                data.get("client_need", ""),
                data.get("service_type"),
            ),
            "follow-up": lambda: agent.generate_follow_up(
                data.get("client_name", ""),
                data.get("context", ""),
                data.get("follow_up_type", "after_meeting"),
            ),
            "cold-email": lambda: agent.generate_cold_email(
                data.get("client_name", ""),
                data.get("company", ""),
                data.get("context", ""),
            ),
            "qualify-lead": lambda: agent.qualify_lead(
                data.get("company", ""),
                data.get("info", ""),
            ),
            "run": lambda: agent.run(data.get("prompt", "")),
        }

    # Finance actions
    elif agent_name == "finance":
        actions = {
            "invoice": lambda: agent.generate_invoice(
                data.get("client_name", ""),
                data.get("description", ""),
                data.get("hours"),
                data.get("fixed_amount"),
                data.get("service_type", "AI Implementatie"),
            ),
            "log-hours": lambda: agent.log_time(
                data.get("client", ""),
                data.get("hours", 0),
                data.get("description", ""),
                data.get("project", "Algemeen"),
            ),
            "report": lambda: agent.financial_report(data.get("period", "current_month")),
            "run": lambda: agent.run(data.get("prompt", "")),
        }

    # Planning actions
    elif agent_name == "planning":
        actions = {
            "week-plan": lambda: agent.create_week_plan(data.get("goals")),
            "day-plan": lambda: agent.create_day_plan(data.get("focus")),
            "add-tasks": lambda: agent.add_tasks(data.get("tasks", "")),
            "prioritize": lambda: agent.prioritize(),
            "run": lambda: agent.run(data.get("prompt", "")),
        }

    else:
        raise ValueError(f"Agent '{agent_name}' niet gevonden")

    if action not in actions:
        available = ", ".join(actions.keys())
        raise ValueError(f"Actie '{action}' niet beschikbaar voor {agent_name}. Beschikbaar: {available}")

    return await actions[action]()
