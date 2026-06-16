import pytest
from datetime import date
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
import app.models  # noqa
from app.core.database import Base
from app.models.employee import Employee, EmploymentType
from app.models.compensation import SalaryRecord, PayFrequency
from app.models.user import User, UserRole
from app.auth.utils import hash_password
from app.services.analytics_service import (
    get_salary_stats, get_headcount, get_top_earners,
    get_salary_distribution, get_budget_by_department, get_compensation_breakdown,
)

_ENGINE = create_async_engine("sqlite+aiosqlite:///:memory:")
_Session = async_sessionmaker(_ENGINE, expire_on_commit=False)

_SETUP_DATA = [
    ("Engineering", "US", 8000), ("Engineering", "US", 7000),
    ("Finance", "US", 6000), ("Finance", "IN", 5000), ("Engineering", "IN", 9000),
]


@pytest.fixture(scope="module")
async def db():
    async with _ENGINE.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with _Session() as s:
        emps = []
        for i, (dept, country, _) in enumerate(_SETUP_DATA, 1):
            emp = Employee(
                employee_id=f"ACME-A{i:04d}", first_name=f"Emp{i}", last_name="Test",
                email=f"emp_analytics{i}@acme.com", department=dept, job_title="Dev",
                country=country, currency="USD", hire_date=date(2022, 1, 1),
                employment_type=EmploymentType.full_time,
            )
            emps.append(emp)
        s.add_all(emps)
        await s.flush()
        for emp, (_, _, salary) in zip(emps, _SETUP_DATA):
            s.add(SalaryRecord(employee_id=emp.id, base_salary=salary, currency="USD", effective_date=date(2024, 1, 1), pay_frequency=PayFrequency.monthly))
        s.add(User(email="a@acme.com", hashed_password=hash_password("pw"), role=UserRole.hr_analyst))
        await s.commit()
    yield s
    async with _ENGINE.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.mark.asyncio
async def test_salary_stats(db):
    stats = await get_salary_stats(db)
    assert stats["count"] == 5
    assert stats["avg"] == pytest.approx(sum(s for _, _, s in _SETUP_DATA) / 5)
    assert stats["min"] == pytest.approx(5000.0)
    assert stats["max"] == pytest.approx(9000.0)


@pytest.mark.asyncio
async def test_salary_stats_filtered(db):
    stats = await get_salary_stats(db, department="Engineering")
    assert stats["count"] == 3


@pytest.mark.asyncio
async def test_headcount_by_department(db):
    result = await get_headcount(db, group_by="department")
    counts = {r["group"]: r["count"] for r in result}
    assert counts["Engineering"] == 3
    assert counts["Finance"] == 2


@pytest.mark.asyncio
async def test_top_earners(db):
    top = await get_top_earners(db, n=2)
    assert len(top) == 2
    assert top[0]["base_salary"] >= top[1]["base_salary"]


@pytest.mark.asyncio
async def test_salary_distribution(db):
    buckets = await get_salary_distribution(db, bucket_size=2000)
    assert sum(b["count"] for b in buckets) == 5


@pytest.mark.asyncio
async def test_budget_by_department(db):
    budget = await get_budget_by_department(db)
    depts = {b["department"]: b["monthly_salary_budget"] for b in budget}
    assert depts["Engineering"] == pytest.approx(8000 + 7000 + 9000)


from datetime import timedelta
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.database import get_db
from app.auth.utils import create_access_token


@pytest.fixture
async def analytics_client(db):
    async def override():
        yield db
    app.dependency_overrides[get_db] = override
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


def _analyst_token() -> str:
    return create_access_token({"sub": "a@acme.com", "role": "hr_analyst"}, expires_delta=timedelta(hours=1))


@pytest.mark.asyncio
async def test_analytics_summary_endpoint(analytics_client):
    resp = await analytics_client.get("/api/analytics/summary", headers={"Authorization": f"Bearer {_analyst_token()}"})
    assert resp.status_code == 200
    assert "avg" in resp.json()


@pytest.mark.asyncio
async def test_analytics_by_department_endpoint(analytics_client):
    resp = await analytics_client.get("/api/analytics/by-department", headers={"Authorization": f"Bearer {_analyst_token()}"})
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
