from __future__ import annotations
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional
from sqlalchemy import String, DateTime, ForeignKey, Numeric, Date
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class PFRule(Base):
    __tablename__ = "pf_rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    country: Mapped[str] = mapped_column(String(3), index=True)
    rule_name: Mapped[str] = mapped_column(String(200))
    employee_contribution_pct: Mapped[Decimal] = mapped_column(Numeric(5, 4))
    employer_contribution_pct: Mapped[Decimal] = mapped_column(Numeric(5, 4))
    applicable_salary_cap: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    effective_from_date: Mapped[date] = mapped_column(Date)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
