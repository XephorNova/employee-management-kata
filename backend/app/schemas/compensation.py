from datetime import date, datetime
from pydantic import BaseModel
from typing import Optional
from app.models.compensation import PayFrequency, BonusType, GrantType, AllowanceType, DeductionType


class SalaryRecordCreate(BaseModel):
    base_salary: float
    currency: str
    effective_date: date
    pay_frequency: PayFrequency = PayFrequency.monthly


class SalaryRecordOut(BaseModel):
    id: int
    employee_id: int
    base_salary: float
    currency: str
    effective_date: date
    pay_frequency: PayFrequency
    created_at: datetime
    model_config = {"from_attributes": True}


class BonusCreate(BaseModel):
    amount: float
    currency: str
    bonus_type: BonusType
    awarded_date: date
    notes: Optional[str] = None


class BonusOut(BaseModel):
    id: int
    employee_id: int
    amount: float
    currency: str
    bonus_type: BonusType
    awarded_date: date
    notes: Optional[str]
    model_config = {"from_attributes": True}


class EquityGrantCreate(BaseModel):
    grant_type: GrantType
    shares: int
    grant_date: date
    vest_start_date: date
    cliff_months: int
    vest_months: int


class EquityGrantOut(BaseModel):
    id: int
    employee_id: int
    grant_type: GrantType
    shares: int
    grant_date: date
    vest_start_date: date
    cliff_months: int
    vest_months: int
    model_config = {"from_attributes": True}


class AllowanceCreate(BaseModel):
    allowance_type: AllowanceType
    amount: float
    currency: str
    frequency: PayFrequency = PayFrequency.monthly


class AllowanceOut(BaseModel):
    id: int
    employee_id: int
    allowance_type: AllowanceType
    amount: float
    currency: str
    frequency: PayFrequency
    model_config = {"from_attributes": True}


class DeductionCreate(BaseModel):
    deduction_type: DeductionType
    amount: float
    is_percentage: bool = False
    currency: Optional[str] = None
    frequency: PayFrequency = PayFrequency.monthly


class DeductionOut(BaseModel):
    id: int
    employee_id: int
    deduction_type: DeductionType
    amount: float
    is_percentage: bool
    currency: Optional[str]
    frequency: PayFrequency
    model_config = {"from_attributes": True}
