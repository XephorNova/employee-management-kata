# AI Insights Token Limiting & Conversation Memory — Design

## Goal

Add per-user daily token limits, persistent conversation memory, and LLM observability to the AI Insights feature. Users see their token usage in the UI and are hard-blocked when the daily limit is reached.

---

## Architecture

Four new service modules sit between the FastAPI endpoint and the Anthropic API:

```
POST /api/ai/query
        │
        ▼
[1] token_limiter.py      — Redis: check daily budget (300k tokens/day)
        │
        ▼
[2] query_cache.py        — Chroma: semantic cache lookup (global, shared across users)
    Cache hit? ──────────────────────────────────────────────────────┐
        │ miss                                                        │
        ▼                                                             │
[3] conversation_store.py — Chroma: load recent + semantically       │
                            similar past exchanges per user           │
        │                                                             │
        ▼                                                             │
[4] ai_service.py (modified) — call Claude with enriched context,    │
                               wrapped by Langfuse trace             │
        │                                                             │
        ▼                                                             │
[5] Post-call: store in query_cache, persist exchange to             │
               conversation_store, INCRBY Redis counter              │
        │                                                             ▼
     Response: answer + token_usage fields          Response: answer + from_cache=true
                                                    (tokens_used=0, no Redis increment)
```

---

## Tech Stack

- **Redis** (`redis-py` with asyncio) — atomic per-user daily token counters
- **Chroma** (`chromadb`, embedded mode) — local vector store for conversation history AND global semantic query cache; default `all-MiniLM-L6-v2` embeddings via `sentence-transformers`
- **Langfuse** (`langfuse` Python SDK, cloud free tier) — LLM observability, one trace per query
- **FastAPI** (existing) — extended AI endpoints
- **React / TanStack Query** (existing) — token gauge UI

---

## New Environment Variables

| Variable | Purpose |
|---|---|
| `REDIS_URL` | e.g. `redis://localhost:6379` |
| `LANGFUSE_PUBLIC_KEY` | Langfuse cloud public key |
| `LANGFUSE_SECRET_KEY` | Langfuse cloud secret key |
| `LANGFUSE_HOST` | Default: `https://cloud.langfuse.com` |

---

## Services

### `backend/app/services/query_cache.py`

Global semantic cache shared across all users. Prevents redundant LLM calls for similar questions.

**Chroma collection:** `global_query_cache` (single collection, not per-user)
**Similarity threshold:** Chroma cosine distance `< 0.08` (equivalent to ~>0.92 cosine similarity) — very high bar to avoid returning subtly different answers
**Cache TTL:** 24 hours — HR data changes (new hires, salary updates), so answers older than 24h are skipped even if semantically similar
**Document format:** the question text as the Chroma document; metadata stores `answer`, `tool_used`, `chart_type`, `data` (JSON string), `cached_at` (Unix timestamp)

```python
async def get_cached_response(question: str) -> dict | None:
    # Semantic search in global_query_cache with k=1
    # Returns cached result dict if distance < 0.08 AND cached_at within 24h
    # Returns None on miss

async def set_cached_response(question: str, result: dict) -> None:
    # Stores result in global_query_cache
    # result keys: answer, tool_used, chart_type, data
```

Cache hits short-circuit the entire LLM + tool pipeline. No Redis token increment on a cache hit (`tokens_used=0`, `tokens_remaining` unchanged).

---

### `backend/app/services/token_limiter.py`

Manages per-user daily token budgets in Redis.

**Redis key pattern:** `ai_tokens:{user_id}:{YYYY-MM-DD}` (UTC date)
**TTL:** 48 hours (survives past midnight, safe cleanup window)
**Daily limit constant:** `TOKEN_LIMIT = 300_000`

```python
async def get_usage(user_id: int) -> dict:
    # Returns: {used, limit, remaining, resets_at (ISO8601 UTC midnight)}

async def check_limit(user_id: int) -> bool:
    # Returns True if user is under limit (can proceed)

async def consume(user_id: int, tokens: int) -> int:
    # INCRBY Redis key, returns new total
```

Redis client is a module-level singleton created from `REDIS_URL`. If Redis is unreachable, the service raises a `503` — no silent fail-open (fail-open would defeat rate limiting).

### `backend/app/services/conversation_store.py`

Stores and retrieves per-user conversation history using Chroma.

**Chroma storage path:** `backend/chroma_data/` (persistent, gitignored)
**Collection naming:** `conversations_user_{user_id}` (one collection per user)
**Document format:** `"Q: {question}\nA: {answer}"` stored as document text; metadata includes `timestamp` (Unix float) and `question` (raw text for display).

```python
async def add_exchange(user_id: int, question: str, answer: str) -> None:
    # Adds Q+A pair to user's Chroma collection

async def get_recent(user_id: int, n: int = 5) -> list[dict]:
    # Returns last n exchanges sorted by timestamp descending
    # Each dict: {question, answer, timestamp}

async def search_similar(user_id: int, question: str, k: int = 3) -> list[dict]:
    # Semantic query against user's collection
    # Returns up to k most similar past exchanges
    # Each dict: {question, answer, timestamp}
```

Chroma operations are CPU-bound (embedding inference). All calls use `asyncio.to_thread`.

### `backend/app/services/langfuse_service.py`

Wraps AI queries as Langfuse traces for observability.

