# ACME HR Salary Management System — Design Spec

**Date:** 2026-06-15
**Author:** Keval Shreya
**Status:** Approved

---

## Goal

Replace ACME's Excel-based salary management process with a web-based system that allows the HR team to manage compensation data for 10,000 employees across multiple countries, and answer analytical questions about how the organization pays people — including AI-powered natural language queries.

---

## Scope & Features

### In Scope

**Employee & Compensation Management**
- Full employee records: personal info, department, country, job title, pay grade
- Complete compensation model: base salary, bonuses, equity grants, allowances, deductions
- Salary history (append-only records — no data loss)
- Soft delete (deactivate employees, never hard delete)

**Taxation & Payroll Rules**
- Country-specific tax rules with progressive bracket support
- Provident Fund (PF) rules per country (employee + employer contribution rates, salary cap)
- Generated salary slips stored permanently for audit trail
- Computed take-home salary: gross → taxable income → tax → PF → net

**Analytics & AI Query**
- Dashboard: KPI cards, salary distribution, avg by department/country, headcount by pay grade
- Structured filters: country, department, pay grade, employment type, salary range
- AI-powered natural language Q&A (hybrid tool calling + text-to-SQL fallback)
- AI responses include structured data + chart type hint for frontend rendering

**Role-Based Access Control**
- Four roles: `admin`, `hr_manager`, `hr_analyst`, `employee`
- JWT authentication (access 30min, refresh 7d), passwords hashed with bcrypt
- Employee self-service: view own compensation and salary slips only

**Developer Readiness**
- Seed script generating 10,000 employees with realistic multi-country data
- Docker Compose for local development
- GCP deployment: Cloud Run (backend) + Firebase Hosting (frontend)

### Deliberately Out of Scope

| Feature | Reason |
|---------|--------|
| Payroll processing / payment runs | Requires payroll provider integration (Gusto, ADP) — separate system boundary |
| Multi-currency conversion / FX rates | Adds live data dependency; salaries stored in local currency with currency field |
| Leave management / attendance | Out of HR salary domain |
| Performance review workflows | Separate product surface |
| Document management (contracts, offer letters) | Storage + compliance complexity out of scope |
| Email notifications | Infrastructure overhead not required for assessment |
| Audit log / change history UI | Salary records are append-only (implicit audit); a full audit log UI is v2 |
| PDF salary slip download | Nice-to-have v2; slip data is fully accessible via API |

---

## Architecture

### Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12, FastAPI (async), SQLAlchemy 2.0 (async), Alembic |
| Database | SQLite (file-based, zero ops; swappable to PostgreSQL via `DATABASE_URL`) |
| AI | Anthropic Claude claude-sonnet-4-6 via `anthropic` SDK |
| SQL Safety | `sqlglot` for parsing + validating fallback text-to-SQL queries |
| Frontend | React 18, Vite, TypeScript, shadcn/ui (Tailwind), React Query, Recharts |
| Auth | JWT (python-jose), bcrypt (passlib) |
| Testing | pytest, pytest-asyncio, httpx (async test client) |
| Containerization | Docker, Docker Compose |
| Deployment | GCP Cloud Run (backend), Firebase Hosting (frontend), GCP Secret Manager |

---

## Data Model

### `employees`
```
id, employee_id (ACME-XXXX), first_name, last_name, email,
department, job_title, pay_grade_id (FK), country (ISO code),
currency, hire_date, employment_type (full-time/part-time/contractor),
status (active/inactive), created_at, updated_at
```

### `pay_grades`
```
id, grade (L1–L8), min_salary, max_salary, currency
```
Band values are stored in USD as a global reference currency. Compliance checks convert employee base salary to USD for comparison using a static FX rate stored in config (not live rates — v2 concern).

### `salary_records`
```
id, employee_id (FK), base_salary, currency,
effective_date, pay_frequency (monthly/annual),
created_at
```
Append-only. Latest record = current salary.

### `bonuses`
```
id, employee_id (FK), amount, currency,
bonus_type (annual/spot/signing/performance),
awarded_date, notes
```

### `equity_grants`
```
id, employee_id (FK), grant_type (RSU/options),
shares, grant_date, vest_start_date,
cliff_months, vest_months
```

### `allowances`
```
id, employee_id (FK), allowance_type (housing/transport/meal/phone),
amount, currency, frequency (monthly/annual)
```

