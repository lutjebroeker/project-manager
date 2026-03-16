"""API authenticatie — simpele bearer token.

Gebruikt een gedeeld token dat je in .env zet.
Licht genoeg voor een persoonlijk platform, zwaar genoeg
om het niet per ongeluk open te laten staan.
"""

import secrets
from pathlib import Path

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.config import settings

security = HTTPBearer(auto_error=False)

# Token wordt geladen uit .env of automatisch gegenereerd bij eerste start
_token: str | None = None


def get_api_token() -> str:
    """Haal het API token op, genereer er een als het nog niet bestaat."""
    global _token
    if _token:
        return _token

    # Check env
    token = getattr(settings, "api_token", "") or ""
    if token:
        _token = token
        return _token

    # Genereer nieuw token en sla op in .env
    _token = secrets.token_urlsafe(32)

    env_path = Path(".env")
    if env_path.exists():
        content = env_path.read_text(encoding="utf-8")
        if "API_TOKEN=" not in content:
            with open(env_path, "a", encoding="utf-8") as f:
                f.write(f"\n# Auto-gegenereerd API token\nAPI_TOKEN={_token}\n")
    else:
        env_path.write_text(f"API_TOKEN={_token}\n", encoding="utf-8")

    return _token


async def verify_token(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> str:
    """Verify bearer token. Webhooks en health endpoint zijn uitgezonderd."""

    # Sta bepaalde paden toe zonder auth
    open_paths = {"/", "/docs", "/openapi.json", "/redoc"}
    if request.url.path in open_paths:
        return "anonymous"

    # Webhooks hebben hun eigen auth (n8n shared secret)
    if request.url.path.startswith("/webhook/"):
        return "webhook"

    if not credentials:
        raise HTTPException(status_code=401, detail="Bearer token vereist")

    expected = get_api_token()
    if credentials.credentials != expected:
        raise HTTPException(status_code=403, detail="Ongeldig token")

    return credentials.credentials
