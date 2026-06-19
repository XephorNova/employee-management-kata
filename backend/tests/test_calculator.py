import pytest
from datetime import date, timedelta
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
import app.models  # noqa
from app.main import app
from app.core.database import Base, get_db
from app.models.user import User, UserRole
from app.models.tax import TaxRule, TaxBracket, TaxRuleType
from app.models.pf import PFRule
from app.auth.utils import hash_password, create_access_token

_ENGINE_CALC = create_async_engine("sqlite+aiosqlite:///:memory:")
_Session_CALC = async_sessionmaker(_ENGINE_CALC, expire_on_commit=False)


@pytest.fixture(scope="module")
async def calc_setup():
    async with _ENGINE_CALC.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with _Session_CALC() as s:
        user = User(
            email="calc_hr@acme.com",
            hashed_password=hash_password("pw"),
            role=UserRole.hr_analyst,
        )
        s.add(user)
        await s.flush()
        tax_rule = TaxRule(
            country="TST",
            rule_name="Test Tax 2024",
            rule_type=TaxRuleType.income_tax,
            tax_year=2024,
            created_by=user.id,
        )
        s.add(tax_rule)
        await s.flush()
        s.add(TaxBracket(
            tax_rule_id=tax_rule.id,
            min_income=0,
            max_income=None,
            rate_pct=0.20,
            currency="USD",
        ))
        s.add(PFRule(
            country="TST",
            rule_name="Test PF",
            employee_contribution_pct=0.06,
            employer_contribution_pct=0.06,
            applicable_salary_cap=None,
            effective_from_date=date(2024, 1, 1),
            created_by=user.id,
        ))
        await s.commit()
    yield
    async with _ENGINE_CALC.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def calc_client(calc_setup):
    async with _Session_CALC() as s:
        async def override():
            yield s
        app.dependency_overrides[get_db] = override
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            yield c
        app.dependency_overrides.clear()


def _token():
    return create_access_token(
        {"sub": "calc_hr@acme.com", "role": "hr_analyst"},
        expires_delta=timedelta(hours=1),
    )


@pytest.mark.asyncio
async def test_calculate_with_rules(calc_client):
    resp = await calc_client.post(
        "/api/calculator/calculate",
        json={
            "country": "TST",
            "base_salary": 5000,
            "pay_frequency": "monthly",
            "allowances": 0,
            "other_deductions": 0,
            "currency": "USD",
        },
        headers={"Authorization": f"Bearer {_token()}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["net_take_home"] < data["gross_salary"]
    assert data["pf_employee_contribution"] > 0
    assert data["tax_deducted"] > 0
    assert data["no_rules_warning"] is False
    assert data["pf_rule_applied"] == "Test PF"
    assert data["tax_rule_applied"] == "Test Tax 2024"
    assert data["gross_salary"] == pytest.approx(5000.0)
    assert data["pf_employee_contribution"] == pytest.approx(300.0)
    assert data["tax_deducted"] == pytest.approx(940.0)
    assert data["net_take_home"] == pytest.approx(3760.0)


@pytest.mark.asyncio
async def test_calculate_no_rules(calc_client):
    resp = await calc_client.post(
        "/api/calculator/calculate",
        json={
            "country": "ZZZ",
            "base_salary": 5000,
            "pay_frequency": "monthly",
            "allowances": 0,
            "other_deductions": 0,
        },
        headers={"Authorization": f"Bearer {_token()}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["net_take_home"] == data["gross_salary"]
    assert data["pf_employee_contribution"] == 0
    assert data["tax_deducted"] == 0
    assert data["no_rules_warning"] is True
    assert data["tax_rule_applied"] is None
    assert data["pf_rule_applied"] is None
