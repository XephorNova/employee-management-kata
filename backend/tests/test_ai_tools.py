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
    token = create_access_token({"sub": "a@acme.com", "role": "hr_analyst"}, expires_delta=timedelta(hours=1))

    mock_response = MagicMock()
    mock_response.stop_reason = "end_turn"
    mock_response.content = [MagicMock(text="Average salary is $75,000.", type="text")]

    with patch("app.services.ai_service.AsyncAnthropic") as MockClient, \
         patch("app.api.ai.settings") as mock_settings:
        mock_settings.anthropic_api_key = "test-key"
        mock_instance = AsyncMock()
        mock_instance.messages.create = AsyncMock(return_value=mock_response)
        MockClient.return_value = mock_instance

        resp = await ai_client.post(
            "/api/ai/query",
            json={"question": "What is the average salary?"},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 200
    assert "answer" in resp.json()
