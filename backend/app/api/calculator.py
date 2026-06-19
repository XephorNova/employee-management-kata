from __future__ import annotations
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.auth.dependencies import any_authenticated
from app.models.user import User
from app.models.tax import TaxRule
from app.models.pf import PFRule
from app.schemas.calculator import CalculatorRequest, CalculatorResponse
from app.services.payroll_service import compute_take_home

router = APIRouter(prefix="/api/calculator", tags=["calculator"])


@router.post("/calculate", response_model=CalculatorResponse)
async def calculate_net_salary(
    body: CalculatorRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(any_authenticated),
) -> CalculatorResponse:
    pf_r = await db.execute(
        select(PFRule)
        .where(PFRule.country == body.country)
        .order_by(PFRule.effective_from_date.desc())
        .limit(1)
    )
    pf_rule = pf_r.scalar_one_or_none()

    tax_r = await db.execute(
        select(TaxRule)
        .where(TaxRule.country == body.country)
        .order_by(TaxRule.tax_year.desc())
        .limit(1)
        .options(selectinload(TaxRule.brackets))
    )
    tax_rule = tax_r.scalar_one_or_none()

    pf_employee_pct = float(pf_rule.employee_contribution_pct) if pf_rule else 0.0
    pf_employer_pct = float(pf_rule.employer_contribution_pct) if pf_rule else 0.0
    pf_cap = float(pf_rule.applicable_salary_cap) if pf_rule and pf_rule.applicable_salary_cap else None

    brackets = [
        {
            "min_income": float(b.min_income),
            "max_income": float(b.max_income) if b.max_income else None,
            "rate_pct": float(b.rate_pct),
        }
        for b in (tax_rule.brackets if tax_rule else [])
    ]

    currency = body.currency
    base_monthly = body.base_salary if body.pay_frequency == "monthly" else body.base_salary / 12

    computed = compute_take_home(
        base_monthly,
        body.allowances,
        pf_employee_pct,
        pf_employer_pct,
        pf_cap,
        brackets,
        body.other_deductions,
    )

    return CalculatorResponse(
        **computed,
        currency=currency,
        tax_rule_applied=tax_rule.rule_name if tax_rule else None,
        pf_rule_applied=pf_rule.rule_name if pf_rule else None,
        no_rules_warning=(pf_rule is None and tax_rule is None),
    )
