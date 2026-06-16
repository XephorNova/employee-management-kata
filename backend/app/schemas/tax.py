from datetime import datetime
from pydantic import BaseModel
from typing import Optional
from app.models.tax import TaxRuleType


class TaxBracketCreate(BaseModel):
    min_income: float
    max_income: Optional[float] = None
    rate_pct: float
    currency: str


class TaxBracketOut(BaseModel):
    id: int
    tax_rule_id: int
    min_income: float
    max_income: Optional[float]
    rate_pct: float
    currency: str
    model_config = {"from_attributes": True}


class TaxRuleCreate(BaseModel):
    country: str
    rule_name: str
    rule_type: TaxRuleType
    tax_year: int
    description: Optional[str] = None
    brackets: list[TaxBracketCreate] = []


class TaxRuleUpdate(BaseModel):
    rule_name: Optional[str] = None
    description: Optional[str] = None


class TaxRuleOut(BaseModel):
    id: int
    country: str
    rule_name: str
    rule_type: TaxRuleType
    tax_year: int
    description: Optional[str]
    created_by: int
    created_at: datetime
    brackets: list[TaxBracketOut] = []
    model_config = {"from_attributes": True}
