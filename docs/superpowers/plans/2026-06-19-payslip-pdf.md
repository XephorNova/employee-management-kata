# Payslip PDF Download — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a server-side PDF download endpoint for salary slips, with Download PDF buttons in both the employee self-service view and the HR employee detail view.

**Architecture:** A new `pdf_service.py` generates a PDF from an existing `SalarySlip` + `Employee` ORM pair using `fpdf2`. A new `GET /api/employees/{id}/salary-slips/{year}/{month}/pdf` endpoint calls it and streams the bytes back. The frontend fetches the binary blob and triggers a browser file download.

**Tech Stack:** Python `fpdf2`, FastAPI `StreamingResponse`, React + axios blob download

---

## File Map

| Action | Path | Responsibility |
|--------|------|---------------|
| Create | `backend/app/services/pdf_service.py` | Pure function: SalarySlip + Employee → PDF bytes |
| Create | `backend/tests/test_pdf_service.py` | Unit tests for pdf_service |
| Modify | `backend/app/api/salary_slips.py` | Add `GET /{year}/{month}/pdf` endpoint |
| Modify | `backend/requirements.txt` | Add `fpdf2` |
| Modify | `frontend/src/lib/api.ts` | Add `downloadSlipPdf()` |
| Modify | `frontend/src/pages/SalarySlips.tsx` | Add Download PDF button per row |
| Modify | `frontend/src/pages/EmployeeDetail.tsx` | Add Download PDF button per row |

---

## Task 1: Install fpdf2

**Files:**
- Modify: `backend/requirements.txt`

- [ ] **Step 1: Add fpdf2 to requirements.txt**

Open `backend/requirements.txt` and add this line at the end:
```
fpdf2==2.8.3
```

- [ ] **Step 2: Install it**

```bash
cd backend && source .venv/bin/activate && pip install fpdf2==2.8.3
```

Expected: `Successfully installed fpdf2-2.8.3` (or already satisfied).

- [ ] **Step 3: Verify import works**

```bash
python -c "from fpdf import FPDF; print('fpdf2 OK')"
```

Expected output: `fpdf2 OK`

- [ ] **Step 4: Commit**

```bash
git add backend/requirements.txt
git commit -m "chore: add fpdf2 dependency for PDF generation"
```

---

## Task 2: PDF generation service

**Files:**
- Create: `backend/app/services/pdf_service.py`
- Create: `backend/tests/test_pdf_service.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_pdf_service.py`:

```python
from datetime import date, datetime
from decimal import Decimal
from app.services.pdf_service import generate_salary_slip_pdf
from app.models.payroll import SalarySlip
from app.models.employee import Employee, EmploymentType


def _slip() -> SalarySlip:
    s = SalarySlip.__new__(SalarySlip)
    s.employee_id = 1
    s.period_month = 6
    s.period_year = 2025
    s.gross_salary = Decimal("8000.00")
    s.taxable_income = Decimal("7100.00")
    s.tax_deducted = Decimal("1003.33")
    s.pf_employee_contribution = Decimal("900.00")
    s.pf_employer_contribution = Decimal("900.00")
    s.other_deductions = Decimal("200.00")
    s.net_take_home = Decimal("5896.67")
    s.currency = "USD"
    s.generated_at = datetime(2025, 6, 19, 10, 0, 0)
    s.generated_by = 1
    return s


def _employee() -> Employee:
    e = Employee.__new__(Employee)
    e.id = 1
    e.employee_id = "ACME-00001"
    e.first_name = "Alice"
    e.last_name = "Lee"
    e.email = "alice@acme.com"
    e.department = "Engineering"
    e.job_title = "Software Engineer"
    e.country = "US"
    e.currency = "USD"
    e.hire_date = date(2022, 1, 1)
    e.employment_type = EmploymentType.full_time
    return e


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
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd backend && source .venv/bin/activate && pytest tests/test_pdf_service.py -v
```

Expected: 4 failures with `ImportError: cannot import name 'generate_salary_slip_pdf'`

- [ ] **Step 3: Implement pdf_service.py**

Create `backend/app/services/pdf_service.py`:

