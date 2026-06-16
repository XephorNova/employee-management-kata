from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload
from app.models.employee import Employee, EmployeeStatus
from app.schemas.employee import EmployeeCreate, EmployeeUpdate


async def create_employee(db: AsyncSession, data: EmployeeCreate) -> Employee:
    result = await db.execute(select(func.count()).select_from(Employee))
    count = result.scalar_one()
    employee = Employee(employee_id=f"ACME-{count + 1:05d}", **data.model_dump())
    db.add(employee)
    await db.commit()
    await db.refresh(employee)
    return employee


async def get_employee(db: AsyncSession, employee_id: int) -> Optional[Employee]:
    result = await db.execute(
        select(Employee)
        .where(Employee.id == employee_id)
        .options(
            selectinload(Employee.salary_records),
            selectinload(Employee.bonuses),
            selectinload(Employee.equity_grants),
            selectinload(Employee.allowances),
            selectinload(Employee.deductions),
        )
    )
    return result.scalar_one_or_none()


async def list_employees(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    country: Optional[str] = None,
    department: Optional[str] = None,
    employment_type: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
) -> tuple:
    filters = [Employee.status == (status or EmployeeStatus.active)]
    if country:
        filters.append(Employee.country == country)
    if department:
        filters.append(Employee.department == department)
    if employment_type:
        filters.append(Employee.employment_type == employment_type)
    if search:
        term = f"%{search}%"
        filters.append(or_(
            Employee.first_name.ilike(term), Employee.last_name.ilike(term),
            Employee.email.ilike(term), Employee.employee_id.ilike(term),
        ))

    count_q = select(func.count()).select_from(Employee)
    query = select(Employee)
    for f in filters:
        count_q = count_q.where(f)
        query = query.where(f)

    total = (await db.execute(count_q)).scalar_one()
    rows = (await db.execute(query.offset((page - 1) * page_size).limit(page_size))).scalars().all()
    return rows, total


async def update_employee(db: AsyncSession, employee_id: int, data: EmployeeUpdate) -> Optional[Employee]:
    employee = await db.get(Employee, employee_id)
    if not employee:
        return None
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(employee, field, value)
    await db.commit()
    await db.refresh(employee)
    return employee


async def soft_delete_employee(db: AsyncSession, employee_id: int) -> bool:
    employee = await db.get(Employee, employee_id)
    if not employee:
        return False
    employee.status = EmployeeStatus.inactive
    await db.commit()
    return True
