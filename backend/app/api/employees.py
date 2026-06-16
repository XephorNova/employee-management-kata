from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.auth.dependencies import analyst_or_above, hr_or_above, admin_only, get_current_user
from app.models.user import User
from app.services.employee_service import create_employee, get_employee, list_employees, update_employee, soft_delete_employee
from app.schemas.employee import EmployeeCreate, EmployeeUpdate, EmployeeOut, EmployeeListResponse

router = APIRouter(prefix="/api/employees", tags=["employees"])


@router.get("", response_model=EmployeeListResponse)
async def list_employees_ep(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    country: Optional[str] = None,
    department: Optional[str] = None,
    employment_type: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(analyst_or_above),
):
    employees, total = await list_employees(db, page, page_size, country, department, employment_type, status, search)
    return EmployeeListResponse(items=employees, total=total, page=page, page_size=page_size)


@router.get("/{employee_id}", response_model=EmployeeOut)
async def get_employee_ep(
    employee_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role == "employee" and current_user.employee_id != employee_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    emp = await get_employee(db, employee_id)
    if not emp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
    return emp


@router.post("", response_model=EmployeeOut, status_code=status.HTTP_201_CREATED)
async def create_employee_ep(
    data: EmployeeCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(hr_or_above),
):
    return await create_employee(db, data)


@router.put("/{employee_id}", response_model=EmployeeOut)
async def update_employee_ep(
    employee_id: int,
    data: EmployeeUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(hr_or_above),
):
    emp = await update_employee(db, employee_id, data)
    if not emp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
    return emp


@router.delete("/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_employee_ep(
    employee_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(admin_only),
):
    if not await soft_delete_employee(db, employee_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
