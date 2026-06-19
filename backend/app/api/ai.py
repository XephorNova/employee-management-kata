from __future__ import annotations

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
