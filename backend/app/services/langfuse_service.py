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
