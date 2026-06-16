from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.models.employee import Employee
from app.models.compensation import SalaryRecord, Allowance, Deduction, PayFrequency
from app.models.tax import TaxRule
from app.models.pf import PFRule
from app.models.payroll import SalarySlip


def compute_progressive_tax(annual_income: float, brackets: list) -> float:
    tax = 0.0
    for b in sorted(brackets, key=lambda x: x["min_income"]):
        lower = b["min_income"]
        upper = b["max_income"]
        if annual_income <= lower:
            break
        taxable = (min(annual_income, upper) if upper else annual_income) - lower
        tax += taxable * b["rate_pct"]
    return tax


def compute_take_home(
    base_salary_monthly: float,
    allowances_monthly: float,
    pf_employee_pct: float,
    pf_employer_pct: float,
    pf_salary_cap: Optional[float],
    tax_brackets: list,
    other_deductions_monthly: float,
) -> dict:
    gross = base_salary_monthly + allowances_monthly
    pf_base = min(base_salary_monthly, pf_salary_cap) if pf_salary_cap else base_salary_monthly
    pf_employee = pf_base * pf_employee_pct
    pf_employer = pf_base * pf_employer_pct
    taxable_monthly = gross - pf_employee
    tax_monthly = compute_progressive_tax(taxable_monthly * 12, tax_brackets) / 12
    net = gross - pf_employee - tax_monthly - other_deductions_monthly
    return {
        "gross_salary": round(gross, 2),
        "taxable_income": round(taxable_monthly, 2),
        "tax_deducted": round(tax_monthly, 2),
        "pf_employee_contribution": round(pf_employee, 2),
        "pf_employer_contribution": round(pf_employer, 2),
        "other_deductions": round(other_deductions_monthly, 2),
        "net_take_home": round(net, 2),
    }


async def generate_salary_slip(
    db: AsyncSession,
    employee_id: int,
    period_month: int,
    period_year: int,
    generated_by_user_id: int,
) -> SalarySlip:
    employee = await db.get(
        Employee, employee_id,
        options=[
            selectinload(Employee.salary_records),
            selectinload(Employee.allowances),
            selectinload(Employee.deductions),
        ],
    )
    if not employee:
        raise ValueError(f"Employee {employee_id} not found")

    records = sorted(employee.salary_records, key=lambda r: r.effective_date, reverse=True)
    if not records:
        raise ValueError(f"No salary records for employee {employee_id}")

    current = records[0]
    base_monthly = float(current.base_salary) if current.pay_frequency == PayFrequency.monthly else float(current.base_salary) / 12
    allowances_monthly = sum(
        float(a.amount) if a.frequency == PayFrequency.monthly else float(a.amount) / 12
        for a in employee.allowances
    )
    other_deductions = 0.0
    for d in employee.deductions:
        amt = float(d.amount)
        if d.is_percentage:
            amt = base_monthly * (amt / 100)
        if d.frequency == PayFrequency.annual:
            amt /= 12
        other_deductions += amt

    pf_r = await db.execute(
        select(PFRule).where(PFRule.country == employee.country).order_by(PFRule.effective_from_date.desc()).limit(1)
    )
    pf_rule = pf_r.scalar_one_or_none()
    pf_employee_pct = float(pf_rule.employee_contribution_pct) if pf_rule else 0.0
    pf_employer_pct = float(pf_rule.employer_contribution_pct) if pf_rule else 0.0
    pf_cap = float(pf_rule.applicable_salary_cap) if pf_rule and pf_rule.applicable_salary_cap else None

    tax_r = await db.execute(
        select(TaxRule)
        .where(TaxRule.country == employee.country)
        .order_by(TaxRule.tax_year.desc())
        .limit(1)
        .options(selectinload(TaxRule.brackets))
    )
    tax_rule = tax_r.scalar_one_or_none()
    brackets = [
        {"min_income": float(b.min_income), "max_income": float(b.max_income) if b.max_income else None, "rate_pct": float(b.rate_pct)}
        for b in (tax_rule.brackets if tax_rule else [])
    ]

    computed = compute_take_home(base_monthly, allowances_monthly, pf_employee_pct, pf_employer_pct, pf_cap, brackets, other_deductions)
    slip = SalarySlip(
        employee_id=employee_id, period_month=period_month, period_year=period_year,
        currency=current.currency, generated_by=generated_by_user_id, **computed,
    )
    db.add(slip)
    await db.commit()
    await db.refresh(slip)
    return slip
