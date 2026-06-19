from __future__ import annotations
import time
import pytest
from unittest.mock import patch
import chromadb


@pytest.fixture
def temp_client(tmp_path):
    return chromadb.PersistentClient(path=str(tmp_path))


@pytest.mark.asyncio
async def test_cache_miss_on_empty(temp_client):
    with patch("app.services.query_cache.get_chroma_client", return_value=temp_client):
        from app.services.query_cache import get_cached_response
        result = await get_cached_response("What is the average salary?")
    assert result is None


@pytest.mark.asyncio
async def test_cache_hit_on_identical_question(temp_client):
    with patch("app.services.query_cache.get_chroma_client", return_value=temp_client):
        from app.services.query_cache import get_cached_response, set_cached_response
        payload = {
            "answer": "Average is $100k",
            "tool_used": "get_salary_stats",
            "chart_type": "none",
            "data": None,
        }
        await set_cached_response("What is the average salary?", payload)
        result = await get_cached_response("What is the average salary?")
    assert result is not None
    assert result["answer"] == "Average is $100k"
    assert result["tool_used"] == "get_salary_stats"


@pytest.mark.asyncio
async def test_cache_hit_on_semantically_similar_question(temp_client):
    with patch("app.services.query_cache.get_chroma_client", return_value=temp_client):
        from app.services.query_cache import get_cached_response, set_cached_response
        payload = {"answer": "Avg is $100k", "tool_used": None, "chart_type": "none", "data": None}
        await set_cached_response("What is the average salary?", payload)
        result = await get_cached_response("What's the average salary?")
    assert result is not None


@pytest.mark.asyncio
async def test_stale_cache_returns_none(temp_client):
    with patch("app.services.query_cache.get_chroma_client", return_value=temp_client):
        from app.services.query_cache import get_cached_response, CACHE_COLLECTION
        col = temp_client.get_or_create_collection(
            name=CACHE_COLLECTION, metadata={"hnsw:space": "cosine"}
        )
        stale_time = time.time() - (25 * 3600)  # 25 hours ago
        col.add(
            documents=["What is the average salary?"],
            metadatas=[{
                "answer": "Old answer",
                "tool_used": "",
                "chart_type": "none",
                "data": "",
                "cached_at": stale_time,
            }],
            ids=["stale_entry_1"],
        )
        result = await get_cached_response("What is the average salary?")
    assert result is None


@pytest.mark.asyncio
async def test_cache_preserves_data_field(temp_client):
    with patch("app.services.query_cache.get_chroma_client", return_value=temp_client):
        from app.services.query_cache import get_cached_response, set_cached_response
        payload = {
            "answer": "Top earners listed",
            "tool_used": "get_top_earners",
            "chart_type": "table",
            "data": [{"name": "Alice", "salary": 200000}],
        }
        await set_cached_response("Who are the top earners?", payload)
        result = await get_cached_response("Who are the top earners?")
    assert result is not None
    assert result["data"] == [{"name": "Alice", "salary": 200000}]
    assert result["chart_type"] == "table"
