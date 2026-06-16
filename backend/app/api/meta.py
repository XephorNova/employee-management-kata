from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, distinct
from app.core.database import get_db
from app.auth.dependencies import analyst_or_above
from app.models.user import User
from app.models.employee import Employee

router = APIRouter(prefix="/api/meta", tags=["meta"])


@router.get("/departments")
async def departments(db: AsyncSession = Depends(get_db), _: User = Depends(analyst_or_above)):
    r = await db.execute(select(distinct(Employee.department)).order_by(Employee.department))
    return [row[0] for row in r.all()]


@router.get("/countries")
async def countries(db: AsyncSession = Depends(get_db), _: User = Depends(analyst_or_above)):
    r = await db.execute(select(distinct(Employee.country)).order_by(Employee.country))
    return [row[0] for row in r.all()]
