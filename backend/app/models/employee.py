from __future__ import annotations
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional, List
from sqlalchemy import String, Date, DateTime, ForeignKey, Enum, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum
from app.core.database import Base


class EmploymentType(str, enum.Enum):
    full_time = "full-time"
    part_time = "part-time"
    contractor = "contractor"


class EmployeeStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"


class PayGrade(Base):
    __tablename__ = "pay_grades"

    id: Mapped[int] = mapped_column(primary_key=True)
    grade: Mapped[str] = mapped_column(String(10), unique=True)
    min_salary: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    max_salary: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(3), default="USD")

    employees: Mapped[list["Employee"]] = relationship(back_populates="pay_grade")


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    department: Mapped[str] = mapped_column(String(100))
    job_title: Mapped[str] = mapped_column(String(100))
    pay_grade_id: Mapped[Optional[int]] = mapped_column(ForeignKey("pay_grades.id"), nullable=True)
    country: Mapped[str] = mapped_column(String(3))
    currency: Mapped[str] = mapped_column(String(3))
    hire_date: Mapped[date] = mapped_column(Date)
    employment_type: Mapped[EmploymentType] = mapped_column(Enum(EmploymentType))
    status: Mapped[EmployeeStatus] = mapped_column(Enum(EmployeeStatus), default=EmployeeStatus.active)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    pay_grade: Mapped[Optional[PayGrade]] = relationship(back_populates="employees")
    salary_records: Mapped[list["SalaryRecord"]] = relationship(back_populates="employee", order_by="SalaryRecord.effective_date.desc()")
    bonuses: Mapped[list["Bonus"]] = relationship(back_populates="employee")
    equity_grants: Mapped[list["EquityGrant"]] = relationship(back_populates="employee")
    allowances: Mapped[list["Allowance"]] = relationship(back_populates="employee")
    deductions: Mapped[list["Deduction"]] = relationship(back_populates="employee")
    salary_slips: Mapped[list["SalarySlip"]] = relationship(back_populates="employee")
