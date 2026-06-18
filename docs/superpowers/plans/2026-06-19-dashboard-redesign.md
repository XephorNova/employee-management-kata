# Dashboard & Layout Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the ACME HR frontend with a dark navy sidebar (icons + labels), white top bar, KPI stat cards with coloured accent icons, a quick-actions right panel on the Dashboard, and indigo primary colour applied to all buttons/form inputs sitewide.

**Architecture:** Five targeted file changes — update CSS tokens in `index.css`, extract a reusable `StatCard`, create `RightPanel` (with Generate Slips modal), overhaul `Layout.tsx` (sidebar + top bar), and rewrite `Dashboard.tsx` to compose the new components. Inner pages (Employees, Insights, admin pages, SalarySlips) are untouched; they inherit the new chrome from Layout automatically.

**Tech Stack:** React 18, TypeScript, Tailwind CSS, shadcn/ui (Button, Card, Dialog, Input, Label), Recharts, Lucide React, React Router v6, @tanstack/react-query

---

## File Map

| Action | File | Responsibility |
|---|---|---|
| Modify | `frontend/src/index.css` | Update `--ring` CSS variable to indigo so input focus rings match buttons |
| Create | `frontend/src/components/StatCard.tsx` | Reusable KPI card: value, label, coloured icon square, optional change line |
| Create | `frontend/src/components/RightPanel.tsx` | Quick-action buttons, Generate Slips modal, employee count badge, system status |
| Modify | `frontend/src/components/Layout.tsx` | Dark sidebar with Lucide icons + labels, nav section divider, white top bar, user footer |
| Modify | `frontend/src/pages/Dashboard.tsx` | 4 KPI cards, chart grid, flex layout including RightPanel |

---

## Task 1: Update CSS ring token

**Files:**
- Modify: `frontend/src/index.css`

The `--ring` CSS variable controls the focus ring on shadcn Input, Select, Checkbox, etc. It is currently grey (`oklch(0.708 0 0)`). Changing it to match `--primary` (indigo-600) makes all form focus rings indigo. `--primary` is already indigo (`oklch(0.511 0.262 276.966)`) so no primary change is needed.

- [ ] **Step 1: Update `--ring` in `index.css`**

In `frontend/src/index.css`, find the `:root` block inside `@layer base` and change the `--ring` line:

```css
/* Before */
--ring: oklch(0.708 0 0);

/* After */
--ring: oklch(0.511 0.262 276.966);
```

The full relevant `:root` block after the change (only `--ring` changes, everything else stays):

```css
:root {
  --background: oklch(1 0 0);
  --foreground: oklch(0.145 0 0);
  --card: oklch(1 0 0);
  --card-foreground: oklch(0.145 0 0);
  --popover: oklch(1 0 0);
  --popover-foreground: oklch(0.145 0 0);
  --primary: oklch(0.511 0.262 276.966);
  --primary-foreground: oklch(0.985 0 0);
  --secondary: oklch(0.94 0.015 277);
  --secondary-foreground: oklch(0.35 0.12 277);
  --muted: oklch(0.96 0 0);
  --muted-foreground: oklch(0.42 0 0);
  --accent: oklch(0.97 0 0);
  --accent-foreground: oklch(0.205 0 0);
  --destructive: oklch(0.577 0.245 27.325);
  --destructive-foreground: 210 40% 98%;
  --border: oklch(0.922 0 0);
  --input: oklch(0.922 0 0);
  --ring: oklch(0.511 0.262 276.966);
  --radius: 0.625rem;
  /* chart and sidebar vars unchanged */
}
```

- [ ] **Step 2: Verify**

```bash
cd /Users/keval-shreya/projects/product-recommender/frontend && npm run dev
```

Navigate to `http://localhost:5173/` (or whichever port Vite uses), log in, click inside any `<Input>` field (e.g. on the Login page or Employees page). The focus ring should be indigo, not grey.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/index.css
git commit -m "style: update focus ring token to indigo primary"
```

---

## Task 2: Create StatCard component

**Files:**
- Create: `frontend/src/components/StatCard.tsx`

A self-contained card: large value, label, a coloured icon square (top-right), and an optional change line. No API calls — all data passed as props.

- [ ] **Step 1: Create `StatCard.tsx`**

```tsx
import { cn } from "@/lib/utils";

