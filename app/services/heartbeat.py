import asyncio
import time

from app.config import HEARTBEAT_PATH

HEARTBEAT_INTERVAL_SECONDS = 60


async def run_heartbeat_loop() -> None:
    """Раз в минуту отмечает, что бот жив — на это смотрит HEALTHCHECK в Docker."""
    while True:
        with open(HEARTBEAT_PATH, "w", encoding="utf-8") as f:
            f.write(str(time.time()))
        await asyncio.sleep(HEARTBEAT_INTERVAL_SECONDS)
