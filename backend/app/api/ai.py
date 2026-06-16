from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.auth.dependencies import analyst_or_above
from app.models.user import User
from app.schemas.ai import AIQueryRequest, AIQueryResponse
from app.services.ai_service import run_ai_query
from app.core.config import settings

router = APIRouter(prefix="/api/ai", tags=["ai"])


@router.post("/query", response_model=AIQueryResponse)
async def ai_query(
    body: AIQueryRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(analyst_or_above),
):
    if not settings.anthropic_api_key:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="AI service not configured (set ANTHROPIC_API_KEY)")
    result = await run_ai_query(db, body.question)
    return AIQueryResponse(**result)
