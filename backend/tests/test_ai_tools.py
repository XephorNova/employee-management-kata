import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import timedelta
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
import app.models  # noqa
from app.main import app
from app.core.database import Base, get_db
from app.models.user import User, UserRole
from app.auth.utils import hash_password, create_access_token
from app.tools.executor import execute_tool

_ENGINE_AI = create_async_engine("sqlite+aiosqlite:///:memory:")
_Session_AI = async_sessionmaker(_ENGINE_AI, expire_on_commit=False)

_MOCK_USAGE = {
    "used": 1000,
    "limit": 300_000,
    "remaining": 299_000,
    "resets_at": "2026-06-20T00:00:00+00:00",
}

_ALL_COLLABORATORS = {
    "app.api.ai.check_limit": AsyncMock(return_value=True),
    "app.api.ai.get_cached_response": AsyncMock(return_value=None),
    "app.api.ai.get_recent": AsyncMock(return_value=[]),
    "app.api.ai.search_similar": AsyncMock(return_value=[]),
    "app.api.ai.set_cached_response": AsyncMock(),
    "app.api.ai.add_exchange": AsyncMock(),
    "app.api.ai.consume": AsyncMock(return_value=1000),
    "app.api.ai.get_usage": AsyncMock(return_value=_MOCK_USAGE),
    "app.api.ai.tracked_ai_query": AsyncMock(return_value={
        "answer": "Average salary is $75,000.",
        "tool_used": None,
        "data": None,
        "chart_type": "none",
        "tokens_used": 1000,
    }),
}


@pytest.fixture(scope="module")
async def ai_setup():
    async with _ENGINE_AI.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with _Session_AI() as s:
        s.add(User(email="a@acme.com", hashed_password=hash_password("pw"), role=UserRole.hr_analyst))
        await s.commit()
    yield
    async with _ENGINE_AI.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def ai_client(ai_setup):
    async with _Session_AI() as s:
        async def override():
            yield s
        app.dependency_overrides[get_db] = override
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            yield c
        app.dependency_overrides.clear()


def _analyst_token():
    return create_access_token({"sub": "a@acme.com", "role": "hr_analyst"}, expires_delta=timedelta(hours=1))


@pytest.mark.asyncio
async def test_execute_get_salary_stats():
    mock_db = AsyncMock()
    with patch("app.tools.executor.get_salary_stats", new=AsyncMock(return_value={"count": 10, "avg": 5000})) as fn:
        result = await execute_tool(mock_db, "get_salary_stats", {"filters": {}})
    fn.assert_called_once()
    assert result["count"] == 10


@pytest.mark.asyncio
async def test_execute_get_headcount():
    mock_db = AsyncMock()
    with patch("app.tools.executor.get_headcount", new=AsyncMock(return_value=[{"group": "Engineering", "count": 50}])) as fn:
        result = await execute_tool(mock_db, "get_headcount", {"group_by": "department", "filters": {}})
    fn.assert_called_once()
    assert result[0]["group"] == "Engineering"


@pytest.mark.asyncio
async def test_unknown_tool_raises():
    mock_db = AsyncMock()
    with pytest.raises(ValueError, match="Unknown tool"):
        await execute_tool(mock_db, "nonexistent_tool", {})


@pytest.mark.asyncio
async def test_sql_injection_blocked():
    mock_db = AsyncMock()
    with pytest.raises(ValueError, match="Only SELECT"):
        await execute_tool(mock_db, "run_analytics_query", {"question": "delete all", "sql": "DELETE FROM employees"})


@pytest.mark.asyncio
async def test_ai_query_endpoint_mocked(ai_client):
    with patch("app.api.ai.settings") as mock_settings, \
         patch("app.api.ai.check_limit", new=AsyncMock(return_value=True)), \
         patch("app.api.ai.get_cached_response", new=AsyncMock(return_value=None)), \
         patch("app.api.ai.get_recent", new=AsyncMock(return_value=[])), \
         patch("app.api.ai.search_similar", new=AsyncMock(return_value=[])), \
         patch("app.api.ai.set_cached_response", new=AsyncMock()), \
         patch("app.api.ai.add_exchange", new=AsyncMock()), \
         patch("app.api.ai.consume", new=AsyncMock(return_value=1000)), \
         patch("app.api.ai.get_usage", new=AsyncMock(return_value=_MOCK_USAGE)), \
         patch("app.api.ai.tracked_ai_query", new=AsyncMock(return_value={
             "answer": "Average salary is $75,000.",
             "tool_used": None,
             "data": None,
             "chart_type": "none",
             "tokens_used": 1000,
         })):
        mock_settings.anthropic_api_key = "test-key"
        resp = await ai_client.post(
            "/api/ai/query",
            json={"question": "What is the average salary?"},
            headers={"Authorization": f"Bearer {_analyst_token()}"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["answer"] == "Average salary is $75,000."
    assert data["tokens_used"] == 1000
    assert data["tokens_remaining"] == 299_000
    assert data["from_cache"] is False


@pytest.mark.asyncio
async def test_ai_query_returns_429_when_over_limit(ai_client):
    over_usage = {"used": 300_000, "limit": 300_000, "remaining": 0, "resets_at": "2026-06-20T00:00:00+00:00"}
    with patch("app.api.ai.settings") as mock_settings, \
         patch("app.api.ai.check_limit", new=AsyncMock(return_value=False)), \
         patch("app.api.ai.get_usage", new=AsyncMock(return_value=over_usage)):
        mock_settings.anthropic_api_key = "test-key"
        resp = await ai_client.post(
            "/api/ai/query",
            json={"question": "Anything"},
            headers={"Authorization": f"Bearer {_analyst_token()}"},
        )

    assert resp.status_code == 429
    assert "2026-06-20" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_ai_query_cache_hit_skips_llm(ai_client):
    cached = {"answer": "Cached answer", "tool_used": None, "data": None, "chart_type": "none"}
    with patch("app.api.ai.settings") as mock_settings, \
         patch("app.api.ai.check_limit", new=AsyncMock(return_value=True)), \
         patch("app.api.ai.get_cached_response", new=AsyncMock(return_value=cached)), \
         patch("app.api.ai.get_usage", new=AsyncMock(return_value=_MOCK_USAGE)), \
         patch("app.api.ai.tracked_ai_query", new=AsyncMock()) as mock_llm:
        mock_settings.anthropic_api_key = "test-key"
        resp = await ai_client.post(
            "/api/ai/query",
            json={"question": "test?"},
            headers={"Authorization": f"Bearer {_analyst_token()}"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["from_cache"] is True
    assert data["tokens_used"] == 0
    mock_llm.assert_not_called()


@pytest.mark.asyncio
async def test_get_ai_usage_endpoint(ai_client):
    with patch("app.api.ai.get_usage", new=AsyncMock(return_value=_MOCK_USAGE)):
        resp = await ai_client.get(
            "/api/ai/usage",
            headers={"Authorization": f"Bearer {_analyst_token()}"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["tokens_used"] == 1000
    assert data["tokens_limit"] == 300_000
    assert data["tokens_remaining"] == 299_000
    assert "resets_at" in data
