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
