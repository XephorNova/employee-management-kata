import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import engine, AsyncSessionLocal, Base, get_db


@pytest.mark.asyncio
async def test_engine_created():
    """Database engine should be created"""
    assert engine is not None


def test_async_session_local_factory():
    """AsyncSessionLocal should be a session factory"""
    assert AsyncSessionLocal is not None


def test_base_declarative():
    """Base should be a DeclarativeBase"""
    assert hasattr(Base, 'metadata')
    assert Base.metadata is not None


@pytest.mark.asyncio
async def test_get_db_generator():
    """get_db should be an async generator that yields AsyncSession"""
    generator = get_db()

    # Check it's an async generator
    assert hasattr(generator, '__anext__')

    # Get the first yielded value (should be AsyncSession)
    session = await generator.__anext__()
    assert isinstance(session, AsyncSession)

    # Clean up
    try:
        await generator.__anext__()
    except StopAsyncIteration:
        pass
