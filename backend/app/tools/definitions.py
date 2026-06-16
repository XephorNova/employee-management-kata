TOOL_DEFINITIONS = [
    {
        "name": "get_salary_stats",
        "description": "Get salary statistics (avg, median, min, max, p25, p75) with optional filters.",
        "input_schema": {
            "type": "object",
            "properties": {
                "filters": {
                    "type": "object",
                    "properties": {
                        "department": {"type": "string"},
                        "country": {"type": "string"},
                        "employment_type": {"type": "string"},
                        "min_salary": {"type": "number"},
                        "max_salary": {"type": "number"},
                    },
                }
            },
            "required": ["filters"],
        },
    },
    {
        "name": "get_headcount",
        "description": "Get employee headcount grouped by a dimension (department, country, employment_type).",
        "input_schema": {
            "type": "object",
            "properties": {
                "group_by": {"type": "string", "enum": ["department", "country", "employment_type"]},
                "filters": {"type": "object"},
            },
            "required": ["group_by"],
        },
    },
    {
        "name": "get_top_earners",
        "description": "Get the top N employees by base salary.",
        "input_schema": {
            "type": "object",
            "properties": {
                "n": {"type": "integer", "default": 10},
                "filters": {"type": "object"},
            },
        },
    },
    {
        "name": "get_salary_distribution",
        "description": "Get salary distribution as histogram buckets.",
        "input_schema": {
            "type": "object",
            "properties": {
                "bucket_size": {"type": "number", "default": 5000},
                "filters": {"type": "object"},
            },
        },
    },
    {
        "name": "get_budget_by_department",
        "description": "Get monthly salary budget aggregated by department.",
        "input_schema": {
            "type": "object",
            "properties": {
                "include_bonuses": {"type": "boolean", "default": False},
            },
        },
    },
    {
        "name": "get_pay_band_compliance",
        "description": "Get counts of employees in, above, or below their pay band.",
        "input_schema": {
            "type": "object",
            "properties": {
                "department": {"type": "string"},
                "country": {"type": "string"},
            },
        },
    },
    {
        "name": "get_compensation_breakdown",
        "description": "Get full compensation breakdown for a specific employee.",
        "input_schema": {
            "type": "object",
            "properties": {"employee_id": {"type": "integer"}},
            "required": ["employee_id"],
        },
    },
    {
        "name": "run_analytics_query",
        "description": "Run a read-only SQL SELECT as a fallback for questions not covered by other tools.",
        "input_schema": {
            "type": "object",
            "properties": {
                "question": {"type": "string"},
                "sql": {"type": "string"},
            },
            "required": ["question", "sql"],
        },
    },
]
