import pytest
from datetime import timedelta
from app.auth.utils import hash_password, verify_password, create_access_token, decode_token


def test_hash_and_verify_password():
    plain = "supersecret123"
    hashed = hash_password(plain)
    assert hashed != plain
    assert verify_password(plain, hashed)
    assert not verify_password("wrongpassword", hashed)


def test_create_and_decode_access_token():
    data = {"sub": "user@example.com", "role": "admin"}
    token = create_access_token(data, expires_delta=timedelta(minutes=30))
    payload = decode_token(token)
    assert payload["sub"] == "user@example.com"
    assert payload["role"] == "admin"


def test_expired_token_raises():
    data = {"sub": "user@example.com"}
    token = create_access_token(data, expires_delta=timedelta(seconds=-1))
    with pytest.raises(ValueError):
        decode_token(token)


import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
import app.models  # noqa
from app.main import app
from app.core.database import Base, get_db
from app.models.user import User, UserRole
from app.auth.utils import hash_password

_ENGINE = create_async_engine("sqlite+aiosqlite:///:memory:")
_Session = async_sessionmaker(_ENGINE, expire_on_commit=False)


@pytest.fixture(scope="module")
async def auth_db():
    async with _ENGINE.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with _Session() as s:
        s.add(User(email="admin@acme.com", hashed_password=hash_password("password123"), role=UserRole.admin))
        await s.commit()
    yield
    async with _ENGINE.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def auth_client(auth_db):
    async with _Session() as s:
        async def override():
            yield s
        app.dependency_overrides[get_db] = override
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            yield c
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_login_success(auth_client):
    resp = await auth_client.post("/auth/login", json={"email": "admin@acme.com", "password": "password123"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_login_wrong_password(auth_client):
    resp = await auth_client.post("/auth/login", json={"email": "admin@acme.com", "password": "wrong"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_endpoint(auth_client):
    login = await auth_client.post("/auth/login", json={"email": "admin@acme.com", "password": "password123"})
    token = login.json()["access_token"]
    resp = await auth_client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["email"] == "admin@acme.com"


@pytest.mark.asyncio
async def test_me_unauthenticated(auth_client):
    resp = await auth_client.get("/auth/me")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_refresh_with_valid_refresh_token(auth_client):
    login = await auth_client.post("/auth/login", json={"email": "admin@acme.com", "password": "password123"})
    refresh_token = login.json()["refresh_token"]
    resp = await auth_client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_refresh_with_access_token_rejected(auth_client):
    login = await auth_client.post("/auth/login", json={"email": "admin@acme.com", "password": "password123"})
    access_token = login.json()["access_token"]
    resp = await auth_client.post("/auth/refresh", json={"refresh_token": access_token})
    assert resp.status_code == 401
