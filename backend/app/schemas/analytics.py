from pydantic import BaseModel
from typing import Any, Optional


class SalaryStatsOut(BaseModel):
    count: int
    avg: float
    median: float
    min: float
    max: float
    p25: float
    p75: float


class HeadcountItem(BaseModel):
    group: str
    count: int


class TopEarnerItem(BaseModel):
    employee_id: int
    name: str
    department: str
    country: str
    base_salary: float


class SalaryBucketItem(BaseModel):
    range_start: float
    range_end: float
    count: int


class DepartmentBudgetItem(BaseModel):
    department: str
    monthly_salary_budget: float


class PayBandComplianceOut(BaseModel):
    in_band: int
    above_band: int
    below_band: int
    total: int
