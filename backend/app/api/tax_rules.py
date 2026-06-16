from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.auth.dependencies import hr_or_above
from app.models.user import User
from app.models.tax import TaxRule, TaxBracket
from app.schemas.tax import TaxRuleCreate, TaxRuleUpdate, TaxRuleOut

router = APIRouter(prefix="/api/tax-rules", tags=["tax-rules"])


async def _load_rule(rule_id: int, db: AsyncSession) -> TaxRule:
    r = await db.execute(select(TaxRule).where(TaxRule.id == rule_id).options(selectinload(TaxRule.brackets)))
    rule = r.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tax rule not found")
    return rule


@router.get("", response_model=list[TaxRuleOut])
async def list_tax_rules(db: AsyncSession = Depends(get_db), _: User = Depends(hr_or_above)):
    r = await db.execute(select(TaxRule).options(selectinload(TaxRule.brackets)))
    return r.scalars().all()


@router.get("/country/{country_code}", response_model=list[TaxRuleOut])
async def list_by_country(country_code: str, db: AsyncSession = Depends(get_db), _: User = Depends(hr_or_above)):
    r = await db.execute(select(TaxRule).where(TaxRule.country == country_code.upper()).options(selectinload(TaxRule.brackets)))
    return r.scalars().all()


@router.get("/{rule_id}", response_model=TaxRuleOut)
async def get_tax_rule(rule_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(hr_or_above)):
    return await _load_rule(rule_id, db)


@router.post("", response_model=TaxRuleOut, status_code=status.HTTP_201_CREATED)
async def create_tax_rule(data: TaxRuleCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(hr_or_above)):
    rule = TaxRule(
        country=data.country.upper(), rule_name=data.rule_name,
        rule_type=data.rule_type, tax_year=data.tax_year,
        description=data.description, created_by=current_user.id,
    )
    db.add(rule)
    await db.flush()
    for b in data.brackets:
        db.add(TaxBracket(tax_rule_id=rule.id, **b.model_dump()))
    await db.commit()
    return await _load_rule(rule.id, db)


@router.put("/{rule_id}", response_model=TaxRuleOut)
async def update_tax_rule(rule_id: int, data: TaxRuleUpdate, db: AsyncSession = Depends(get_db), _: User = Depends(hr_or_above)):
    rule = await db.get(TaxRule, rule_id)
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tax rule not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(rule, field, value)
    await db.commit()
    return await _load_rule(rule_id, db)
