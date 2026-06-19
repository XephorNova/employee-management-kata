from __future__ import annotations
import asyncio
import json
import time
from app.services.chroma_client import get_chroma_client

CACHE_COLLECTION = "global_query_cache"
SIMILARITY_THRESHOLD = 0.08  # cosine distance; <0.08 ≈ >0.92 cosine similarity
CACHE_TTL_SECONDS = 24 * 3600


def _get_collection():
    client = get_chroma_client()
    return client.get_or_create_collection(
        name=CACHE_COLLECTION,
        metadata={"hnsw:space": "cosine"},
    )


def _sync_get_cached(question: str) -> dict | None:
    col = _get_collection()
    if col.count() == 0:
        return None
    results = col.query(
        query_texts=[question],
        n_results=1,
        include=["distances", "metadatas"],
    )
    distances = results["distances"][0]
    metadatas = results["metadatas"][0]
    if not distances:
        return None
    if distances[0] >= SIMILARITY_THRESHOLD:
        return None
    metadata = metadatas[0]
    if time.time() - metadata.get("cached_at", 0) > CACHE_TTL_SECONDS:
        return None
    return {
        "answer": metadata["answer"],
        "tool_used": metadata.get("tool_used") or None,
        "chart_type": metadata.get("chart_type", "none"),
        "data": json.loads(metadata["data"]) if metadata.get("data") else None,
    }


def _sync_set_cached(question: str, result: dict) -> None:
    col = _get_collection()
    col.add(
        documents=[question],
        metadatas=[{
            "answer": result["answer"],
            "tool_used": result.get("tool_used") or "",
            "chart_type": result.get("chart_type", "none"),
            "data": json.dumps(result.get("data"), default=str) if result.get("data") else "",
            "cached_at": time.time(),
        }],
        ids=[f"cache_{int(time.time() * 1000000)}"],
    )


async def get_cached_response(question: str) -> dict | None:
    try:
        return await asyncio.to_thread(_sync_get_cached, question)
    except Exception:
        return None


async def set_cached_response(question: str, result: dict) -> None:
    try:
        await asyncio.to_thread(_sync_set_cached, question, result)
    except Exception:
        pass
