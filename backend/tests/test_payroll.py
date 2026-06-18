import pytest
from app.services.payroll_service import compute_progressive_tax, compute_take_home


def test_flat_tax():
    brackets = [{"min_income": 0, "max_income": None, "rate_pct": 0.20}]
    assert compute_progressive_tax(60000, brackets) == pytest.approx(12000.0)


def test_progressive_two_brackets():
    # 10% up to 10000, 20% above → 10000*0.10 + 20000*0.20 = 1000 + 4000 = 5000
    brackets = [
        {"min_income": 0, "max_income": 10000, "rate_pct": 0.10},
        {"min_income": 10000, "max_income": None, "rate_pct": 0.20},
    ]
    assert compute_progressive_tax(30000, brackets) == pytest.approx(5000.0)


def test_compute_take_home():
    # gross = 7500 + 500 = 8000
    # pf_employee = 7500 * 0.12 = 900
    # taxable_monthly = 8000 - 900 = 7100; annual = 85200
    # tax_annual = 50000*0.10 + 35200*0.20 = 5000 + 7040 = 12040; monthly = 12040/12
    # net = 8000 - 900 - 12040/12 - 200
    result = compute_take_home(
        base_salary_monthly=7500.0, allowances_monthly=500.0,
        pf_employee_pct=0.12, pf_employer_pct=0.12, pf_salary_cap=None,
        tax_brackets=[
            {"min_income": 0, "max_income": 50000, "rate_pct": 0.10},
            {"min_income": 50000, "max_income": None, "rate_pct": 0.20},
        ],
        other_deductions_monthly=200.0,
    )
    assert result["gross_salary"] == pytest.approx(8000.0)
    assert result["pf_employee_contribution"] == pytest.approx(900.0)
    assert result["tax_deducted"] == pytest.approx(12040 / 12, rel=1e-3)
    assert result["net_take_home"] == pytest.approx(8000 - 900 - 12040 / 12 - 200, rel=1e-3)


import pytest
from datetime import date, timedelta
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
import app.models  # noqa
from app.main import app
from app.core.database import Base, get_db
from app.models.employee import Employee, EmploymentType
from app.models.user import User, UserRole
from app.models.compensation import SalaryRecord, Allowance, AllowanceType, PayFrequency
from app.models.tax import TaxRule, TaxBracket, TaxRuleType
from app.auth.utils import hash_password, create_access_token

_ENGINE2 = create_async_engine("sqlite+aiosqlite:///:memory:")
_Session2 = async_sessionmaker(_ENGINE2, expire_on_commit=False)


@pytest.fixture(scope="module")
async def slip_setup():
    async with _ENGINE2.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with _Session2() as s:
        hr = User(email="hr2@acme.com", hashed_password=hash_password("pw"), role=UserRole.hr_manager)
        s.add(hr)
        await s.flush()
        emp = Employee(
            employee_id="ACME-00002", first_name="Alice", last_name="Lee",
            email="alice@acme.com", department="Eng", job_title="Dev",
            country="US", currency="USD", hire_date=date(2022, 1, 1),
            employment_type=EmploymentType.full_time,
        )
        s.add(emp)
        await s.flush()
        s.add(SalaryRecord(employee_id=emp.id, base_salary=6000, currency="USD", effective_date=date(2024, 1, 1), pay_frequency=PayFrequency.monthly))
        s.add(Allowance(employee_id=emp.id, allowance_type=AllowanceType.transport, amount=200, currency="USD", frequency=PayFrequency.monthly))
        tax_rule = TaxRule(country="US", rule_name="US Tax 2024", rule_type=TaxRuleType.income_tax, tax_year=2024, created_by=hr.id)
        s.add(tax_rule)
        await s.flush()
        s.add(TaxBracket(tax_rule_id=tax_rule.id, min_income=0, max_income=None, rate_pct=0.20, currency="USD"))
        await s.commit()
    yield
    async with _ENGINE2.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def slip_client(slip_setup):
    async with _Session2() as s:
        async def override():
            yield s
        app.dependency_overrides[get_db] = override
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            yield c
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_generate_salary_slip(slip_client):
    token = create_access_token({"sub": "hr2@acme.com", "role": "hr_manager"}, expires_delta=timedelta(hours=1))
    resp = await slip_client.post(
        "/api/employees/1/salary-slips/generate",
        json={"period_month": 1, "period_year": 2024},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["gross_salary"] == pytest.approx(6200.0)
    assert data["net_take_home"] > 0


@pytest.mark.asyncio
async def test_download_slip_pdf(slip_client):
    token = create_access_token(
        {"sub": "hr2@acme.com", "role": "hr_manager"},
        expires_delta=timedelta(hours=1),
    )
    # Generate a slip for month 3 first
    gen = await slip_client.post(
        "/api/employees/1/salary-slips/generate",
        json={"period_month": 3, "period_year": 2025},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert gen.status_code == 201

    # Download the PDF
    resp = await slip_client.get(
        "/api/employees/1/salary-slips/2025/3/pdf",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content[:4] == b"%PDF"


@pytest.mark.asyncio
async def test_download_slip_pdf_not_found(slip_client):
    token = create_access_token(
        {"sub": "hr2@acme.com", "role": "hr_manager"},
        expires_delta=timedelta(hours=1),
    )
    resp = await slip_client.get(
        "/api/employees/1/salary-slips/1990/1/pdf",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404
