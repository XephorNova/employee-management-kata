from __future__ import annotations
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional
from sqlalchemy import String, Date, DateTime, ForeignKey, Enum, Numeric, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum
from app.core.database import Base


class PayFrequency(str, enum.Enum):
    monthly = "monthly"
    annual = "annual"


class BonusType(str, enum.Enum):
    annual = "annual"
    spot = "spot"
    signing = "signing"
    performance = "performance"


class GrantType(str, enum.Enum):
    RSU = "RSU"
    options = "options"


class AllowanceType(str, enum.Enum):
    housing = "housing"
    transport = "transport"
    meal = "meal"
    phone = "phone"


class DeductionType(str, enum.Enum):
    health_insurance = "health_insurance"
    pension = "pension"
    other = "other"


class SalaryRecord(Base):
    __tablename__ = "salary_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    base_salary: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(3))
    effective_date: Mapped[date] = mapped_column(Date)
    pay_frequency: Mapped[PayFrequency] = mapped_column(Enum(PayFrequency), default=PayFrequency.monthly)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    employee: Mapped["Employee"] = relationship(back_populates="salary_records")


class Bonus(Base):
    __tablename__ = "bonuses"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(3))
    bonus_type: Mapped[BonusType] = mapped_column(Enum(BonusType))
    awarded_date: Mapped[date] = mapped_column(Date)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    employee: Mapped["Employee"] = relationship(back_populates="bonuses")


class EquityGrant(Base):
    __tablename__ = "equity_grants"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    grant_type: Mapped[GrantType] = mapped_column(Enum(GrantType))
    shares: Mapped[int]
    grant_date: Mapped[date] = mapped_column(Date)
    vest_start_date: Mapped[date] = mapped_column(Date)
    cliff_months: Mapped[int]
    vest_months: Mapped[int]

    employee: Mapped["Employee"] = relationship(back_populates="equity_grants")


class Allowance(Base):
    __tablename__ = "allowances"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    allowance_type: Mapped[AllowanceType] = mapped_column(Enum(AllowanceType))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(3))
    frequency: Mapped[PayFrequency] = mapped_column(Enum(PayFrequency), default=PayFrequency.monthly)

    employee: Mapped["Employee"] = relationship(back_populates="allowances")


class Deduction(Base):
    __tablename__ = "deductions"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    deduction_type: Mapped[DeductionType] = mapped_column(Enum(DeductionType))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    is_percentage: Mapped[bool] = mapped_column(Boolean, default=False)
    currency: Mapped[Optional[str]] = mapped_column(String(3), nullable=True)
    frequency: Mapped[PayFrequency] = mapped_column(Enum(PayFrequency), default=PayFrequency.monthly)

    employee: Mapped["Employee"] = relationship(back_populates="deductions")