### `deductions`
```
id, employee_id (FK), deduction_type (health_insurance/pension/other),
amount, is_percentage, currency, frequency
```
Manual, non-computed deductions only. Income tax and PF are never stored here — they are computed at slip generation time from `tax_rules` and `pf_rules` and stored in `salary_slips`.

### `tax_rules`
```
id, country (ISO code), rule_name, rule_type (income_tax/social_security/other),
tax_year, description, created_by (FK users), created_at
```

### `tax_brackets`
```
id, tax_rule_id (FK), min_income, max_income (null = no ceiling),
rate_pct, currency, created_at
```
Supports progressive taxation. Flat tax = single bracket (0 → null).

### `pf_rules`
```
id, country, rule_name, employee_contribution_pct,
employer_contribution_pct, applicable_salary_cap (nullable),
effective_from_date, created_by (FK users), created_at
```

### `salary_slips`
```
id, employee_id (FK), period_month, period_year,
gross_salary, taxable_income, tax_deducted,
pf_employee_contribution, pf_employer_contribution,
other_deductions, net_take_home, currency,
generated_at, generated_by (FK users)
```
Stored permanently — never recomputed. Source of truth for audit.

### `users`
```
id, email, hashed_password, role (admin/hr_manager/hr_analyst/employee),
employee_id (nullable FK, for self-service employees),
is_active, created_at
```

---

## API Endpoints

### Auth
```
POST /auth/login          → { access_token, refresh_token }
POST /auth/refresh        → { access_token }
GET  /auth/me             → current user info
```

### Employees
```
GET    /api/employees              # paginated, filterable
GET    /api/employees/{id}         # full compensation detail
POST   /api/employees              # create (hr_manager, admin)
PUT    /api/employees/{id}         # update (hr_manager, admin)
DELETE /api/employees/{id}         # soft delete (admin)
```

### Analytics
```
GET /api/analytics/summary
GET /api/analytics/by-country
GET /api/analytics/by-department
GET /api/analytics/salary-bands
```

### AI Query
```
POST /api/ai/query    # { "question": "..." }
                      # → { answer, tool_used, data, chart_type }
```

### Tax Rules (hr_manager, admin)
```
GET/POST     /api/tax-rules
GET/PUT      /api/tax-rules/{id}
GET          /api/tax-rules/country/{country_code}
```

### PF Rules (hr_manager, admin)
```
GET/POST     /api/pf-rules
GET/PUT      /api/pf-rules/{id}
GET          /api/pf-rules/country/{country_code}
```

### Salary Slips
```
POST /api/employees/{id}/salary-slips/generate   # hr_manager, admin
GET  /api/employees/{id}/salary-slips            # hr_manager, admin, hr_analyst, own employee
GET  /api/employees/{id}/salary-slips/{year}/{month}
```

### Meta
```
GET /api/meta/departments
GET /api/meta/countries
```

### Admin
```
GET/POST     /api/admin/users         # admin only
PUT          /api/admin/users/{id}    # activate/deactivate, change role
```

---

## RBAC Matrix

| Action | admin | hr_manager | hr_analyst | employee |
|--------|-------|-----------|-----------|---------|
| Create/edit employees | ✓ | ✓ | | |
| View all employees | ✓ | ✓ | ✓ | |
| View own profile | ✓ | ✓ | ✓ | ✓ |
| Soft delete employee | ✓ | | | |
| View analytics | ✓ | ✓ | ✓ | |
| AI query | ✓ | ✓ | ✓ | |
| Add/edit tax rules | ✓ | ✓ | | |
| Add/edit PF rules | ✓ | ✓ | | |
| Generate salary slips | ✓ | ✓ | | |
| View any salary slip | ✓ | ✓ | ✓ | |
| View own salary slip | ✓ | ✓ | ✓ | ✓ |
| Manage users | ✓ | | | |

---

## LLM Integration (Hybrid Tool Calling)

**Model:** `claude-sonnet-4-6`

