from __future__ import annotations
from typing import Literal, Optional
from pydantic import BaseModel


class CalculatorRequest(BaseModel):
    country: str
    base_salary: float
    pay_frequency: Literal["monthly", "annual"] = "monthly"
    allowances: float = 0.0
    other_deductions: float = 0.0
    currency: str = "USD"


class CalculatorResponse(BaseModel):
    gross_salary: float
    taxable_income: float
    pf_employee_contribution: float
    pf_employer_contribution: float
    tax_deducted: float
    other_deductions: float
    net_take_home: float
    currency: str
    tax_rule_applied: Optional[str]
    pf_rule_applied: Optional[str]
    no_rules_warning: bool
