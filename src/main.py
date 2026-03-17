"""FastAPI application entry point."""

import uvicorn
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from src.api.routes import router
from src.api.webhooks import webhook_router
from src.api.auth import verify_token
from src.config import settings

app = FastAPI(
    title="AI Business Agent",
    description="Persoonlijke AI Business Automation Platform",
    version="0.1.0",
    dependencies=[Depends(verify_token)],
)

# CORS — nodig voor dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://jellespek.nl",
        "https://www.jellespek.nl",
        f"http://localhost:{settings.port}",
        f"http://127.0.0.1:{settings.port}",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")
app.include_router(webhook_router)

# Dashboard static files
dashboard_dir = Path(__file__).parent.parent / "dashboard"
if dashboard_dir.exists():
    app.mount("/dashboard", StaticFiles(directory=str(dashboard_dir), html=True), name="dashboard")


@app.get("/")
async def root():
    return {
        "name": "AI Business Agent",
        "version": "0.1.0",
        "docs": "/docs",
        "dashboard": "/dashboard",
    }


if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
    )
