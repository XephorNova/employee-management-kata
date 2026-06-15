from __future__ import annotations
from datetime import datetime
from sqlalchemy import Integer, DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class SalarySlip(Base):
    __tablename__ = "salary_slips"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    period_month: Mapped[int] = mapped_column(Integer)
    period_year: Mapped[int] = mapped_column(Integer)
    gross_salary: Mapped[float] = mapped_column(Numeric(12, 2))
    taxable_income: Mapped[float] = mapped_column(Numeric(12, 2))
    tax_deducted: Mapped[float] = mapped_column(Numeric(12, 2))
    pf_employee_contribution: Mapped[float] = mapped_column(Numeric(12, 2))
    pf_employer_contribution: Mapped[float] = mapped_column(Numeric(12, 2))
    other_deductions: Mapped[float] = mapped_column(Numeric(12, 2))
    net_take_home: Mapped[float] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(3))
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    generated_by: Mapped[int] = mapped_column(ForeignKey("users.id"))

    employee: Mapped["Employee"] = relationship(back_populates="salary_slips")
