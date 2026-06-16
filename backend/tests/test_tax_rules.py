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
async def test_create_tax_rule_with_brackets(client):
    resp = await client.post(
        "/api/tax-rules",
        json={
            "country": "US", "rule_name": "US Federal Tax 2024",
            "rule_type": "income_tax", "tax_year": 2024,
            "brackets": [
                {"min_income": 0, "max_income": 11600, "rate_pct": 0.10, "currency": "USD"},
                {"min_income": 11600, "max_income": None, "rate_pct": 0.22, "currency": "USD"},
            ],
        },
        headers={"Authorization": f"Bearer {_hr_token()}"},
    )
    assert resp.status_code == 201
    assert len(resp.json()["brackets"]) == 2
    assert resp.json()["country"] == "US"


@pytest.mark.asyncio
async def test_list_by_country(client):
    resp = await client.get("/api/tax-rules/country/US", headers={"Authorization": f"Bearer {_hr_token()}"})
    assert resp.status_code == 200
    assert len(resp.json()) >= 1
