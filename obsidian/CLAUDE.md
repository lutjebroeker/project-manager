# Project Instructies

## Obsidian Status Logging

Na elke afgeronde taak of milestone, update de Obsidian project note via:

```bash
curl -s "https://n8n.jellespek.nl/webhook/update-obsidian-log?project=${PROJECT_NAME}&status=$(python3 -c "import urllib.parse; print(urllib.parse.quote('STATUS_TEKST'))")"
```

Gebruik dit in de volgende situaties:
- **Taak afgerond**: `✅ <beschrijving van wat is gedaan>`
- **Probleem tegengekomen**: `⚠️ <beschrijving van het probleem>`
- **Wacht op input**: `⏳ <wat er nodig is>`
- **Sessie gestart**: `🚀 Sessie gestart`
- **Sessie afgerond**: `🏁 Sessie afgerond — <samenvatting>`

De PROJECT_NAME komt uit de mapnaam van het project (basename van de huidige directory).

Voorbeeld:
```bash
PROJECT_NAME=$(basename "$PWD")
curl -s "https://n8n.jellespek.nl/webhook/update-obsidian-log?project=${PROJECT_NAME}&status=$(python3 -c "import urllib.parse; print(urllib.parse.quote('✅ Authentication module toegevoegd'))")"
```

## Samenwerking met OpenBrain

Dit project wordt beheerd via het Agentic Company model. De Obsidian note is de single source of truth voor projectstatus. Houd de log actueel zodat andere agents en OpenBrain altijd de laatste stand kunnen lezen.
