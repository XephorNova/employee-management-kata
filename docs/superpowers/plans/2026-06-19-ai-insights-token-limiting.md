# AI Insights Token Limiting & Conversation Memory — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add per-user daily token limits (300k/day via Redis), global semantic query caching (Chroma), per-user conversation memory (Chroma), and LLM observability (Langfuse) to the AI Insights page, with a live token usage gauge in the frontend.

**Architecture:** Five service modules sit between the FastAPI endpoint and Anthropic: `token_limiter` (Redis counter), `query_cache` (global Chroma collection, shared across users), `conversation_store` (per-user Chroma collections), `langfuse_service` (trace wrapper), and the updated `ai_service`. On every query: check limit → check cache → load context → call LLM (traced) → persist to cache + conversation store → increment Redis counter → return answer with token usage fields.

**Tech Stack:** `redis[asyncio]` 5.x, `chromadb` 0.5.x + `sentence-transformers` (Chroma default embeddings), `langfuse` 2.x, `fakeredis` 2.x (tests only), FastAPI + SQLAlchemy (existing), React + TanStack Query (existing).

**Spec:** `docs/superpowers/specs/2026-06-19-ai-insights-token-limiting-design.md`

---

## File Map

| Action | Path | Responsibility |
|---|---|---|
| Create | `backend/app/services/chroma_client.py` | Singleton `PersistentClient`, shared by query_cache and conversation_store |
| Create | `backend/app/services/token_limiter.py` | Redis per-user daily token counter |
| Create | `backend/app/services/query_cache.py` | Global semantic cache (Chroma `global_query_cache` collection) |
| Create | `backend/app/services/conversation_store.py` | Per-user conversation history (Chroma `conversations_user_{id}`) |
| Create | `backend/app/services/langfuse_service.py` | Langfuse trace wrapper around `run_ai_query` |
| Create | `backend/tests/test_token_limiter.py` | Unit tests for token_limiter |
| Create | `backend/tests/test_query_cache.py` | Unit tests for query_cache |
| Create | `backend/tests/test_conversation_store.py` | Unit tests for conversation_store |
| Modify | `backend/requirements.txt` | Add redis, chromadb, langfuse, sentence-transformers, fakeredis |
| Modify | `backend/app/core/config.py` | Add REDIS_URL, LANGFUSE_* env vars |
| Modify | `backend/app/schemas/ai.py` | Add token fields + from_cache to AIQueryResponse; add AIUsageResponse |
| Modify | `backend/app/services/ai_service.py` | Accept context_messages, track + return tokens_used |
| Modify | `backend/app/api/ai.py` | Full pipeline; add GET /api/ai/usage |
| Modify | `backend/tests/test_ai_tools.py` | Update existing test; add 429 + cache-hit + usage tests |
| Modify | `frontend/src/lib/api.ts` | Add getAIUsage() |
| Modify | `frontend/src/pages/Insights.tsx` | Token gauge, 429 handling, cache indicator |
| Modify | `.gitignore` | Ignore `backend/chroma_data/` |

---

## Task 1: Dependencies, config, gitignore

**Files:**
- Modify: `backend/requirements.txt`
- Modify: `backend/app/core/config.py`
- Modify: `.gitignore`

- [ ] **Step 1: Add new Python dependencies**

Open `backend/requirements.txt` and append these lines:

```
redis[asyncio]==5.0.8
chromadb==0.5.23
langfuse==2.57.6
sentence-transformers==3.3.1
fakeredis==2.26.2
```

- [ ] **Step 2: Install them**

```bash
cd backend
.venv/bin/pip install redis[asyncio]==5.0.8 chromadb==0.5.23 langfuse==2.57.6 "sentence-transformers==3.3.1" fakeredis==2.26.2
```

`sentence-transformers` will download the `all-MiniLM-L6-v2` model (~90 MB) on first Chroma collection query. This is expected. Expected output ends with `Successfully installed ...`.

- [ ] **Step 3: Add config fields**

Open `backend/app/core/config.py`. Replace the entire file with:

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite+aiosqlite:///./acme_hr.db"
    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    anthropic_api_key: str = ""
    redis_url: str = "redis://localhost:6379"
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "https://cloud.langfuse.com"

    class Config:
        env_file = ".env"


settings = Settings()
```

- [ ] **Step 4: Gitignore Chroma data directory**

Open `.gitignore` (project root) and append:

```
backend/chroma_data/
```

- [ ] **Step 5: Verify config loads**

```bash
cd backend
.venv/bin/python -c "from app.core.config import settings; print(settings.redis_url)"
```

Expected: `redis://localhost:6379`

- [ ] **Step 6: Commit**

```bash
git add backend/requirements.txt backend/app/core/config.py .gitignore
git commit -m "feat: add redis, chromadb, langfuse deps and config fields"
```

---

## Task 2: Extend AI schemas

**Files:**
- Modify: `backend/app/schemas/ai.py`

- [ ] **Step 1: Replace the file**

