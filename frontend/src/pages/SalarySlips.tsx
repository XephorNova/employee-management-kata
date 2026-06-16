import { useQuery } from "@tanstack/react-query";
import { useAuth } from "@/context/AuthContext";
import { listSalarySlips } from "@/lib/api";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

function fmt(n: number, currency = "USD") {
  return new Intl.NumberFormat("en-US", { style: "currency", currency, maximumFractionDigits: 0 }).format(n);
}

export default function SalarySlips() {
  const { user } = useAuth();

  const { data: slips, isLoading } = useQuery({
    queryKey: ["my-salary-slips"],
    queryFn: () => listSalarySlips(user!.employee_id!),
    enabled: !!user?.employee_id,
  });

  if (!user?.employee_id) {
    return <div className="text-slate-400 p-4">No employee record linked to your account.</div>;
  }

  return (
    <div className="space-y-4 max-w-3xl">
      <h1 className="text-2xl font-bold">My Salary Slips</h1>

      {isLoading ? <div className="text-slate-400">Loading…</div> : (
        slips?.length ? (
          <Card>
            <CardHeader><CardTitle className="text-base">Slip History</CardTitle></CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Period</TableHead>
                    <TableHead>Gross</TableHead>
                    <TableHead>PF</TableHead>
                    <TableHead>Tax</TableHead>
                    <TableHead>Net Take-Home</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {slips.map((s: { id: number; period_month: number; period_year: number; gross_salary: number; pf_employee_contribution: number; tax_deducted: number; net_take_home: number; currency: string }) => (
                    <TableRow key={s.id}>
                      <TableCell>{s.period_month}/{s.period_year}</TableCell>
                      <TableCell>{fmt(s.gross_salary, s.currency)}</TableCell>
                      <TableCell>{fmt(s.pf_employee_contribution, s.currency)}</TableCell>
                      <TableCell>{fmt(s.tax_deducted, s.currency)}</TableCell>
                      <TableCell className="font-bold">{fmt(s.net_take_home, s.currency)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        ) : <p className="text-slate-400">No salary slips found.</p>
      )}
    </div>
  );
}
