"""
Run: cd backend && source .venv/bin/activate && python seed.py
Credentials created: admin@acme.com/Admin123!, hr@acme.com/Hr123!, analyst@acme.com/Analyst123!
"""
import asyncio
import random
from datetime import date, timedelta
from faker import Faker
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.core.config import settings
from app.core.database import Base
import app.models  # noqa
from app.models.employee import Employee, PayGrade, EmploymentType, EmployeeStatus
from app.models.compensation import SalaryRecord, Allowance, AllowanceType, PayFrequency
from app.models.tax import TaxRule, TaxBracket, TaxRuleType
from app.models.pf import PFRule
from app.models.user import User, UserRole
from app.auth.utils import hash_password

fake = Faker()

COUNTRIES = ["US", "IN", "GB", "DE", "SG"]
CURRENCIES = {"US": "USD", "IN": "INR", "GB": "GBP", "DE": "EUR", "SG": "SGD"}
DEPARTMENTS = ["Engineering", "Finance", "HR", "Sales", "Marketing", "Operations", "Legal", "Product"]
EMP_TYPES = [EmploymentType.full_time, EmploymentType.part_time, EmploymentType.contractor]
EMP_WEIGHTS = [0.80, 0.10, 0.10]
GRADES = [("L1", 30000, 50000), ("L2", 50000, 80000), ("L3", 80000, 120000), ("L4", 120000, 180000),
          ("L5", 180000, 250000), ("L6", 250000, 350000), ("L7", 350000, 500000), ("L8", 500000, 800000)]


async def seed():
    engine = create_async_engine(settings.database_url)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with Session() as db:
        # Users
        admin = User(email="admin@acme.com", hashed_password=hash_password("Admin123!"), role=UserRole.admin)
        hr = User(email="hr@acme.com", hashed_password=hash_password("Hr123!"), role=UserRole.hr_manager)
        analyst = User(email="analyst@acme.com", hashed_password=hash_password("Analyst123!"), role=UserRole.hr_analyst)
        db.add_all([admin, hr, analyst])
        await db.flush()

        # Pay grades
        grades = []
        for name, min_s, max_s in GRADES:
            g = PayGrade(grade=name, min_salary=min_s, max_salary=max_s, currency="USD")
            db.add(g)
            grades.append(g)
        await db.flush()

        # Tax rules (3 brackets per country)
        for country in COUNTRIES:
            rule = TaxRule(country=country, rule_name=f"{country} Income Tax 2024",
                           rule_type=TaxRuleType.income_tax, tax_year=2024, created_by=admin.id)
            db.add(rule)
            await db.flush()
            cur = CURRENCIES[country]
            db.add_all([
                TaxBracket(tax_rule_id=rule.id, min_income=0, max_income=30000, rate_pct=0.10, currency=cur),
                TaxBracket(tax_rule_id=rule.id, min_income=30000, max_income=100000, rate_pct=0.20, currency=cur),
                TaxBracket(tax_rule_id=rule.id, min_income=100000, max_income=None, rate_pct=0.30, currency=cur),
            ])

        # PF rules
        for country in COUNTRIES:
            db.add(PFRule(country=country, rule_name=f"{country} PF 2024",
                          employee_contribution_pct=0.06, employer_contribution_pct=0.06,
                          applicable_salary_cap=None, effective_from_date=date(2024, 1, 1), created_by=admin.id))
        await db.flush()

        # 10,000 employees in batches of 500
        batch_size = 500
        for batch_start in range(0, 10000, batch_size):
            emps, records, allowances = [], [], []
            for i in range(batch_start, min(batch_start + batch_size, 10000)):
                country = random.choice(COUNTRIES)
                grade = random.choice(grades)
                emp = Employee(
                    employee_id=f"ACME-{i + 1:05d}",
                    first_name=fake.first_name(), last_name=fake.last_name(),
                    email=f"emp{i + 1}@acme.com", department=random.choice(DEPARTMENTS),
                    job_title=fake.job()[:100], pay_grade_id=grade.id,
                    country=country, currency=CURRENCIES[country],
                    hire_date=date(2019, 1, 1) + timedelta(days=random.randint(0, 365 * 5)),
                    employment_type=random.choices(EMP_TYPES, weights=EMP_WEIGHTS)[0],
                    status=EmployeeStatus.active if random.random() > 0.05 else EmployeeStatus.inactive,
                )
                emps.append(emp)
            db.add_all(emps)
            await db.flush()

            for emp, i in zip(emps, range(batch_start, min(batch_start + batch_size, 10000))):
                grade = next(g for g in grades if g.id == emp.pay_grade_id)
                monthly = random.uniform(float(grade.min_salary), float(grade.max_salary)) / 12
                records.append(SalaryRecord(
                    employee_id=emp.id, base_salary=round(monthly, 2),
                    currency=emp.currency, effective_date=emp.hire_date, pay_frequency=PayFrequency.monthly,
                ))
                if random.random() > 0.5:
                    allowances.append(Allowance(
                        employee_id=emp.id, allowance_type=random.choice(list(AllowanceType)),
                        amount=round(random.uniform(100, 500), 2),
                        currency=emp.currency, frequency=PayFrequency.monthly,
                    ))
            db.add_all(records + allowances)
            await db.commit()
            print(f"  Seeded {min(batch_start + batch_size, 10000)}/10000 employees")

    print("\nSeed complete!")
    print("  admin@acme.com / Admin123!")
    print("  hr@acme.com / Hr123!")
    print("  analyst@acme.com / Analyst123!")


if __name__ == "__main__":
    asyncio.run(seed())