```python
from pydantic import BaseModel
from typing import Any, Optional


class AIQueryRequest(BaseModel):
    question: str


class AIQueryResponse(BaseModel):
    answer: str
    tool_used: Optional[str] = None
    data: Optional[Any] = None
    chart_type: str = "none"
    tokens_used: int = 0
    tokens_remaining: int = 300_000
    resets_at: str = ""
    from_cache: bool = False


class AIUsageResponse(BaseModel):
    tokens_used: int
    tokens_limit: int
    tokens_remaining: int
    resets_at: str
```

- [ ] **Step 2: Verify it imports cleanly**

```bash
cd backend
.venv/bin/python -c "from app.schemas.ai import AIQueryResponse, AIUsageResponse; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/schemas/ai.py
git commit -m "feat: extend AI schemas with token usage and from_cache fields"
```

---

## Task 3: Shared Chroma client module

**Files:**
- Create: `backend/app/services/chroma_client.py`

The Chroma `PersistentClient` is expensive to initialize (it creates or opens an on-disk database). Both `query_cache` and `conversation_store` will share one instance via this module.

- [ ] **Step 1: Create the file**

```python
from __future__ import annotations
from pathlib import Path
import chromadb

_CHROMA_DIR = Path(__file__).parent.parent.parent / "chroma_data"
_client: chromadb.PersistentClient | None = None


def get_chroma_client() -> chromadb.PersistentClient:
    global _client
    if _client is None:
        _CHROMA_DIR.mkdir(exist_ok=True)
        _client = chromadb.PersistentClient(path=str(_CHROMA_DIR))
    return _client
```

- [ ] **Step 2: Verify import**

```bash
cd backend
.venv/bin/python -c "from app.services.chroma_client import get_chroma_client; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/chroma_client.py
git commit -m "feat: add shared Chroma persistent client module"
```

---

## Task 4: Token limiter service (TDD)

**Files:**
- Create: `backend/tests/test_token_limiter.py`
- Create: `backend/app/services/token_limiter.py`

Uses `fakeredis.aioredis.FakeRedis` as an in-memory async Redis substitute. Tests patch `_get_redis` to return the fake client.

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_token_limiter.py`:

```python
from __future__ import annotations
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import fakeredis.aioredis


def make_fake_redis() -> fakeredis.aioredis.FakeRedis:
    return fakeredis.aioredis.FakeRedis(decode_responses=True)


@pytest.mark.asyncio
async def test_check_limit_under_limit():
    r = make_fake_redis()
    with patch("app.services.token_limiter._get_redis", return_value=r):
        from app.services.token_limiter import check_limit
        result = await check_limit(user_id=1)
    assert result is True


@pytest.mark.asyncio
async def test_check_limit_at_limit():
    r = make_fake_redis()
    with patch("app.services.token_limiter._get_redis", return_value=r):
        from app.services.token_limiter import check_limit, consume, TOKEN_LIMIT
        await consume(1, TOKEN_LIMIT)
        result = await check_limit(1)
    assert result is False


@pytest.mark.asyncio
async def test_consume_returns_new_total():
    r = make_fake_redis()
    with patch("app.services.token_limiter._get_redis", return_value=r):
        from app.services.token_limiter import consume
        total = await consume(user_id=1, tokens=500)
    assert total == 500


@pytest.mark.asyncio
async def test_consume_accumulates():
    r = make_fake_redis()
    with patch("app.services.token_limiter._get_redis", return_value=r):
        from app.services.token_limiter import consume
        await consume(1, 200)
        total = await consume(1, 300)
    assert total == 500


@pytest.mark.asyncio
async def test_get_usage_shape():
    r = make_fake_redis()
    with patch("app.services.token_limiter._get_redis", return_value=r):
        from app.services.token_limiter import consume, get_usage, TOKEN_LIMIT
        await consume(1, 1000)
        usage = await get_usage(1)
    assert usage["used"] == 1000
    assert usage["limit"] == TOKEN_LIMIT
    assert usage["remaining"] == TOKEN_LIMIT - 1000
    assert "resets_at" in usage


@pytest.mark.asyncio
async def test_get_usage_zero_when_no_activity():
    r = make_fake_redis()
    with patch("app.services.token_limiter._get_redis", return_value=r):
        from app.services.token_limiter import get_usage
        usage = await get_usage(user_id=99)
    assert usage["used"] == 0
    assert usage["remaining"] == usage["limit"]
```

- [ ] **Step 2: Run tests — expect failure**

```bash
cd backend
.venv/bin/pytest tests/test_token_limiter.py -v 2>&1 | head -30
```

Expected: `ModuleNotFoundError: No module named 'app.services.token_limiter'`

- [ ] **Step 3: Implement token_limiter.py**

Create `backend/app/services/token_limiter.py`:

```python
from __future__ import annotations
from datetime import datetime, timezone, timedelta
import redis.asyncio as aioredis
from app.core.config import settings

TOKEN_LIMIT = 300_000
_client: aioredis.Redis | None = None


