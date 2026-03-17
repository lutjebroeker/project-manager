# Volledig Overzicht & Gap Analysis — VOF Jelle & Daan

## Context

Jelle en Daan starten een VOF (Vennootschap Onder Firma) gericht op AI & Technology Consulting. Er is al een aanzienlijk platform gebouwd. Dit document geeft een volledig overzicht van wat er is, wat er mist, en wat de prioriteiten zijn om een solide basis neer te zetten waarmee jullie kunnen doorgroeien.

---

## DEEL 1: WAT ER AL IS (Inventaris)

### A. AI Business Agent Platform (`ai-business-agent/`)

**5 Gespecialiseerde AI Agents:**

| Agent | Functionaliteiten |
|-------|------------------|
| **Marketing** | LinkedIn posts, blog outlines, content calendars |
| **Sales** | Offertes, follow-ups, cold emails, lead kwalificatie (BANT) |
| **Finance** | Facturatie (21% BTW), urenregistratie, financiële rapportages |
| **Planning** | Week-/dagplanning, taakbeheer, Eisenhower matrix |
| **Builder** | Meta-agent: bouwt plugins en connectors vanuit natuurlijke taal |

**Core Features:**
- Zelflerend systeem (feedback → preferenties → prompt verbetering)
- Prompt versioning met rollback
- Cross-agent kennisdeling
- CLAUDE.md sync (geleerde voorkeuren → Claude context)
- Multi-LLM providers (Claude SDK, Anthropic, OpenAI, Ollama)
- MCP integratie voor Claude Desktop
- Obsidian vault indexing
- n8n webhook automatie
- Plugin systeem (dynamisch uitbreidbaar)
- REST API (50+ endpoints) + Bearer token auth
- Web dashboard
- SQLite database (7 tabellen)
- Docker deployment
- 92+ tests in 9 test suites

**Pricing in business context:**
- AI Strategy: €750 - €8.000
- AI Implementation: €1.200 - €45.000
- Workshops: €1.500 - €2.500
- Retainer: €1.100 - €2.000/maand

### B. Project Manager (`project-manager/`)
- Vercel-hosted dashboard voor projectbeheer
- 7 n8n workflows (start/stop/new project sessions)
- Tmux-based sessiebeheer op server

### C. Claude Config (`claude-config/`)
- Version-controlled Claude Code settings
- Git safety hooks
- SessionStart skill
- sync.sh voor symlinks naar ~/.claude/

---

## DEEL 2: WAT ER MIST — Gap Analysis

### P0 — KRITISCH (voor lancering VOF)

#### 1. AVG/GDPR Compliance
**Status:** Niet geïmplementeerd
**Risico:** Boetes tot 4% jaaromzet, reputatieschade

Wat mist:
- Verwerkersovereenkomst template voor klanten
- Privacy policy
- Data retention beleid (wat bewaar je, hoe lang)
- Recht op verwijdering (data wissen per klant)
- Logging van wie wat wanneer heeft ingezien (audit trail)
- Encryptie van klantdata at rest (SQLite is plaintext)

**Actie:** Verwerkersovereenkomst template + `DELETE /api/client/{name}/data` endpoint + encryptie SQLite

#### 2. Contract & Offerte Management
**Status:** Sales agent maakt offertes, maar geen signing/tracking
**Risico:** Geen juridische basis voor werk

Wat mist:
- Standaard contract templates (raamovereenkomst, projectovereenkomst)
- Offerte → akkoord → factuur workflow
- Digitale ondertekening
- Contractversioning

