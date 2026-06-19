# Net Salary Calculator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `POST /api/calculator/calculate` endpoint and a `/calculator` frontend page so any authenticated user can enter a gross salary and country to see their estimated net take-home after PF and tax deductions.

**Architecture:** The endpoint reuses the existing `compute_take_home` function from `payroll_service.py`, looking up PF and tax rules from the DB exactly as `generate_salary_slip` does. The frontend is a two-column card: inputs on the left, results breakdown on the right. No new math logic.

**Tech Stack:** FastAPI, SQLAlchemy async, Pydantic v2, pytest-asyncio, React 18, react-query (`useMutation`), Tailwind CSS, shadcn/ui components (`Card`, `Button`, `Input`, `Label`).

---

## File Map

| File | Action | Purpose |
|---|---|---|
| `backend/app/schemas/calculator.py` | Create | `CalculatorRequest` + `CalculatorResponse` Pydantic models |
| `backend/app/api/calculator.py` | Create | `POST /api/calculator/calculate` router |
| `backend/app/main.py` | Modify | Register calculator router |
| `backend/tests/test_calculator.py` | Create | 2 integration tests (with rules, no rules) |
| `frontend/src/lib/api.ts` | Modify | Add `CalculatorRequest`, `CalculatorResponse` types + `calculateNetSalary` |
| `frontend/src/pages/Calculator.tsx` | Create | Two-column calculator UI |
| `frontend/src/router.tsx` | Modify | Add `/calculator` route |
| `frontend/src/components/Layout.tsx` | Modify | Add "Calculator" nav item for all roles |

---

## Task 1: Backend — Schemas, Endpoint, Tests

**Files:**
- Create: `backend/app/schemas/calculator.py`
- Create: `backend/app/api/calculator.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_calculator.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_calculator.py` with this exact content:

```python
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
        },
        headers={"Authorization": f"Bearer {_token()}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["net_take_home"] < data["gross_salary"]
    assert data["pf_employee_contribution"] > 0   # 5000 * 0.06 = 300
    assert data["tax_deducted"] > 0
    assert data["no_rules_warning"] is False
    assert data["pf_rule_applied"] == "Test PF"
    assert data["tax_rule_applied"] == "Test Tax 2024"


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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend
pytest tests/test_calculator.py -v
```

