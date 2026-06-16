import pytest
from unittest.mock import AsyncMock, patch
from app.tools.executor import execute_tool


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