```python
from datetime import datetime, timezone
from fpdf import FPDF
from app.models.payroll import SalarySlip
from app.models.employee import Employee

_MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


def generate_salary_slip_pdf(slip: SalarySlip, employee: Employee) -> bytes:
    pdf = FPDF()
    pdf.set_margins(15, 15, 15)
    pdf.add_page()

    # ── Header ────────────────────────────────────────────────────────────
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 8, "ACME HR", new_x="LMARGIN", new_y="NEXT")
    generated_on = datetime.now(timezone.utc).strftime("%d %b %Y")
    pdf.set_font("Helvetica", "", 9)
    pdf.set_y(pdf.get_y() - 8)
    pdf.cell(0, 8, generated_on, align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(160, 160, 160)
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.ln(3)

    # ── Title ─────────────────────────────────────────────────────────────
    period = f"{_MONTHS[slip.period_month - 1]} {slip.period_year}"
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, f"SALARY SLIP  -  {period}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    # ── Employee info ─────────────────────────────────────────────────────
    pdf.set_font("Helvetica", "", 10)
    half = 90
    name = f"{employee.first_name} {employee.last_name}"
    pdf.cell(half, 6, f"Employee : {name}")
    pdf.cell(half, 6, f"ID : {employee.employee_id}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(half, 6, f"Department : {employee.department}")
    pdf.cell(half, 6, f"Country : {employee.country}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(half, 6, f"Currency : {slip.currency}")
    pdf.cell(half, 6, f"Job Title : {employee.job_title[:40]}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    # ── Table helpers ─────────────────────────────────────────────────────
    label_w, amount_w = 130, 50

    def section_header(title: str) -> None:
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_fill_color(230, 230, 230)
        pdf.cell(label_w, 7, title, border=1, fill=True)
        pdf.cell(amount_w, 7, "Amount", border=1, fill=True, align="R",
                 new_x="LMARGIN", new_y="NEXT")

    def data_row(label: str, amount: float) -> None:
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(label_w, 7, label, border=1)
        pdf.cell(amount_w, 7, f"{amount:,.2f}", border=1, align="R",
                 new_x="LMARGIN", new_y="NEXT")

    # ── Earnings ──────────────────────────────────────────────────────────
    section_header("EARNINGS")
    data_row("Gross Salary", float(slip.gross_salary))
    pdf.ln(4)

    # ── Deductions ────────────────────────────────────────────────────────
    section_header("DEDUCTIONS")
    data_row("PF (Employee Contribution)", float(slip.pf_employee_contribution))
    data_row("Income Tax Deducted", float(slip.tax_deducted))
    data_row("Other Deductions", float(slip.other_deductions))
    pdf.ln(4)

    # ── Net take-home ─────────────────────────────────────────────────────
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_fill_color(220, 235, 255)
    pdf.cell(label_w, 8, "NET TAKE-HOME", border=1, fill=True)
    pdf.cell(amount_w, 8, f"{float(slip.net_take_home):,.2f}", border=1,
             fill=True, align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)

    # ── Footer ────────────────────────────────────────────────────────────
    pdf.set_draw_color(160, 160, 160)
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.ln(2)
    pdf.set_font("Helvetica", "", 8)
    ts = slip.generated_at.strftime("%d %b %Y %H:%M UTC") if slip.generated_at else "-"
    pdf.cell(0, 5, f"Generated at: {ts}", new_x="LMARGIN", new_y="NEXT")

    return bytes(pdf.output())
```

- [ ] **Step 4: Run tests — all must pass**

```bash
cd backend && source .venv/bin/activate && pytest tests/test_pdf_service.py -v
```

Expected:
```
tests/test_pdf_service.py::test_returns_pdf_bytes PASSED
tests/test_pdf_service.py::test_pdf_contains_employee_name PASSED
tests/test_pdf_service.py::test_pdf_contains_period PASSED
tests/test_pdf_service.py::test_pdf_contains_net_amount PASSED
4 passed
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/pdf_service.py backend/tests/test_pdf_service.py
git commit -m "feat: add PDF generation service using fpdf2"
```

---

## Task 3: PDF download endpoint

**Files:**
- Modify: `backend/app/api/salary_slips.py`
- Modify: `backend/tests/test_payroll.py` (add PDF download test)

- [ ] **Step 1: Write failing integration test**

Add this test to the bottom of `backend/tests/test_payroll.py`:

```python
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
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd backend && source .venv/bin/activate && pytest tests/test_payroll.py::test_download_slip_pdf tests/test_payroll.py::test_download_slip_pdf_not_found -v
```

