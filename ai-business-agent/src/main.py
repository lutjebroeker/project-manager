"""FastAPI application entry point."""

import uvicorn
from fastapi import FastAPI

from src.api.routes import router
from src.api.webhooks import webhook_router
from src.config import settings

app = FastAPI(
    title="AI Business Agent",
    description="Persoonlijke AI Business Automation Platform",
    version="0.1.0",
)

app.include_router(router, prefix="/api")
app.include_router(webhook_router)


@app.get("/")
async def root():
    return {
        "name": "AI Business Agent",
        "version": "0.1.0",
        "docs": "/docs",
    }


if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
    )
