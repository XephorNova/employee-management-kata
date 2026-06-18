from datetime import date, datetime
from decimal import Decimal
from app.services.pdf_service import generate_salary_slip_pdf
from app.models.payroll import SalarySlip
from app.models.employee import Employee, EmploymentType


def _slip() -> SalarySlip:
    return SalarySlip(
        employee_id=1,
        period_month=6,
        period_year=2025,
        gross_salary=Decimal("8000.00"),
        taxable_income=Decimal("7100.00"),
        tax_deducted=Decimal("1003.33"),
        pf_employee_contribution=Decimal("900.00"),
        pf_employer_contribution=Decimal("900.00"),
        other_deductions=Decimal("200.00"),
        net_take_home=Decimal("5896.67"),
        currency="USD",
        generated_at=datetime(2025, 6, 19, 10, 0, 0),
        generated_by=1,
    )


def _employee() -> Employee:
    return Employee(
        employee_id="ACME-00001",
        first_name="Alice",
        last_name="Lee",
        email="alice@acme.com",
        department="Engineering",
        job_title="Software Engineer",
        country="US",
        currency="USD",
        hire_date=date(2022, 1, 1),
        employment_type=EmploymentType.full_time,
    )


def test_returns_pdf_bytes():
    result = generate_salary_slip_pdf(_slip(), _employee())
    assert isinstance(result, bytes)
    assert result[:4] == b"%PDF"


def test_pdf_contains_employee_name():
    result = generate_salary_slip_pdf(_slip(), _employee())
    assert b"Alice" in result


def test_pdf_contains_period():
    result = generate_salary_slip_pdf(_slip(), _employee())
    assert b"June 2025" in result


def test_pdf_contains_net_amount():
    result = generate_salary_slip_pdf(_slip(), _employee())
    # net_take_home formatted as 5,896.67
    assert b"5,896.67" in result
