# app/utils/cache.py
"""
Centralised async Redis cache helper.

Usage:
    from app.utils.cache import get_cache, set_cache, delete_cache, delete_pattern

All functions are safe to call even when Redis is unavailable – they simply
become no-ops and the application continues working without caching.
"""

import json
import logging
from typing import Any, Optional

import redis.asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger(__name__)

# Module-level client – set during startup, cleared on shutdown.
_redis: Optional[aioredis.Redis] = None


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------

async def connect_redis() -> None:
    """Create the async Redis client and verify the connection."""
    global _redis
    try:
        _redis = aioredis.from_url(
            settings.REDIS_URL,
            username=settings.REDIS_USERNAME,
            password=settings.REDIS_PASSWORD,
            decode_responses=True,
            socket_connect_timeout=3,
            socket_timeout=3,
        )
        await _redis.ping()
        logger.info("Redis connected: %s", settings.REDIS_URL.split("@")[-1])
    except Exception as exc:
        logger.warning("Redis unavailable – caching disabled. Reason: %s", exc)
        _redis = None


async def disconnect_redis() -> None:
    """Close the Redis connection pool gracefully."""
    global _redis
    if _redis:
        await _redis.aclose()
        _redis = None
        logger.info("Redis disconnected.")


# ---------------------------------------------------------------------------
# Core helpers
# ---------------------------------------------------------------------------

async def get_cache(key: str) -> Optional[Any]:
    """Return the cached value for *key*, or ``None`` on miss / error."""
    if not _redis:
        return None
    try:
        raw = await _redis.get(key)
        if raw is not None:
            return json.loads(raw)
    except Exception as exc:
        logger.warning("Cache GET error [%s]: %s", key, exc)
    return None


async def set_cache(key: str, value: Any, ttl: int) -> None:
    """Serialise *value* to JSON and store it in Redis with the given *ttl* (seconds)."""
    if not _redis:
        return
    try:
        await _redis.setex(key, ttl, json.dumps(value, default=str))
    except Exception as exc:
        logger.warning("Cache SET error [%s]: %s", key, exc)


async def delete_cache(*keys: str) -> None:
    """Delete one or more explicit cache keys."""
    if not _redis or not keys:
        return
    try:
        await _redis.delete(*keys)
    except Exception as exc:
        logger.warning("Cache DELETE error %s: %s", keys, exc)


async def delete_pattern(pattern: str) -> None:
    """
    Delete all keys matching *pattern* using SCAN (non-blocking, production-safe).

    Example pattern: ``ct:feed:*``
    """
    if not _redis:
        return
    try:
        cursor: int = 0
        while True:
            cursor, keys = await _redis.scan(cursor, match=pattern, count=200)
            if keys:
                await _redis.delete(*keys)
            if cursor == 0:
                break
    except Exception as exc:
        logger.warning("Cache DELETE pattern error [%s]: %s", pattern, exc)


# ---------------------------------------------------------------------------
# Key builders  (keep in one place for easy refactoring)
# ---------------------------------------------------------------------------

def key_feed(user_id: Optional[str], skip: int, limit: int, school_scope: Optional[str]) -> str:
    uid = user_id or "anon"
    scope = school_scope or "none"
    return f"ct:feed:{uid}:{skip}:{limit}:{scope}"


def key_reels(user_id: Optional[str], skip: int, limit: int) -> str:
    uid = user_id or "anon"
    return f"ct:reels:{uid}:{skip}:{limit}"


def key_post(post_id: str, user_id: Optional[str]) -> str:
    uid = user_id or "anon"
    return f"ct:post:{post_id}:{uid}"


def key_institution(institution_id: str) -> str:
    return f"ct:institution:{institution_id}"


def key_institution_posts(institution_id: str, user_id: Optional[str], skip: int, limit: int, post_type: Optional[str]) -> str:
    uid = user_id or "anon"
    pt = post_type or "all"
    return f"ct:inst_posts:{institution_id}:{uid}:{skip}:{limit}:{pt}"


def key_user(user_id: str) -> str:
    return f"ct:user:{user_id}"
