import { useState } from "react";
import { useParams } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getEmployee, listSalaryRecords, listBonuses, listAllowances, generateSalarySlip, listSalarySlips } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

function fmt(n: number, currency = "USD") {
  return new Intl.NumberFormat("en-US", { style: "currency", currency, maximumFractionDigits: 0 }).format(n);
}

export default function EmployeeDetail() {
  const { id } = useParams<{ id: string }>();
  const empId = Number(id);
  const qc = useQueryClient();

  const { data: emp, isLoading } = useQuery({ queryKey: ["employee", empId], queryFn: () => getEmployee(empId) });
  const { data: salaryRecords } = useQuery({ queryKey: ["salary-records", empId], queryFn: () => listSalaryRecords(empId) });
  const { data: bonuses } = useQuery({ queryKey: ["bonuses", empId], queryFn: () => listBonuses(empId) });
  const { data: allowances } = useQuery({ queryKey: ["allowances", empId], queryFn: () => listAllowances(empId) });
  const { data: slips } = useQuery({ queryKey: ["salary-slips", empId], queryFn: () => listSalarySlips(empId) });

  const now = new Date();
  const [genMonth] = useState(now.getMonth() + 1);
  const [genYear] = useState(now.getFullYear());

  const generateMutation = useMutation({
    mutationFn: () => generateSalarySlip(empId, genMonth, genYear),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["salary-slips", empId] }),
  });

  if (isLoading) return <div className="text-slate-400">Loading…</div>;
  if (!emp) return <div className="text-red-500">Employee not found</div>;

  const currentSalary = salaryRecords?.[0];

  return (
    <div className="space-y-6 max-w-4xl">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold">{emp.first_name} {emp.last_name}</h1>
          <p className="text-slate-500">{emp.job_title} · {emp.department} · {emp.country}</p>
          <p className="text-slate-400 text-sm font-mono">{emp.employee_id}</p>
        </div>
        <Badge variant={emp.status === "active" ? "default" : "secondary"}>{emp.status}</Badge>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card><CardHeader className="pb-1"><CardTitle className="text-xs text-slate-500">Base Salary</CardTitle></CardHeader>
          <CardContent><p className="text-xl font-bold">{currentSalary ? fmt(currentSalary.base_salary, currentSalary.currency) : "—"}</p></CardContent></Card>
        <Card><CardHeader className="pb-1"><CardTitle className="text-xs text-slate-500">Currency</CardTitle></CardHeader>
          <CardContent><p className="text-xl font-bold">{emp.currency}</p></CardContent></Card>
        <Card><CardHeader className="pb-1"><CardTitle className="text-xs text-slate-500">Type</CardTitle></CardHeader>
          <CardContent><p className="text-xl font-bold capitalize">{emp.employment_type}</p></CardContent></Card>
        <Card><CardHeader className="pb-1"><CardTitle className="text-xs text-slate-500">Hire Date</CardTitle></CardHeader>
          <CardContent><p className="text-xl font-bold">{emp.hire_date}</p></CardContent></Card>
      </div>

      {allowances && allowances.length > 0 && (
        <Card>
          <CardHeader><CardTitle className="text-base">Allowances</CardTitle></CardHeader>
          <CardContent>
            <Table>
              <TableHeader><TableRow><TableHead>Type</TableHead><TableHead>Amount</TableHead><TableHead>Frequency</TableHead></TableRow></TableHeader>
              <TableBody>
                {allowances.map((a: { id: number; allowance_type: string; amount: number; currency: string; frequency: string }) => (
                  <TableRow key={a.id}>
                    <TableCell className="capitalize">{a.allowance_type}</TableCell>
                    <TableCell>{fmt(a.amount, a.currency)}</TableCell>
                    <TableCell className="capitalize">{a.frequency}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {bonuses && bonuses.length > 0 && (
        <Card>
          <CardHeader><CardTitle className="text-base">Bonuses</CardTitle></CardHeader>
          <CardContent>
            <Table>
              <TableHeader><TableRow><TableHead>Type</TableHead><TableHead>Amount</TableHead><TableHead>Date</TableHead></TableRow></TableHeader>
              <TableBody>
                {bonuses.map((b: { id: number; bonus_type: string; amount: number; currency: string; awarded_date: string }) => (
                  <TableRow key={b.id}>
                    <TableCell className="capitalize">{b.bonus_type}</TableCell>
                    <TableCell>{fmt(b.amount, b.currency)}</TableCell>
                    <TableCell>{b.awarded_date}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-base">Salary Slips</CardTitle>
          <Button size="sm" onClick={() => generateMutation.mutate()} disabled={generateMutation.isPending}>
            {generateMutation.isPending ? "Generating…" : `Generate ${genMonth}/${genYear}`}
          </Button>
        </CardHeader>
        <CardContent>
          {slips && slips.length > 0 ? (
            <Table>
              <TableHeader><TableRow><TableHead>Period</TableHead><TableHead>Gross</TableHead><TableHead>Tax</TableHead><TableHead>Net</TableHead></TableRow></TableHeader>
              <TableBody>
                {slips.map((s: { id: number; period_month: number; period_year: number; gross_salary: number; tax_deducted: number; net_take_home: number; currency: string }) => (
                  <TableRow key={s.id}>
                    <TableCell>{s.period_month}/{s.period_year}</TableCell>
                    <TableCell>{fmt(s.gross_salary, s.currency)}</TableCell>
                    <TableCell>{fmt(s.tax_deducted, s.currency)}</TableCell>
                    <TableCell className="font-medium">{fmt(s.net_take_home, s.currency)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : <p className="text-slate-400 text-sm">No salary slips yet.</p>}
        </CardContent>
      </Card>
    </div>
  );
}