**Actie:** BUY — Gebruik een tool als [Proposify](https://proposify.com), [PandaDoc](https://pandadoc.com), of simpelweg PDF + DocuSign. Integreer via n8n webhook.

#### 3. Boekhouding & Fiscale Vereisten
**Status:** Finance agent doet basale facturatie + BTW overzicht
**Risico:** Niet compliant met Nederlandse fiscale vereisten

Wat mist:
- 7 jaar bewaarplicht (SQLite backup strategie)
- Factuurnummering moet doorlopend en ononderbroken zijn
- Debiteurenbeheer (betaaltermijn tracking, herinneringen)
- Aansluiting met boekhoudpakket (wettelijk vereist voor VOF)
- Jaarrekening voorbereiding
- BTW-aangifte export (compatible met Belastingdienst)

**Actie:** BUY boekhoudpakket (Moneybird of e-Boekhouden) + BUILD integratie via hun API

#### 4. Backup & Data Veiligheid
**Status:** Enkele SQLite file, geen backup strategie
**Risico:** Dataverlies

Wat mist:
- Automatische backups (dagelijks minimum)
- Off-site backup (niet alleen op dezelfde server)
- Recovery procedure getest
- Database migratie strategie

**Actie:** BUILD — Cronjob voor SQLite backup + sync naar cloud storage (S3/Backblaze B2)

#### 5. HTTPS & API Security
**Status:** Bearer token, geen HTTPS in eigen deployment
**Risico:** Credentials in plaintext over netwerk

Wat mist:
- TLS/HTTPS (via reverse proxy: Caddy of nginx)
- Rate limiting
- Input validation/sanitization
- Secrets management (tokens in .env file = fragiel)
- CORS configuratie

**Actie:** BUILD — Caddy reverse proxy (auto-HTTPS) + rate limiter middleware in FastAPI

---

### P1 — BELANGRIJK (eerste 6 maanden)

#### 6. Multi-User Support
**Status:** Single-user, single token
**Impact:** Daan kan niet parallel werken

Wat mist:
- User accounts (minimaal Jelle + Daan)
- Per-user API tokens
- Activiteitslog per gebruiker
- Role-based access (admin vs user)

**Actie:** BUILD — Simpele user tabel + JWT tokens. Geen OAuth nodig voor 2 personen.

#### 7. CRM Verbetering
**Status:** Basis lead tracking in Sales agent
**Impact:** Geen compleet klantoverzicht

Wat mist:
- Klant lifecycle tracking (prospect → lead → klant → terugkerend)
- Contactpersonen per organisatie
- Interactiehistorie (calls, mails, meetings)
- Pipeline visualisatie
- Verwachte omzet forecast

**Actie:** Twijfelgeval BUILD vs BUY. Voor 2 personen: BUILD minimale CRM in platform (jullie hebben al client knowledge). Voor 5+ personen: BUY (HubSpot Free, Pipedrive).

#### 8. Nederlandse Boekhoudintegratie
**Status:** Niet aanwezig
**Impact:** Dubbel werk (handmatig overzetten)

Opties:
- **Moneybird** — Populair bij ZZP/VOF, goede API, €16,50/maand
- **e-Boekhouden** — Goedkoop, basis API
- **Exact Online** — Enterprise, duur maar compleet

**Actie:** BUILD connector via Builder agent of handmatig. Moneybird API is goed gedocumenteerd. Sync: facturen, BTW, urenregistratie.

#### 9. CI/CD Pipeline
**Status:** Geen
**Impact:** Handmatig testen en deployen

Wat mist:
- GitHub Actions workflow (lint, test, deploy)
- Automatische tests bij PR
- Deployment pipeline (staging → productie)

**Actie:** BUILD — GitHub Actions workflow (~1 uur werk)

#### 10. Monitoring & Observability
**Status:** Alleen `/status` endpoint
**Impact:** Geen zicht op uptime, errors, performance

Wat mist:
- Structured logging (JSON logs)
- Error alerting (email/Slack bij crashes)
- Uptime monitoring
- Request metrics

**Actie:** BUILD basis logging + BUY uptime monitor (UptimeRobot gratis, of Healthchecks.io)

#### 11. Kalender Integratie
**Status:** Planning agent plant, maar niet gekoppeld aan agenda
**Impact:** Planningen worden niet automatisch geblokt

**Actie:** BUILD — Google Calendar API integratie via n8n of directe connector

---

### P2 — NICE TO HAVE (6-12 maanden)

#### 12. Client Portal
- Klanten kunnen eigen facturen/offertes inzien
- Project status dashboard voor klanten
- Zelfbediening voor simpele verzoeken

#### 13. Document Management
- Templates opslag en versioning
- Projectdocumentatie per klant
- Knowledge base doorzoekbaar voor team

#### 14. Banking Integratie (PSD2)
- Automatisch matchen van betalingen met facturen
- Bunq/ING/ABN AMRO via open banking APIs
- Real-time cash flow overzicht

#### 15. Geavanceerde Analytics
- Revenue per klant/dienst/maand
- Uurtarief effectiviteit
- Marketing ROI (welke content → leads → omzet)
- Voorspellend model voor pipeline

#### 16. Team Onboarding
- Documentatie voor nieuwe medewerkers
- Gestandaardiseerde werkwijzen
- Kennisbank met best practices

---

## DEEL 3: BUILD vs BUY Samenvatting

| Onderdeel | Advies | Reden |
|-----------|--------|-------|
| Boekhouding | **BUY** (Moneybird) | Wettelijk vereist, te complex om zelf te bouwen |
| Contracten/signing | **BUY** (PandaDoc/DocuSign) | Juridische geldigheid, niet je core business |
| CRM | **BUILD** (uitbreiden platform) | Jullie hebben al de basis, uniek door AI-integratie |
| CI/CD | **BUILD** (GitHub Actions) | Simpel, eenmalig ~1 uur |
| Backup | **BUILD** (cronjob + cloud sync) | Simpel, kritisch |
| HTTPS | **BUILD** (Caddy) | Eenmalige setup |
| Monitoring | **MIX** — BUILD logging, BUY uptime | Pragmatisch |
| Kalender | **BUILD** via n8n | n8n heeft native Google Calendar nodes |
| Banking | **BUY** later | PSD2 integratie is complex |
| AVG templates | **BUY** (jurist) | Juridisch advies nodig |

---

## DEEL 4: COMPETITIEF VOORDEEL

### Waar jullie UNIEK in zijn (dubbel inzetten):
1. **Zelflerend systeem** — Geen enkel off-the-shelf tool leert van feedback en verbetert zichzelf
2. **Cross-agent kennisdeling** — Sales weet wat Finance weet. Dat is enterprise-niveau AI orchestration
3. **Plugin builder** — Klanten vragen om een integratie → jullie bouwen het in minuten
4. **Provider-agnostisch** — Geen vendor lock-in, schaal van gratis (Ollama) tot premium (Claude)
5. **MCP native** — Direct bruikbaar vanuit Claude Desktop/Code

### Waar jullie NIET in moeten investeren:
- Eigen boekhoudmodule bouwen (Moneybird doet het beter)
- Eigen e-mail versturen (gebruik Resend/Postmark via n8n)
- Eigen hosting panel (gebruik Coolify of gewoon Docker)

---

## DEEL 5: GROEI-ROADMAP

### Maand 1-2: Fundament (P0)
- [ ] AVG/GDPR compliance (verwerkersovereenkomst, data deletion)
- [ ] Moneybird account + basis integratie
- [ ] Caddy reverse proxy + HTTPS
- [ ] SQLite backup cronjob + off-site sync
- [ ] Contract templates laten opstellen door jurist
- [ ] GitHub Actions CI/CD

### Maand 3-4: Operationeel (P1)
- [ ] Multi-user support (Jelle + Daan accounts)
- [ ] CRM uitbreiden (lifecycle, pipeline)
- [ ] Moneybird full sync (facturen ↔ platform)
- [ ] Google Calendar integratie
- [ ] Monitoring + alerting

### Maand 5-6: Schalen
- [ ] Client portal (basis)
- [ ] Revenue analytics dashboard
- [ ] Eerste klant-specifieke plugin
- [ ] Team onboarding documentatie

### Maand 7-12: Groeien
- [ ] Banking integratie
- [ ] Geavanceerde analytics
- [ ] Mogelijk: platform als SaaS aanbieden aan andere consultancies

---

## DEEL 6: QUICK WINS (vandaag/deze week)

1. **SQLite backup script** — 15 min, voorkomt dataverlies
2. **GitHub Actions basis** — 30 min, runt tests automatisch
3. **Caddy installatie** — 30 min, HTTPS voor API
4. **Moneybird account aanmaken** — 10 min, gratis proefperiode
5. **`DELETE /api/client/{name}/data` endpoint** — 1 uur, AVG basis

---

---

## DEEL 7: LEARNINGS VAN n8n-claw

[freddy-schuetz/n8n-claw](https://github.com/freddy-schuetz/n8n-claw) is een zelf-gehoste AI agent op n8n + PostgreSQL + Claude met Telegram interface. Relevante vergelijking:

### Wat n8n-claw WEL heeft en wij NIET:

| Feature | n8n-claw | Ons platform | Actie |
|---------|----------|-------------|-------|
| **Telegram bot interface** | Ja — primaire interface | Nee — alleen API + dashboard | Overweeg: WhatsApp/Telegram bot als snelle interface voor onderweg |
| **Voice transcription** | OpenAI Whisper | Nee | P2 — leuk voor meeting notes |
| **Proactieve herinneringen** | Heartbeat elke 15 min + morning briefing | Nee — alleen reactief | **P1 — Dagelijkse briefing** ("Vandaag: 2 follow-ups, 1 factuur overdue, content calendar") |
| **Scheduled actions** | Agent voert taken uit op gezette tijden | Alleen via n8n triggers | Verbeteren: n8n scheduler → agent acties |
| **Memory consolidation** | Dagelijks om 3:00 samenvatten | Nee — groeit onbeperkt | **P1 — Memory cleanup** (samenvatten oude entries, archiveren) |
| **PostgreSQL + vector embeddings** | RAG met semantic search | SQLite + keyword search | **P1 — Upgrade naar vector search** voor betere kennisretrieval |
| **Web search** | SearXNG (zelf-gehost) | Nee | P2 — marktonderzoek agent zou dit kunnen gebruiken |
| **Web scraping** | Crawl4AI met JS rendering | Nee | P2 — handig voor competitive analysis |
| **Expert agents (sub-agents)** | Research, Content Creator, Data Analyst | Builder bouwt plugins, geen sub-agent delegatie | **P1 — Agent-to-agent delegatie** (Sales vraagt Finance om pricing check) |
| **Soul/personality config** | Database tabel voor persoonlijkheid | business_context.json (statisch) | Minor — onze aanpak werkt prima |
| **Credential management** | One-time links voor veilig delen | .env file | P2 — vault-achtige credential store |

### Wat WIJ WEL hebben en n8n-claw NIET:

| Feature | Ons platform | n8n-claw |
|---------|-------------|----------|
| **Zelflerend systeem** | Feedback → preferenties → betere output | Geen feedback loop |
| **Prompt versioning** | Rollback naar eerdere versies | Geen versioning |
| **Cross-agent knowledge sharing** | Sales ↔ Finance ↔ Marketing | Agents zijn geïsoleerd |
| **Provider-agnostisch** | 4 LLM backends | Alleen Claude |
| **MCP native** | Werkt in Claude Desktop/Code | Eigen MCP maar geen Claude integratie |
| **Plugin builder** | Bouw connectors vanuit taal | Bouwt MCP tools maar minder gestructureerd |
| **Business domain agents** | Specifiek voor consulting (offertes, facturen) | Generiek (research, content, data) |
| **Obsidian integratie** | Vault indexing | Nee |

### Top 3 ideeën om over te nemen:

1. **Dagelijkse briefing** (morning summary via n8n scheduler)
   - "Goedemorgen! Vandaag: 2 klantgesprekken, offerte X verloopt morgen, 3 uur content werk gepland"
   - Via Telegram/WhatsApp of als eerste MCP tool output

2. **Memory consolidation** (nachtelijke cleanup)
   - Samenvatten van agent logs ouder dan 30 dagen
   - Archiveren van afgeronde projecten
   - Voorkomt dat SQLite/kennisbank onbeheersbaar groeit

3. **Telegram/WhatsApp bot** als mobiele interface
   - Snel factuur status checken
   - "Maak een follow-up voor klant X"
   - Voice notes → transcriptie → agent actie
   - n8n heeft native Telegram nodes

---

## DEEL 8: TELEGRAM BOT — Implementatieplan

### Platform keuze: Slack + Telegram

**Slack als primaire werkplek:**
- **Kanalen per klant/project** — `#klant-acme`, `#klant-techcorp`, `#project-ai-strategie`
- **Interne kanalen** — `#sales-pipeline`, `#financieel`, `#content-planning`
- **Gratis tier** — 90 dagen berichthistorie, voldoende voor start
- **n8n native nodes** — Slack Trigger + Slack Send zijn built-in
- **Bot/App** — Slack App met slash commands + event subscriptions
- **Threading** — Agent antwoorden in threads houden per vraag
- **Twee gebruikers** — Jelle + Daan werken samen in dezelfde workspace

**Telegram als mobiele companion:**
- Snel iets checken onderweg
- Voice notes voor later verwerken
- Persoonlijke notificaties (briefing, reminders)

Beide interfaces praten met dezelfde `/webhook/run` backend — geen duplicatie.

### Architectuur

```
Slack Message / Slash Command          Telegram Message
    ↓                                      ↓
n8n Slack Trigger node              n8n Telegram Trigger node
    ↓                                      ↓
    └──────────── MERGE ──────────────────┘
                    ↓
         n8n Function node (intent parsing)
                    ↓
         n8n HTTP Request → POST /webhook/run
                    ↓
         AI Business Agent (bestaande webhook infra)
                    ↓
         Response terug via origineel kanaal
              ↓                    ↓
    Slack Send (in thread)    Telegram Send
```

**Geen code wijzigingen nodig aan het platform** — alles loopt via de bestaande `/webhook/run` endpoint. De intelligentie zit in de n8n workflow.

### Slack Workspace Structuur

```
#algemeen          — Team updates, announcements
#sales-pipeline    — Lead updates, offerte status, follow-up reminders
#financieel        — Factuur notificaties, betalingen, omzet updates
#content           — Content calendar, LinkedIn drafts ter review
#planning          — Dagelijkse briefing, weekplanning
#bot-testing       — Testen van bot commands

Per klant (aanmaken wanneer nodig):
#klant-acme-bv     — Alles over Acme: offerte, facturen, notities
#klant-techcorp    — Idem
```

**Bot reageert op:**
- Slash commands in elk kanaal
- @mentions in klant-kanalen (context-aware: weet in welk klantkanaal je zit)
- DM's voor persoonlijke queries

### Implementatie: n8n Workflow

**Workflow: "Telegram Bot Agent"**

1. **Telegram Trigger** — luistert op berichten naar @JullieBotNaam
2. **Intent Parser** (n8n Function node):
   ```
   /status     → GET /status
   /plan       → POST /webhook/planning/day-plan
   /week       → POST /webhook/planning/week-plan
   /factuur    → POST /webhook/finance/invoice + data
   /uren X Y   → POST /webhook/finance/log-hours
   /linkedin   → POST /webhook/marketing/linkedin-post
   /offerte    → POST /webhook/sales/quote
   /briefing   → Combinatie: planning + finance + sales status
   vrije tekst → POST /webhook/run met auto-detect agent
   ```
3. **HTTP Request** → bestaande webhook endpoints
4. **Response Formatter** — trim output voor Telegram (max 4096 chars, markdown)
5. **Telegram Send** — antwoord terug naar gebruiker

### Slash Commands (Slack + Telegram)

| Commando | Agent | Actie |
|----------|-------|-------|
| `/briefing` | Planning + Finance + Sales | Dagelijkse samenvatting |
| `/plan` | Planning | Dagplanning |
| `/week` | Planning | Weekplanning |
| `/taak [beschrijving]` | Planning | Taak toevoegen |
| `/uren [klant] [uren] [beschrijving]` | Finance | Uren loggen |
| `/factuur [klant] [beschrijving]` | Finance | Factuur aanmaken |
| `/linkedin [topic]` | Marketing | LinkedIn post genereren |
| `/offerte [klant] [behoefte]` | Sales | Offerte maken |
| `/followup [klant]` | Sales | Follow-up email |
| `/status` | Systeem | Platform status |
| `@bot [vrije tekst]` | Auto-detect | Stuur naar meest passende agent |

**Slack-specifiek:**
- In `#klant-*` kanalen: bot weet automatisch welke klant het betreft
- `/offerte dit project` in `#klant-acme-bv` → offerte voor Acme B.V. zonder klant te noemen
- Thread replies: agent antwoordt altijd in een thread om kanaal clean te houden

### Dagelijkse Briefing (automatisch)

**Nieuwe n8n workflow: "Morning Briefing"**

1. **Schedule Trigger** — elke werkdag om 08:00
2. **Parallel HTTP Requests:**
   - `POST /webhook/planning/day-plan` → taken vandaag
   - `GET /api/agent/finance/invoices?status=overdue` → openstaande facturen
   - `GET /api/agent/sales/leads?status=pending` → follow-ups nodig
3. **Merge + Format** → samenvatten in 1 bericht
4. **Slack Send** → naar `#planning` kanaal + **Telegram Send** → naar Jelle + Daan

**Voorbeeld output (Slack #planning):**
```
🌅 Goedemorgen! Hier is je briefing:

📋 Vandaag gepland:
• 09:00-11:00 — Deep work: AI strategie Acme B.V.
• 11:00-12:00 — Content: LinkedIn post
• 14:00-15:00 — Call: Demo TechCorp

💰 Financieel:
• 1 factuur overdue: €2.400 (Acme B.V., 7 dagen)
• Deze week gefactureerd: €4.800

📩 Follow-ups:
• TechCorp — offerte verstuurd 3 dagen geleden
• StartupXYZ — cold email, geen reactie (7d)
```

### Bestanden die NIET wijzigen
- `src/api/webhooks.py` — bestaande endpoints werken al
- `src/api/routes.py` — GET endpoints voor status queries bestaan al
- Geen Python code nodig

### Bestanden die WEL aangemaakt worden
- `workflows/slack-bot-agent.json` — n8n Slack bot workflow
- `workflows/telegram-bot-agent.json` — n8n Telegram bot workflow
- `workflows/morning-briefing.json` — n8n scheduled briefing (→ Slack + Telegram)

### Setup stappen

**Slack (primair):**
1. Maak Slack workspace aan (bijv. `jullie-vof.slack.com`)
2. Maak Slack App via api.slack.com → Bot Token + Slash Commands
3. Maak kanalen aan: `#planning`, `#sales-pipeline`, `#financieel`, `#content`
4. Importeer `slack-bot-agent.json` in n8n
5. Configureer Slack OAuth credentials in n8n
6. Test met `/status` in `#bot-testing`

**Telegram (companion):**
7. Maak Telegram bot via @BotFather → krijg `TELEGRAM_BOT_TOKEN`
8. Importeer `telegram-bot-agent.json` in n8n
9. Test met `/briefing`

**Morning Briefing:**
10. Importeer `morning-briefing.json` in n8n
11. Configureer schedule (werkdagen 08:00)

### Later uitbreiden (P2)
- Voice messages → OpenAI Whisper transcriptie → agent
- Foto's van bonnen → Finance agent voor boekhouding
- Slack interactive buttons voor snelle feedback (+1/-1)
- Slack canvas/bookmarks voor offerte previews
- Automatisch klant-kanaal aanmaken bij nieuwe lead

---

## Verificatie

Na implementatie van P0 items:
1. `curl -k https://jouw-server/status` → HTTPS werkt
2. `python -m pytest tests/ -v` → alle tests passing
3. Moneybird API test → factuur aanmaken werkt
4. SQLite backup check → backup file bestaat op remote storage
5. `DELETE /api/client/test/data` → data daadwerkelijk verwijderd
