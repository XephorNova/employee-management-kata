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
    # Compression disabled so PDF stream bytes are human-readable and testable with raw byte assertions.
    pdf.set_compression(False)
    pdf.add_page()

    # ── Header ────────────────────────────────────────────────────────────
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 8, "ACME HR", new_x="LMARGIN", new_y="NEXT")
    generated_on = (slip.generated_at or datetime.now(timezone.utc)).strftime("%d %b %Y")
    pdf.set_font("Helvetica", "", 9)
    pdf.set_y(pdf.get_y() - 8)
    pdf.cell(0, 8, generated_on, align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(160, 160, 160)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.l_margin + pdf.epw, pdf.get_y())
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
    title = employee.job_title if len(employee.job_title) <= 40 else employee.job_title[:39] + "..."
    pdf.cell(half, 6, f"Job Title : {title}", new_x="LMARGIN", new_y="NEXT")
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
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.l_margin + pdf.epw, pdf.get_y())
    pdf.ln(2)
    pdf.set_font("Helvetica", "", 8)
    ts = slip.generated_at.strftime("%d %b %Y %H:%M UTC") if slip.generated_at else "-"
    pdf.cell(0, 5, f"Generated at: {ts}", new_x="LMARGIN", new_y="NEXT")

    return bytes(pdf.output())
