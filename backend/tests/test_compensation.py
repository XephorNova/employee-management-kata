import pytest
from datetime import date, timedelta
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
import app.models  # noqa
from app.main import app
from app.core.database import Base, get_db
from app.models.employee import Employee, EmploymentType
from app.models.user import User, UserRole
from app.auth.utils import create_access_token, hash_password

_ENGINE = create_async_engine("sqlite+aiosqlite:///:memory:")
_Session = async_sessionmaker(_ENGINE, expire_on_commit=False)


def _hr_token() -> str:
    return create_access_token({"sub": "hr@acme.com", "role": "hr_manager"}, expires_delta=timedelta(hours=1))


@pytest.fixture(scope="module")
async def setup():
    async with _ENGINE.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with _Session() as s:
        s.add(User(email="hr@acme.com", hashed_password=hash_password("pw"), role=UserRole.hr_manager))
        emp = Employee(
            employee_id="ACME-00001", first_name="Test", last_name="User",
            email="test.comp@acme.com", department="Eng", job_title="Dev",
            country="US", currency="USD", hire_date=date(2022, 1, 1),
            employment_type=EmploymentType.full_time,
        )
        s.add(emp)
        await s.commit()
        await s.refresh(emp)
    yield
    async with _ENGINE.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client(setup):
    async with _Session() as s:
        async def override():
            yield s
        app.dependency_overrides[get_db] = override
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            yield c
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_create_and_list_salary_record(client):
    token = _hr_token()
    resp = await client.post(
        "/api/employees/1/salary-records",
        json={"base_salary": 90000, "currency": "USD", "effective_date": "2024-01-01", "pay_frequency": "monthly"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    assert resp.json()["base_salary"] == 90000.0

    list_resp = await client.get("/api/employees/1/salary-records", headers={"Authorization": f"Bearer {token}"})
    assert list_resp.status_code == 200
    assert len(list_resp.json()) >= 1


@pytest.mark.asyncio
async def test_create_bonus(client):
    token = _hr_token()
    resp = await client.post(
        "/api/employees/1/bonuses",
        json={"amount": 5000, "currency": "USD", "bonus_type": "annual", "awarded_date": "2024-03-15"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    assert resp.json()["bonus_type"] == "annual"


@pytest.mark.asyncio
async def test_create_allowance(client):
    token = _hr_token()
    resp = await client.post(
        "/api/employees/1/allowances",
        json={"allowance_type": "transport", "amount": 200, "currency": "USD", "frequency": "monthly"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
