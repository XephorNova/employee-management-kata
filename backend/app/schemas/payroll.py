from datetime import datetime
from pydantic import BaseModel


class SalarySlipGenerateRequest(BaseModel):
    period_month: int
    period_year: int


class SalarySlipOut(BaseModel):
    id: int
    employee_id: int
    period_month: int
    period_year: int
    gross_salary: float
    taxable_income: float
    tax_deducted: float
    pf_employee_contribution: float
    pf_employer_contribution: float
    other_deductions: float
    net_take_home: float
    currency: str
    generated_at: datetime
    generated_by: int
    model_config = {"from_attributes": True}