**Predefined tools (fast, deterministic, token-efficient):**
- `get_salary_stats(filters)` → avg, median, min, max, p25, p75
- `get_headcount(group_by, filters)` → count per group
- `get_top_earners(n, metric, filters)` → top N by base or total comp
- `get_salary_distribution(bucket_size, filters)` → histogram buckets
- `get_budget_by_department(include_bonuses, include_equity)` → spend per dept
- `get_pay_band_compliance(department, country)` → in/above/below band counts
- `get_compensation_breakdown(employee_id)` → full breakdown for one employee
- `run_analytics_query(question)` → text-to-SQL fallback (read-only, validated)

**Request flow:**
1. User submits question
2. System prompt sent with tool definitions only (~400 tokens)
3. Claude selects tool(s) + parameters
4. Executor calls analytics_service function(s)
5. Claude synthesizes data into natural language answer
6. Response: `{ answer, tool_used, data, chart_type }`

**Safety (fallback tool):**
- Read-only SQLite connection (`uri=True&mode=ro`)
- SQL parsed with `sqlglot` — any non-SELECT statement rejected before execution
- Schema context pruned to table names + columns only (no sample data)

**`chart_type` values:** `table | bar | pie | line | none`

---

## Take-Home Salary Calculation

```
gross_monthly = base_salary_monthly + sum(allowances_monthly)
pf_applicable_salary = min(gross_monthly, pf_salary_cap or gross_monthly)
pf_employee = pf_applicable_salary × employee_contribution_pct
pf_employer = pf_applicable_salary × employer_contribution_pct
taxable_income = gross_monthly - pf_employee - pre_tax_deductions
tax = apply_progressive_brackets(taxable_income × 12, country_brackets) / 12
net_take_home = gross_monthly - pf_employee - tax - other_post_tax_deductions
```

Salary slips are generated on demand and stored — never recomputed from live rules.

---

## Frontend Views

| Route | Access | Description |
|-------|--------|-------------|
| `/login` | public | Email + password |
| `/` | hr+analyst | Dashboard: KPIs, charts |
| `/employees` | hr+analyst | Paginated table + filters |
| `/employees/:id` | hr+analyst | Full compensation detail + slip generation |
| `/insights` | hr+analyst | AI query chat interface |
| `/admin/tax-rules` | hr_manager, admin | Tax rule + bracket management |
| `/admin/pf-rules` | hr_manager, admin | PF rule management |
| `/admin/users` | admin | User management |
| `/my/salary-slips` | employee | Own slip history |

Auth: JWT stored in `httpOnly` cookie (XSS-safe). React Query for server state caching.

---

## Testing Strategy

**Backend (pytest + pytest-asyncio):**
- `conftest.py` — in-memory SQLite DB, seeded fixtures, async test client
- `test_employees.py` — CRUD, pagination, filters, soft delete
- `test_analytics.py` — each predefined tool function with known fixture data
- `test_payroll.py` — tax bracket application, PF calculation, net take-home
- `test_ai_tools.py` — tool executor dispatch, SQL safety validator
- `test_auth.py` — login, JWT, role enforcement (403 on wrong role)

**Principles:**
- Tests hit real in-memory SQLite — no DB mocking
- LLM calls mocked — deterministic, no API cost in CI
- Each test is self-contained with its own fixture data

---

## Deployment

**Local:**
```
docker-compose up   # backend :8000, frontend :5173
```

**GCP:**
- Backend → Cloud Run (containerized, scales to zero)
- Frontend → Firebase Hosting (static SPA)
- SQLite → Cloud Run persistent volume (swappable to Cloud SQL via `DATABASE_URL`)
- Secrets → GCP Secret Manager

---

## Project Structure

```
product-recommender/
  backend/
    app/
      api/
        employees.py
        analytics.py
        ai.py
        tax_rules.py
        pf_rules.py
        salary_slips.py
        auth.py
        admin.py
        meta.py
      core/
        config.py
        database.py
      models/
      schemas/
      services/
        employee_service.py
        analytics_service.py
        payroll_service.py
        ai_service.py
      tools/
        definitions.py
        executor.py
      auth/
        router.py
        dependencies.py
        utils.py
    alembic/
    seed.py
    tests/
  frontend/
    src/
      pages/
        Dashboard.tsx
        Employees.tsx
        EmployeeDetail.tsx
        Insights.tsx
        SalarySlips.tsx
        admin/
          TaxRules.tsx
          PFRules.tsx
          Users.tsx
      components/
      hooks/
      lib/
        api.ts
        auth.ts
  docker-compose.yml
  docs/
```