Expected: `404 Not Found` response for the PDF route (route doesn't exist yet).

- [ ] **Step 3: Add the endpoint to salary_slips.py**

Add these imports at the top of `backend/app/api/salary_slips.py` (after existing imports):

```python
from io import BytesIO
from fastapi.responses import StreamingResponse
```

Add this route to `router` in `backend/app/api/salary_slips.py`, after the existing `get_slip` route:

```python
@router.get("/{year}/{month}/pdf")
async def download_slip_pdf(
    employee_id: int,
    year: int,
    month: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.models.employee import Employee
    from app.services.pdf_service import generate_salary_slip_pdf

    if current_user.role == UserRole.employee and current_user.employee_id != employee_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    r = await db.execute(
        select(SalarySlip).where(
            SalarySlip.employee_id == employee_id,
            SalarySlip.period_year == year,
            SalarySlip.period_month == month,
        )
    )
    slip = r.scalar_one_or_none()
    if not slip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Salary slip not found")

    employee = await db.get(Employee, employee_id)
    if not employee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")

    pdf_bytes = generate_salary_slip_pdf(slip, employee)
    filename = f"slip_{employee_id}_{year}_{month:02d}.pdf"
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
```

- [ ] **Step 4: Run all payroll tests — all must pass**

```bash
cd backend && source .venv/bin/activate && pytest tests/test_payroll.py -v
```

Expected: all tests pass including the two new ones.

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/salary_slips.py backend/tests/test_payroll.py
git commit -m "feat: add GET /salary-slips/{year}/{month}/pdf endpoint"
```

---

## Task 4: Frontend — downloadSlipPdf API function

**Files:**
- Modify: `frontend/src/lib/api.ts`

- [ ] **Step 1: Add downloadSlipPdf to api.ts**

In `frontend/src/lib/api.ts`, add after the `getTaxStatement` export (around line 111):

```ts
export async function downloadSlipPdf(
  employeeId: number,
  year: number,
  month: number,
): Promise<void> {
  const response = await api.get(
    `/api/employees/${employeeId}/salary-slips/${year}/${month}/pdf`,
    { responseType: "blob" },
  );
  const url = URL.createObjectURL(
    new Blob([response.data], { type: "application/pdf" }),
  );
  const a = document.createElement("a");
  a.href = url;
  a.download = `slip_${employeeId}_${year}_${String(month).padStart(2, "0")}.pdf`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npm run build 2>&1 | tail -5
```

Expected: build succeeds (or only pre-existing warnings, no new errors).

- [ ] **Step 3: Commit**

```bash
git add frontend/src/lib/api.ts
git commit -m "feat: add downloadSlipPdf API helper"
```

---

## Task 5: Download PDF button — SalarySlips page (employee view)

**Files:**
- Modify: `frontend/src/pages/SalarySlips.tsx`

Context: In `SalarySlips.tsx`, the slip history table is inside the `SalarySlips` default export function. The table columns are Period, Gross, PF, Tax, Net Take-Home. We add a final column with a per-row download button.

- [ ] **Step 1: Add import and state to SalarySlips.tsx**

At the top of `frontend/src/pages/SalarySlips.tsx`, add `downloadSlipPdf` to the imports from `@/lib/api`:

```ts
import {
  listSalarySlips, listBankDetails, createBankDetail, updateBankDetail,
  deleteBankDetail, getTaxStatement, downloadSlipPdf,
} from "@/lib/api";
```

- [ ] **Step 2: Add downloadingId state inside SalarySlips component**

Inside the `SalarySlips` function body (after the `slips` query), add:

```tsx
const [downloadingId, setDownloadingId] = useState<number | null>(null);

async function handleDownload(s: { id: number; period_year: number; period_month: number }) {
  setDownloadingId(s.id);
  try {
    await downloadSlipPdf(user!.employee_id!, s.period_year, s.period_month);
  } finally {
    setDownloadingId(null);
  }
}
```

- [ ] **Step 3: Add table header and button cell**

Replace the existing `<TableHeader>` in the slip history table:

```tsx
<TableHeader>
  <TableRow>
    <TableHead>Period</TableHead>
    <TableHead>Gross</TableHead>
    <TableHead>PF</TableHead>
    <TableHead>Tax</TableHead>
    <TableHead>Net Take-Home</TableHead>
    <TableHead></TableHead>
  </TableRow>
</TableHeader>
```

Replace the existing `<TableRow>` inside `slips.map(...)`:

```tsx
{slips.map((s: { id: number; period_month: number; period_year: number; gross_salary: number; pf_employee_contribution: number; tax_deducted: number; net_take_home: number; currency: string }) => (
  <TableRow key={s.id}>
    <TableCell>{s.period_month}/{s.period_year}</TableCell>
    <TableCell>{fmt(s.gross_salary, s.currency)}</TableCell>
    <TableCell>{fmt(s.pf_employee_contribution, s.currency)}</TableCell>
    <TableCell>{fmt(s.tax_deducted, s.currency)}</TableCell>
    <TableCell className="font-bold">{fmt(s.net_take_home, s.currency)}</TableCell>
    <TableCell>
      <Button
        size="sm"
        variant="outline"
        disabled={downloadingId === s.id}
        onClick={() => handleDownload(s)}
      >
        {downloadingId === s.id ? "…" : "Download PDF"}
      </Button>
    </TableCell>
  </TableRow>
))}
```

- [ ] **Step 4: Verify TypeScript compiles**

```bash
cd frontend && npm run build 2>&1 | tail -5
```

Expected: build succeeds with no new errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/SalarySlips.tsx
git commit -m "feat: add Download PDF button to employee salary slips page"
```

---

## Task 6: Download PDF button — EmployeeDetail page (HR view)

**Files:**
- Modify: `frontend/src/pages/EmployeeDetail.tsx`

Context: In `EmployeeDetail.tsx`, the salary slips table is around line 418-431. The columns are Period, Gross, Tax, Net. The `empId` variable is available from `useParams`. Add `downloadSlipPdf` import, `downloadingId` state, a handler, and a button column.

- [ ] **Step 1: Add downloadSlipPdf import**

In `frontend/src/pages/EmployeeDetail.tsx`, find the existing import from `@/lib/api` (line 5-7) and add `downloadSlipPdf`:

```ts
import {
  getEmployee, listSalaryRecords, listBonuses, listAllowances, generateSalarySlip,
  listSalarySlips, listBankDetails, createBankDetail, updateBankDetail,
  deleteBankDetail, getTaxStatement, downloadSlipPdf,
} from "@/lib/api";
```

- [ ] **Step 2: Add downloadingId state near the slips query**

Find where `const { data: slips }` is declared (around line 331) and add after it:

```tsx
const [downloadingId, setDownloadingId] = useState<number | null>(null);

async function handleDownload(s: { id: number; period_year: number; period_month: number }) {
  setDownloadingId(s.id);
  try {
    await downloadSlipPdf(empId, s.period_year, s.period_month);
  } finally {
    setDownloadingId(null);
  }
}
```

- [ ] **Step 3: Add table header and button cell**

Find the salary slips `<TableHeader>` (around line 419) and replace it:

```tsx
<TableHeader>
  <TableRow>
    <TableHead>Period</TableHead>
    <TableHead>Gross</TableHead>
    <TableHead>Tax</TableHead>
    <TableHead>Net</TableHead>
    <TableHead></TableHead>
  </TableRow>
</TableHeader>
```

Replace the `slips.map(...)` TableRow (around line 421-427):

```tsx
{slips.map((s: { id: number; period_month: number; period_year: number; gross_salary: number; tax_deducted: number; net_take_home: number; currency: string }) => (
  <TableRow key={s.id}>
    <TableCell>{s.period_month}/{s.period_year}</TableCell>
    <TableCell>{fmt(s.gross_salary, s.currency)}</TableCell>
    <TableCell>{fmt(s.tax_deducted, s.currency)}</TableCell>
    <TableCell className="font-medium">{fmt(s.net_take_home, s.currency)}</TableCell>
    <TableCell>
      <Button
        size="sm"
        variant="outline"
        disabled={downloadingId === s.id}
        onClick={() => handleDownload(s)}
      >
        {downloadingId === s.id ? "…" : "Download PDF"}
      </Button>
    </TableCell>
  </TableRow>
))}
```

- [ ] **Step 4: Verify TypeScript compiles**

```bash
cd frontend && npm run build 2>&1 | tail -5
```

Expected: build succeeds with no new errors.

- [ ] **Step 5: Run all backend tests to confirm nothing broke**

```bash
cd backend && source .venv/bin/activate && pytest --tb=short -q
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/EmployeeDetail.tsx
git commit -m "feat: add Download PDF button to HR employee detail salary slips"
```

---

## Done

After all tasks complete, verify manually:
1. Start the app: `cd backend && uvicorn app.main:app --reload` + `cd frontend && npm run dev`
2. Log in as `admin@acme.com` / `Admin123!`
3. Go to an employee's detail page → Salary Slips section → click **Download PDF**
4. Confirm a PDF file downloads and opens correctly in a PDF viewer
5. Log in as an employee (if one exists with `employee` role) → My Salary Slips → click **Download PDF**
