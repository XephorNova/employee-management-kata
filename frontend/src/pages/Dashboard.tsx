import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { getAnalyticsSummary, getAnalyticsByDepartment, getSalaryBands, bulkGenerateSalarySlips } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend } from "recharts";

const COLORS = ["#6366f1", "#22c55e", "#f59e0b", "#ef4444", "#8b5cf6", "#06b6d4", "#ec4899", "#14b8a6"];

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <Card>
      <CardHeader className="pb-1">
        <CardTitle className="text-sm font-medium text-slate-500">{label}</CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-2xl font-bold">{value}</p>
      </CardContent>
    </Card>
  );
}

function fmt(n: number) {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(n);
}

interface BulkResult {
  generated: number;
  errors: { employee_id: number; error: string }[];
  total: number;
}

function BulkGenerateCard() {
  const now = new Date();
  // Pre-fill next month
  const nextMonth = now.getMonth() === 11 ? 1 : now.getMonth() + 2;
  const nextYear = now.getMonth() === 11 ? now.getFullYear() + 1 : now.getFullYear();

  const [month, setMonth] = useState(nextMonth);
  const [year, setYear] = useState(nextYear);
  const [result, setResult] = useState<BulkResult | null>(null);

  const bulkMutation = useMutation({
    mutationFn: () => bulkGenerateSalarySlips(month, year),
    onSuccess: (data: BulkResult) => setResult(data),
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Generate Upcoming Salary Slips</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-end gap-3">
          <div>
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
          <div>
            <Label>Year</Label>
            <Input
              type="number"
              value={year}
              onChange={(e) => setYear(Number(e.target.value))}
              className="w-28"
            />
          </div>
          <Button onClick={() => { setResult(null); bulkMutation.mutate(); }} disabled={bulkMutation.isPending}>
            {bulkMutation.isPending ? "Generating…" : "Generate for all active employees"}
          </Button>
        </div>

        {bulkMutation.isError && (
          <p className="text-red-500 text-sm">Failed to generate salary slips. Check permissions or try again.</p>
        )}

        {result && (
          <div className="text-sm space-y-1">
            <p className="text-green-600 font-medium">Generated {result.generated} slip{result.generated !== 1 ? "s" : ""} out of {result.total} active employees.</p>
            {result.errors.length > 0 && (
              <details>
                <summary className="text-red-500 cursor-pointer">{result.errors.length} error{result.errors.length !== 1 ? "s" : ""}</summary>
                <ul className="mt-1 text-slate-600 space-y-1">
                  {result.errors.map((e) => (
                    <li key={e.employee_id}>Employee #{e.employee_id}: {e.error}</li>
                  ))}
                </ul>
              </details>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default function Dashboard() {
  const { user } = useAuth();

  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ["analytics", "summary"],
    queryFn: () => getAnalyticsSummary(),
  });

  const { data: byDept } = useQuery({
    queryKey: ["analytics", "by-department"],
    queryFn: getAnalyticsByDepartment,
  });

  const { data: bands } = useQuery({
    queryKey: ["analytics", "salary-bands"],
    queryFn: () => getSalaryBands(5000),
  });

  if (statsLoading) return <div className="text-slate-400">Loading…</div>;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Dashboard</h1>

      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard label="Total Employees" value={stats.count} />
          <StatCard label="Avg Monthly Salary" value={fmt(stats.avg)} />
          <StatCard label="Median" value={fmt(stats.median)} />
          <StatCard label="Salary Range" value={`${fmt(stats.min)} – ${fmt(stats.max)}`} />
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {byDept && (
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Headcount by Department</CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={240}>
                <PieChart>
                  <Pie data={byDept} dataKey="count" nameKey="group" cx="50%" cy="50%" outerRadius={80}>
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
              <CardTitle className="text-base">Salary Distribution</CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={240}>
                <BarChart data={bands}>
                  <XAxis dataKey="range_start" tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`} tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip formatter={(v) => [v, "Employees"]} labelFormatter={(v) => `$${(Number(v) / 1000).toFixed(0)}k+`} />
                  <Bar dataKey="count" fill="#6366f1" radius={[3, 3, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        )}
      </div>

      {user?.role === "admin" && <BulkGenerateCard />}
    </div>
  );
}
