# /backend/app/core/redis.py
import json
from typing import Any

import redis.asyncio as aioredis

from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)

# Session TTL matches the agreed 1-hour window from CLAUDE.md
SESSION_TTL = 3600
SESSION_MAX_MESSAGES = 20

_redis: aioredis.Redis | None = None


def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis


async def check_redis() -> str:
    """Returns 'ok' if Redis is reachable, 'error' otherwise."""
    try:
        await get_redis().ping()
        return "ok"
    except Exception as exc:
        logger.error("Redis health check failed: %s", exc)
        return "error"


async def get_session(session_id: str) -> list[dict[str, Any]]:
    """Retrieve the message history for a session."""
    raw = await get_redis().get(f"session:{session_id}")
    if raw is None:
        return []
    return json.loads(raw)


async def save_session(session_id: str, messages: list[dict[str, Any]]) -> None:
    """Persist message history; keeps only the last SESSION_MAX_MESSAGES entries."""
    trimmed = messages[-SESSION_MAX_MESSAGES:]
    await get_redis().setex(
        f"session:{session_id}",
        SESSION_TTL,
        json.dumps(trimmed),
    )


async def clear_session(session_id: str) -> None:
    await get_redis().delete(f"session:{session_id}")
