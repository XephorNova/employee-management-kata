from pydantic import BaseModel
from typing import Any, Optional


class AIQueryRequest(BaseModel):
    question: str


class AIQueryResponse(BaseModel):
    answer: str
    tool_used: Optional[str] = None
    data: Optional[Any] = None
    chart_type: str = "none"
