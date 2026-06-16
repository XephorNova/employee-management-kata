from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.auth.dependencies import hr_or_above
from app.models.user import User
from app.models.pf import PFRule
from app.schemas.pf import PFRuleCreate, PFRuleUpdate, PFRuleOut

router = APIRouter(prefix="/api/pf-rules", tags=["pf-rules"])


@router.get("", response_model=list[PFRuleOut])
async def list_pf_rules(db: AsyncSession = Depends(get_db), _: User = Depends(hr_or_above)):
    r = await db.execute(select(PFRule))
    return r.scalars().all()


@router.get("/country/{country_code}", response_model=list[PFRuleOut])
async def list_by_country(country_code: str, db: AsyncSession = Depends(get_db), _: User = Depends(hr_or_above)):
    r = await db.execute(select(PFRule).where(PFRule.country == country_code.upper()))
    return r.scalars().all()


@router.get("/{rule_id}", response_model=PFRuleOut)
async def get_pf_rule(rule_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(hr_or_above)):
    rule = await db.get(PFRule, rule_id)
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PF rule not found")
    return rule


@router.post("", response_model=PFRuleOut, status_code=status.HTTP_201_CREATED)
async def create_pf_rule(data: PFRuleCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(hr_or_above)):
    rule = PFRule(created_by=current_user.id, **{**data.model_dump(), "country": data.country.upper()})
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return rule


@router.put("/{rule_id}", response_model=PFRuleOut)
async def update_pf_rule(rule_id: int, data: PFRuleUpdate, db: AsyncSession = Depends(get_db), _: User = Depends(hr_or_above)):
    rule = await db.get(PFRule, rule_id)
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PF rule not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(rule, field, value)
    await db.commit()
    await db.refresh(rule)
    return rule