def _get_redis() -> aioredis.Redis:
    global _client
    if _client is None:
        _client = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _client


def _day_key(user_id: int) -> str:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return f"ai_tokens:{user_id}:{today}"


def _resets_at() -> str:
    now = datetime.now(timezone.utc)
    midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return midnight.isoformat()


async def get_usage(user_id: int) -> dict:
    r = _get_redis()
    used = int(await r.get(_day_key(user_id)) or 0)
    return {
        "used": used,
        "limit": TOKEN_LIMIT,
        "remaining": max(0, TOKEN_LIMIT - used),
        "resets_at": _resets_at(),
    }


async def check_limit(user_id: int) -> bool:
    r = _get_redis()
    used = int(await r.get(_day_key(user_id)) or 0)
    return used < TOKEN_LIMIT


async def consume(user_id: int, tokens: int) -> int:
    r = _get_redis()
    key = _day_key(user_id)
    pipe = r.pipeline()
    pipe.incrby(key, tokens)
    pipe.expire(key, 48 * 3600)
    results = await pipe.execute()
    return results[0]
```

- [ ] **Step 4: Run tests — expect all pass**

```bash
cd backend
.venv/bin/pytest tests/test_token_limiter.py -v
```

Expected: `6 passed`

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/token_limiter.py backend/tests/test_token_limiter.py
git commit -m "feat: add Redis per-user daily token limiter with tests"
```

---

## Task 5: Global semantic query cache (TDD)

**Files:**
- Create: `backend/tests/test_query_cache.py`
- Create: `backend/app/services/query_cache.py`

Uses a real Chroma `PersistentClient` pointed at a temp directory, patching `get_chroma_client` from `chroma_client` module. The sentence-transformers model will be downloaded on first run (one-time, ~90 MB).

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_query_cache.py`:

```python
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
        from app.services.query_cache import get_cached_response, CACHE_COLLECTION, SIMILARITY_THRESHOLD
        col = temp_client.get_or_create_collection(
            name=CACHE_COLLECTION, metadata={"hnsw:space": "cosine"}
        )
        import json
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
```

- [ ] **Step 2: Run tests — expect failure**

```bash
cd backend
.venv/bin/pytest tests/test_query_cache.py -v 2>&1 | head -20
```

Expected: `ModuleNotFoundError: No module named 'app.services.query_cache'`

- [ ] **Step 3: Implement query_cache.py**

Create `backend/app/services/query_cache.py`:

```python
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
```

- [ ] **Step 4: Run tests — expect all pass**

```bash
cd backend
.venv/bin/pytest tests/test_query_cache.py -v
```

Expected: `5 passed` (first run downloads model, may take 1–2 min)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/query_cache.py backend/tests/test_query_cache.py
git commit -m "feat: add global semantic query cache using Chroma with TTL and similarity threshold"
```

---

## Task 6: Per-user conversation store (TDD)

**Files:**
- Create: `backend/tests/test_conversation_store.py`
- Create: `backend/app/services/conversation_store.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_conversation_store.py`:

```python
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
```

- [ ] **Step 2: Run tests — expect failure**

```bash
cd backend
.venv/bin/pytest tests/test_conversation_store.py -v 2>&1 | head -20
```

Expected: `ModuleNotFoundError: No module named 'app.services.conversation_store'`

- [ ] **Step 3: Implement conversation_store.py**

Create `backend/app/services/conversation_store.py`:

```python
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
```

- [ ] **Step 4: Run tests — expect all pass**

```bash
cd backend
.venv/bin/pytest tests/test_conversation_store.py -v
```

Expected: `7 passed`

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/conversation_store.py backend/tests/test_conversation_store.py
git commit -m "feat: add per-user conversation store with Chroma semantic search"
```

---

## Task 7: Langfuse observability wrapper

**Files:**
- Create: `backend/app/services/langfuse_service.py`

No TDD here — Langfuse tracing is best-effort and falls back gracefully when not configured, making tests against the real service impractical in CI.

- [ ] **Step 1: Create langfuse_service.py**

```python
from __future__ import annotations
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings

logger = logging.getLogger(__name__)
_langfuse_client = None


def _get_langfuse():
    global _langfuse_client
    if _langfuse_client is None and settings.langfuse_public_key:
        try:
            from langfuse import Langfuse
            _langfuse_client = Langfuse(
                public_key=settings.langfuse_public_key,
                secret_key=settings.langfuse_secret_key,
                host=settings.langfuse_host,
            )
        except Exception as exc:
            logger.warning("Langfuse init failed: %s", exc)
    return _langfuse_client


