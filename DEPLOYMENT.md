# AI Business Agent — Deployment Guide

## Wat je nodig hebt

- Server: `root@192.168.1.34`
- Claude Max abonnement (ingelogd via `claude login`)
- Optioneel: Obsidian vault op de server (of via sync)

---

## Stap 1: Business context invullen

Pas `data/business_context.json` aan met jouw echte info:
- Bedrijfsnaam, beschrijving, diensten
- Tarieven, doelgroep, tone of voice

Dit is het bestand dat alle agents gebruiken om gepersonaliseerde output te genereren.

---

## Stap 2: Deployen op de server

```bash
ssh root@192.168.1.34
cd /root/projects
git clone <repo-url> ai-business-agent
cd ai-business-agent
git checkout claude/agentic-ai-business-plan-O0Uxu
bash setup.sh
```

Het setup script:
- Maakt een virtual environment
- Installeert alle dependencies
- Draait de tests (92 stuks)
- Genereert een API token → **bewaar dit token!**

---

## Stap 3: .env aanpassen

```bash
nano .env
```

| Variabele | Wat invullen |
|-----------|-------------|
| `OBSIDIAN_VAULT_PATH` | Pad naar je Obsidian vault op de server (of leeg laten) |
| `API_TOKEN` | Wordt auto-gegenereerd door setup.sh |

---

## Stap 4: Server starten

**Optie A — Direct:**
```bash
source .venv/bin/activate
python -m src.main
```

**Optie B — Docker:**
```bash
docker-compose up -d
```

**Optie C — Als systemd service (persistent):**
```bash
cat > /etc/systemd/system/ai-business-agent.service << 'EOF'
[Unit]
Description=AI Business Agent
After=network.target

[Service]
Type=simple
WorkingDirectory=/root/projects/ai-business-agent
ExecStart=/root/projects/ai-business-agent/.venv/bin/python -m src.main
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl enable ai-business-agent
systemctl start ai-business-agent
```

---

## Stap 5: MCP koppelen aan Claude Desktop

Op je **Mac/PC**, bewerk je Claude Desktop config:

- **Mac:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "ai-business-agent": {
      "command": "ssh",
      "args": [
        "root@192.168.1.34",
        "cd /root/projects/ai-business-agent && .venv/bin/python mcp_server.py --vault /pad/naar/vault"
      ]
    }
  }
}
```

> Als je de MCP server lokaal draait (vault op je Mac), gebruik dan `python` direct i.p.v. `ssh`.

---

## Stap 6: Eerste keer testen

| Wat | URL |
|-----|-----|
| Dashboard | `http://192.168.1.34:8000/dashboard` |
| API Docs (Swagger) | `http://192.168.1.34:8000/docs` |
| Health check | `http://192.168.1.34:8000/` |

- Login op het dashboard met je API token
- Test of de MCP tools in Claude Desktop verschijnen (herstart Claude Desktop na config wijziging)
- Probeer: "Wat zijn mijn voorkeuren?" in Claude Desktop → moet de `get_my_preferences` tool aanroepen

---

## Beschikbare endpoints

### Agents
| Methode | Pad | Functie |
|---------|-----|---------|
| POST | `/api/agent/{naam}/run` | Agent draaien met een prompt |
| GET | `/api/agent/{naam}/logs` | Recente activiteit |

### Kennis
| Methode | Pad | Functie |
|---------|-----|---------|
| POST | `/api/knowledge/share` | Voorkeur opslaan |
| GET | `/api/knowledge/shared` | Alle voorkeuren ophalen |
| POST | `/api/knowledge/client` | Klantinfo opslaan |
| GET | `/api/knowledge/client/{naam}` | Klantinfo ophalen |
| GET | `/api/knowledge/clients` | Alle klanten |
| POST | `/api/knowledge/learn-all` | Trigger learning voor alle agents |
| POST | `/api/knowledge/sync` | Sync naar CLAUDE.md |

### Feedback
| Methode | Pad | Functie |
|---------|-----|---------|
| POST | `/api/feedback` | Feedback geven op agent output |
| GET | `/api/agent/{naam}/feedback/stats` | Feedback statistieken |

### Obsidian
| Methode | Pad | Functie |
|---------|-----|---------|
| POST | `/api/obsidian/index` | Vault indexeren |
| GET | `/api/obsidian/search?query=...` | Zoeken in vault |
| GET | `/api/obsidian/note?path=...` | Notitie lezen |

### Plugins
| Methode | Pad | Functie |
|---------|-----|---------|
| GET | `/api/plugins` | Alle plugins |
| POST | `/api/plugins/build` | Nieuwe plugin bouwen |
| POST | `/api/plugins/{naam}/activate` | Plugin activeren |
| POST | `/api/plugins/{naam}/disable` | Plugin uitschakelen |

### Webhooks (voor n8n)
| Methode | Pad | Functie |
|---------|-----|---------|
| POST | `/webhook/agent` | Universeel webhook endpoint |
| POST | `/webhook/marketing/{actie}` | Marketing agent direct |
| POST | `/webhook/sales/{actie}` | Sales agent direct |
| POST | `/webhook/finance/{actie}` | Finance agent direct |
| POST | `/webhook/planning/{actie}` | Planning agent direct |
| POST | `/webhook/builder/{actie}` | Builder agent direct |

---

## MCP Tools (beschikbaar in Claude Desktop/Web/Code)

| Tool | Functie |
|------|---------|
| `get_my_preferences` | Werkwijze en voorkeuren ophalen |
| `learn_preference` | Nieuwe voorkeur opslaan |
| `get_client_info` | Klantinfo ophalen |
| `remember_about_client` | Klantinfo opslaan |
| `list_clients` | Alle klanten tonen |
| `get_project_context` | Projectinfo ophalen (memory + Obsidian) |
| `give_feedback` | Feedback op agent output |
| `run_agent` | Agent aansturen (marketing/sales/finance/planning) |
| `build_plugin` | Nieuwe connector bouwen |
| `list_plugins` | Plugins tonen |
| `search_obsidian` | Zoeken in Obsidian vault |
| `read_obsidian_note` | Notitie lezen |
| `index_obsidian` | Vault herindexeren |
| `get_knowledge_status` | Systeem overzicht |