Expected: FAIL — `404 Not Found` (route doesn't exist yet).

- [ ] **Step 3: Create the Pydantic schemas**

Create `backend/app/schemas/calculator.py`:

```python
from __future__ import annotations
from typing import Literal, Optional
from pydantic import BaseModel


class CalculatorRequest(BaseModel):
    country: str
    base_salary: float
    pay_frequency: Literal["monthly", "annual"] = "monthly"
    allowances: float = 0.0
    other_deductions: float = 0.0


class CalculatorResponse(BaseModel):
    gross_salary: float
    pf_employee_contribution: float
    pf_employer_contribution: float
    tax_deducted: float
    other_deductions: float
    net_take_home: float
    currency: str
    tax_rule_applied: Optional[str]
    pf_rule_applied: Optional[str]
    no_rules_warning: bool
```

- [ ] **Step 4: Create the endpoint**

Create `backend/app/api/calculator.py`:

```python
from __future__ import annotations
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.auth.dependencies import any_authenticated
from app.models.user import User
from app.models.tax import TaxRule
from app.models.pf import PFRule
from app.schemas.calculator import CalculatorRequest, CalculatorResponse
from app.services.payroll_service import compute_take_home

router = APIRouter(prefix="/api/calculator", tags=["calculator"])


@router.post("/calculate", response_model=CalculatorResponse)
async def calculate_net_salary(
    body: CalculatorRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(any_authenticated),
) -> CalculatorResponse:
    pf_r = await db.execute(
        select(PFRule)
        .where(PFRule.country == body.country)
        .order_by(PFRule.effective_from_date.desc())
        .limit(1)
    )
    pf_rule = pf_r.scalar_one_or_none()

    tax_r = await db.execute(
        select(TaxRule)
        .where(TaxRule.country == body.country)
        .order_by(TaxRule.tax_year.desc())
        .limit(1)
        .options(selectinload(TaxRule.brackets))
    )
    tax_rule = tax_r.scalar_one_or_none()

    pf_employee_pct = float(pf_rule.employee_contribution_pct) if pf_rule else 0.0
    pf_employer_pct = float(pf_rule.employer_contribution_pct) if pf_rule else 0.0
    pf_cap = float(pf_rule.applicable_salary_cap) if pf_rule and pf_rule.applicable_salary_cap else None

    brackets = [
        {
            "min_income": float(b.min_income),
            "max_income": float(b.max_income) if b.max_income else None,
            "rate_pct": float(b.rate_pct),
        }
        for b in (tax_rule.brackets if tax_rule else [])
    ]

    currency = tax_rule.brackets[0].currency if tax_rule and tax_rule.brackets else "USD"
    base_monthly = body.base_salary if body.pay_frequency == "monthly" else body.base_salary / 12

    computed = compute_take_home(
        base_monthly,
        body.allowances,
        pf_employee_pct,
        pf_employer_pct,
        pf_cap,
        brackets,
        body.other_deductions,
    )

    return CalculatorResponse(
        **computed,
        currency=currency,
        tax_rule_applied=tax_rule.rule_name if tax_rule else None,
        pf_rule_applied=pf_rule.rule_name if pf_rule else None,
        no_rules_warning=(pf_rule is None and tax_rule is None),
    )
```

- [ ] **Step 5: Register the router in main.py**

In `backend/app/main.py`, add the import at the top with the other router imports:

```python
from app.api.calculator import router as calculator_router
```

Then add `calculator_router` to the router list (the `for router in [...]` loop):

```python
for router in [auth_router, employees_router, compensation_router, tax_rules_router,
               pf_rules_router, salary_slips_router, salary_admin_router, tax_statement_router,
               analytics_router, ai_router, meta_router, admin_router, bank_router,
               calculator_router]:
    app.include_router(router)
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
cd backend
pytest tests/test_calculator.py -v
```

Expected output:
```
tests/test_calculator.py::test_calculate_with_rules PASSED
tests/test_calculator.py::test_calculate_no_rules PASSED
2 passed in ...
```

- [ ] **Step 7: Run the full test suite to check for regressions**

```bash
cd backend
pytest --tb=short -q
```

Expected: all previously passing tests still pass.

- [ ] **Step 8: Commit**

```bash
git add backend/app/schemas/calculator.py backend/app/api/calculator.py backend/app/main.py backend/tests/test_calculator.py
git commit -m "feat: add net salary calculator endpoint"
```

---

## Task 2: Frontend — Page, API Call, Route, Nav

**Files:**
- Modify: `frontend/src/lib/api.ts`
- Create: `frontend/src/pages/Calculator.tsx`
- Modify: `frontend/src/router.tsx`
- Modify: `frontend/src/components/Layout.tsx`

- [ ] **Step 1: Add API types and function to api.ts**

Open `frontend/src/lib/api.ts`. At the end of the file add:

```typescript
// Calculator
export interface CalculatorRequest {
  country: string;
  base_salary: number;
  pay_frequency: "monthly" | "annual";
  allowances: number;
  other_deductions: number;
}

export interface CalculatorResponse {
  gross_salary: number;
  pf_employee_contribution: number;
  pf_employer_contribution: number;
  tax_deducted: number;
  other_deductions: number;
  net_take_home: number;
  currency: string;
  tax_rule_applied: string | null;
  pf_rule_applied: string | null;
  no_rules_warning: boolean;
}

export const calculateNetSalary = (data: CalculatorRequest): Promise<CalculatorResponse> =>
  api.post("/api/calculator/calculate", data).then((r) => r.data);
```

- [ ] **Step 2: Create the Calculator page**

Create `frontend/src/pages/Calculator.tsx`:

```tsx
import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import {
  calculateNetSalary,
  type CalculatorRequest,
  type CalculatorResponse,
} from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

function fmt(n: number, currency = "USD") {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    maximumFractionDigits: 0,
  }).format(n);
}

export default function Calculator() {
  const [country, setCountry] = useState("");
  const [baseSalary, setBaseSalary] = useState("");
  const [payFrequency, setPayFrequency] = useState<"monthly" | "annual">("monthly");
  const [allowances, setAllowances] = useState("0");
  const [otherDeductions, setOtherDeductions] = useState("0");

  const mutation = useMutation({
    mutationFn: (data: CalculatorRequest) => calculateNetSalary(data),
  });

  function handleSubmit() {
    mutation.mutate({
      country: country.trim().toUpperCase(),
      base_salary: Number(baseSalary),
      pay_frequency: payFrequency,
      allowances: Number(allowances) || 0,
      other_deductions: Number(otherDeductions) || 0,
    });
  }

  const result: CalculatorResponse | undefined = mutation.data;
  const canSubmit = country.trim().length > 0 && Number(baseSalary) > 0;

  return (
    <div className="max-w-3xl space-y-4">
      <h1 className="text-2xl font-bold">Net Salary Calculator</h1>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
        {/* Inputs */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Inputs</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label>Country (ISO code)</Label>
              <Input
                placeholder="e.g. USA, IND"
                value={country}
                onChange={(e) => setCountry(e.target.value)}
                maxLength={3}
              />
            </div>
            <div>
              <Label>Base Salary</Label>
              <Input
                type="number"
                placeholder="0"
                value={baseSalary}
                onChange={(e) => setBaseSalary(e.target.value)}
              />
            </div>
            <div>
              <Label>Pay Frequency</Label>
              <div className="flex gap-2 mt-1">
                <Button
                  size="sm"
                  variant={payFrequency === "monthly" ? "default" : "outline"}
                  onClick={() => setPayFrequency("monthly")}
                >
                  Monthly
                </Button>
                <Button
                  size="sm"
                  variant={payFrequency === "annual" ? "default" : "outline"}
                  onClick={() => setPayFrequency("annual")}
                >
                  Annual
                </Button>
              </div>
            </div>
            <div>
              <Label>Allowances (monthly)</Label>
              <Input
                type="number"
                placeholder="0"
                value={allowances}
                onChange={(e) => setAllowances(e.target.value)}
              />
            </div>
            <div>
              <Label>Other Deductions (monthly)</Label>
              <Input
                type="number"
                placeholder="0"
                value={otherDeductions}
                onChange={(e) => setOtherDeductions(e.target.value)}
              />
            </div>
            <Button
              className="w-full"
              onClick={handleSubmit}
              disabled={!canSubmit || mutation.isPending}
            >
              {mutation.isPending ? "Calculating…" : "Calculate"}
            </Button>
            {mutation.isError && (
              <p className="text-sm text-red-600">
                Calculation failed. Please try again.
              </p>
            )}
          </CardContent>
        </Card>

        {/* Results */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Result</CardTitle>
          </CardHeader>
          <CardContent>
            {!result ? (
              <p className="text-slate-400 text-sm">
                Enter your details and click Calculate.
              </p>
            ) : (
              <div className="space-y-4">
                {result.no_rules_warning && (
                  <div className="rounded-md bg-amber-50 border border-amber-200 px-3 py-2 text-sm text-amber-700">
                    No tax or PF rules found for{" "}
                    <strong>{country.toUpperCase()}</strong> — result shows
                    gross only.
                  </div>
                )}
                <div>
                  <p className="text-xs text-slate-500 uppercase tracking-wide">
                    Net Take-Home / mo
                  </p>
                  <p className="text-3xl font-bold text-indigo-600">
                    {fmt(result.net_take_home, result.currency)}
                  </p>
                </div>
                <table className="w-full text-sm">
                  <tbody className="divide-y divide-slate-100">
                    <tr>
                      <td className="py-1.5 text-slate-600">Gross Salary</td>
                      <td className="py-1.5 text-right font-medium">
                        {fmt(result.gross_salary, result.currency)}
                      </td>
                    </tr>
                    <tr>
                      <td className="py-1.5 text-slate-600">− PF (Employee)</td>
                      <td className="py-1.5 text-right text-red-600">
                        −{fmt(result.pf_employee_contribution, result.currency)}
                      </td>
                    </tr>
                    <tr>
                      <td className="py-1.5 text-slate-600">− Income Tax</td>
                      <td className="py-1.5 text-right text-red-600">
                        −{fmt(result.tax_deducted, result.currency)}
                      </td>
                    </tr>
                    <tr>
                      <td className="py-1.5 text-slate-600">
                        − Other Deductions
                      </td>
                      <td className="py-1.5 text-right text-red-600">
                        −{fmt(result.other_deductions, result.currency)}
                      </td>
                    </tr>
                    <tr className="border-t-2 border-slate-300 font-semibold">
                      <td className="py-1.5">= Net Take-Home</td>
                      <td className="py-1.5 text-right text-indigo-600">
                        {fmt(result.net_take_home, result.currency)}
                      </td>
                    </tr>
                  </tbody>
                </table>
                {result.pf_employer_contribution > 0 && (
                  <p className="text-xs text-slate-500">
                    Your employer contributes an additional{" "}
                    {fmt(result.pf_employer_contribution, result.currency)} to
                    your PF.
                  </p>
                )}
                {(result.tax_rule_applied || result.pf_rule_applied) && (
                  <p className="text-xs text-slate-400">
                    Rules applied:{" "}
                    {[result.tax_rule_applied, result.pf_rule_applied]
                      .filter(Boolean)
                      .join(" · ")}
                  </p>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Add the route in router.tsx**

Open `frontend/src/router.tsx`. Add the import at the top with the other page imports:

```typescript
import Calculator from "@/pages/Calculator";
```

Then add this route inside the inner `<Routes>` block, after the `/insights` route:

```tsx
<Route path="/calculator" element={<Calculator />} />
```

The inner Routes block should look like:

```tsx
<Routes>
  <Route path="/" element={<Dashboard />} />
  <Route path="/employees" element={<Employees />} />
  <Route path="/employees/:id" element={<EmployeeDetail />} />
  <Route path="/insights" element={<Insights />} />
  <Route path="/calculator" element={<Calculator />} />
  <Route path="/my/salary-slips" element={<SalarySlips />} />
  <Route path="/admin/tax-rules" element={<TaxRules />} />
  <Route path="/admin/pf-rules" element={<PFRules />} />
  <Route path="/admin/users" element={<Users />} />
  <Route path="*" element={<Navigate to="/" replace />} />
</Routes>
```

- [ ] **Step 4: Add the nav item in Layout.tsx**

Open `frontend/src/components/Layout.tsx`.

Add `Calculator` to the lucide-react import (it's currently importing: `LayoutDashboard, Users, MessageSquare, FileText, Briefcase, UserCog, Receipt, Layers`):

```typescript
import {
  LayoutDashboard,
  Users,
  MessageSquare,
  FileText,
  Briefcase,
  UserCog,
  Receipt,
  Layers,
  Calculator,
} from "lucide-react";
```

Add this entry to the `navItems` array, after the AI Insights entry (line 18):

```typescript
{ href: "/calculator", label: "Calculator", icon: Calculator, roles: ["admin", "hr_manager", "hr_analyst", "employee"] },
```

Add this entry to the `routeTitles` object:

```typescript
"/calculator": "Net Salary Calculator",
```

- [ ] **Step 5: Check TypeScript compiles cleanly**

```bash
cd frontend
npx tsc --noEmit
```

Expected: no output (zero errors).

- [ ] **Step 6: Verify in the browser**

With the Vite dev server running (`npm run dev` in `frontend/`):

1. Log in as any user (admin, hr_analyst, or employee)
2. Confirm "Calculator" appears in the left sidebar
3. Click it — page loads at `/calculator` with two cards side by side
4. Enter `TST` as country, `5000` as monthly salary, click Calculate
   - If TST rules exist in your DB: right card shows a breakdown with PF and tax deducted
   - If not: amber warning banner appears, net = gross
5. Switch pay frequency to "Annual", enter `60000`, click Calculate — result should match `5000/mo` case

- [ ] **Step 7: Commit**

```bash
git add frontend/src/lib/api.ts frontend/src/pages/Calculator.tsx frontend/src/router.tsx frontend/src/components/Layout.tsx
git commit -m "feat: add net salary calculator page"
```
