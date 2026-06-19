# ACME HR — Employee Salary Management

A full-stack HR platform for managing employees, running payroll, and generating salary slips. Built with FastAPI + SQLite on the backend and React + Tailwind on the frontend.

---

## Features

| Feature | Description |
|---|---|
| Employee management | Add, view, and manage employee profiles and compensation |
| Salary slip generation | Bulk-generate monthly salary slips with PF and tax deductions |
| PDF payslip download | Download individual salary slips as formatted PDFs |
| Tax rule management | Configure country-specific tax brackets per year |
| PF rule management | Configure provident fund contribution rates and caps |
| Net salary calculator | Estimate take-home pay using live tax and PF rules |
| Bank details | Store and manage employee bank accounts |
| Yearly tax statement | View annual tax summary per employee |
| AI Insights | Chat with an AI assistant over your HR data |
| User management | Role-based access with admin, HR manager, HR analyst, and employee roles |
| Analytics | Headcount and payroll cost overview |

---

## Tech Stack

**Backend**
- Python 3.11+, FastAPI, SQLAlchemy (async), SQLite, Alembic
- JWT authentication (python-jose + argon2)
- PDF generation (fpdf2)
- AI layer: Anthropic Claude, ChromaDB, Langfuse, sentence-transformers

**Frontend**
- React 18, TypeScript, Vite
- Tailwind CSS v3, shadcn/ui on @base-ui/react
- react-query, react-router-dom, axios

---

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- macOS (the `start.sh` script uses `osascript` to open a new terminal window)

### 1. Clone the repository

```bash
git clone git@github.com:XephorNova/employee-management-kata.git
cd employee-management-kata
```

### 2. Backend setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Frontend setup

```bash
cd frontend
npm install
```

### 4. Run the app

From the project root:

```bash
./start.sh
```

This starts the backend on `http://localhost:8000` and opens the frontend in a new terminal window on `http://localhost:5173`.

Or start them separately:

```bash
# Backend
cd backend && source .venv/bin/activate && uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend && npm run dev
```

### 5. Seed data

```bash
cd backend
source .venv/bin/activate
python seed.py                # employees, compensation, salary slips
python seed_tax_rules.py      # country tax brackets
python seed_bank_details.py   # employee bank accounts
```

---

## Default Credentials

| Role | Email | Password |
|---|---|---|
| Admin | admin@acme.com | Admin123! |
| HR Manager | hr@acme.com | Admin123! |

---

## Project Structure

```
.
├── backend/
│   ├── app/
│   │   ├── api/          # Route handlers (employees, payroll, calculator, AI, …)
│   │   ├── models/       # SQLAlchemy ORM models
│   │   ├── schemas/      # Pydantic request/response schemas
│   │   ├── services/     # Business logic (payroll computation, PDF generation)
│   │   └── core/         # Database, settings, auth
│   ├── tests/            # pytest integration tests
│   ├── seed.py
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── pages/        # Route-level components (Dashboard, Employees, Calculator, …)
│       ├── components/   # Shared UI components
│       ├── lib/          # API client and type definitions
│       └── context/      # Auth context
├── docs/
│   └── superpowers/      # Feature specs and implementation plans
└── start.sh
```

---

## API Docs

Interactive Swagger UI is available at `http://localhost:8000/docs` when the backend is running.

---

## Running Tests

```bash
cd backend
source .venv/bin/activate
pytest
```
