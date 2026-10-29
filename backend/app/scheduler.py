from __future__ import annotations

import asyncio
import logging
import signal
from datetime import datetime, timezone

from arq import create_pool
from arq.connections import RedisSettings

from app.config import settings

logging.basicConfig(level=settings.log_level, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("kairos.scheduler")


async def enqueue_tick(pool, function: str, bucket: str) -> None:
    job_id = f"{function}:{bucket}"
    await pool.enqueue_job(function, _job_id=job_id)


async def main() -> None:
    logger.info("Kairos scheduler starting")
    pool = await create_pool(RedisSettings.from_dsn(settings.redis_url))
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop.set)
        except NotImplementedError:
            pass

    minute_bucket = None
    five_minute_bucket = None
    fifteen_minute_bucket = None
    while not stop.is_set():
        now = datetime.now(timezone.utc)
        try:
            current_minute = now.strftime("%Y%m%d%H%M")
            if current_minute != minute_bucket:
                minute_bucket = current_minute
                await enqueue_tick(pool, "run_actions", current_minute)
            current_five = now.strftime("%Y%m%d%H") + str(now.minute // 5)
            if current_five != five_minute_bucket:
                five_minute_bucket = current_five
                await enqueue_tick(pool, "run_enrollments", current_five)
            current_fifteen = now.strftime("%Y%m%d%H") + str(now.minute // 15)
            if current_fifteen != fifteen_minute_bucket:
                fifteen_minute_bucket = current_fifteen
                await enqueue_tick(pool, "sync_accounts", current_fifteen)
        except Exception as exc:  # noqa: BLE001 - scheduler must survive Redis blips
            logger.warning("Scheduler tick failed: %s", exc)
        try:
            await asyncio.wait_for(stop.wait(), timeout=30)
        except TimeoutError:
            pass
    await pool.aclose()
    logger.info("Kairos scheduler stopped")


if __name__ == "__main__":
    asyncio.run(main())
