import { useState } from "react";
import { useParams } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getEmployee, listSalaryRecords, listBonuses, listAllowances, generateSalarySlip, listSalarySlips,
  listBankDetails, createBankDetail, updateBankDetail, deleteBankDetail, getTaxStatement, downloadSlipPdf,
} from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

function fmt(n: number, currency = "USD") {
  return new Intl.NumberFormat("en-US", { style: "currency", currency, maximumFractionDigits: 0 }).format(n);
}

function maskAccount(accountNumber: string) {
  if (accountNumber.length <= 4) return accountNumber;
  return `••••${accountNumber.slice(-4)}`;
}

interface BankDetail {
  id: number;
  employee_id: number;
  bank_name: string;
  account_number: string;
  account_type: string;
  routing_number: string | null;
  ifsc_code: string | null;
  swift_code: string | null;
  is_primary: boolean;
}

interface BankDetailForm {
  bank_name: string;
  account_number: string;
  account_type: string;
  routing_number: string;
  ifsc_code: string;
  swift_code: string;
  is_primary: boolean;
}

const emptyBankForm: BankDetailForm = {
  bank_name: "", account_number: "", account_type: "savings",
  routing_number: "", ifsc_code: "", swift_code: "", is_primary: true,
};

function BankDetailsCard({ empId }: { empId: number }) {
  const qc = useQueryClient();
  const { data: bankDetails } = useQuery({
    queryKey: ["bank-details", empId],
    queryFn: () => listBankDetails(empId),
  });

  const [showAdd, setShowAdd] = useState(false);
  const [addForm, setAddForm] = useState<BankDetailForm>(emptyBankForm);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editForm, setEditForm] = useState<BankDetailForm>(emptyBankForm);

  const createMutation = useMutation({
    mutationFn: (data: unknown) => createBankDetail(empId, data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["bank-details", empId] }); setShowAdd(false); setAddForm(emptyBankForm); },
  });

  const updateMutation = useMutation({
    mutationFn: ({ detailId, data }: { detailId: number; data: unknown }) => updateBankDetail(empId, detailId, data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["bank-details", empId] }); setEditingId(null); },
  });

  const deleteMutation = useMutation({
    mutationFn: (detailId: number) => deleteBankDetail(empId, detailId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["bank-details", empId] }),
  });

  function startEdit(detail: BankDetail) {
    setEditingId(detail.id);
    setEditForm({
      bank_name: detail.bank_name,
      account_number: detail.account_number,
      account_type: detail.account_type,
      routing_number: detail.routing_number ?? "",
      ifsc_code: detail.ifsc_code ?? "",
      swift_code: detail.swift_code ?? "",
      is_primary: detail.is_primary,
    });
  }

  function buildPayload(f: BankDetailForm) {
    return {
      bank_name: f.bank_name,
      account_number: f.account_number,
      account_type: f.account_type,
      routing_number: f.routing_number || null,
      ifsc_code: f.ifsc_code || null,
      swift_code: f.swift_code || null,
      is_primary: f.is_primary,
    };
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-base">Bank Details</CardTitle>
        <Button size="sm" variant="outline" onClick={() => setShowAdd((v) => !v)}>+ Add bank account</Button>
      </CardHeader>
      <CardContent className="space-y-4">
        {showAdd && (
          <div className="border rounded p-3 space-y-3 bg-slate-50">
            <p className="text-sm font-medium">New Bank Account</p>
            <div className="grid grid-cols-2 gap-3">
              <div><Label>Bank Name</Label><Input value={addForm.bank_name} onChange={(e) => setAddForm({ ...addForm, bank_name: e.target.value })} /></div>
              <div><Label>Account Number</Label><Input value={addForm.account_number} onChange={(e) => setAddForm({ ...addForm, account_number: e.target.value })} /></div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label>Account Type</Label>
                <select
                  className="w-full border rounded px-2 py-1 text-sm"
                  value={addForm.account_type}
                  onChange={(e) => setAddForm({ ...addForm, account_type: e.target.value })}
                >
                  <option value="savings">Savings</option>
                  <option value="checking">Checking</option>
                  <option value="current">Current</option>
                </select>
              </div>
              <div><Label>Routing Number</Label><Input value={addForm.routing_number} onChange={(e) => setAddForm({ ...addForm, routing_number: e.target.value })} placeholder="Optional" /></div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div><Label>IFSC Code</Label><Input value={addForm.ifsc_code} onChange={(e) => setAddForm({ ...addForm, ifsc_code: e.target.value })} placeholder="Optional" /></div>
              <div><Label>SWIFT Code</Label><Input value={addForm.swift_code} onChange={(e) => setAddForm({ ...addForm, swift_code: e.target.value })} placeholder="Optional" /></div>
            </div>
            <div className="flex items-center gap-2">
              <input type="checkbox" id="add-primary" checked={addForm.is_primary} onChange={(e) => setAddForm({ ...addForm, is_primary: e.target.checked })} />
              <label htmlFor="add-primary" className="text-sm">Primary account</label>
            </div>
            <div className="flex gap-2">
              <Button size="sm" onClick={() => createMutation.mutate(buildPayload(addForm))} disabled={createMutation.isPending}>
                {createMutation.isPending ? "Saving…" : "Save"}
              </Button>
              <Button size="sm" variant="outline" onClick={() => { setShowAdd(false); setAddForm(emptyBankForm); }}>Cancel</Button>
            </div>
          </div>
        )}

        {bankDetails && bankDetails.length > 0 ? (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Bank Name</TableHead>
                <TableHead>Account Number</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Routing/IFSC</TableHead>
                <TableHead>Primary</TableHead>
                <TableHead></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {bankDetails.map((detail: BankDetail) => (
                <>
                  <TableRow key={detail.id}>
                    <TableCell>{detail.bank_name}</TableCell>
                    <TableCell className="font-mono">{maskAccount(detail.account_number)}</TableCell>
                    <TableCell className="capitalize">{detail.account_type}</TableCell>
                    <TableCell className="text-slate-500">{detail.routing_number || detail.ifsc_code || "—"}</TableCell>
                    <TableCell>{detail.is_primary ? <Badge>Primary</Badge> : null}</TableCell>
                    <TableCell>
                      <div className="flex gap-1">
                        <Button size="sm" variant="outline" onClick={() => startEdit(detail)}>Edit</Button>
                        <Button size="sm" variant="outline" className="text-red-600" onClick={() => deleteMutation.mutate(detail.id)} disabled={deleteMutation.isPending}>Delete</Button>
                      </div>
                    </TableCell>
                  </TableRow>
                  {editingId === detail.id && (
                    <TableRow key={`edit-${detail.id}`}>
                      <TableCell colSpan={6}>
                        <div className="border rounded p-3 space-y-3 bg-slate-50">
                          <p className="text-sm font-medium">Edit Bank Account</p>
                          <div className="grid grid-cols-2 gap-3">
                            <div><Label>Bank Name</Label><Input value={editForm.bank_name} onChange={(e) => setEditForm({ ...editForm, bank_name: e.target.value })} /></div>
                            <div><Label>Account Number</Label><Input value={editForm.account_number} onChange={(e) => setEditForm({ ...editForm, account_number: e.target.value })} /></div>
                          </div>
                          <div className="grid grid-cols-2 gap-3">
                            <div>
                              <Label>Account Type</Label>
                              <select
                                className="w-full border rounded px-2 py-1 text-sm"
                                value={editForm.account_type}
                                onChange={(e) => setEditForm({ ...editForm, account_type: e.target.value })}
                              >
                                <option value="savings">Savings</option>
                                <option value="checking">Checking</option>
                                <option value="current">Current</option>
                              </select>
                            </div>
                            <div><Label>Routing Number</Label><Input value={editForm.routing_number} onChange={(e) => setEditForm({ ...editForm, routing_number: e.target.value })} placeholder="Optional" /></div>
                          </div>
                          <div className="grid grid-cols-2 gap-3">
                            <div><Label>IFSC Code</Label><Input value={editForm.ifsc_code} onChange={(e) => setEditForm({ ...editForm, ifsc_code: e.target.value })} placeholder="Optional" /></div>
                            <div><Label>SWIFT Code</Label><Input value={editForm.swift_code} onChange={(e) => setEditForm({ ...editForm, swift_code: e.target.value })} placeholder="Optional" /></div>
                          </div>
                          <div className="flex items-center gap-2">
                            <input type="checkbox" id={`edit-primary-${detail.id}`} checked={editForm.is_primary} onChange={(e) => setEditForm({ ...editForm, is_primary: e.target.checked })} />
                            <label htmlFor={`edit-primary-${detail.id}`} className="text-sm">Primary account</label>
                          </div>
                          <div className="flex gap-2">
                            <Button size="sm" onClick={() => updateMutation.mutate({ detailId: detail.id, data: buildPayload(editForm) })} disabled={updateMutation.isPending}>
                              {updateMutation.isPending ? "Saving…" : "Save"}
                            </Button>
                            <Button size="sm" variant="outline" onClick={() => setEditingId(null)}>Cancel</Button>
                          </div>
                        </div>
                      </TableCell>
                    </TableRow>
                  )}
                </>
              ))}
            </TableBody>
          </Table>
        ) : <p className="text-slate-400 text-sm">No bank accounts on file.</p>}
      </CardContent>
    </Card>
  );
}

