import { useQuery } from "@tanstack/react-query";
import { getAnalyticsSummary, getAnalyticsByDepartment, getSalaryBands } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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

export default function Dashboard() {
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
    </div>
  );
}
