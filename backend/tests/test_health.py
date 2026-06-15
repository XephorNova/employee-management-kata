import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine

import app.models as _models  # noqa: F401 - registers models with Base.metadata
from app.main import app
from app.core.database import Base


@pytest.mark.asyncio
async def test_health():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_all_tables_create():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    expected = {
        "users", "employees", "pay_grades", "salary_records", "bonuses",
        "equity_grants", "allowances", "deductions", "tax_rules",
        "tax_brackets", "pf_rules", "salary_slips",
    }
    assert expected.issubset(set(Base.metadata.tables.keys()))
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
