import statistics
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from sqlalchemy.orm import selectinload
from app.models.employee import Employee, EmployeeStatus
from app.models.compensation import SalaryRecord, PayFrequency


def _latest_salary_sq():
    return (
        select(SalaryRecord.employee_id, func.max(SalaryRecord.effective_date).label("max_date"))
        .group_by(SalaryRecord.employee_id)
        .subquery()
    )


async def get_salary_stats(
    db: AsyncSession,
    department: Optional[str] = None,
    country: Optional[str] = None,
    employment_type: Optional[str] = None,
    min_salary: Optional[float] = None,
    max_salary: Optional[float] = None,
) -> dict:
    sq = _latest_salary_sq()
    q = (
        select(SalaryRecord.base_salary, SalaryRecord.pay_frequency)
        .join(sq, (SalaryRecord.employee_id == sq.c.employee_id) & (SalaryRecord.effective_date == sq.c.max_date))
        .join(Employee, Employee.id == SalaryRecord.employee_id)
        .where(Employee.status == EmployeeStatus.active)
    )
    if department:
        q = q.where(Employee.department == department)
    if country:
        q = q.where(Employee.country == country)
    if employment_type:
        q = q.where(Employee.employment_type == employment_type)

    rows = (await db.execute(q)).all()
    salaries = [
        float(r.base_salary) if r.pay_frequency == PayFrequency.monthly else float(r.base_salary) / 12
        for r in rows
    ]
    if min_salary:
        salaries = [s for s in salaries if s >= min_salary]
    if max_salary:
        salaries = [s for s in salaries if s <= max_salary]

    if not salaries:
        return {"count": 0, "avg": 0, "median": 0, "min": 0, "max": 0, "p25": 0, "p75": 0}

    n = len(salaries)
    s = sorted(salaries)
    return {
        "count": n, "avg": round(sum(salaries) / n, 2), "median": round(statistics.median(salaries), 2),
        "min": round(min(salaries), 2), "max": round(max(salaries), 2),
        "p25": round(s[n // 4], 2), "p75": round(s[3 * n // 4], 2),
    }


async def get_headcount(db: AsyncSession, group_by: str = "department", filters: Optional[dict] = None) -> list:
    filters = filters or {}
    col = getattr(Employee, group_by, Employee.department)
    q = select(col.label("group"), func.count(Employee.id).label("count")).where(Employee.status == EmployeeStatus.active)
    if filters.get("country"):
        q = q.where(Employee.country == filters["country"])
    if filters.get("department"):
        q = q.where(Employee.department == filters["department"])
    q = q.group_by(col)
    return [{"group": str(r.group), "count": r.count} for r in (await db.execute(q)).all()]


async def get_top_earners(db: AsyncSession, n: int = 10, filters: Optional[dict] = None) -> list:
    filters = filters or {}
    sq = _latest_salary_sq()
    q = (
        select(Employee.id, Employee.first_name, Employee.last_name, Employee.department, Employee.country, SalaryRecord.base_salary)
        .join(sq, (SalaryRecord.employee_id == sq.c.employee_id) & (SalaryRecord.effective_date == sq.c.max_date))
        .join(Employee, Employee.id == SalaryRecord.employee_id)
        .where(Employee.status == EmployeeStatus.active)
        .order_by(SalaryRecord.base_salary.desc()).limit(n)
    )
    if filters.get("country"):
        q = q.where(Employee.country == filters["country"])
    if filters.get("department"):
        q = q.where(Employee.department == filters["department"])
    return [{"employee_id": r.id, "name": f"{r.first_name} {r.last_name}", "department": r.department, "country": r.country, "base_salary": float(r.base_salary)} for r in (await db.execute(q)).all()]


async def get_salary_distribution(db: AsyncSession, bucket_size: float = 5000, filters: Optional[dict] = None) -> list:
    sq = _latest_salary_sq()
    q = (
        select(SalaryRecord.base_salary)
        .join(sq, (SalaryRecord.employee_id == sq.c.employee_id) & (SalaryRecord.effective_date == sq.c.max_date))
        .join(Employee, Employee.id == SalaryRecord.employee_id)
        .where(Employee.status == EmployeeStatus.active)
    )
    salaries = [float(r.base_salary) for r in (await db.execute(q)).all()]
    if not salaries:
        return []
    buckets: dict = {}
    for s in salaries:
        floor = (s // bucket_size) * bucket_size
        buckets[floor] = buckets.get(floor, 0) + 1
    return [{"range_start": k, "range_end": k + bucket_size, "count": v} for k, v in sorted(buckets.items())]


async def get_budget_by_department(db: AsyncSession, include_bonuses: bool = False) -> list:
    sq = _latest_salary_sq()
    q = (
        select(Employee.department, func.sum(SalaryRecord.base_salary).label("monthly_salary_budget"))
        .join(sq, (SalaryRecord.employee_id == sq.c.employee_id) & (SalaryRecord.effective_date == sq.c.max_date))
        .join(Employee, Employee.id == SalaryRecord.employee_id)
        .where(Employee.status == EmployeeStatus.active)
        .group_by(Employee.department)
    )
    return [{"department": r.department, "monthly_salary_budget": float(r.monthly_salary_budget)} for r in (await db.execute(q)).all()]


async def get_pay_band_compliance(db: AsyncSession, department: Optional[str] = None, country: Optional[str] = None) -> dict:
    from app.models.employee import PayGrade
    sq = _latest_salary_sq()
    q = (
        select(SalaryRecord.base_salary, PayGrade.min_salary, PayGrade.max_salary)
        .join(sq, (SalaryRecord.employee_id == sq.c.employee_id) & (SalaryRecord.effective_date == sq.c.max_date))
        .join(Employee, Employee.id == SalaryRecord.employee_id)
        .join(PayGrade, Employee.pay_grade_id == PayGrade.id)
        .where(Employee.status == EmployeeStatus.active)
    )
    if department:
        q = q.where(Employee.department == department)
    if country:
        q = q.where(Employee.country == country)
    rows = (await db.execute(q)).all()
    in_band = above_band = below_band = 0
    for r in rows:
        s = float(r.base_salary)
        if s < float(r.min_salary):
            below_band += 1
        elif s > float(r.max_salary):
            above_band += 1
        else:
            in_band += 1
    return {"in_band": in_band, "above_band": above_band, "below_band": below_band, "total": len(rows)}


async def get_compensation_breakdown(db: AsyncSession, employee_id: int) -> dict:
    emp = await db.get(
        Employee, employee_id,
        options=[
            selectinload(Employee.salary_records),
            selectinload(Employee.bonuses),
            selectinload(Employee.allowances),
            selectinload(Employee.deductions),
            selectinload(Employee.equity_grants),
        ],
    )
    if not emp:
        return {}
    records = sorted(emp.salary_records, key=lambda r: r.effective_date, reverse=True)
    return {
        "employee_id": employee_id,
        "name": f"{emp.first_name} {emp.last_name}",
        "base_salary": float(records[0].base_salary) if records else 0.0,
        "currency": emp.currency,
        "allowances": [{"type": a.allowance_type, "amount": float(a.amount)} for a in emp.allowances],
        "bonuses": [{"type": b.bonus_type, "amount": float(b.amount), "date": str(b.awarded_date)} for b in emp.bonuses],
        "equity_grants": [{"type": g.grant_type, "shares": g.shares} for g in emp.equity_grants],
        "deductions": [{"type": d.deduction_type, "amount": float(d.amount)} for d in emp.deductions],
    }


async def run_analytics_query(db: AsyncSession, sql: str) -> list:
    import sqlglot
    stmts = sqlglot.parse(sql)
    if not stmts or not isinstance(stmts[0], sqlglot.exp.Select):
        raise ValueError("Only SELECT statements are allowed")
    result = await db.execute(text(sql))
    return [dict(row) for row in result.mappings().all()]
