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


# ---------------------------------------------------------------------------
# API-level tests
# ---------------------------------------------------------------------------
from datetime import timedelta
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.database import get_db
from app.auth.utils import create_access_token
from app.models.user import UserRole


def _token(role: str) -> str:
    return create_access_token({"sub": f"{role}@acme.com", "role": role}, expires_delta=timedelta(hours=1))


@pytest.fixture
async def api_client(db):
    # Seed users so get_current_user DB lookup succeeds for each role under test.
    # Use INSERT OR IGNORE (SQLite dialect) via raw text to be idempotent across
    # multiple fixture invocations sharing the module-scoped db session.
    from sqlalchemy import text
    await db.execute(
        text(
            "INSERT OR IGNORE INTO users (email, hashed_password, role, is_active, created_at)"
            " VALUES (:email, :pw, :role, 1, datetime('now'))"
        ),
        [
            {"email": "hr_analyst@acme.com", "pw": "unused", "role": "hr_analyst"},
            {"email": "hr_manager@acme.com", "pw": "unused", "role": "hr_manager"},
        ],
    )
    await db.commit()

    async def override():
        yield db
    app.dependency_overrides[get_db] = override
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_list_employees_requires_auth(api_client):
    resp = await api_client.get("/api/employees")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_list_employees_as_analyst(api_client):
    resp = await api_client.get("/api/employees", headers={"Authorization": f"Bearer {_token('hr_analyst')}"})
    assert resp.status_code == 200
    assert "items" in resp.json()


@pytest.mark.asyncio
async def test_create_employee_as_hr_manager(api_client):
    payload = {
        "first_name": "Bob", "last_name": "Smith", "email": "bob.smith.api@acme.com",
        "department": "Finance", "job_title": "Analyst", "country": "GB",
        "currency": "GBP", "hire_date": "2023-03-01", "employment_type": "full-time",
    }
    resp = await api_client.post("/api/employees", json=payload, headers={"Authorization": f"Bearer {_token('hr_manager')}"})
    assert resp.status_code == 201
    assert resp.json()["employee_id"].startswith("ACME-")


@pytest.mark.asyncio
async def test_create_employee_forbidden_for_analyst(api_client):
    payload = {
        "first_name": "No", "last_name": "Access", "email": "no.access@acme.com",
        "department": "Finance", "job_title": "Analyst", "country": "GB",
        "currency": "GBP", "hire_date": "2023-03-01", "employment_type": "full-time",
    }
    resp = await api_client.post("/api/employees", json=payload, headers={"Authorization": f"Bearer {_token('hr_analyst')}"})
    assert resp.status_code == 403
