from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.auth.dependencies import any_authenticated, hr_or_above
from app.models.user import User
from app.models.bank import BankDetail
from app.models.employee import Employee
from app.schemas.bank import BankDetailCreate, BankDetailUpdate, BankDetailOut
from typing import List

router = APIRouter(prefix="/api/employees", tags=["bank-details"])


async def _check_access(employee_id: int, current_user: User, db: AsyncSession):
    """HR and above can access any employee. Employees can only access their own."""
    emp = await db.get(Employee, employee_id)
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    if current_user.role in ("hr_manager", "hr_analyst", "admin"):
        return emp
    if current_user.employee_id != employee_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return emp


@router.get("/{employee_id}/bank-details", response_model=List[BankDetailOut])
async def list_bank_details(employee_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(any_authenticated)):
    await _check_access(employee_id, current_user, db)
    r = await db.execute(select(BankDetail).where(BankDetail.employee_id == employee_id))
    return r.scalars().all()


@router.post("/{employee_id}/bank-details", response_model=BankDetailOut, status_code=201)
async def create_bank_detail(employee_id: int, data: BankDetailCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(any_authenticated)):
    await _check_access(employee_id, current_user, db)
    detail = BankDetail(employee_id=employee_id, **data.model_dump())
    db.add(detail)
    await db.commit()
    await db.refresh(detail)
    return detail


@router.put("/{employee_id}/bank-details/{detail_id}", response_model=BankDetailOut)
async def update_bank_detail(employee_id: int, detail_id: int, data: BankDetailUpdate, db: AsyncSession = Depends(get_db), current_user: User = Depends(any_authenticated)):
    await _check_access(employee_id, current_user, db)
    r = await db.execute(select(BankDetail).where(BankDetail.id == detail_id, BankDetail.employee_id == employee_id))
    detail = r.scalar_one_or_none()
    if not detail:
        raise HTTPException(status_code=404, detail="Bank detail not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(detail, field, value)
    await db.commit()
    await db.refresh(detail)
    return detail


@router.delete("/{employee_id}/bank-details/{detail_id}", status_code=204)
async def delete_bank_detail(employee_id: int, detail_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(any_authenticated)):
    await _check_access(employee_id, current_user, db)
    r = await db.execute(select(BankDetail).where(BankDetail.id == detail_id, BankDetail.employee_id == employee_id))
    detail = r.scalar_one_or_none()
    if not detail:
        raise HTTPException(status_code=404, detail="Bank detail not found")
    await db.delete(detail)
    await db.commit()
