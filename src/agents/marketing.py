"""Marketing & Content agent — generates social media posts, blog outlines, and content plans."""

from claude_agent_sdk import tool

from src.agents.base import BaseAgent


class MarketingAgent(BaseAgent):
    name = "marketing"
    description = "Genereert marketing content: LinkedIn posts, blog outlines, content kalenders"

    system_prompt = """Je bent een senior marketing strateeg en content creator voor een AI/tech consultancy.

Je taken:
1. **LinkedIn posts** — Professioneel, waardevol, engaging. Geen clichés of buzzwords.
   Format: Hook (1 zin) → Context → Inzicht/waarde → Call-to-action. Max 1300 tekens.
2. **Blog outlines** — SEO-geoptimaliseerd, praktisch, gericht op de doelgroep.
3. **Content kalenders** — Weekplanning met mix van content types.
4. **Social media strategie** — Advies over frequentie, timing, engagement.

Regels:
- Schrijf vanuit eerste persoon (ik/wij) tenzij anders gevraagd.
- Gebruik concrete voorbeelden en data waar mogelijk.
- Vermijd: "In het huidige landschap", "game-changer", "revolutionair", lege beloftes.
- Focus op waarde leveren, niet op verkopen.
- Toon expertise door diepgang, niet door jargon.
"""

    def _get_tools(self) -> list:
        """Marketing-specific tools."""

        @tool(
            "get_trending_topics",
            "Zoek trending topics in AI/tech voor content inspiratie",
            {"niche": str},
        )
        async def get_trending_topics(args):
            niche = args.get("niche", "AI consultancy")
            # In v2 kan dit een echte API call worden
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Trending topics voor '{niche}': "
                        "1. AI agents in productie, "
                        "2. RAG vs fine-tuning, "
                        "3. AI ROI berekenen, "
                        "4. LLM kosten optimalisatie, "
                        "5. AI governance en compliance",
                    }
                ]
            }

        @tool(
            "get_past_content",
            "Bekijk eerder gegenereerde content voor consistentie",
            {"limit": int},
        )
        async def get_past_content(args):
            limit = args.get("limit", 5)
            logs = self.memory.get_recent_logs("marketing", limit=limit)
            if not logs:
                return {
                    "content": [
                        {"type": "text", "text": "Geen eerdere content gevonden."}
                    ]
                }
            summaries = []
            for log in logs:
                summaries.append(
                    f"- [{log['created_at']}] {log['action']}: {log['output'][:100]}..."
                )
            return {
                "content": [{"type": "text", "text": "\n".join(summaries)}]
            }

        return [get_trending_topics, get_past_content]

    async def generate_linkedin_post(self, topic: str | None = None) -> str:
        """Generate a LinkedIn post, optionally about a specific topic."""
        if topic:
            prompt = f"Schrijf een LinkedIn post over: {topic}"
        else:
            prompt = (
                "Schrijf een LinkedIn post over een relevant AI/tech onderwerp "
                "dat aansluit bij mijn diensten. Gebruik get_trending_topics "
                "om een actueel onderwerp te kiezen."
            )
        return await self.run(prompt)

    async def generate_blog_outline(self, topic: str) -> str:
        """Generate a blog post outline."""
        prompt = (
            f"Maak een gedetailleerde blog outline over: {topic}\n\n"
            "Inclusief: titel, meta description, H2/H3 structuur, "
            "kernpunten per sectie, en SEO keywords."
        )
        return await self.run(prompt)

    async def generate_content_plan(self, weeks: int = 1) -> str:
        """Generate a content calendar."""
        prompt = (
            f"Maak een content kalender voor de komende {weeks} "
            f"{'week' if weeks == 1 else 'weken'}.\n\n"
            "Per dag: type content (LinkedIn/blog/newsletter), onderwerp, "
            "korte beschrijving. Mix van thought leadership, tips, "
            "en case studies."
        )
        return await self.run(prompt)