async def tracked_ai_query(
    db: AsyncSession,
    question: str,
    user_id: int,
    context_messages: list[dict],
) -> dict:
    from app.services.ai_service import run_ai_query

    langfuse = _get_langfuse()
    if langfuse is None:
        return await run_ai_query(db, question, user_id, context_messages)

    trace = langfuse.trace(name="ai_query", user_id=str(user_id), input=question)
    try:
        result = await run_ai_query(db, question, user_id, context_messages)
        trace.update(
            output=result["answer"],
            metadata={
                "tokens_used": result.get("tokens_used", 0),
                "tool_used": result.get("tool_used"),
            },
        )
        return result
    except Exception as exc:
        trace.update(metadata={"error": str(exc)})
        raise
    finally:
        try:
            langfuse.flush()
        except Exception:
            pass
```

- [ ] **Step 2: Verify import**

```bash
cd backend
.venv/bin/python -c "from app.services.langfuse_service import tracked_ai_query; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/langfuse_service.py
git commit -m "feat: add Langfuse observability wrapper with graceful fallback"
```

---

## Task 8: Modify ai_service.py

**Files:**
- Modify: `backend/app/services/ai_service.py`

Add `context_messages` parameter (pre-built conversation context), inject it as a question prefix, and return `tokens_used` by summing `usage.input_tokens + usage.output_tokens` across both Anthropic calls.

- [ ] **Step 1: Replace ai_service.py**

```python
from __future__ import annotations
import json
from anthropic import AsyncAnthropic
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.tools.definitions import TOOL_DEFINITIONS
from app.tools.executor import execute_tool

_SYSTEM = """You are an HR analytics assistant for ACME Corporation.
Use the available tools to answer compensation and headcount questions.
After receiving tool results, synthesize a clear natural language answer.
Always set chart_type in your reasoning: table | bar | pie | line | none."""


def _infer_chart_type(tool_name):
    if not tool_name:
        return "none"
    if "distribution" in tool_name or "budget" in tool_name:
        return "bar"
    if "headcount" in tool_name:
        return "pie"
    if "top_earners" in tool_name:
        return "table"
    return "table"


async def run_ai_query(
    db: AsyncSession,
    question: str,
    user_id: int = 0,
    context_messages: list[dict] | None = None,
) -> dict:
    client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    total_tokens = 0

    content = question
    if context_messages:
        context_str = "\n\n".join(
            f"Previous Q: {m['question']}\nPrevious A: {m['answer']}"
            for m in context_messages
        )
        content = f"Context from previous conversations:\n{context_str}\n\nCurrent question: {question}"

    response = await client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=_SYSTEM,
        tools=TOOL_DEFINITIONS,
        messages=[{"role": "user", "content": content}],
    )
    total_tokens += response.usage.input_tokens + response.usage.output_tokens

    tool_used = None
    data = None

    if response.stop_reason == "tool_use":
        tool_block = next((b for b in response.content if b.type == "tool_use"), None)
        if tool_block:
            tool_used = tool_block.name
            data = await execute_tool(db, tool_used, tool_block.input)

            synthesis = await client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=1024,
                system=_SYSTEM,
                tools=TOOL_DEFINITIONS,
                messages=[
                    {"role": "user", "content": content},
                    {"role": "assistant", "content": response.content},
                    {
                        "role": "user",
                        "content": [{"type": "tool_result", "tool_use_id": tool_block.id, "content": json.dumps(data, default=str)}],
                    },
                ],
            )
            total_tokens += synthesis.usage.input_tokens + synthesis.usage.output_tokens
            answer = next((b.text for b in synthesis.content if hasattr(b, "text")), "")
        else:
            answer = next((b.text for b in response.content if hasattr(b, "text")), "")
    else:
        answer = next((b.text for b in response.content if hasattr(b, "text")), "")

    return {
        "answer": answer,
        "tool_used": tool_used,
        "data": data,
        "chart_type": _infer_chart_type(tool_used),
        "tokens_used": total_tokens,
    }
