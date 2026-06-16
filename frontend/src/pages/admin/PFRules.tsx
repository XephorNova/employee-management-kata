import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { listPFRules, createPFRule } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export default function PFRules() {
  const qc = useQueryClient();
  const { data: rules, isLoading } = useQuery({ queryKey: ["pf-rules"], queryFn: listPFRules });
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    country: "", rule_name: "", employee_contribution_pct: 0.06,
    employer_contribution_pct: 0.06, applicable_salary_cap: "", effective_from_date: "",
  });

  const createMutation = useMutation({
    mutationFn: () => createPFRule({ ...form, applicable_salary_cap: form.applicable_salary_cap ? Number(form.applicable_salary_cap) : null }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["pf-rules"] }); setShowForm(false); },
  });

  return (
    <div className="space-y-4 max-w-3xl">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">PF Rules</h1>
        <Button size="sm" onClick={() => setShowForm((v) => !v)}>+ New Rule</Button>
      </div>

      {showForm && (
        <Card>
          <CardHeader><CardTitle className="text-base">Create PF Rule</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div><Label>Country (ISO)</Label><Input value={form.country} onChange={(e) => setForm({ ...form, country: e.target.value })} maxLength={3} /></div>
              <div><Label>Effective Date</Label><Input type="date" value={form.effective_from_date} onChange={(e) => setForm({ ...form, effective_from_date: e.target.value })} /></div>
            </div>
            <div><Label>Rule Name</Label><Input value={form.rule_name} onChange={(e) => setForm({ ...form, rule_name: e.target.value })} /></div>
            <div className="grid grid-cols-3 gap-3">
              <div><Label>Employee % </Label><Input type="number" step="0.01" value={form.employee_contribution_pct} onChange={(e) => setForm({ ...form, employee_contribution_pct: Number(e.target.value) })} /></div>
              <div><Label>Employer %</Label><Input type="number" step="0.01" value={form.employer_contribution_pct} onChange={(e) => setForm({ ...form, employer_contribution_pct: Number(e.target.value) })} /></div>
              <div><Label>Salary Cap</Label><Input type="number" value={form.applicable_salary_cap} onChange={(e) => setForm({ ...form, applicable_salary_cap: e.target.value })} placeholder="None" /></div>
            </div>
            <Button onClick={() => createMutation.mutate()} disabled={createMutation.isPending}>
              {createMutation.isPending ? "Creating…" : "Create"}
            </Button>
          </CardContent>
        </Card>
      )}

      {isLoading ? <div className="text-slate-400">Loading…</div> : (
        <div className="space-y-3">
          {rules?.map((rule: { id: number; country: string; rule_name: string; employee_contribution_pct: number; employer_contribution_pct: number }) => (
            <Card key={rule.id}>
              <CardContent className="p-4">
                <p className="font-medium">{rule.rule_name}</p>
                <p className="text-sm text-slate-500">
                  {rule.country} · Employee {(rule.employee_contribution_pct * 100).toFixed(1)}% · Employer {(rule.employer_contribution_pct * 100).toFixed(1)}%
                </p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
