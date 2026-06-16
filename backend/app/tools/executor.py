import sqlglot
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.services.analytics_service import (
    get_salary_stats, get_headcount, get_top_earners,
    get_salary_distribution, get_budget_by_department,
    get_pay_band_compliance, get_compensation_breakdown,
)


async def execute_tool(db: AsyncSession, tool_name: str, tool_input: dict):
    filters = tool_input.get("filters", {})

    if tool_name == "get_salary_stats":
        return await get_salary_stats(db, **filters)
    elif tool_name == "get_headcount":
        return await get_headcount(db, group_by=tool_input.get("group_by", "department"), filters=filters)
    elif tool_name == "get_top_earners":
        return await get_top_earners(db, n=tool_input.get("n", 10), filters=filters)
    elif tool_name == "get_salary_distribution":
        return await get_salary_distribution(db, bucket_size=tool_input.get("bucket_size", 5000), filters=filters)
    elif tool_name == "get_budget_by_department":
        return await get_budget_by_department(db, include_bonuses=tool_input.get("include_bonuses", False))
    elif tool_name == "get_pay_band_compliance":
        return await get_pay_band_compliance(db, department=tool_input.get("department"), country=tool_input.get("country"))
    elif tool_name == "get_compensation_breakdown":
        return await get_compensation_breakdown(db, employee_id=tool_input["employee_id"])
    elif tool_name == "run_analytics_query":
        sql = tool_input["sql"]
        stmts = sqlglot.parse(sql)
        if not stmts or not isinstance(stmts[0], sqlglot.exp.Select):
            raise ValueError("Only SELECT statements are allowed")
        result = await db.execute(text(sql))
        return [dict(row) for row in result.mappings().all()]
    else:
        raise ValueError(f"Unknown tool: {tool_name}")