```

- [ ] **Step 2: Verify import**

```bash
cd backend
.venv/bin/python -c "from app.services.ai_service import run_ai_query; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/ai_service.py
git commit -m "feat: extend ai_service to accept conversation context and return tokens_used"
```

---

## Task 9: Wire the full pipeline in api/ai.py

**Files:**
- Modify: `backend/app/api/ai.py`

This is where all services are composed. The order is: limit check → cache lookup → context load → LLM call (traced) → cache write → conversation write → token consume → respond.

- [ ] **Step 1: Replace api/ai.py**

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.auth.dependencies import analyst_or_above
from app.models.user import User
from app.schemas.ai import AIQueryRequest, AIQueryResponse, AIUsageResponse
from app.services.token_limiter import check_limit, consume, get_usage
from app.services.query_cache import get_cached_response, set_cached_response
from app.services.conversation_store import get_recent, search_similar, add_exchange
from app.services.langfuse_service import tracked_ai_query
from app.core.config import settings

router = APIRouter(prefix="/api/ai", tags=["ai"])


@router.post("/query", response_model=AIQueryResponse)
async def ai_query(
    body: AIQueryRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(analyst_or_above),
):
    if not settings.anthropic_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service not configured (set ANTHROPIC_API_KEY)",
        )

    if not await check_limit(current_user.id):
        usage = await get_usage(current_user.id)
        raise HTTPException(
            status_code=429,
            detail=f"Daily token limit reached. Resets at {usage['resets_at']}",
        )

    cached = await get_cached_response(body.question)
    if cached:
        usage = await get_usage(current_user.id)
        return AIQueryResponse(
            answer=cached["answer"],
            tool_used=cached.get("tool_used"),
            data=cached.get("data"),
            chart_type=cached.get("chart_type", "none"),
            tokens_used=0,
            tokens_remaining=usage["remaining"],
            resets_at=usage["resets_at"],
            from_cache=True,
        )

    recent = await get_recent(current_user.id, n=5)
    similar = await search_similar(current_user.id, body.question, k=3)

    seen: set[float] = set()
    context_messages: list[dict] = []
    for msg in sorted(recent + similar, key=lambda m: m["timestamp"], reverse=True):
        ts = msg["timestamp"]
        if ts not in seen:
            seen.add(ts)
            context_messages.append(msg)
    context_messages = context_messages[:6]

    result = await tracked_ai_query(db, body.question, current_user.id, context_messages)

    await set_cached_response(body.question, result)
    await add_exchange(current_user.id, body.question, result["answer"])

    tokens_used = result.get("tokens_used", 0)
    await consume(current_user.id, tokens_used)
    usage = await get_usage(current_user.id)

    return AIQueryResponse(
        answer=result["answer"],
        tool_used=result.get("tool_used"),
        data=result.get("data"),
        chart_type=result.get("chart_type", "none"),
        tokens_used=tokens_used,
        tokens_remaining=usage["remaining"],
        resets_at=usage["resets_at"],
        from_cache=False,
    )


@router.get("/usage", response_model=AIUsageResponse)
async def get_ai_usage(
    current_user: User = Depends(analyst_or_above),
):
    usage = await get_usage(current_user.id)
    return AIUsageResponse(
        tokens_used=usage["used"],
        tokens_limit=usage["limit"],
        tokens_remaining=usage["remaining"],
        resets_at=usage["resets_at"],
    )
```

- [ ] **Step 2: Verify FastAPI starts without errors**

```bash
cd backend
.venv/bin/python -c "from app.main import app; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/api/ai.py
git commit -m "feat: wire token limiting, query cache, conversation context, and Langfuse in AI endpoint"
```

---

## Task 10: Update integration tests

**Files:**
- Modify: `backend/tests/test_ai_tools.py`

The existing `test_ai_query_endpoint_mocked` test patches `AsyncAnthropic` and `settings`. After our changes, the endpoint calls many more collaborators, so they must all be mocked. We also add three new tests: 429, cache-hit, and usage endpoint.

- [ ] **Step 1: Replace test_ai_tools.py**

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import timedelta
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
import app.models  # noqa
from app.main import app
from app.core.database import Base, get_db
from app.models.user import User, UserRole
from app.auth.utils import hash_password, create_access_token
from app.tools.executor import execute_tool

_ENGINE_AI = create_async_engine("sqlite+aiosqlite:///:memory:")
_Session_AI = async_sessionmaker(_ENGINE_AI, expire_on_commit=False)

_MOCK_USAGE = {
    "used": 1000,
    "limit": 300_000,
    "remaining": 299_000,
    "resets_at": "2026-06-20T00:00:00+00:00",
}

_ALL_COLLABORATORS = {
    "app.api.ai.check_limit": AsyncMock(return_value=True),
    "app.api.ai.get_cached_response": AsyncMock(return_value=None),
    "app.api.ai.get_recent": AsyncMock(return_value=[]),
    "app.api.ai.search_similar": AsyncMock(return_value=[]),
    "app.api.ai.set_cached_response": AsyncMock(),
    "app.api.ai.add_exchange": AsyncMock(),
    "app.api.ai.consume": AsyncMock(return_value=1000),
    "app.api.ai.get_usage": AsyncMock(return_value=_MOCK_USAGE),
    "app.api.ai.tracked_ai_query": AsyncMock(return_value={
        "answer": "Average salary is $75,000.",
        "tool_used": None,
        "data": None,
        "chart_type": "none",
        "tokens_used": 1000,
    }),
}


@pytest.fixture(scope="module")
async def ai_setup():
    async with _ENGINE_AI.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with _Session_AI() as s:
        s.add(User(email="a@acme.com", hashed_password=hash_password("pw"), role=UserRole.hr_analyst))
        await s.commit()
    yield
    async with _ENGINE_AI.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def ai_client(ai_setup):
    async with _Session_AI() as s:
        async def override():
            yield s
        app.dependency_overrides[get_db] = override
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            yield c
        app.dependency_overrides.clear()


def _analyst_token():
    return create_access_token({"sub": "a@acme.com", "role": "hr_analyst"}, expires_delta=timedelta(hours=1))


