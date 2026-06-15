import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_setup_db_fixture_exists():
    """setup_db fixture should exist (it's implicit, but test its imports work)"""
    from tests.conftest import setup_db
    assert setup_db is not None


@pytest.mark.asyncio
async def test_db_session_fixture_is_async_session(db_session):
    """db_session fixture should yield an AsyncSession"""
    assert isinstance(db_session, AsyncSession)


@pytest.mark.asyncio
async def test_client_fixture_is_async_client(client):
    """client fixture should yield an AsyncClient"""
    assert isinstance(client, AsyncClient)


@pytest.mark.asyncio
async def test_client_can_make_requests(client):
    """client fixture should allow making requests to the app"""
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_client_uses_overridden_get_db(client, db_session):
    """client fixture should override get_db dependency"""
    from app.main import app
    from app.core.database import get_db
    assert get_db in app.dependency_overrides
