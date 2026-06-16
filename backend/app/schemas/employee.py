from datetime import date, datetime
from pydantic import BaseModel, EmailStr
from typing import Optional
from app.models.employee import EmploymentType, EmployeeStatus


class PayGradeOut(BaseModel):
    id: int
    grade: str
    min_salary: float
    max_salary: float
    currency: str
    model_config = {"from_attributes": True}


class EmployeeCreate(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    department: str
    job_title: str
    pay_grade_id: Optional[int] = None
    country: str
    currency: str
    hire_date: date
    employment_type: EmploymentType


class EmployeeUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    department: Optional[str] = None
    job_title: Optional[str] = None
    pay_grade_id: Optional[int] = None
    country: Optional[str] = None
    currency: Optional[str] = None
    hire_date: Optional[date] = None
    employment_type: Optional[EmploymentType] = None


class EmployeeOut(BaseModel):
    id: int
    employee_id: str
    first_name: str
    last_name: str
    email: str
    department: str
    job_title: str
    pay_grade_id: Optional[int]
    country: str
    currency: str
    hire_date: date
    employment_type: EmploymentType
    status: EmployeeStatus
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


class EmployeeListResponse(BaseModel):
    items: list[EmployeeOut]
    total: int
    page: int
    page_size: int
