"""
FastAPI application entry point.

Starts the app with a lifespan that initialises logging on startup.
The DB engine and Kernel are created once and reused across requests.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    configure_logging()
    settings = get_settings()
    logger.info("startup", env=settings.app_env, model=settings.openai_model)
    yield
    logger.info("shutdown")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Streaming Support Agent",
        description="Multi-agent AI support assistant for a streaming and rental platform.",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router, prefix="")

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok", "model": settings.openai_model}

    return app


app = create_app()
