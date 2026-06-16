from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.auth.dependencies import hr_or_above, get_current_user
from app.models.user import User, UserRole
from app.models.payroll import SalarySlip
from app.schemas.payroll import SalarySlipGenerateRequest, SalarySlipOut
from app.services.payroll_service import generate_salary_slip

router = APIRouter(prefix="/api/employees/{employee_id}/salary-slips", tags=["salary-slips"])


@router.post("/generate", response_model=SalarySlipOut, status_code=status.HTTP_201_CREATED)
async def generate_slip(
    employee_id: int, body: SalarySlipGenerateRequest,
    db: AsyncSession = Depends(get_db), current_user: User = Depends(hr_or_above),
):
    try:
        return await generate_salary_slip(db, employee_id, body.period_month, body.period_year, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.get("", response_model=list[SalarySlipOut])
async def list_slips(
    employee_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user),
):
    if current_user.role == UserRole.employee and current_user.employee_id != employee_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    r = await db.execute(
        select(SalarySlip)
        .where(SalarySlip.employee_id == employee_id)
        .order_by(SalarySlip.period_year.desc(), SalarySlip.period_month.desc())
    )
    return r.scalars().all()


@router.get("/{year}/{month}", response_model=SalarySlipOut)
async def get_slip(
    employee_id: int, year: int, month: int,
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user),
):
    if current_user.role == UserRole.employee and current_user.employee_id != employee_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    r = await db.execute(
        select(SalarySlip).where(
            SalarySlip.employee_id == employee_id,
            SalarySlip.period_year == year,
            SalarySlip.period_month == month,
        )
    )
    slip = r.scalar_one_or_none()
    if not slip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Salary slip not found")
    return slip
