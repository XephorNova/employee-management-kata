from __future__ import annotations
import pytest
from unittest.mock import patch
import chromadb


@pytest.fixture
def temp_client(tmp_path):
    return chromadb.PersistentClient(path=str(tmp_path))


@pytest.mark.asyncio
async def test_get_recent_empty(temp_client):
    with patch("app.services.conversation_store.get_chroma_client", return_value=temp_client):
        from app.services.conversation_store import get_recent
        result = await get_recent(user_id=1)
    assert result == []


@pytest.mark.asyncio
async def test_add_and_get_recent(temp_client):
    with patch("app.services.conversation_store.get_chroma_client", return_value=temp_client):
        from app.services.conversation_store import add_exchange, get_recent
        await add_exchange(1, "What is avg salary?", "It is $100k.")
        result = await get_recent(1)
    assert len(result) == 1
    assert result[0]["question"] == "What is avg salary?"
    assert result[0]["answer"] == "It is $100k."
    assert "timestamp" in result[0]


@pytest.mark.asyncio
async def test_get_recent_returns_n_most_recent(temp_client):
    with patch("app.services.conversation_store.get_chroma_client", return_value=temp_client):
        from app.services.conversation_store import add_exchange, get_recent
        for i in range(7):
            await add_exchange(1, f"Question {i}", f"Answer {i}")
        result = await get_recent(1, n=5)
    assert len(result) == 5


@pytest.mark.asyncio
async def test_get_recent_sorted_newest_first(temp_client):
    with patch("app.services.conversation_store.get_chroma_client", return_value=temp_client):
        from app.services.conversation_store import add_exchange, get_recent
        await add_exchange(1, "First question", "First answer")
        await add_exchange(1, "Second question", "Second answer")
        result = await get_recent(1)
    assert result[0]["question"] == "Second question"


@pytest.mark.asyncio
async def test_search_similar_returns_empty_when_no_history(temp_client):
    with patch("app.services.conversation_store.get_chroma_client", return_value=temp_client):
        from app.services.conversation_store import search_similar
        result = await search_similar(1, "salary question", k=3)
    assert result == []


@pytest.mark.asyncio
async def test_search_similar_returns_relevant(temp_client):
    with patch("app.services.conversation_store.get_chroma_client", return_value=temp_client):
        from app.services.conversation_store import add_exchange, search_similar
        await add_exchange(1, "What is the average salary?", "It is $100k.")
        await add_exchange(1, "How many employees are in Engineering?", "There are 50.")
        result = await search_similar(1, "average salary amount", k=3)
    assert len(result) >= 1
    assert result[0]["question"] == "What is the average salary?"


@pytest.mark.asyncio
async def test_conversations_isolated_by_user(temp_client):
    with patch("app.services.conversation_store.get_chroma_client", return_value=temp_client):
        from app.services.conversation_store import add_exchange, get_recent
        await add_exchange(user_id=1, question="User 1 question", answer="User 1 answer")
        result_user2 = await get_recent(user_id=2)
    assert result_user2 == []
