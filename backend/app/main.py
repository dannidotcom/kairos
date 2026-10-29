from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from sqlalchemy import text

from app.config import settings
from app.db import SessionLocal, engine
from app.routers import auth, campaigns, dashboard, demo, icps, leads, linkedin, mcp, settings as settings_router, signals, unibox

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger("kairos")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Kairos API starting in %s mode", settings.environment)
    yield
    await engine.dispose()
    logger.info("Kairos API stopped")


app = FastAPI(
    title="Kairos API",
    description="Le bon message, au bon moment. Signal-led LinkedIn prospecting.",
    version="0.1.0",
    lifespan=lifespan,
    default_response_class=ORJSONResponse,
    docs_url="/api/docs",
    redoc_url=None,
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)

api = APIRouter(prefix="/api")
api.include_router(auth.router, prefix="/auth")
api.include_router(icps.router)
api.include_router(linkedin.router)
api.include_router(linkedin.webhook_router)
api.include_router(leads.router)
api.include_router(signals.router)
api.include_router(campaigns.router)
api.include_router(unibox.router)
api.include_router(dashboard.router)
api.include_router(mcp.router)
api.include_router(settings_router.router)
api.include_router(demo.router)
app.include_router(api)


@app.get("/health", tags=["system"])
async def health():
    database_ok = True
    try:
        async with SessionLocal() as session:
            await session.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001
        logger.warning("Database health check failed: %s", exc)
        database_ok = False
    return {
        "status": "ok" if database_ok else "degraded",
        "service": "kairos-api",
        "database": "ok" if database_ok else "unavailable",
        "version": "0.1.0",
    }


@app.get("/", include_in_schema=False)
async def root():
    return {
        "name": "Kairos",
        "tagline": "Le bon message, au bon moment.",
        "docs": "/api/docs",
        "health": "/health",
    }
