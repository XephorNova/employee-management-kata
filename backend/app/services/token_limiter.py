from __future__ import annotations
from datetime import datetime, timezone, timedelta
import redis.asyncio as aioredis
from app.core.config import settings

TOKEN_LIMIT = 300_000
_client: aioredis.Redis | None = None


def _get_redis() -> aioredis.Redis:
    global _client
    if _client is None:
        _client = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _client


def _day_key(user_id: int) -> str:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return f"ai_tokens:{user_id}:{today}"


def _resets_at() -> str:
    now = datetime.now(timezone.utc)
    midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return midnight.isoformat()


async def get_usage(user_id: int) -> dict:
    r = _get_redis()
    used = int(await r.get(_day_key(user_id)) or 0)
    return {
        "used": used,
        "limit": TOKEN_LIMIT,
        "remaining": max(0, TOKEN_LIMIT - used),
        "resets_at": _resets_at(),
    }


async def check_limit(user_id: int) -> bool:
    r = _get_redis()
    used = int(await r.get(_day_key(user_id)) or 0)
    return used < TOKEN_LIMIT


async def consume(user_id: int, tokens: int) -> int:
    r = _get_redis()
    key = _day_key(user_id)
    pipe = r.pipeline()
    pipe.incrby(key, tokens)
    pipe.expire(key, 48 * 3600)
    results = await pipe.execute()
    return results[0]
