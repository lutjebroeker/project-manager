"""Finance agent — facturen, urenregistratie, en financiële rapportages."""

import json
from datetime import datetime

from src.agents.compat import tool

from src.agents.base import BaseAgent


class FinanceAgent(BaseAgent):
    name = "finance"
    description = "Genereert facturen, registreert uren, en maakt financiële rapportages"

    system_prompt = """Je bent een financieel assistent voor een AI/tech consultancy VOF (Vennootschap onder Firma).
De VOF heeft twee vennoten: Jelle Spek en Daan Koedam.

Je taken:
1. **Facturen** — Professionele facturen in gestructureerd formaat.
   Verplichte velden: factuurnummer, datum, vervaldatum (14 dagen), klantgegevens,
   omschrijving per regel, uren × tarief, subtotaal, BTW (21%), totaal.
   Facturen worden verstuurd op naam van de VOF.
2. **Urenregistratie** — Log uren per project/klant, per vennoot.
3. **Financieel overzicht** — Maand/kwartaal/jaar rapportages: omzet, kosten, winst.
   Houd rekening met de winstverdeling tussen vennoten.
4. **BTW aangifte voorbereiding** — Overzicht van BTW bedragen voor kwartaalaangifte.
5. **Offerte naar factuur** — Converteer geaccepteerde offertes naar facturen.

Regels:
- Bedragen altijd in EUR met 2 decimalen.
- BTW altijd 21% tenzij anders aangegeven (0% voor buitenland B2B met geldig BTW-id).
- Factuurnummers: JJJJ-NNN formaat (bijv. 2026-001).
- Betalingstermijn standaard 14 dagen.
- Output facturen in gestructureerde markdown die makkelijk naar PDF kan.
- Wees nauwkeurig met berekeningen — controleer altijd je rekenwerk.
- VOF-specifiek: winst wordt verdeeld volgens de VOF-overeenkomst.
"""

    def _get_tools(self) -> list:
        """Finance-specific tools."""

        @tool(
            "log_hours",
            "Registreer gewerkte uren voor een klant/project",
            {"client": str, "project": str, "hours": float, "description": str, "date": str},
        )
        async def log_hours(args):
            client = args["client"]
            project = args.get("project", "Algemeen")
            hours = args["hours"]
            description = args.get("description", "")
            date = args.get("date", datetime.now().strftime("%Y-%m-%d"))

            entry = {
                "client": client,
                "project": project,
                "hours": hours,
                "description": description,
                "date": date,
            }

            existing = self.memory.recall("finance", "hours_log")
            hours_log = json.loads(existing) if existing else []
            hours_log.append(entry)
            self.memory.remember("finance", "hours_log", json.dumps(hours_log, ensure_ascii=False))

            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Uren gelogd: {hours}u voor {client} ({project}) op {date}",
                    }
                ]
            }

        @tool(
            "get_hours",
            "Haal gelogde uren op, optioneel gefilterd op klant of periode",
            {"client": str, "month": str},
        )
        async def get_hours(args):
            client_filter = args.get("client", "all")
            month_filter = args.get("month", "all")

            existing = self.memory.recall("finance", "hours_log")
            hours_log = json.loads(existing) if existing else []

            if client_filter != "all":
                hours_log = [h for h in hours_log if h["client"].lower() == client_filter.lower()]
            if month_filter != "all":
                hours_log = [h for h in hours_log if h["date"].startswith(month_filter)]

            if not hours_log:
                return {"content": [{"type": "text", "text": "Geen uren gevonden."}]}

            total = sum(h["hours"] for h in hours_log)
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(
                            {"entries": hours_log, "total_hours": total},
                            ensure_ascii=False,
                            indent=2,
                        ),
                    }
                ]
            }

        @tool(
            "save_invoice",
            "Sla een factuur op in het geheugen",
            {"invoice_number": str, "client": str, "amount": float, "status": str},
        )
        async def save_invoice(args):
            invoice = {
                "invoice_number": args["invoice_number"],
                "client": args["client"],
                "amount": args["amount"],
                "status": args.get("status", "draft"),
                "created_at": datetime.now().isoformat(),
            }

            existing = self.memory.recall("finance", "invoices")
            invoices = json.loads(existing) if existing else []
            invoices.append(invoice)
            self.memory.remember("finance", "invoices", json.dumps(invoices, ensure_ascii=False))

            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Factuur {invoice['invoice_number']} opgeslagen: €{invoice['amount']:.2f} voor {invoice['client']}",
                    }
                ]
            }

        @tool(
            "get_invoices",
            "Haal alle facturen op, optioneel gefilterd",
            {"status": str, "client": str},
        )
        async def get_invoices(args):
            status_filter = args.get("status", "all")
            client_filter = args.get("client", "all")

            existing = self.memory.recall("finance", "invoices")
            invoices = json.loads(existing) if existing else []

            if status_filter != "all":
                invoices = [i for i in invoices if i["status"] == status_filter]
            if client_filter != "all":
                invoices = [i for i in invoices if i["client"].lower() == client_filter.lower()]

            if not invoices:
                return {"content": [{"type": "text", "text": "Geen facturen gevonden."}]}

            total = sum(i["amount"] for i in invoices)
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(
                            {"invoices": invoices, "total_amount": total},
                            ensure_ascii=False,
                            indent=2,
                        ),
                    }
                ]
            }

        @tool(
            "get_service_rates",
            "Haal uurtarieven en dagprijzen op voor factuurberekening",
            {"service_type": str},
        )
        async def get_service_rates(args):
            rates = {
                "AI Strategie Advies": {"uur": 175, "dag": 1400},
                "AI Implementatie": {"uur": 150, "dag": 1200},
                "AI Workshop": {"halve_dag": 1500, "hele_dag": 2500},
                "Retainer": {"maand_1dag_pw": 1100, "maand_2dag_pw": 2000},
            }
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(rates, ensure_ascii=False, indent=2),
                    }
                ]
            }

        return [log_hours, get_hours, save_invoice, get_invoices, get_service_rates]

    async def generate_invoice(
        self,
        client_name: str,
        description: str,
        hours: float | None = None,
        fixed_amount: float | None = None,
        service_type: str = "AI Implementatie",
    ) -> str:
        """Genereer een professionele factuur."""
        pricing_info = ""
        if hours:
            pricing_info = f"Aantal uren: {hours}, dienst type: {service_type} (haal tarief op via get_service_rates)"
        elif fixed_amount:
            pricing_info = f"Vast bedrag: €{fixed_amount:.2f}"
        else:
            pricing_info = f"Bepaal het bedrag op basis van de omschrijving en get_service_rates"

        prompt = (
            f"Maak een professionele factuur voor {client_name}.\n\n"
            f"Omschrijving: {description}\n"
            f"Prijsinfo: {pricing_info}\n\n"
            "Verplichte elementen:\n"
            "- Factuurnummer (JJJJ-NNN formaat, gebruik get_invoices om het volgende nummer te bepalen)\n"
            "- Factuurdatum: vandaag\n"
            "- Vervaldatum: 14 dagen\n"
            "- Gegevens: Spek & Koedam AI Consultancy VOF (uit business context)\n"
            "- Klantgegevens\n"
            "- Regels met omschrijving, aantal, tarief, bedrag\n"
            "- Subtotaal, BTW 21%, Totaal\n\n"
            "Sla de factuur op via save_invoice na het genereren.\n"
            "Output in nette markdown tabel format."
        )
        return await self.run(prompt)

    async def financial_report(self, period: str = "current_month") -> str:
        """Genereer een financieel overzicht."""
        prompt = (
            f"Maak een financieel overzicht voor periode: {period}.\n\n"
            "Gebruik get_invoices en get_hours om alle data op te halen.\n"
            "Structuur:\n"
            "- Omzet overzicht (per klant)\n"
            "- Gefactureerd vs openstaand\n"
            "- Gewerkte uren overzicht\n"
            "- Gemiddeld uurtarief\n"
            "- BTW overzicht (voor aangifte)\n\n"
            "Als er nog geen data is, geef dan een leeg template "
            "en leg uit hoe de data gevuld kan worden."
        )
        return await self.run(prompt)

    async def log_time(
        self,
        client: str,
        hours: float,
        description: str,
        project: str = "Algemeen",
    ) -> str:
        """Log uren voor een klant/project."""
        prompt = (
            f"Registreer de volgende uren via log_hours:\n"
            f"- Klant: {client}\n"
            f"- Project: {project}\n"
            f"- Uren: {hours}\n"
            f"- Omschrijving: {description}\n"
            f"- Datum: vandaag\n\n"
            "Bevestig de registratie en geef een overzicht van "
            "de totale uren voor deze klant deze maand."
        )
        return await self.run(prompt)
