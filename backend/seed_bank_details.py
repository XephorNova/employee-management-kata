"""
Seed bank details for all existing employees.
Run: cd backend && source .venv/bin/activate && python seed_bank_details.py
"""
import asyncio
import random
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import select

from app.core.config import settings
from app.core.database import Base
import app.models  # noqa
from app.models.employee import Employee
from app.models.bank import BankDetail

BANKS = {
    "US": [
        {"bank_name": "Chase", "routing_prefix": "021"},
        {"bank_name": "Wells Fargo", "routing_prefix": "121"},
        {"bank_name": "Bank of America", "routing_prefix": "026"},
        {"bank_name": "Citibank", "routing_prefix": "021"},
    ],
    "IN": [
        {"bank_name": "HDFC Bank", "ifsc_prefix": "HDFC"},
        {"bank_name": "State Bank of India", "ifsc_prefix": "SBIN"},
        {"bank_name": "ICICI Bank", "ifsc_prefix": "ICIC"},
        {"bank_name": "Axis Bank", "ifsc_prefix": "UTIB"},
    ],
    "GB": [
        {"bank_name": "Barclays", "sort_prefix": "20"},
        {"bank_name": "HSBC UK", "sort_prefix": "40"},
        {"bank_name": "Lloyds Bank", "sort_prefix": "30"},
        {"bank_name": "NatWest", "sort_prefix": "60"},
    ],
    "DE": [
        {"bank_name": "Deutsche Bank", "swift": "DEUTDEDB"},
        {"bank_name": "Commerzbank", "swift": "COBADEFF"},
        {"bank_name": "DZ Bank", "swift": "GENODEFF"},
        {"bank_name": "Sparkasse", "swift": "BELADEBE"},
    ],
    "SG": [
        {"bank_name": "DBS Bank", "swift": "DBSSSGSG"},
        {"bank_name": "OCBC Bank", "swift": "OCBCSGSG"},
        {"bank_name": "UOB", "swift": "UOVBSGSG"},
        {"bank_name": "Standard Chartered SG", "swift": "SCBLSGSG"},
    ],
}

ACCOUNT_TYPES = {
    "US": ["checking", "savings"],
    "IN": ["savings", "current"],
    "GB": ["current", "savings"],
    "DE": ["current", "savings"],
    "SG": ["savings", "current"],
}


def _random_account_number() -> str:
    return str(random.randint(10_000_000_00, 99_999_999_99))


def _make_bank_detail(emp_id: int, country: str, is_primary: bool) -> BankDetail:
    bank = random.choice(BANKS.get(country, BANKS["US"]))
    account_type = random.choice(ACCOUNT_TYPES.get(country, ["savings"]))
    account_number = _random_account_number()

    routing_number = None
    ifsc_code = None
    swift_code = None

    if country == "US":
        routing_number = bank["routing_prefix"] + str(random.randint(1_000_000, 9_999_999))
    elif country == "IN":
        ifsc_code = bank["ifsc_prefix"] + "0" + f"{random.randint(100000, 999999)}"
    elif country == "GB":
        routing_number = bank["sort_prefix"] + "-" + str(random.randint(10, 99)) + "-" + str(random.randint(10, 99))
    elif country in ("DE", "SG"):
        swift_code = bank["swift"]

    return BankDetail(
        employee_id=emp_id,
        bank_name=bank["bank_name"],
        account_number=account_number,
        account_type=account_type,
        routing_number=routing_number,
        ifsc_code=ifsc_code,
        swift_code=swift_code,
        is_primary=is_primary,
    )


async def seed():
    engine = create_async_engine(settings.database_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    Session = async_sessionmaker(engine, expire_on_commit=False)

    async with Session() as db:
        result = await db.execute(select(Employee))
        employees = result.scalars().all()
        total = len(employees)
        print(f"Found {total} employees. Seeding bank details...")

        batch_size = 500
        for batch_start in range(0, total, batch_size):
            batch = employees[batch_start: batch_start + batch_size]
            details = []
            for emp in batch:
                details.append(_make_bank_detail(emp.id, emp.country, is_primary=True))
                # ~30% of employees have a second account
                if random.random() < 0.30:
                    details.append(_make_bank_detail(emp.id, emp.country, is_primary=False))
            db.add_all(details)
            await db.commit()
            print(f"  Processed {min(batch_start + batch_size, total)}/{total}")

    print(f"\nDone. Bank details seeded for {total} employees.")


if __name__ == "__main__":
    asyncio.run(seed())
