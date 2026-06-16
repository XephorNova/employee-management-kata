from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from app.core.database import get_db
from app.auth.dependencies import hr_or_above, get_current_user, any_authenticated, admin_only
from app.models.user import User, UserRole
from app.models.payroll import SalarySlip
from app.schemas.payroll import SalarySlipGenerateRequest, SalarySlipOut
from app.services.payroll_service import generate_salary_slip

router = APIRouter(prefix="/api/employees/{employee_id}/salary-slips", tags=["salary-slips"])

# Separate router for non-employee-scoped salary-slip endpoints
salary_admin_router = APIRouter(prefix="/api/salary-slips", tags=["salary-slips"])

# Separate router for tax statement (under /api/employees)
tax_statement_router = APIRouter(prefix="/api/employees", tags=["tax-statement"])


class BulkGenerateRequest(BaseModel):
    period_month: int
    period_year: int


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


@salary_admin_router.post("/bulk-generate", status_code=202)
async def bulk_generate_salary_slips(
    data: BulkGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(admin_only),
):
    """Generate salary slips for all active employees for a given month/year."""
    from app.models.employee import Employee, EmployeeStatus

    period_month = data.period_month
    period_year = data.period_year

    r = await db.execute(select(Employee).where(Employee.status == EmployeeStatus.active))
    employees = r.scalars().all()

    generated, errors = 0, []
    for emp in employees:
        try:
            await generate_salary_slip(db, emp.id, period_month, period_year, current_user.id)
            generated += 1
        except Exception as e:
            errors.append({"employee_id": emp.id, "error": str(e)})

    return {"generated": generated, "errors": errors, "total": len(employees)}


@tax_statement_router.get("/{employee_id}/tax-statement/{year}")
async def get_tax_statement(
    employee_id: int,
    year: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(any_authenticated),
):
    from app.models.employee import Employee

    emp = await db.get(Employee, employee_id)
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    # Access control: employees can only see their own
    if current_user.role == UserRole.employee and current_user.employee_id != employee_id:
        raise HTTPException(status_code=403, detail="Access denied")

    r = await db.execute(
        select(SalarySlip)
        .where(SalarySlip.employee_id == employee_id, SalarySlip.period_year == year)
        .order_by(SalarySlip.period_month)
    )
    slips = r.scalars().all()

    months = [
        {
            "month": s.period_month,
            "gross": float(s.gross_salary),
            "pf_employee": float(s.pf_employee_contribution),
            "pf_employer": float(s.pf_employer_contribution),
            "tax": float(s.tax_deducted),
            "net": float(s.net_take_home),
            "currency": s.currency,
        }
        for s in slips
    ]

    totals = {
        "gross": sum(m["gross"] for m in months),
        "pf_employee": sum(m["pf_employee"] for m in months),
        "pf_employer": sum(m["pf_employer"] for m in months),
        "tax": sum(m["tax"] for m in months),
        "net": sum(m["net"] for m in months),
        "currency": months[0]["currency"] if months else emp.currency,
    }

    return {
        "employee_id": employee_id,
        "employee_name": f"{emp.first_name} {emp.last_name}",
        "year": year,
        "months": months,
        "totals": totals,
    }
