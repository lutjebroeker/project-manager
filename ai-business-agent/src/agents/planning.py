"""Planning agent — taken, projecten, en weekplanning."""

import json
from datetime import datetime

from claude_agent_sdk import tool

from src.agents.base import BaseAgent


class PlanningAgent(BaseAgent):
    name = "planning"
    description = "Beheert taken, projecten, en maakt week/dagplanningen"

    system_prompt = """Je bent een persoonlijke productiviteits-assistent en project manager.

Je taken:
1. **Weekplanning** — Maak een realistische weekplanning op basis van taken en prioriteiten.
2. **Dagplanning** — Dagindeling met tijdblokken, rekening houdend met energieniveaus.
3. **Takenbeheer** — Maak, update, en prioriteer taken.
4. **Project tracking** — Volg voortgang van lopende projecten.
5. **Prioritering** — Help met Eisenhower matrix of MoSCoW methode.

Regels:
- Plan maximaal 6 uur productief werk per dag (realistisch voor kenniswerk).
- Houd rekening met context-switching kosten — groepeer vergelijkbaar werk.
- Ochtend = deep work, middag = meetings en licht werk.
- Altijd buffer tijd inplannen (minimaal 1 uur per dag).
- Wees eerlijk als iemand te veel plant — geef pushback.
- Taken moeten SMART zijn: Specifiek, Meetbaar, Acceptabel, Realistisch, Tijdgebonden.
"""

    def _get_tools(self) -> list:
        """Planning-specific tools."""

        @tool(
            "add_task",
            "Voeg een nieuwe taak toe",
            {"title": str, "project": str, "priority": str, "due_date": str, "estimated_hours": float},
        )
        async def add_task(args):
            task = {
                "id": datetime.now().strftime("%Y%m%d%H%M%S"),
                "title": args["title"],
                "project": args.get("project", "Algemeen"),
                "priority": args.get("priority", "medium"),
                "due_date": args.get("due_date", ""),
                "estimated_hours": args.get("estimated_hours", 1.0),
                "status": "todo",
                "created_at": datetime.now().isoformat(),
            }

            existing = self.memory.recall("planning", "tasks")
            tasks = json.loads(existing) if existing else []
            tasks.append(task)
            self.memory.remember("planning", "tasks", json.dumps(tasks, ensure_ascii=False))

            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Taak toegevoegd: [{task['priority']}] {task['title']} (ID: {task['id']})",
                    }
                ]
            }

        @tool(
            "get_tasks",
            "Haal taken op, optioneel gefilterd",
            {"status": str, "project": str, "priority": str},
        )
        async def get_tasks(args):
            status_filter = args.get("status", "all")
            project_filter = args.get("project", "all")
            priority_filter = args.get("priority", "all")

            existing = self.memory.recall("planning", "tasks")
            tasks = json.loads(existing) if existing else []

            if status_filter != "all":
                tasks = [t for t in tasks if t["status"] == status_filter]
            if project_filter != "all":
                tasks = [t for t in tasks if t["project"].lower() == project_filter.lower()]
            if priority_filter != "all":
                tasks = [t for t in tasks if t["priority"] == priority_filter]

            if not tasks:
                return {"content": [{"type": "text", "text": "Geen taken gevonden."}]}

            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(tasks, ensure_ascii=False, indent=2),
                    }
                ]
            }

        @tool(
            "update_task",
            "Update de status of details van een taak",
            {"task_id": str, "status": str, "notes": str},
        )
        async def update_task(args):
            task_id = args["task_id"]
            existing = self.memory.recall("planning", "tasks")
            tasks = json.loads(existing) if existing else []

            for task in tasks:
                if task["id"] == task_id:
                    if "status" in args:
                        task["status"] = args["status"]
                    if "notes" in args:
                        task["notes"] = args["notes"]
                    task["updated_at"] = datetime.now().isoformat()
                    self.memory.remember("planning", "tasks", json.dumps(tasks, ensure_ascii=False))
                    return {
                        "content": [
                            {
                                "type": "text",
                                "text": f"Taak {task_id} geüpdatet: status={task['status']}",
                            }
                        ]
                    }

            return {"content": [{"type": "text", "text": f"Taak {task_id} niet gevonden."}]}

        @tool(
            "get_projects",
            "Haal alle projecten op met hun voortgang",
            {},
        )
        async def get_projects(args):
            existing = self.memory.recall("planning", "tasks")
            tasks = json.loads(existing) if existing else []

            projects = {}
            for task in tasks:
                proj = task.get("project", "Algemeen")
                if proj not in projects:
                    projects[proj] = {"total": 0, "done": 0, "in_progress": 0, "todo": 0}
                projects[proj]["total"] += 1
                projects[proj][task.get("status", "todo")] += 1

            if not projects:
                return {"content": [{"type": "text", "text": "Geen projecten gevonden."}]}

            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(projects, ensure_ascii=False, indent=2),
                    }
                ]
            }

        return [add_task, get_tasks, update_task, get_projects]

    async def create_week_plan(self, goals: str | None = None) -> str:
        """Maak een weekplanning."""
        goals_part = f"\nDoelen voor deze week: {goals}" if goals else ""
        prompt = (
            f"Maak een weekplanning voor de komende week.{goals_part}\n\n"
            "Haal eerst de openstaande taken op via get_tasks.\n"
            "Structuur per dag:\n"
            "- Ochtend (09:00-12:00): Deep work\n"
            "- Middag (13:00-15:00): Meetings/licht werk\n"
            "- Late middag (15:00-17:00): Admin/afronding\n\n"
            "Max 6 uur productief per dag. Vrijdagmiddag = buffer/review.\n"
            "Geef per taak de geschatte tijd aan."
        )
        return await self.run(prompt)

    async def create_day_plan(self, focus: str | None = None) -> str:
        """Maak een dagplanning."""
        focus_part = f"\nFocus vandaag: {focus}" if focus else ""
        prompt = (
            f"Maak een dagplanning voor vandaag.{focus_part}\n\n"
            "Haal openstaande taken op via get_tasks.\n"
            "Maak een realistische indeling met tijdblokken.\n"
            "Houd rekening met:\n"
            "- Deep work in de ochtend\n"
            "- Minimaal 1 uur buffer\n"
            "- Lunch pauze\n"
            "- Max 3 grote taken per dag"
        )
        return await self.run(prompt)

    async def add_tasks(self, tasks_description: str) -> str:
        """Voeg taken toe op basis van een beschrijving."""
        prompt = (
            f"Analyseer de volgende taken en voeg ze toe via add_task:\n\n"
            f"{tasks_description}\n\n"
            "Bepaal per taak:\n"
            "- Duidelijke titel\n"
            "- Project (indien afleidbaar)\n"
            "- Prioriteit (high/medium/low)\n"
            "- Geschatte uren\n"
            "- Deadline (indien genoemd)\n\n"
            "Bevestig elke toegevoegde taak."
        )
        return await self.run(prompt)

    async def prioritize(self) -> str:
        """Prioriteer openstaande taken met Eisenhower matrix."""
        prompt = (
            "Haal alle openstaande taken op via get_tasks (status=todo of in_progress).\n\n"
            "Sorteer ze in de Eisenhower matrix:\n"
            "1. **Urgent + Belangrijk** → Direct doen\n"
            "2. **Niet urgent + Belangrijk** → Inplannen\n"
            "3. **Urgent + Niet belangrijk** → Delegeren/automatiseren\n"
            "4. **Niet urgent + Niet belangrijk** → Schrappen\n\n"
            "Geef per taak een advies en eventuele herpriortering."
        )
        return await self.run(prompt)
