from datetime import date, datetime
from pydantic import BaseModel
from typing import Optional


class PFRuleCreate(BaseModel):
    country: str
    rule_name: str
    employee_contribution_pct: float
    employer_contribution_pct: float
    applicable_salary_cap: Optional[float] = None
    effective_from_date: date


class PFRuleUpdate(BaseModel):
    rule_name: Optional[str] = None
    employee_contribution_pct: Optional[float] = None
    employer_contribution_pct: Optional[float] = None
    applicable_salary_cap: Optional[float] = None
    effective_from_date: Optional[date] = None


class PFRuleOut(BaseModel):
    id: int
    country: str
    rule_name: str
    employee_contribution_pct: float
    employer_contribution_pct: float
    applicable_salary_cap: Optional[float]
    effective_from_date: date
    created_by: int
    created_at: datetime
    model_config = {"from_attributes": True}
