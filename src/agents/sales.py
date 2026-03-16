"""Sales agent — offertes, follow-up emails, en lead management."""

import json
from datetime import datetime

from src.agents.compat import tool

from src.agents.base import BaseAgent


class SalesAgent(BaseAgent):
    name = "sales"
    description = "Genereert offertes, follow-up emails, en beheert leads/pipeline"

    system_prompt = """Je bent een ervaren sales consultant voor een AI/tech consultancy.

Je taken:
1. **Offertes** — Professionele offertes op basis van klantbehoefte en diensten.
   Structuur: Samenvatting → Probleemanalyse → Oplossing → Aanpak/fasen → Investering → Tijdlijn → Voorwaarden.
2. **Follow-up emails** — Persoonlijk, waardevol, niet pushy. Altijd een reden om te mailen.
3. **Cold outreach** — Korte, relevante eerste contactemails. Toon begrip van hun situatie.
4. **Lead kwalificatie** — Analyseer of een lead past bij onze diensten (BANT: Budget, Authority, Need, Timeline).
5. **Pitch decks** — Kernboodschappen en structuur voor presentaties.

Regels:
- Schrijf altijd persoonlijk en specifiek. Geen generieke templates.
- Offertes: gebruik concrete bedragen op basis van de tarievenlijst.
- Emails: max 150 woorden voor cold outreach, max 200 voor follow-ups.
- Vermijd: "Ik hoop dat het goed met u gaat", "Even een herinnering", drukke layouts.
- Focus op de klant, niet op ons. Laat zien dat we hun probleem begrijpen.
- Gebruik informeel 'je' tenzij de klant formeel communiceert.
"""

    def _get_tools(self) -> list:
        """Sales-specific tools."""

        @tool(
            "get_service_pricing",
            "Haal tarievenlijst op voor offertes en prijsindicaties",
            {"service_type": str},
        )
        async def get_service_pricing(args):
            service_type = args.get("service_type", "all")
            pricing = {
                "AI Strategie Advies": {
                    "dagdeel": "€750",
                    "dag": "€1.400",
                    "traject": "€3.500 - €8.000",
                    "beschrijving": "Strategisch advies, roadmap, business case",
                },
                "AI Implementatie": {
                    "dag": "€1.200",
                    "sprint_2w": "€9.500",
                    "project": "€15.000 - €45.000",
                    "beschrijving": "Hands-on bouwen van AI oplossingen",
                },
                "AI Workshop": {
                    "halve_dag": "€1.500",
                    "hele_dag": "€2.500",
                    "beschrijving": "Team training en hands-on workshop",
                },
                "Retainer": {
                    "maand_1dag": "€1.100/maand",
                    "maand_2dag": "€2.000/maand",
                    "beschrijving": "Doorlopende ondersteuning en advies",
                },
            }
            if service_type != "all" and service_type in pricing:
                pricing = {service_type: pricing[service_type]}
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(pricing, ensure_ascii=False, indent=2),
                    }
                ]
            }

        @tool(
            "save_lead",
            "Sla lead informatie op in het geheugen",
            {"company": str, "contact": str, "notes": str},
        )
        async def save_lead(args):
            company = args["company"]
            contact = args.get("contact", "")
            notes = args.get("notes", "")
            lead_data = {
                "company": company,
                "contact": contact,
                "notes": notes,
                "status": "new",
                "created_at": datetime.now().isoformat(),
            }
            # Sla op in memory store
            existing = self.memory.recall("sales", "leads")
            leads = json.loads(existing) if existing else []
            leads.append(lead_data)
            self.memory.remember("sales", "leads", json.dumps(leads, ensure_ascii=False))
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Lead opgeslagen: {company} ({contact})",
                    }
                ]
            }

        @tool(
            "get_leads",
            "Haal alle opgeslagen leads op",
            {"status_filter": str},
        )
        async def get_leads(args):
            status_filter = args.get("status_filter", "all")
            existing = self.memory.recall("sales", "leads")
            leads = json.loads(existing) if existing else []
            if status_filter != "all":
                leads = [l for l in leads if l.get("status") == status_filter]
            if not leads:
                return {
                    "content": [
                        {"type": "text", "text": "Geen leads gevonden."}
                    ]
                }
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(leads, ensure_ascii=False, indent=2),
                    }
                ]
            }

        @tool(
            "get_past_interactions",
            "Bekijk eerdere sales interacties voor context",
            {"limit": int},
        )
        async def get_past_interactions(args):
            limit = args.get("limit", 10)
            logs = self.memory.get_recent_logs("sales", limit=limit)
            if not logs:
                return {
                    "content": [
                        {"type": "text", "text": "Geen eerdere interacties gevonden."}
                    ]
                }
            summaries = []
            for log in logs:
                summaries.append(
                    f"- [{log['created_at']}] {log['action']}: {log['output'][:150]}..."
                )
            return {
                "content": [{"type": "text", "text": "\n".join(summaries)}]
            }

        return [get_service_pricing, save_lead, get_leads, get_past_interactions]

    async def generate_quote(
        self,
        client_name: str,
        client_need: str,
        service_type: str | None = None,
    ) -> str:
        """Genereer een professionele offerte."""
        service_hint = f" Focus op de dienst: {service_type}." if service_type else ""
        prompt = (
            f"Maak een professionele offerte voor {client_name}.\n\n"
            f"Klantbehoefte: {client_need}\n"
            f"{service_hint}\n\n"
            "Gebruik get_service_pricing om de juiste tarieven op te halen. "
            "Structuur: Samenvatting → Probleemanalyse → Voorgestelde oplossing → "
            "Aanpak in fasen → Investering (concreet) → Tijdlijn → Voorwaarden.\n\n"
            "Maak het persoonlijk en specifiek voor deze klant. "
            "Output in nette markdown."
        )
        return await self.run(prompt)

    async def generate_follow_up(
        self,
        client_name: str,
        context: str,
        follow_up_type: str = "after_meeting",
    ) -> str:
        """Genereer een follow-up email."""
        type_instructions = {
            "after_meeting": "Bedank voor het gesprek, vat de key takeaways samen, "
            "en geef een duidelijke volgende stap.",
            "after_quote": "Refereer aan de verstuurde offerte, bied aan om vragen "
            "te beantwoorden, en stel een belmoment voor.",
            "check_in": "Deel iets waardevols (artikel, inzicht, case) dat relevant "
            "is voor hun situatie. Geen harde sell.",
            "re_engage": "Kort en vriendelijk. Refereer aan eerder contact. "
            "Bied een concreet haakje (nieuw inzicht, case study, event).",
        }
        instruction = type_instructions.get(follow_up_type, type_instructions["after_meeting"])
        prompt = (
            f"Schrijf een follow-up email aan {client_name}.\n\n"
            f"Context: {context}\n"
            f"Type: {follow_up_type}\n"
            f"Instructie: {instruction}\n\n"
            "Max 200 woorden. Persoonlijk, niet pushy. "
            "Duidelijke call-to-action."
        )
        return await self.run(prompt)

    async def generate_cold_email(
        self,
        client_name: str,
        company: str,
        context: str,
    ) -> str:
        """Genereer een cold outreach email."""
        prompt = (
            f"Schrijf een cold outreach email aan {client_name} van {company}.\n\n"
            f"Wat we weten: {context}\n\n"
            "Regels:\n"
            "- Max 150 woorden\n"
            "- Toon dat je hun situatie begrijpt\n"
            "- Bied één concreet inzicht of waarde\n"
            "- Simpele, lage-drempel CTA (bijv. 15 min call)\n"
            "- Geen bijlagen, geen brochures, geen feature-lijsten\n"
            "- Onderwerpregel die nieuwsgierig maakt (niet clickbait)"
        )
        return await self.run(prompt)

    async def qualify_lead(self, company: str, info: str) -> str:
        """Analyseer en kwalificeer een lead (BANT)."""
        prompt = (
            f"Kwalificeer deze lead met het BANT framework:\n\n"
            f"Bedrijf: {company}\n"
            f"Beschikbare info: {info}\n\n"
            "Geef per criterium (Budget, Authority, Need, Timeline) een score "
            "(groen/oranje/rood) en toelichting. "
            "Eindig met een overall advies: wel/niet opvolgen, en zo ja, "
            "met welke aanpak.\n\n"
            "Sla de lead op via save_lead als het een nieuwe lead is."
        )
        return await self.run(prompt)
