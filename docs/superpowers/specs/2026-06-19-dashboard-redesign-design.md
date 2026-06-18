# ACME HR — Dashboard & Layout Redesign

**Date:** 2026-06-19
**Scope:** Full app layout chrome + Dashboard page + sitewide button/form color scheme

---

## Overview

Redesign the ACME HR frontend to match a modern analytics dashboard aesthetic: dark navy sidebar with icons and labels, light content area, colorful KPI stat cards, and a role-aware quick-actions right panel on the Dashboard. Sitewide buttons and form inputs adopt the indigo primary color token. Inner page layouts (Employees, Insights, Tax Rules, PF Rules, Users, SalarySlips) are not restructured — they inherit the new chrome automatically.

---

## Visual Design

**Style:** Dark sidebar + light cards (Option A from brainstorm)

| Token | Value | Used for |
|---|---|---|
| Primary | `#6366f1` (indigo-500) | Buttons, active nav indicator, input focus ring, stat icon backgrounds |
| Sidebar bg | `#0f172a` (slate-900) | Sidebar background |
| Active nav bg | `#1e293b` (slate-800) | Hovered/active nav item background |
| Content bg | `#f1f5f9` (slate-100) | Page background |
| Card bg | `white` | Stat cards, chart cards, right panel |
| Card border | `#e2e8f0` (slate-200) | All card borders |
| Text primary | `#0f172a` (slate-900) | Headings, values |
| Text secondary | `#64748b` (slate-500) | Labels, subtitles |

Stat card accent icon colors (one per KPI, for background square behind the icon):

| KPI | Icon bg | Icon stroke |
|---|---|---|
| Total Employees | `#fef3c7` (amber-100) | `#f59e0b` (amber-500) |
| Monthly Payroll | `#e0f2fe` (sky-100) | `#0284c7` (sky-600) |
| Avg Annual Salary | `#dcfce7` (green-100) | `#16a34a` (green-600) |
| Slips Generated | `#ede9fe` (violet-100) | `#7c3aed` (violet-600) |

---

## Architecture

### Files Modified

**`frontend/src/components/Layout.tsx`**
- Sidebar: `w-52` dark slate-900 background, logo icon + "ACME HR" wordmark at top
- Nav items: icon (Lucide, 18px) + label, left border accent `border-indigo-500` when active, `bg-slate-800` on active/hover
- Nav sections: "Admin" label divider above Tax Rules / PF Rules / Users (only shown to admin/hr_manager)
- Top bar: white `h-14` bar with page title (derived from current route) on left, user full name + avatar circle on right
- User footer: avatar + email + role + sign-out link, pinned to sidebar bottom
- No collapse toggle — sidebar is always expanded at `w-52`
- No CTA button at bottom

**`frontend/src/pages/Dashboard.tsx`**
- Remove inline `StatCard` and `BulkGenerateCard` — replaced by the new extracted components
- Grid of 4 `StatCard` components using analytics summary API data
- Two-column chart grid: Headcount by Department (Pie) + Salary Distribution (Bar) — same Recharts components, restyled
- Renders `<RightPanel />` alongside main content (flex row layout)

**`frontend/src/index.css`**
- Tailwind base layer override: `button` primary variant → indigo-600 background
- Input focus ring: `focus:ring-indigo-500 focus:border-indigo-500`
- shadcn/ui CSS variable overrides: `--primary: 239 68% 60%` (indigo hue) so shadcn `Button` and `Input` components pick up the new color automatically

### Files Created

**`frontend/src/components/StatCard.tsx`**

Props:
```ts
interface StatCardProps {
  label: string;
  value: string | number;
  icon: React.ReactNode;       // Lucide icon element
  iconBg: string;              // Tailwind bg class e.g. "bg-amber-100"
  change?: string;             // e.g. "↑ 12% this month"
  changeUp?: boolean;          // green if true, slate if false/undefined
}
```

**`frontend/src/components/RightPanel.tsx`**

- Shown only when `user.role` is `admin` or `hr_manager` (hidden for `hr_analyst` and `employee`)
- Sections:
  1. **Date** — current date, formatted `Thu, 19 Jun 2026`
  2. **Quick Actions** — three buttons:
     - "Generate Slips" (primary indigo) — opens a modal dialog with month/year inputs and a confirm button; replaces the existing `BulkGenerateCard` on the Dashboard. Only shown when `user.role === "admin"`.
     - "Add Employee" (secondary) — navigates to `/employees` (no separate new-employee route exists).
     - "Edit Tax Rules" (secondary) — navigates to `/admin/tax-rules`.
  3. **Pending Slips alert** — amber badge showing count of employees without a slip for the current month. Derived by calling the existing `bulkGenerateSalarySlips` API in dry-run mode, or computed as `total_active_employees - slips_generated_this_month` from analytics summary.
  4. **System status** — green dot + "Backend online" (static, no health-check endpoint needed)

---

## Data Flow

Dashboard fetches three existing endpoints (no new backend work):

| Query key | Endpoint | Used for |
|---|---|---|
| `["analytics", "summary"]` | `GET /analytics/summary` | Total employees, avg salary, median (used for KPI cards) |
| `["analytics", "by-department"]` | `GET /analytics/by-department` | Pie chart |
| `["analytics", "salary-bands"]` | `GET /analytics/salary-bands?band_size=5000` | Bar chart |

Slips-generated KPI: derived from `summary.count` vs a new query for slips generated this month. If the backend doesn't expose this directly, the KPI shows `summary.count` with label "Active Employees" instead — no new endpoint required.

Pending slips count in `RightPanel`: shown as a static amber badge using `summary.count` with label "Active Employees without slips this month" — no additional API call. Badge is hidden if `summary` is unavailable.

---

## Sitewide Color Changes (Buttons & Forms)

Applied via shadcn/ui CSS variable override in `index.css`:

```css
:root {
  --primary: 239 68% 60%;           /* indigo-500 */
  --primary-foreground: 0 0% 100%;  /* white */
  --ring: 239 68% 60%;              /* indigo focus ring */
}
```

This affects all shadcn `Button` (default variant), `Input`, `Select`, `Checkbox`, `Switch` components sitewide with no per-component changes needed.

---

## Error Handling

- Analytics queries show a skeleton/loading state (`text-slate-400 "Loading…"`) — same as existing behavior
- If any query errors, the corresponding card/chart is hidden (existing React Query `isError` pattern)
- RightPanel pending-slips badge is hidden if count cannot be computed

---

## Out of Scope

- Inner page layouts (Employees table, AI Insights chat, Tax/PF/User admin forms) — structure unchanged
- Sidebar collapse/expand toggle
- CTA button in sidebar
- Mobile/responsive layout
- Dark mode