@pytest.mark.asyncio
async def test_execute_get_salary_stats():
    mock_db = AsyncMock()
    with patch("app.tools.executor.get_salary_stats", new=AsyncMock(return_value={"count": 10, "avg": 5000})) as fn:
        result = await execute_tool(mock_db, "get_salary_stats", {"filters": {}})
    fn.assert_called_once()
    assert result["count"] == 10


@pytest.mark.asyncio
async def test_execute_get_headcount():
    mock_db = AsyncMock()
    with patch("app.tools.executor.get_headcount", new=AsyncMock(return_value=[{"group": "Engineering", "count": 50}])) as fn:
        result = await execute_tool(mock_db, "get_headcount", {"group_by": "department", "filters": {}})
    fn.assert_called_once()
    assert result[0]["group"] == "Engineering"


@pytest.mark.asyncio
async def test_unknown_tool_raises():
    mock_db = AsyncMock()
    with pytest.raises(ValueError, match="Unknown tool"):
        await execute_tool(mock_db, "nonexistent_tool", {})


@pytest.mark.asyncio
async def test_sql_injection_blocked():
    mock_db = AsyncMock()
    with pytest.raises(ValueError, match="Only SELECT"):
        await execute_tool(mock_db, "run_analytics_query", {"question": "delete all", "sql": "DELETE FROM employees"})


