from __future__ import annotations

import logging
import signal

from arq import create_pool
from arq.connections import RedisSettings

from app.config import settings
from app.db import SessionLocal, engine
from app.services.campaign import (
    process_auto_enrollment,
    process_demo_acceptances,
    process_due_actions,
)

logger = logging.getLogger("kairos.worker")


async def run_actions(ctx: dict) -> dict:
    async with SessionLocal() as session:
        accepted = await process_demo_acceptances(session)
        await session.commit()
        stats = await process_due_actions(session)
        stats["accepted"] = accepted
        if stats["processed"]:
            logger.info("Outbound tick: %s", stats)
        return stats


async def run_enrollments(ctx: dict) -> dict:
    async with SessionLocal() as session:
        enrolled = await process_auto_enrollment(session)
        await session.commit()
        if enrolled:
            logger.info("Auto-enrolled %s leads", enrolled)
        return {"enrolled": enrolled}


async def sync_accounts(ctx: dict) -> dict:
    from datetime import datetime, timezone

    from sqlalchemy import select

    from app.models import LinkedInAccount

    async with SessionLocal() as session:
        accounts = (await session.execute(select(LinkedInAccount))).scalars().all()
        for account in accounts:
            if account.status != "disconnected":
                account.last_sync_at = datetime.now(timezone.utc)
        await session.commit()
        return {"synced": len(accounts)}


async def startup(ctx: dict) -> None:
    logger.info("Kairos worker ready")


async def shutdown(ctx: dict) -> None:
    await engine.dispose()


class WorkerSettings:
    functions = [run_actions, run_enrollments, sync_accounts]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    on_startup = startup
    on_shutdown = shutdown
    max_jobs = 5
    job_timeout = 300
    keep_result = 3600
    health_check_interval = 30
