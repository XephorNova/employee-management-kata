import pytest
from datetime import date
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
import app.models  # noqa
from app.core.database import Base
from app.services.employee_service import (
    create_employee, get_employee, list_employees, update_employee, soft_delete_employee,
)
from app.schemas.employee import EmployeeCreate, EmployeeUpdate
from app.models.employee import EmploymentType, EmployeeStatus

_ENGINE = create_async_engine("sqlite+aiosqlite:///:memory:")
_Session = async_sessionmaker(_ENGINE, expire_on_commit=False)


@pytest.fixture(scope="module")
async def db():
    async with _ENGINE.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with _Session() as s:
        yield s
    async with _ENGINE.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


def _emp(**kwargs) -> EmployeeCreate:
    d = dict(
        first_name="Jane", last_name="Doe", email="jane.doe@acme.com",
        department="Engineering", job_title="Engineer",
        country="US", currency="USD", hire_date=date(2022, 1, 15),
        employment_type=EmploymentType.full_time,
    )
    d.update(kwargs)
    return EmployeeCreate(**d)


@pytest.mark.asyncio
async def test_create_employee(db):
    emp = await create_employee(db, _emp())
    assert emp.employee_id.startswith("ACME-")
    assert emp.status == EmployeeStatus.active


@pytest.mark.asyncio
async def test_list_employees_department_filter(db):
    await create_employee(db, _emp(email="eng2@acme.com", department="Engineering"))
    await create_employee(db, _emp(email="fin1@acme.com", department="Finance"))
    employees, _ = await list_employees(db, department="Engineering")
    assert all(e.department == "Engineering" for e in employees)


@pytest.mark.asyncio
async def test_update_employee(db):
    emp = await create_employee(db, _emp(email="update_me@acme.com"))
    updated = await update_employee(db, emp.id, EmployeeUpdate(job_title="Senior Engineer"))
    assert updated.job_title == "Senior Engineer"
    assert updated.first_name == "Jane"


@pytest.mark.asyncio
async def test_soft_delete(db):
    emp = await create_employee(db, _emp(email="delete_me@acme.com"))
    assert await soft_delete_employee(db, emp.id)
    fetched = await get_employee(db, emp.id)
    assert fetched.status == EmployeeStatus.inactive