```python
async def tracked_ai_query(db, question, user_id, context_messages) -> dict:
    # Creates a Langfuse trace with user_id tag
    # Calls run_ai_query(db, question, user_id, context_messages)
    # Records: input tokens, output tokens, model, latency
    # Returns same dict as run_ai_query
```

Langfuse client initialized at module level from env vars. If `LANGFUSE_PUBLIC_KEY` is not set, `tracked_ai_query` falls back to calling `run_ai_query` directly (observability is optional, rate limiting is not).

### `backend/app/services/ai_service.py` (modified)

```python
async def run_ai_query(
    db: AsyncSession,
    question: str,
    user_id: int,
    context_messages: list[dict],  # pre-built from conversation_store
) -> dict:
    # Builds Claude messages: context_messages + current question
    # Returns: {answer, tool_used, data, chart_type, tokens_used}
    # tokens_used = response.usage.input_tokens + response.usage.output_tokens
```

Context message format injected before the user question:
```
[System context: Previous relevant conversations]
Q: <past question>
A: <past answer>
...
[End context]
```

---

## API Changes

### `POST /api/ai/query` (modified)

**Request:** unchanged — `{"question": "..."}`

**Success response (200):**
```json
{
  "answer": "The average salary in Engineering is $145,000.",
  "tool_used": "get_avg_salary_by_dept",
  "data": [...],
  "chart_type": "bar",
  "tokens_used": 1240,
  "tokens_remaining": 298760,
  "resets_at": "2026-06-20T00:00:00Z"
}
```

**Rate limit response (429):**
```json
{
  "detail": "Daily token limit reached. Resets at 2026-06-20T00:00:00Z"
}
```

**Endpoint logic:**
1. Extract `current_user` (already injected, `analyst_or_above` dependency)
2. `await check_limit(current_user.id)` → 429 if over limit
3. `cached = await get_cached_response(question)` → if hit, return immediately with `from_cache=True`, `tokens_used=0`
4. `recent = await get_recent(current_user.id, n=5)`
5. `similar = await search_similar(current_user.id, question, k=3)`
6. Deduplicate by timestamp, build `context_messages`
7. `result = await tracked_ai_query(db, question, current_user.id, context_messages)`
8. `await set_cached_response(question, result)`
9. `await consume(current_user.id, result["tokens_used"])`
10. `await add_exchange(current_user.id, question, result["answer"])`
11. Fetch updated usage → append to response

### `GET /api/ai/usage` (new)

Returns the current user's token usage without making a query. Called on page load to populate the gauge.

**Response (200):**
```json
{
  "tokens_used": 150000,
  "tokens_limit": 300000,
  "tokens_remaining": 150000,
  "resets_at": "2026-06-20T00:00:00Z"
}
```

---

## Schema Changes (`backend/app/schemas/ai.py`)

```python
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
    resets_at: str  # ISO8601 UTC
```

---

## Frontend Changes

### Token usage gauge (`frontend/src/pages/Insights.tsx`)

Shown at the top of the page at all times, above the suggestion chips.

```
[████████████░░░░░░░░] 150,000 / 300,000 tokens · Resets at midnight UTC
```

**Color thresholds:**
- `< 80%` used → indigo fill
- `80–95%` used → amber fill
- `> 95%` used → red fill

**Data lifecycle:**
- Fetched via `useQuery(['ai-usage'], getAIUsage)` on page load
- After each successful query mutation, update usage state from the response directly (no extra network call)
- When 429 received: disable Input + Ask button, show message "Daily token limit reached. Resets at midnight UTC."

### `frontend/src/lib/api.ts`

```typescript
export const getAIUsage = () =>
  api.get("/api/ai/usage").then((r) => r.data);
```

`aiQuery` return type updated to include `tokens_used`, `tokens_remaining`, `resets_at`.

---

## Testing

**`backend/tests/test_token_limiter.py`**
- Uses `fakeredis` for unit tests (no real Redis dependency)
- Tests: under limit returns True, at limit returns False, consume increments correctly, TTL is set

**`backend/tests/test_conversation_store.py`**
- Uses a temp Chroma directory (cleaned up after each test)
- Tests: add exchange stores document, get_recent returns sorted by timestamp, search_similar returns relevant results

**`backend/tests/test_query_cache.py`**
- Uses a temp Chroma directory (cleaned up after each test)
- Tests: cache miss returns None, cache hit returns result when distance < threshold, stale entry (>24h) returns None, fresh entry within 24h is returned

**`backend/tests/test_ai.py`** (extends existing)
- Mocked Redis and Chroma
- Tests: 429 returned when over limit, usage fields present in 200 response, `GET /api/ai/usage` returns correct shape, cache hit returns `from_cache=True` and `tokens_used=0`

---

## Error Handling

| Failure | Behavior |
|---|---|
| Redis unreachable | 503 — do not fail open |
| Chroma cache error on read | Log warning, proceed as cache miss (best-effort) |
| Chroma cache error on write | Log warning, do not fail the query response |
| Chroma conversation error on load | Log warning, proceed with empty context (best-effort) |
| Chroma conversation error on save | Log warning, do not fail the query response |
| Langfuse unreachable | Log warning, proceed without tracing |
| Anthropic API error | Existing behavior (propagate error) |

---

## New Dependencies

```
redis[asyncio]>=5.0
chromadb>=0.5
langfuse>=2.0
sentence-transformers>=2.0
```

Added to `backend/requirements.txt`.