@pytest.mark.asyncio
async def test_ai_query_endpoint_mocked(ai_client):
    with patch("app.api.ai.settings") as mock_settings, \
         patch("app.api.ai.check_limit", new=AsyncMock(return_value=True)), \
         patch("app.api.ai.get_cached_response", new=AsyncMock(return_value=None)), \
         patch("app.api.ai.get_recent", new=AsyncMock(return_value=[])), \
         patch("app.api.ai.search_similar", new=AsyncMock(return_value=[])), \
         patch("app.api.ai.set_cached_response", new=AsyncMock()), \
         patch("app.api.ai.add_exchange", new=AsyncMock()), \
         patch("app.api.ai.consume", new=AsyncMock(return_value=1000)), \
         patch("app.api.ai.get_usage", new=AsyncMock(return_value=_MOCK_USAGE)), \
         patch("app.api.ai.tracked_ai_query", new=AsyncMock(return_value={
             "answer": "Average salary is $75,000.",
             "tool_used": None,
             "data": None,
             "chart_type": "none",
             "tokens_used": 1000,
         })):
        mock_settings.anthropic_api_key = "test-key"
        resp = await ai_client.post(
            "/api/ai/query",
            json={"question": "What is the average salary?"},
            headers={"Authorization": f"Bearer {_analyst_token()}"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["answer"] == "Average salary is $75,000."
    assert data["tokens_used"] == 1000
    assert data["tokens_remaining"] == 299_000
    assert data["from_cache"] is False


@pytest.mark.asyncio
async def test_ai_query_returns_429_when_over_limit(ai_client):
    over_usage = {"used": 300_000, "limit": 300_000, "remaining": 0, "resets_at": "2026-06-20T00:00:00+00:00"}
    with patch("app.api.ai.settings") as mock_settings, \
         patch("app.api.ai.check_limit", new=AsyncMock(return_value=False)), \
         patch("app.api.ai.get_usage", new=AsyncMock(return_value=over_usage)):
        mock_settings.anthropic_api_key = "test-key"
        resp = await ai_client.post(
            "/api/ai/query",
            json={"question": "Anything"},
            headers={"Authorization": f"Bearer {_analyst_token()}"},
        )

    assert resp.status_code == 429
    assert "resets_at" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_ai_query_cache_hit_skips_llm(ai_client):
    cached = {"answer": "Cached answer", "tool_used": None, "data": None, "chart_type": "none"}
    with patch("app.api.ai.settings") as mock_settings, \
         patch("app.api.ai.check_limit", new=AsyncMock(return_value=True)), \
         patch("app.api.ai.get_cached_response", new=AsyncMock(return_value=cached)), \
         patch("app.api.ai.get_usage", new=AsyncMock(return_value=_MOCK_USAGE)), \
         patch("app.api.ai.tracked_ai_query", new=AsyncMock()) as mock_llm:
        mock_settings.anthropic_api_key = "test-key"
        resp = await ai_client.post(
            "/api/ai/query",
            json={"question": "test?"},
            headers={"Authorization": f"Bearer {_analyst_token()}"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["from_cache"] is True
    assert data["tokens_used"] == 0
    mock_llm.assert_not_called()


@pytest.mark.asyncio
async def test_get_ai_usage_endpoint(ai_client):
    with patch("app.api.ai.get_usage", new=AsyncMock(return_value=_MOCK_USAGE)):
        resp = await ai_client.get(
            "/api/ai/usage",
            headers={"Authorization": f"Bearer {_analyst_token()}"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["tokens_used"] == 1000
    assert data["tokens_limit"] == 300_000
    assert data["tokens_remaining"] == 299_000
    assert "resets_at" in data
```

- [ ] **Step 2: Run the full test suite**

```bash
cd backend
.venv/bin/pytest tests/test_ai_tools.py -v
```

Expected: `8 passed`

- [ ] **Step 3: Run all tests to check for regressions**

```bash
cd backend
.venv/bin/pytest --ignore=tests/test_query_cache.py --ignore=tests/test_conversation_store.py -v 2>&1 | tail -20
```

Expected: all tests pass (the two Chroma tests are excluded here because they download the embedding model; run them separately if needed).

- [ ] **Step 4: Commit**

```bash
git add backend/tests/test_ai_tools.py
git commit -m "test: update AI integration tests for token limiting, cache hit, and usage endpoint"
```

---

## Task 11: Frontend — token gauge and 429 handling

**Files:**
- Modify: `frontend/src/lib/api.ts`
- Modify: `frontend/src/pages/Insights.tsx`

- [ ] **Step 1: Add getAIUsage to api.ts**

Open `frontend/src/lib/api.ts`. Add after the existing `aiQuery` export (before the `// Meta` comment):

```typescript
// AI usage
export interface AIUsage {
  tokens_used: number;
  tokens_limit: number;
  tokens_remaining: number;
  resets_at: string;
}

export const getAIUsage = (): Promise<AIUsage> =>
  api.get("/api/ai/usage").then((r) => r.data);
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend
npm run build 2>&1 | tail -10
```

Expected: no TypeScript errors.

- [ ] **Step 3: Replace Insights.tsx**

```typescript
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { aiQuery, getAIUsage, type AIUsage } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from "recharts";

const COLORS = ["#6366f1", "#22c55e", "#f59e0b", "#ef4444", "#8b5cf6", "#06b6d4"];

const SUGGESTIONS = [
  "What is the average salary in Engineering?",
  "Which department has the most employees?",
  "Show me the top 5 earners",
  "What is the salary distribution?",
  "How many employees are in each country?",
];

interface Message {
  role: "user" | "assistant";
  content: string;
  data?: unknown;
  chart_type?: string;
  tool_used?: string | null;
  from_cache?: boolean;
}

function TokenGauge({ usage }: { usage: AIUsage | undefined }) {
  if (!usage) return null;
  const pct = (usage.tokens_used / usage.tokens_limit) * 100;
  const barColor = pct > 95 ? "bg-red-500" : pct > 80 ? "bg-amber-500" : "bg-indigo-500";
  const resetTime = new Date(usage.resets_at).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });
  return (
    <div className="space-y-1 p-3 rounded-lg border border-slate-200 bg-white">
      <div className="flex justify-between text-xs text-slate-500">
        <span>
          {usage.tokens_used.toLocaleString()} / {usage.tokens_limit.toLocaleString()} tokens used today
        </span>
        <span>Resets at {resetTime}</span>
      </div>
      <div className="h-1.5 w-full bg-slate-200 rounded-full overflow-hidden">
        <div
          className={`h-full ${barColor} rounded-full transition-all duration-500`}
          style={{ width: `${Math.min(pct, 100)}%` }}
        />
      </div>
    </div>
  );
}

function ChartBlock({ data, chartType }: { data: unknown; chartType: string }) {
  const arr = Array.isArray(data) ? data : [];
  if (!arr.length) return null;

  if (chartType === "bar") {
    const keys = Object.keys(arr[0] as Record<string, unknown>).filter(
      (k) => k !== "group" && k !== "department" && k !== "range_start" && k !== "range_end"
    );
    const xKey = Object.keys(arr[0] as Record<string, unknown>)[0];
    return (
      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={arr}>
          <XAxis dataKey={xKey} tick={{ fontSize: 11 }} />
          <YAxis tick={{ fontSize: 11 }} />
          <Tooltip />
          {keys.map((k, i) => (
            <Bar key={k} dataKey={k} fill={COLORS[i % COLORS.length]} radius={[3, 3, 0, 0]} />
          ))}
        </BarChart>
      </ResponsiveContainer>
    );
  }

  if (chartType === "pie") {
    return (
      <ResponsiveContainer width="100%" height={200}>
        <PieChart>
          <Pie data={arr} dataKey="count" nameKey="group" cx="50%" cy="50%" outerRadius={70}>
            {arr.map((_: unknown, i: number) => (
              <Cell key={String(i)} fill={COLORS[i % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip />
        </PieChart>
      </ResponsiveContainer>
    );
  }

  if (chartType === "table" && arr.length) {
    const headers = Object.keys(arr[0] as Record<string, unknown>);
    return (
      <div className="overflow-x-auto mt-2">
        <table className="text-xs w-full">
          <thead>
            <tr>
              {headers.map((h) => (
                <th key={h} className="text-left px-2 py-1 bg-slate-100 font-medium">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {arr.slice(0, 20).map((row: unknown, i: number) => (
              <tr key={i} className="border-t">
                {headers.map((h) => (
                  <td key={h} className="px-2 py-1">
                    {String((row as Record<string, unknown>)[h] ?? "")}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  return null;
}

export default function Insights() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [limitReached, setLimitReached] = useState(false);
  const queryClient = useQueryClient();

  const { data: usage } = useQuery({
    queryKey: ["ai-usage"],
    queryFn: getAIUsage,
    refetchInterval: 60_000,
  });

  const mutation = useMutation({
    mutationFn: (question: string) => aiQuery(question),
    onSuccess: (data, question) => {
      setMessages((prev) => [
        ...prev,
        { role: "user", content: question },
        {
          role: "assistant",
          content: data.answer,
          data: data.data,
          chart_type: data.chart_type,
          tool_used: data.tool_used,
          from_cache: data.from_cache,
        },
      ]);
      queryClient.invalidateQueries({ queryKey: ["ai-usage"] });
    },
    onError: (error: unknown) => {
      const status = (error as { response?: { status?: number } })?.response?.status;
      if (status === 429) {
        setLimitReached(true);
        queryClient.invalidateQueries({ queryKey: ["ai-usage"] });
      }
    },
  });

  function ask(question: string) {
    if (!question.trim() || limitReached) return;
    setInput("");
    mutation.mutate(question);
  }

  return (
    <div className="space-y-4 max-w-3xl">
      <h1 className="text-2xl font-bold">AI Insights</h1>
      <p className="text-slate-500 text-sm">
        Ask natural language questions about employee compensation and headcount.
      </p>

      <TokenGauge usage={usage} />

      {limitReached && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          Daily token limit reached. You can ask more questions tomorrow.
        </div>
      )}

      {messages.length === 0 && !limitReached && (
        <div className="space-y-2">
          <p className="text-xs text-slate-400 uppercase font-medium">Try asking…</p>
          <div className="flex flex-wrap gap-2">
            {SUGGESTIONS.map((s) => (
              <button
                key={s}
                onClick={() => ask(s)}
                className="text-sm px-3 py-1.5 rounded-full border border-slate-200 hover:border-indigo-300 hover:text-indigo-600 transition-colors"
              >
                {s}
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="space-y-4">
        {messages.map((msg, i) => (
          <div key={i} className={msg.role === "user" ? "text-right" : ""}>
            <Card className={msg.role === "user" ? "inline-block bg-indigo-600 text-white" : ""}>
              <CardContent className="p-3 text-sm whitespace-pre-wrap">
                {msg.content}
                {msg.role === "assistant" && !!msg.data && msg.chart_type !== "none" && (
                  <ChartBlock data={msg.data} chartType={msg.chart_type!} />
                )}
                {msg.role === "assistant" && msg.tool_used && (
                  <p className="text-xs text-slate-400 mt-2">Tool: {msg.tool_used}</p>
                )}
                {msg.role === "assistant" && msg.from_cache && (
                  <p className="text-xs text-slate-400 mt-1">Cached · 0 tokens used</p>
                )}
              </CardContent>
            </Card>
          </div>
        ))}
        {mutation.isPending && (
          <div className="text-slate-400 text-sm animate-pulse">Thinking…</div>
        )}
      </div>

      <div className="flex gap-2 sticky bottom-0 bg-slate-50 pt-2">
        <Input
          placeholder="Ask a question about salary data…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && ask(input)}
          disabled={mutation.isPending || limitReached}
        />
        <Button
          onClick={() => ask(input)}
          disabled={mutation.isPending || !input.trim() || limitReached}
        >
          Ask
        </Button>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Verify TypeScript compiles**

```bash
cd frontend
npm run build 2>&1 | tail -10
```

Expected: no errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/api.ts frontend/src/pages/Insights.tsx
git commit -m "feat: add token gauge, cache indicator, and 429 handling to AI Insights page"
```

---

## Self-Review

**Spec coverage:**
- ✅ Redis per-user daily token limit (300k) → Task 4 (token_limiter)
- ✅ Hard block at limit → Task 9 (ai.py returns 429)
- ✅ Daily reset via TTL → token_limiter `expire(key, 48*3600)`
- ✅ Global semantic query cache → Task 5 (query_cache, SIMILARITY_THRESHOLD=0.08, TTL=24h)
- ✅ Cache hit: from_cache=True, tokens_used=0 → Task 9 + Task 10
- ✅ Per-user conversation store → Task 6 (conversation_store)
- ✅ Recent (n=5) + similar (k=3) context → Task 9 (dedup + cap at 6)
- ✅ Langfuse tracing with fallback → Task 7
- ✅ GET /api/ai/usage endpoint → Task 9
- ✅ Frontend token gauge with color thresholds → Task 11
- ✅ 429 disables input + shows message → Task 11
- ✅ Cache indicator on assistant messages → Task 11

**Placeholder scan:** No TBDs, TODOs, or vague steps. Every step has concrete code.

**Type consistency:**
- `get_usage` returns `{used, limit, remaining, resets_at}` — consumed consistently across api/ai.py
- `run_ai_query` returns `{answer, tool_used, data, chart_type, tokens_used}` — all keys present throughout
- `AIUsage` interface in api.ts matches `AIUsageResponse` Pydantic model field names exactly
