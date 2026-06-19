from __future__ import annotations
import asyncio
import time
from app.services.chroma_client import get_chroma_client


def _get_collection(user_id: int):
    client = get_chroma_client()
    return client.get_or_create_collection(
        name=f"conversations_user_{user_id}",
        metadata={"hnsw:space": "cosine"},
    )


def _sync_add_exchange(user_id: int, question: str, answer: str) -> None:
    col = _get_collection(user_id)
    col.add(
        documents=[f"Q: {question}\nA: {answer}"],
        metadatas=[{"question": question, "answer": answer, "timestamp": time.time()}],
        ids=[f"exchange_{user_id}_{int(time.time() * 1000000)}"],
    )


def _sync_get_recent(user_id: int, n: int) -> list[dict]:
    col = _get_collection(user_id)
    if col.count() == 0:
        return []
    all_results = col.get(include=["metadatas"])
    sorted_meta = sorted(all_results["metadatas"], key=lambda m: m["timestamp"], reverse=True)
    return [
        {"question": m["question"], "answer": m["answer"], "timestamp": m["timestamp"]}
        for m in sorted_meta[:n]
    ]


def _sync_search_similar(user_id: int, question: str, k: int) -> list[dict]:
    col = _get_collection(user_id)
    count = col.count()
    if count == 0:
        return []
    results = col.query(
        query_texts=[question],
        n_results=min(k, count),
        include=["metadatas"],
    )
    return [
        {"question": m["question"], "answer": m["answer"], "timestamp": m["timestamp"]}
        for m in results["metadatas"][0]
    ]


async def add_exchange(user_id: int, question: str, answer: str) -> None:
    try:
        await asyncio.to_thread(_sync_add_exchange, user_id, question, answer)
    except Exception:
        pass


async def get_recent(user_id: int, n: int = 5) -> list[dict]:
    try:
        return await asyncio.to_thread(_sync_get_recent, user_id, n)
    except Exception:
        return []


async def search_similar(user_id: int, question: str, k: int = 3) -> list[dict]:
    try:
        return await asyncio.to_thread(_sync_search_similar, user_id, question, k)
    except Exception:
        return []
