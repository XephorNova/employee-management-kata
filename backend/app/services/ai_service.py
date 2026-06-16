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


async def run_ai_query(db: AsyncSession, question: str) -> dict:
    client = AsyncAnthropic(api_key=settings.anthropic_api_key)

    response = await client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=_SYSTEM,
        tools=TOOL_DEFINITIONS,
        messages=[{"role": "user", "content": question}],
    )

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
                    {"role": "user", "content": question},
                    {"role": "assistant", "content": response.content},
                    {
                        "role": "user",
                        "content": [{"type": "tool_result", "tool_use_id": tool_block.id, "content": json.dumps(data, default=str)}],
                    },
                ],
            )
            answer = next((b.text for b in synthesis.content if hasattr(b, "text")), "")
        else:
            answer = next((b.text for b in response.content if hasattr(b, "text")), "")
    else:
        answer = next((b.text for b in response.content if hasattr(b, "text")), "")

    return {"answer": answer, "tool_used": tool_used, "data": data, "chart_type": _infer_chart_type(tool_used)}
