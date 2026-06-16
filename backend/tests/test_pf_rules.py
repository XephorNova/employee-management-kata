import pytest
from datetime import timedelta
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
import app.models  # noqa
from app.main import app
from app.core.database import Base, get_db
from app.models.user import User, UserRole
from app.auth.utils import hash_password, create_access_token

_ENGINE = create_async_engine("sqlite+aiosqlite:///:memory:")
_Session = async_sessionmaker(_ENGINE, expire_on_commit=False)


def _hr_token() -> str:
    return create_access_token({"sub": "hr@acme.com", "role": "hr_manager"}, expires_delta=timedelta(hours=1))


@pytest.fixture(scope="module")
async def setup():
    async with _ENGINE.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with _Session() as s:
        s.add(User(email="hr@acme.com", hashed_password=hash_password("pw"), role=UserRole.hr_manager))
        await s.commit()
    yield
    async with _ENGINE.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client(setup):
    async with _Session() as s:
        async def override():
            yield s
        app.dependency_overrides[get_db] = override
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            yield c
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_create_pf_rule(client):
    resp = await client.post(
        "/api/pf-rules",
        json={
            "country": "IN", "rule_name": "India PF 2024",
            "employee_contribution_pct": 0.12, "employer_contribution_pct": 0.12,
            "applicable_salary_cap": 15000, "effective_from_date": "2024-04-01",
        },
        headers={"Authorization": f"Bearer {_hr_token()}"},
    )
    assert resp.status_code == 201
    assert resp.json()["country"] == "IN"


@pytest.mark.asyncio
async def test_list_by_country(client):
    resp = await client.get("/api/pf-rules/country/IN", headers={"Authorization": f"Bearer {_hr_token()}"})
    assert resp.status_code == 200
    assert len(resp.json()) >= 1
