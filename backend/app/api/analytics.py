from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.auth.dependencies import analyst_or_above
from app.models.user import User
from app.services.analytics_service import get_salary_stats, get_headcount, get_salary_distribution, get_budget_by_department
from app.schemas.analytics import SalaryStatsOut, HeadcountItem, SalaryBucketItem, DepartmentBudgetItem

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/summary", response_model=SalaryStatsOut)
async def summary(
    country: Optional[str] = None,
    department: Optional[str] = None,
    employment_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(analyst_or_above),
):
    return await get_salary_stats(db, department=department, country=country, employment_type=employment_type)


@router.get("/by-country", response_model=List[HeadcountItem])
async def by_country(db: AsyncSession = Depends(get_db), _: User = Depends(analyst_or_above)):
    return await get_headcount(db, group_by="country")


@router.get("/by-department", response_model=List[HeadcountItem])
async def by_department(db: AsyncSession = Depends(get_db), _: User = Depends(analyst_or_above)):
    return await get_headcount(db, group_by="department")


@router.get("/salary-bands", response_model=List[SalaryBucketItem])
async def salary_bands(
    bucket_size: float = Query(5000, ge=100),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(analyst_or_above),
):
    return await get_salary_distribution(db, bucket_size=bucket_size)
