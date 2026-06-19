# Net Salary Calculator — Design Spec

**Goal:** Add a standalone calculator page where any authenticated user can enter a gross salary and see their estimated net take-home after PF and tax deductions, using the real rules already in the database.

**Architecture:** A single new backend endpoint calls the existing `compute_take_home` function from `payroll_service.py`. The frontend is a two-column form + results card. No new math logic — everything reuses what already powers salary slip generation.

**Tech Stack:** FastAPI (new router), SQLAlchemy async (rule lookups), Pydantic (schemas), React + react-query (frontend), Tailwind + shadcn/ui components.

---

## API

### `POST /api/calculator/calculate`

**Auth:** Any authenticated user (`any_authenticated` dependency).

**Request schema (`CalculatorRequest`):**
```json
{
  "country": "USA",
  "base_salary": 8000.00,
  "pay_frequency": "monthly",
  "allowances": 500.00,
  "other_deductions": 200.00
}
```

- `pay_frequency`: `"monthly"` or `"annual"`. If `"annual"`, divide `base_salary` by 12 before passing to `compute_take_home`.
- `allowances` and `other_deductions` are always monthly amounts; default to `0.0` if omitted.

**Response schema (`CalculatorResponse`):**
```json
{
  "gross_salary": 8500.00,
  "pf_employee_contribution": 480.00,
  "pf_employer_contribution": 480.00,
  "tax_deducted": 1200.00,
  "other_deductions": 200.00,
  "net_take_home": 6620.00,
  "currency": "USD",
  "tax_rule_applied": "US Federal Income Tax 2024",
  "pf_rule_applied": "US 401k Rule",
  "no_rules_warning": false
}
```

- `tax_rule_applied` / `pf_rule_applied`: name of the matched rule, or `null` if none found.
- `no_rules_warning`: `true` when neither PF nor tax rules exist for the country — frontend shows a warning banner.
- `currency`: taken from the PF rule's country context; defaults to `"USD"` if no rules found.

**Internal logic (mirrors `generate_salary_slip`):**
1. Fetch latest PF rule for `country` (order by `effective_from_date DESC LIMIT 1`). If none, use 0% rates and no cap.
2. Fetch latest tax rule for `country` (order by `tax_year DESC LIMIT 1`) with brackets. If none, use empty brackets.
3. Convert `base_salary` to monthly if `pay_frequency == "annual"`.
4. Call `compute_take_home(base_monthly, allowances, pf_employee_pct, pf_employer_pct, pf_cap, brackets, other_deductions)`.
5. Return response.

**New files:**
- `backend/app/api/calculator.py` — router + endpoint
- `backend/app/schemas/calculator.py` — `CalculatorRequest`, `CalculatorResponse`

**Modified files:**
- `backend/app/main.py` — register the new router

---

## Frontend

### Page: `frontend/src/pages/Calculator.tsx`

Route: `/calculator`. Accessible to all roles — no role gate.

**Layout:** Single `Card` with two-column grid (stacks to one column on mobile).

**Left column — Inputs:**
| Field | Type | Notes |
|---|---|---|
| Country | Text input | ISO 3-letter code, e.g. `USA`, `IND` |
| Base Salary | Number input | Amount in the entered currency |
| Pay Frequency | Toggle buttons | `Monthly` / `Annual` |
| Allowances | Number input | Monthly amount, optional (default 0) |
| Other Deductions | Number input | Monthly amount, optional (default 0) |

"Calculate" button below the form. Disabled when country or base salary is empty.

**Right column — Results (hidden until first successful calculation):**
- Headline: **Net Take-Home: $6,620 / mo** (formatted with `Intl.NumberFormat`)
- Breakdown table:

| | Amount |
|---|---|
| Gross Salary | $8,500 |
| − PF (Employee) | $480 |
| − Income Tax | $1,200 |
| − Other Deductions | $200 |
| **= Net Take-Home** | **$6,620** |

- Employer PF shown as a separate info line below the table (not a deduction from net): "Your employer contributes an additional $480 to your PF."
- If `no_rules_warning: true`: amber warning banner — "No tax or PF rules found for [country] — result shows gross only."

**State management:** `useMutation` from react-query posts to `/api/calculator/calculate`. Results replace the right panel on success. Error shown inline below the Calculate button.

**New API call in `frontend/src/lib/api.ts`:**
```typescript
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

**Modified files:**
- `frontend/src/lib/api.ts` — add `CalculatorRequest`, `CalculatorResponse` types and `calculateNetSalary`
- `frontend/src/router.tsx` — add `<Route path="/calculator" element={<Calculator />} />`
- `frontend/src/components/Layout.tsx` — add nav entry `{ href: "/calculator", label: "Calculator", icon: Calculator, roles: ["admin", "hr_manager", "hr_analyst", "employee"] }` and import `Calculator` icon from lucide-react; add `"/calculator": "Net Salary Calculator"` to `routeTitles`

---

## Error Handling

| Scenario | Behaviour |
|---|---|
| Country empty or base salary ≤ 0 | Calculate button disabled; no request sent |
| No PF/tax rules for country | 200 response with `no_rules_warning: true`; frontend shows amber banner |
| Network/server error | Inline red error message below Calculate button |

---

## Testing

**`backend/tests/test_calculator.py`** — two tests:

1. **`test_calculate_with_rules`** — seeds one `TaxRule` (with brackets) and one `PFRule` for country `"TST"`, posts `{ country: "TST", base_salary: 5000, pay_frequency: "monthly", allowances: 0, other_deductions: 0 }`. Asserts:
   - `status_code == 200`
   - `net_take_home < gross_salary`
   - `pf_employee_contribution > 0`
   - `tax_deducted > 0`
   - `no_rules_warning == false`

2. **`test_calculate_no_rules`** — posts `{ country: "ZZZ", base_salary: 5000, pay_frequency: "monthly", allowances: 0, other_deductions: 0 }` (no rules seeded). Asserts:
   - `status_code == 200`
   - `net_take_home == gross_salary`
   - `pf_employee_contribution == 0`
   - `tax_deducted == 0`
   - `no_rules_warning == true`
