from __future__ import annotations
import pytest
from unittest.mock import patch
import fakeredis.aioredis


def make_fake_redis() -> fakeredis.aioredis.FakeRedis:
    return fakeredis.aioredis.FakeRedis(decode_responses=True)


@pytest.mark.asyncio
async def test_check_limit_under_limit():
    r = make_fake_redis()
    with patch("app.services.token_limiter._get_redis", return_value=r):
        from app.services.token_limiter import check_limit
        result = await check_limit(user_id=1)
    assert result is True


@pytest.mark.asyncio
async def test_check_limit_at_limit():
    r = make_fake_redis()
    with patch("app.services.token_limiter._get_redis", return_value=r):
        from app.services.token_limiter import check_limit, consume, TOKEN_LIMIT
        await consume(1, TOKEN_LIMIT)
        result = await check_limit(1)
    assert result is False


@pytest.mark.asyncio
async def test_consume_returns_new_total():
    r = make_fake_redis()
    with patch("app.services.token_limiter._get_redis", return_value=r):
        from app.services.token_limiter import consume
        total = await consume(user_id=1, tokens=500)
    assert total == 500


@pytest.mark.asyncio
async def test_consume_accumulates():
    r = make_fake_redis()
    with patch("app.services.token_limiter._get_redis", return_value=r):
        from app.services.token_limiter import consume
        await consume(1, 200)
        total = await consume(1, 300)
    assert total == 500


@pytest.mark.asyncio
async def test_get_usage_shape():
    r = make_fake_redis()
    with patch("app.services.token_limiter._get_redis", return_value=r):
        from app.services.token_limiter import consume, get_usage, TOKEN_LIMIT
        await consume(1, 1000)
        usage = await get_usage(1)
    assert usage["used"] == 1000
    assert usage["limit"] == TOKEN_LIMIT
    assert usage["remaining"] == TOKEN_LIMIT - 1000
    assert "resets_at" in usage


@pytest.mark.asyncio
async def test_get_usage_zero_when_no_activity():
    r = make_fake_redis()
    with patch("app.services.token_limiter._get_redis", return_value=r):
        from app.services.token_limiter import get_usage
        usage = await get_usage(user_id=99)
    assert usage["used"] == 0
    assert usage["remaining"] == usage["limit"]
