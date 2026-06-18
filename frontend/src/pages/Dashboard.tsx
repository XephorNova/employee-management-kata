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
