#!/bin/bash
# AI Business Agent — eerste installatie
# Gebruik: bash setup.sh

set -e

echo "=== AI Business Agent Setup ==="
echo ""

# 1. Python versie check
PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
if [[ "$(echo "$PYTHON_VERSION >= 3.10" | bc -l)" != "1" ]]; then
    echo "Python 3.10+ vereist (gevonden: $PYTHON_VERSION)"
    exit 1
fi
echo "[ok] Python $PYTHON_VERSION"

# 2. Virtual environment
if [ ! -d ".venv" ]; then
    echo "[..] Virtuele omgeving aanmaken..."
    python3 -m venv .venv
fi
source .venv/bin/activate
echo "[ok] Virtual environment actief"

# 3. Dependencies installeren
echo "[..] Dependencies installeren..."
pip install -e ".[dev]" --quiet 2>/dev/null || pip install -e ".[dev]"
echo "[ok] Dependencies geïnstalleerd"

# 4. Data directories
mkdir -p data data/plugins
echo "[ok] Data directories aangemaakt"

# 5. .env bestand
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "[ok] .env aangemaakt (pas de paden aan!)"
else
    echo "[ok] .env bestaat al"
fi

# 6. Business context
if [ ! -f "data/business_context.json" ]; then
    cat > data/business_context.json << 'JSONEOF'
{
  "bedrijf": "Jouw Bedrijf",
  "beschrijving": "Beschrijf hier wat je doet",
  "diensten": [
    {
      "naam": "Dienst 1",
      "beschrijving": "Wat je aanbiedt",
      "tarief": "€125/uur"
    }
  ],
  "tone_of_voice": "Professioneel maar toegankelijk",
  "taal": "Nederlands",
  "doelgroep": "MKB"
}
JSONEOF
    echo "[ok] Business context template aangemaakt — pas data/business_context.json aan!"
else
    echo "[ok] Business context bestaat al"
fi

# 7. Claude login check
if command -v claude &> /dev/null; then
    echo "[ok] Claude CLI gevonden"
    echo "     Zorg dat je bent ingelogd: claude login"
else
    echo "[!!] Claude CLI niet gevonden — installeer via: npm install -g @anthropic-ai/claude-code"
    echo "     Daarna: claude login (Max abonnement vereist)"
fi

# 8. Tests draaien
echo ""
echo "[..] Tests draaien..."
python -m pytest tests/ -v --tb=short 2>&1 | tail -5
echo ""

# 9. API token genereren
if ! grep -q "API_TOKEN=" .env 2>/dev/null || grep -q "API_TOKEN=$" .env 2>/dev/null; then
    TOKEN=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
    echo "API_TOKEN=$TOKEN" >> .env
    echo "[ok] API token gegenereerd: $TOKEN"
    echo "     Bewaar dit token — je hebt het nodig voor het dashboard en API calls"
else
    echo "[ok] API token staat al in .env"
fi

echo ""
echo "=== Setup Compleet ==="
echo ""
echo "Volgende stappen:"
echo "  1. Pas data/business_context.json aan met jouw bedrijfsinfo"
echo "  2. Pas .env aan (Obsidian vault pad, etc.)"
echo "  3. Start de server:  source .venv/bin/activate && python -m src.main"
echo "  4. Open dashboard:   http://localhost:8000/dashboard"
echo "  5. API docs:         http://localhost:8000/docs"
echo ""
echo "MCP voor Claude Desktop:"
echo "  Kopieer de config uit claude-mcp-config.json naar je Claude Desktop settings"
echo ""