interface TaxMonth {
  month: number;
  gross: number;
  pf_employee: number;
  pf_employer: number;
  tax: number;
  net: number;
  currency: string;
}

interface TaxStatement {
  employee_id: number;
  employee_name: string;
  year: number;
  months: TaxMonth[];
  totals: { gross: number; pf_employee: number; pf_employer: number; tax: number; net: number; currency: string };
}

const MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

function TaxStatementCard({ empId }: { empId: number }) {
  const currentYear = new Date().getFullYear();
  const [year, setYear] = useState(currentYear);
  const [fetchYear, setFetchYear] = useState<number | null>(null);

  const { data: statement, isLoading, isError } = useQuery<TaxStatement>({
    queryKey: ["tax-statement", empId, fetchYear],
    queryFn: () => getTaxStatement(empId, fetchYear!),
    enabled: fetchYear !== null,
  });

  return (
    <Card>
      <CardHeader><CardTitle className="text-base">Yearly Tax Statement</CardTitle></CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-end gap-3">
          <div>
            <Label>Year</Label>
            <Input
              type="number"
              value={year}
              onChange={(e) => setYear(Number(e.target.value))}
              className="w-28"
              min={2000}
              max={currentYear}
            />
          </div>
          <Button size="sm" onClick={() => setFetchYear(year)}>View Statement</Button>
        </div>

        {isLoading && <p className="text-slate-400 text-sm">Loading…</p>}
        {isError && <p className="text-red-500 text-sm">Failed to load tax statement.</p>}
        {statement && (
          <div>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Month</TableHead>
                  <TableHead className="text-right">Gross</TableHead>
                  <TableHead className="text-right">PF (Employee)</TableHead>
                  <TableHead className="text-right">Tax</TableHead>
                  <TableHead className="text-right">Net</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {statement.months.map((m) => (
                  <TableRow key={m.month}>
                    <TableCell>{MONTH_NAMES[m.month - 1]}</TableCell>
                    <TableCell className="text-right">{fmt(m.gross, m.currency)}</TableCell>
                    <TableCell className="text-right">{fmt(m.pf_employee, m.currency)}</TableCell>
                    <TableCell className="text-right">{fmt(m.tax, m.currency)}</TableCell>
                    <TableCell className="text-right">{fmt(m.net, m.currency)}</TableCell>
                  </TableRow>
                ))}
                <TableRow className="font-bold border-t-2">
                  <TableCell>Total</TableCell>
                  <TableCell className="text-right">{fmt(statement.totals.gross, statement.totals.currency)}</TableCell>
                  <TableCell className="text-right">{fmt(statement.totals.pf_employee, statement.totals.currency)}</TableCell>
                  <TableCell className="text-right">{fmt(statement.totals.tax, statement.totals.currency)}</TableCell>
                  <TableCell className="text-right">{fmt(statement.totals.net, statement.totals.currency)}</TableCell>
                </TableRow>
              </TableBody>
            </Table>
            {statement.months.length === 0 && (
              <p className="text-slate-400 text-sm mt-2">No salary slips found for {fetchYear}.</p>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
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

  const [downloadingId, setDownloadingId] = useState<number | null>(null);

  async function handleDownload(s: { id: number; period_year: number; period_month: number }) {
    setDownloadingId(s.id);
    try {
      await downloadSlipPdf(empId, s.period_year, s.period_month);
    } catch {
      alert("Failed to download salary slip. Please try again.");
    } finally {
      setDownloadingId(null);
    }
  }

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
              <TableHeader>
                <TableRow>
                  <TableHead>Period</TableHead>
                  <TableHead>Gross</TableHead>
                  <TableHead>Tax</TableHead>
                  <TableHead>Net</TableHead>
                  <TableHead></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
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
              </TableBody>
            </Table>
          ) : <p className="text-slate-400 text-sm">No salary slips yet.</p>}
        </CardContent>
      </Card>

      <BankDetailsCard empId={empId} />

      <TaxStatementCard empId={empId} />
    </div>
  );
}
