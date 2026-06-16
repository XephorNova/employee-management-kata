from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.auth.dependencies import hr_or_above, analyst_or_above
from app.models.user import User
from app.models.employee import Employee
from app.models.compensation import SalaryRecord, Bonus, EquityGrant, Allowance, Deduction
from app.schemas.compensation import (
    SalaryRecordCreate, SalaryRecordOut,
    BonusCreate, BonusOut,
    EquityGrantCreate, EquityGrantOut,
    AllowanceCreate, AllowanceOut,
    DeductionCreate, DeductionOut,
)

router = APIRouter(prefix="/api/employees/{employee_id}", tags=["compensation"])


async def _require_employee(employee_id: int, db: AsyncSession) -> Employee:
    emp = await db.get(Employee, employee_id)
    if not emp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
    return emp


@router.get("/salary-records", response_model=list[SalaryRecordOut])
async def list_salary_records(employee_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(analyst_or_above)):
    await _require_employee(employee_id, db)
    r = await db.execute(select(SalaryRecord).where(SalaryRecord.employee_id == employee_id).order_by(SalaryRecord.effective_date.desc()))
    return r.scalars().all()


@router.post("/salary-records", response_model=SalaryRecordOut, status_code=status.HTTP_201_CREATED)
async def create_salary_record(employee_id: int, data: SalaryRecordCreate, db: AsyncSession = Depends(get_db), _: User = Depends(hr_or_above)):
    await _require_employee(employee_id, db)
    rec = SalaryRecord(employee_id=employee_id, **data.model_dump())
    db.add(rec)
    await db.commit()
    await db.refresh(rec)
    return rec


@router.get("/bonuses", response_model=list[BonusOut])
async def list_bonuses(employee_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(analyst_or_above)):
    await _require_employee(employee_id, db)
    r = await db.execute(select(Bonus).where(Bonus.employee_id == employee_id))
    return r.scalars().all()


@router.post("/bonuses", response_model=BonusOut, status_code=status.HTTP_201_CREATED)
async def create_bonus(employee_id: int, data: BonusCreate, db: AsyncSession = Depends(get_db), _: User = Depends(hr_or_above)):
    await _require_employee(employee_id, db)
    b = Bonus(employee_id=employee_id, **data.model_dump())
    db.add(b)
    await db.commit()
    await db.refresh(b)
    return b


@router.get("/equity-grants", response_model=list[EquityGrantOut])
async def list_equity_grants(employee_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(analyst_or_above)):
    await _require_employee(employee_id, db)
    r = await db.execute(select(EquityGrant).where(EquityGrant.employee_id == employee_id))
    return r.scalars().all()


@router.post("/equity-grants", response_model=EquityGrantOut, status_code=status.HTTP_201_CREATED)
async def create_equity_grant(employee_id: int, data: EquityGrantCreate, db: AsyncSession = Depends(get_db), _: User = Depends(hr_or_above)):
    await _require_employee(employee_id, db)
    g = EquityGrant(employee_id=employee_id, **data.model_dump())
    db.add(g)
    await db.commit()
    await db.refresh(g)
    return g


@router.get("/allowances", response_model=list[AllowanceOut])
async def list_allowances(employee_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(analyst_or_above)):
    await _require_employee(employee_id, db)
    r = await db.execute(select(Allowance).where(Allowance.employee_id == employee_id))
    return r.scalars().all()


@router.post("/allowances", response_model=AllowanceOut, status_code=status.HTTP_201_CREATED)
async def create_allowance(employee_id: int, data: AllowanceCreate, db: AsyncSession = Depends(get_db), _: User = Depends(hr_or_above)):
    await _require_employee(employee_id, db)
    a = Allowance(employee_id=employee_id, **data.model_dump())
    db.add(a)
    await db.commit()
    await db.refresh(a)
    return a


@router.get("/deductions", response_model=list[DeductionOut])
async def list_deductions(employee_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(analyst_or_above)):
    await _require_employee(employee_id, db)
    r = await db.execute(select(Deduction).where(Deduction.employee_id == employee_id))
    return r.scalars().all()


@router.post("/deductions", response_model=DeductionOut, status_code=status.HTTP_201_CREATED)
async def create_deduction(employee_id: int, data: DeductionCreate, db: AsyncSession = Depends(get_db), _: User = Depends(hr_or_above)):
    await _require_employee(employee_id, db)
    d = Deduction(employee_id=employee_id, **data.model_dump())
    db.add(d)
    await db.commit()
    await db.refresh(d)
    return d
