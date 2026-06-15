from __future__ import annotations
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from sqlalchemy import String, DateTime, ForeignKey, Enum, Numeric, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum
from app.core.database import Base


class TaxRuleType(str, enum.Enum):
    income_tax = "income_tax"
    social_security = "social_security"
    other = "other"


class TaxRule(Base):
    __tablename__ = "tax_rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    country: Mapped[str] = mapped_column(String(3), index=True)
    rule_name: Mapped[str] = mapped_column(String(200))
    rule_type: Mapped[TaxRuleType] = mapped_column(Enum(TaxRuleType))
    tax_year: Mapped[int] = mapped_column(Integer)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    brackets: Mapped[list["TaxBracket"]] = relationship(back_populates="tax_rule", order_by="TaxBracket.min_income")


class TaxBracket(Base):
    __tablename__ = "tax_brackets"

    id: Mapped[int] = mapped_column(primary_key=True)
    tax_rule_id: Mapped[int] = mapped_column(ForeignKey("tax_rules.id"))
    min_income: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    max_income: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    rate_pct: Mapped[Decimal] = mapped_column(Numeric(5, 4))
    currency: Mapped[str] = mapped_column(String(3))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    tax_rule: Mapped[TaxRule] = relationship(back_populates="brackets")
