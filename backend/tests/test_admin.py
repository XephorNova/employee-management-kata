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


@pytest.fixture(scope="module")
async def setup():
    async with _ENGINE.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with _Session() as s:
        s.add(User(email="admin@acme.com", hashed_password=hash_password("pw"), role=UserRole.admin))
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


def _admin_token() -> str:
    return create_access_token({"sub": "admin@acme.com", "role": "admin"}, expires_delta=timedelta(hours=1))


@pytest.mark.asyncio
async def test_create_user(client):
    resp = await client.post(
        "/api/admin/users",
        json={"email": "newuser@acme.com", "password": "secure123", "role": "hr_analyst"},
        headers={"Authorization": f"Bearer {_admin_token()}"},
    )
    assert resp.status_code == 201
    assert resp.json()["role"] == "hr_analyst"


@pytest.mark.asyncio
async def test_non_admin_forbidden(client):
    token = create_access_token({"sub": "hr@acme.com", "role": "hr_manager"}, expires_delta=timedelta(hours=1))
    resp = await client.get("/api/admin/users", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403