interface StatCardProps {
  label: string;
  value: string | number;
  icon: React.ReactNode;
  iconBg: string;        // Tailwind bg class, e.g. "bg-amber-100"
  change?: string;       // e.g. "↑ 12% this month"
  changeUp?: boolean;    // true → green text, false/undefined → slate
}

export default function StatCard({ label, value, icon, iconBg, change, changeUp }: StatCardProps) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-4 flex flex-col gap-3">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-2xl font-bold text-slate-900">{value}</p>
          <p className="text-sm text-slate-500 mt-0.5">{label}</p>
        </div>
        <div className={cn("w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0", iconBg)}>
          {icon}
        </div>
      </div>
      {change && (
        <p className={cn("text-xs font-medium", changeUp ? "text-green-500" : "text-slate-400")}>
          {change}
        </p>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Verify it compiles (no dev server restart needed)**

With the dev server running from Task 1, check the browser console for TypeScript errors. If the dev server isn't running:

```bash
cd /Users/keval-shreya/projects/product-recommender/frontend && npm run dev
```

The file has no imports that could fail. No page uses it yet, so no visual change is expected.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/StatCard.tsx
git commit -m "feat: add StatCard component"
```

---

## Task 3: Create RightPanel component

**Files:**
- Create: `frontend/src/components/RightPanel.tsx`

Visible only to `admin` and `hr_manager` (Dashboard renders it conditionally). Contains:
1. Current date
2. Quick Actions: "Generate Slips" (admin only, opens a Dialog), "Add Employee" (→ `/employees`), "Edit Tax Rules" (→ `/admin/tax-rules`)
3. Employee count badge (amber)
4. System status indicator

The Generate Slips modal reuses the exact logic from the old `BulkGenerateCard` in `Dashboard.tsx`.

- [ ] **Step 1: Create `RightPanel.tsx`**

```tsx
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { bulkGenerateSalarySlips } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { FileText, Plus, Pencil, AlertCircle } from "lucide-react";

interface BulkResult {
  generated: number;
  errors: { employee_id: number; error: string }[];
  total: number;
}

interface RightPanelProps {
  employeeCount?: number;
}

export default function RightPanel({ employeeCount }: RightPanelProps) {
  const navigate = useNavigate();
  const { user } = useAuth();

  const now = new Date();
  const dateStr = now.toLocaleDateString("en-GB", {
    weekday: "short",
    day: "numeric",
    month: "short",
    year: "numeric",
  });

  const nextMonth = now.getMonth() === 11 ? 1 : now.getMonth() + 2;
  const nextYear = now.getMonth() === 11 ? now.getFullYear() + 1 : now.getFullYear();

  const [dialogOpen, setDialogOpen] = useState(false);
  const [month, setMonth] = useState(nextMonth);
  const [year, setYear] = useState(nextYear);
  const [result, setResult] = useState<BulkResult | null>(null);

  const bulkMutation = useMutation({
    mutationFn: () => bulkGenerateSalarySlips(month, year),
    onSuccess: (data: BulkResult) => setResult(data),
  });

  function handleDialogChange(open: boolean) {
    setDialogOpen(open);
    if (!open) {
      setResult(null);
      bulkMutation.reset();
    }
  }

  return (
    <div className="w-56 flex-shrink-0 bg-white rounded-xl border border-slate-200 p-4 flex flex-col gap-5 overflow-y-auto self-start sticky top-0">
      {/* Date */}
      <p className="text-xs font-semibold text-slate-900 border-b border-slate-100 pb-3">
        {dateStr}
      </p>

      {/* Quick Actions */}
      <div className="flex flex-col gap-2">
        <p className="text-[10px] font-semibold uppercase tracking-widest text-slate-400 mb-1">
          Quick Actions
        </p>

        {user?.role === "admin" && (
          <Dialog open={dialogOpen} onOpenChange={handleDialogChange}>
            <DialogTrigger asChild>
              <Button size="sm" className="w-full justify-start gap-2 text-xs h-8">
                <FileText className="w-3.5 h-3.5" />
                Generate Slips
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Generate Salary Slips</DialogTitle>
              </DialogHeader>
              <div className="flex flex-col gap-4 pt-2">
                <div className="flex gap-3 items-end">
                  <div className="flex flex-col gap-1.5">
                    <Label>Month</Label>
                    <Input
                      type="number"
                      min={1}
                      max={12}
                      value={month}
                      onChange={(e) => setMonth(Number(e.target.value))}
                      className="w-20"
                    />
                  </div>
                  <div className="flex flex-col gap-1.5">
                    <Label>Year</Label>
                    <Input
                      type="number"
                      value={year}
                      onChange={(e) => setYear(Number(e.target.value))}
                      className="w-28"
                    />
                  </div>
                </div>
                <Button
                  onClick={() => { setResult(null); bulkMutation.mutate(); }}
                  disabled={bulkMutation.isPending}
                >
                  {bulkMutation.isPending ? "Generating…" : "Generate for all active employees"}
                </Button>
                {bulkMutation.isError && (
                  <p className="text-red-500 text-sm">
                    Failed to generate. Check permissions or try again.
                  </p>
                )}
                {result && (
                  <div className="text-sm space-y-1">
                    <p className="text-green-600 font-medium">
                      Generated {result.generated} of {result.total} slips.
                    </p>
                    {result.errors.length > 0 && (
                      <details>
                        <summary className="text-red-500 cursor-pointer text-xs">
                          {result.errors.length} error(s)
                        </summary>
                        <ul className="mt-1 text-slate-500 text-xs space-y-1">
                          {result.errors.map((e) => (
                            <li key={e.employee_id}>
                              #{e.employee_id}: {e.error}
                            </li>
                          ))}
                        </ul>
                      </details>
                    )}
                  </div>
                )}
              </div>
            </DialogContent>
          </Dialog>
        )}

        <Button
          variant="outline"
          size="sm"
          className="w-full justify-start gap-2 text-xs h-8"
          onClick={() => navigate("/employees")}
        >
          <Plus className="w-3.5 h-3.5" />
          Add Employee
        </Button>
        <Button
          variant="outline"
          size="sm"
          className="w-full justify-start gap-2 text-xs h-8"
          onClick={() => navigate("/admin/tax-rules")}
        >
          <Pencil className="w-3.5 h-3.5" />
          Edit Tax Rules
        </Button>
      </div>

      {/* Employee count badge */}
      {employeeCount !== undefined && (
        <div className="flex flex-col gap-2">
          <p className="text-[10px] font-semibold uppercase tracking-widest text-slate-400 mb-1">
            Active Employees
          </p>
          <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 flex items-center justify-between">
            <div>
              <p className="text-xl font-bold text-amber-600">{employeeCount}</p>
              <p className="text-xs text-amber-700 mt-0.5 leading-tight">employees on record</p>
            </div>
            <AlertCircle className="w-5 h-5 text-amber-400 flex-shrink-0" />
          </div>
        </div>
      )}

      {/* System status */}
      <div className="mt-auto flex flex-col gap-2">
        <p className="text-[10px] font-semibold uppercase tracking-widest text-slate-400 mb-1">
          System
        </p>
        <div className="flex items-center gap-2 text-xs text-slate-500">
          <span className="w-2 h-2 rounded-full bg-green-500 flex-shrink-0" />
          Backend online
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Verify it compiles**

With dev server running, check the browser console for TypeScript/import errors. Dashboard hasn't been updated to import `RightPanel` yet, so no visual change is expected.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/RightPanel.tsx
git commit -m "feat: add RightPanel with quick actions and generate slips modal"
```

---

## Task 4: Redesign Layout.tsx

**Files:**
- Modify: `frontend/src/components/Layout.tsx`

Replace the current minimal sidebar and no-top-bar layout with:
- Dark slate-900 sidebar (`w-52`), always expanded
- Lucide icon + text label per nav item
- "Admin" section divider above Tax Rules / PF Rules / Users
- Indigo left-border accent on active nav item
- White top bar (`h-14`) with page title (derived from route) on left, user email + avatar on right
- User email + role + Sign out pinned to sidebar bottom
- `bg-slate-100` page background (was `bg-slate-50`)

- [ ] **Step 1: Replace `Layout.tsx` entirely**

```tsx
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { cn } from "@/lib/utils";
import {
  LayoutDashboard,
  Users,
  MessageSquare,
  FileText,
  Briefcase,
  UserCog,
  Receipt,
  Layers,
} from "lucide-react";

const navItems = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard, roles: ["admin", "hr_manager", "hr_analyst"] },
  { href: "/employees", label: "Employees", icon: Users, roles: ["admin", "hr_manager", "hr_analyst"] },
  { href: "/insights", label: "AI Insights", icon: MessageSquare, roles: ["admin", "hr_manager", "hr_analyst"] },
  { href: "/admin/tax-rules", label: "Tax Rules", icon: FileText, roles: ["admin", "hr_manager"], section: "Admin" },
  { href: "/admin/pf-rules", label: "PF Rules", icon: Briefcase, roles: ["admin", "hr_manager"] },
  { href: "/admin/users", label: "Users", icon: UserCog, roles: ["admin"] },
  { href: "/my/salary-slips", label: "My Slips", icon: Receipt, roles: ["employee"] },
];

const routeTitles: Record<string, string> = {
  "/": "Dashboard",
  "/employees": "Employees",
  "/insights": "AI Insights",
  "/admin/tax-rules": "Tax Rules",
  "/admin/pf-rules": "PF Rules",
  "/admin/users": "Users",
  "/my/salary-slips": "My Salary Slips",
};

function getPageTitle(pathname: string): string {
  if (routeTitles[pathname]) return routeTitles[pathname];
  if (pathname.startsWith("/employees/")) return "Employee Detail";
  return "ACME HR";
}

function initial(email: string): string {
  return email.charAt(0).toUpperCase();
}

export default function Layout({ children }: { children: React.ReactNode }) {
  const { user, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();

  const visibleNav = navItems.filter(
    (item) => user && item.roles.includes(user.role)
  );

  function handleLogout() {
    logout();
    navigate("/login");
  }

  const pageTitle = getPageTitle(location.pathname);

  return (
    <div className="flex min-h-screen">
      {/* Sidebar */}
      <aside className="w-52 bg-slate-900 text-white flex flex-col flex-shrink-0">
        {/* Logo */}
        <div className="p-4 flex items-center gap-2.5 border-b border-slate-700/60">
          <div className="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center flex-shrink-0">
            <Layers className="w-4 h-4 text-white" />
          </div>
          <span className="font-bold text-base tracking-tight">ACME HR</span>
        </div>

        {/* Nav */}
        <nav className="flex-1 py-3">
          {visibleNav.map((item) => {
            const Icon = item.icon;
            const isActive =
              item.href === "/"
                ? location.pathname === "/"
                : location.pathname.startsWith(item.href);
            return (
              <div key={item.href}>
                {item.section && (
                  <p className="px-4 pt-4 pb-1 text-[10px] font-semibold uppercase tracking-widest text-slate-500">
                    {item.section}
                  </p>
                )}
                <Link
                  to={item.href}
                  className={cn(
                    "flex items-center gap-2.5 px-4 py-2.5 text-sm transition-colors border-l-2",
                    isActive
                      ? "bg-slate-800 text-white border-indigo-500"
                      : "text-slate-400 hover:bg-slate-800 hover:text-white border-transparent"
                  )}
                >
                  <Icon className="w-4 h-4 flex-shrink-0" />
                  {item.label}
                </Link>
              </div>
            );
          })}
        </nav>

        {/* User footer */}
        <div className="p-4 border-t border-slate-700/60">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-full bg-indigo-600 flex items-center justify-center text-xs font-semibold flex-shrink-0">
              {user ? initial(user.email) : "?"}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium text-white truncate">{user?.email}</p>
              <p className="text-xs text-slate-500 capitalize">
                {user?.role?.replace(/_/g, " ")}
              </p>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="mt-2 text-xs text-slate-500 hover:text-slate-300 transition-colors"
          >
            Sign out
          </button>
        </div>
      </aside>

      {/* Main column */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top bar */}
        <header className="h-14 bg-white border-b border-slate-200 flex items-center justify-between px-6 flex-shrink-0">
          <h1 className="text-base font-semibold text-slate-900">{pageTitle}</h1>
          <div className="flex items-center gap-3">
            <span className="text-sm text-slate-500 hidden sm:block">{user?.email}</span>
            <div className="w-9 h-9 rounded-full bg-indigo-600 flex items-center justify-center text-sm font-semibold text-white flex-shrink-0">
              {user ? initial(user.email) : "?"}
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 bg-slate-100 overflow-auto p-6">
          {children}
        </main>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Verify**

With dev server running, log in and confirm:
- Sidebar is dark navy (`bg-slate-900`)
- Each nav item shows a Lucide icon + label
- Active item has indigo left-border and `bg-slate-800` background
- "Admin" section label appears above Tax Rules (admin/hr_manager only)
- Top bar shows page title on left and user email + indigo avatar on right
- User email + role + "Sign out" appear at sidebar bottom
- All inner pages (Employees, AI Insights, etc.) still render correctly inside the new layout

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/Layout.tsx
git commit -m "feat: redesign Layout with dark sidebar, icons, top bar"
```

---

## Task 5: Redesign Dashboard.tsx

**Files:**
- Modify: `frontend/src/pages/Dashboard.tsx`

Replace the current Dashboard with:
- 4 `StatCard` components (Total Employees, Avg Monthly Salary, Salary Range low end, Salary Band count)
- Existing Recharts charts restyled (card title font update only)
- `RightPanel` rendered to the right of main content, visible to admin/hr_manager only
- Removes inline `StatCard` and `BulkGenerateCard` definitions (they are now in separate files)

- [ ] **Step 1: Replace `Dashboard.tsx` entirely**

```tsx
import { useQuery } from "@tanstack/react-query";
import { getAnalyticsSummary, getAnalyticsByDepartment, getSalaryBands } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import StatCard from "@/components/StatCard";
import RightPanel from "@/components/RightPanel";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
} from "recharts";
import { Users, DollarSign, TrendingUp, BarChart2 } from "lucide-react";

const COLORS = [
  "#6366f1", "#22c55e", "#f59e0b", "#ef4444",
  "#8b5cf6", "#06b6d4", "#ec4899", "#14b8a6",
];

function fmt(n: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(n);
}

export default function Dashboard() {
  const { user } = useAuth();

  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ["analytics", "summary"],
    queryFn: getAnalyticsSummary,
  });

  const { data: byDept } = useQuery({
    queryKey: ["analytics", "by-department"],
    queryFn: getAnalyticsByDepartment,
  });

  const { data: bands } = useQuery({
    queryKey: ["analytics", "salary-bands"],
    queryFn: () => getSalaryBands(5000),
  });

  const showRightPanel =
    user?.role === "admin" || user?.role === "hr_manager";

  if (statsLoading) return <div className="text-slate-400">Loading…</div>;

  return (
    <div className="flex gap-6 items-start">
      {/* Main content */}
      <div className="flex-1 min-w-0 space-y-6">
        {/* KPI stat cards */}
        {stats && (
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <StatCard
              label="Total Employees"
              value={stats.count}
              icon={<Users className="w-5 h-5 text-amber-500" />}
              iconBg="bg-amber-100"
              change="Active on record"
            />
            <StatCard
              label="Avg Monthly Salary"
              value={fmt(stats.avg)}
              icon={<DollarSign className="w-5 h-5 text-sky-600" />}
              iconBg="bg-sky-100"
              change={`Median: ${fmt(stats.median)}`}
              changeUp
            />
            <StatCard
              label="Salary Floor"
              value={fmt(stats.min)}
              icon={<TrendingUp className="w-5 h-5 text-green-600" />}
              iconBg="bg-green-100"
              change={`Ceiling: ${fmt(stats.max)}`}
            />
            <StatCard
              label="Salary Bands"
              value={bands?.length ?? "—"}
              icon={<BarChart2 className="w-5 h-5 text-violet-600" />}
              iconBg="bg-violet-100"
              change="Distribution buckets"
            />
          </div>
        )}

        {/* Charts */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {byDept && (
            <Card>
              <CardHeader>
                <CardTitle className="text-sm font-semibold text-slate-900">
                  Headcount by Department
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={240}>
                  <PieChart>
                    <Pie
                      data={byDept}
                      dataKey="count"
                      nameKey="group"
                      cx="50%"
                      cy="50%"
                      outerRadius={80}
                    >
                      {byDept.map((_: unknown, index: number) => (
                        <Cell key={String(index)} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          )}

          {bands && (
            <Card>
              <CardHeader>
                <CardTitle className="text-sm font-semibold text-slate-900">
                  Salary Distribution
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={240}>
                  <BarChart data={bands}>
                    <XAxis
                      dataKey="range_start"
                      tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`}
                      tick={{ fontSize: 11 }}
                    />
                    <YAxis tick={{ fontSize: 11 }} />
                    <Tooltip
                      formatter={(v) => [v, "Employees"]}
                      labelFormatter={(v) => `$${(Number(v) / 1000).toFixed(0)}k+`}
                    />
                    <Bar dataKey="count" fill="#6366f1" radius={[3, 3, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          )}
        </div>
      </div>

      {/* Right panel — admin and hr_manager only */}
      {showRightPanel && <RightPanel employeeCount={stats?.count} />}
    </div>
  );
}
```

- [ ] **Step 2: Verify**

With dev server running, log in as admin (credentials: `admin@acme.com` / `Admin123!`):

- Dashboard shows 4 stat cards in a row, each with a coloured icon square
- Below cards: two charts side by side (Pie + Bar)
- Right panel visible with date, "Generate Slips" (indigo), "Add Employee", "Edit Tax Rules" buttons, and amber employee count badge
- "Generate Slips" opens a Dialog with month/year inputs; submitting calls the bulk API
- Log out, log in as `hr_manager` role user: RightPanel shows but "Generate Slips" button is hidden
- Log in as `hr_analyst`: RightPanel is not rendered at all

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/Dashboard.tsx
git commit -m "feat: redesign Dashboard with StatCard grid and RightPanel"
```

---

## Self-Review

**Spec coverage:**
- ✅ Dark sidebar with icons + labels → Task 4 (Layout.tsx)
- ✅ Top bar with page title and user avatar → Task 4
- ✅ 4 KPI stat cards with coloured icon squares → Task 2 (StatCard) + Task 5 (Dashboard)
- ✅ Right panel with Quick Actions (Generate Slips modal, Add Employee, Edit Tax Rules) → Task 3 (RightPanel)
- ✅ Pending/employee count amber badge → Task 3
- ✅ System status → Task 3
- ✅ Indigo primary on buttons sitewide → already set via `--primary` CSS variable (confirmed existing)
- ✅ Indigo focus ring on inputs → Task 1 (index.css `--ring`)
- ✅ Inner pages unchanged → no inner page tasks
- ✅ `BulkGenerateCard` removed from Dashboard, logic moved to RightPanel Generate Slips modal → Task 3 + Task 5

**Type consistency:**
- `StatCardProps.iconBg` is a Tailwind class string — used as `iconBg="bg-amber-100"` in Task 5 ✅
- `RightPanelProps.employeeCount` is `number | undefined` — passed as `stats?.count` in Task 5 ✅
- `BulkResult` interface defined in `RightPanel.tsx` — not imported from elsewhere ✅
- `bulkGenerateSalarySlips(month, year)` signature matches `api.ts:106` ✅
- `getAnalyticsSummary` returns object with `.count`, `.avg`, `.median`, `.min`, `.max` — confirmed from existing Dashboard usage ✅
