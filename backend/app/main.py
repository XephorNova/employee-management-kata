from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.auth import router as auth_router
from app.api.employees import router as employees_router
from app.api.compensation import router as compensation_router
from app.api.tax_rules import router as tax_rules_router
from app.api.pf_rules import router as pf_rules_router
from app.api.salary_slips import router as salary_slips_router, salary_admin_router, tax_statement_router
from app.api.analytics import router as analytics_router
from app.api.ai import router as ai_router
from app.api.meta import router as meta_router
from app.api.admin import router as admin_router
from app.api.bank import router as bank_router
from app.api.calculator import router as calculator_router
from app.core.database import engine, Base
import app.models  # noqa — ensures all models registered


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(title="ACME HR Salary Management API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for router in [auth_router, employees_router, compensation_router, tax_rules_router,
               pf_rules_router, salary_slips_router, salary_admin_router, tax_statement_router,
               analytics_router, ai_router, meta_router, admin_router, bank_router,
               calculator_router]:
    app.include_router(router)


@app.get("/health")
async def health():
    return {"status": "ok"}
