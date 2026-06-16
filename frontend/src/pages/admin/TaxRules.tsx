import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { listTaxRules, createTaxRule } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";

export default function TaxRules() {
  const qc = useQueryClient();
  const { data: rules, isLoading } = useQuery({ queryKey: ["tax-rules"], queryFn: listTaxRules });
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ country: "", rule_name: "", rule_type: "income_tax", tax_year: new Date().getFullYear() });

  const createMutation = useMutation({
    mutationFn: () => createTaxRule({ ...form, brackets: [] }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["tax-rules"] }); setShowForm(false); },
  });

  return (
    <div className="space-y-4 max-w-3xl">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Tax Rules</h1>
        <Button size="sm" onClick={() => setShowForm((v) => !v)}>+ New Rule</Button>
      </div>

      {showForm && (
        <Card>
          <CardHeader><CardTitle className="text-base">Create Tax Rule</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div><Label>Country (ISO)</Label><Input value={form.country} onChange={(e) => setForm({ ...form, country: e.target.value })} maxLength={3} /></div>
              <div><Label>Tax Year</Label><Input type="number" value={form.tax_year} onChange={(e) => setForm({ ...form, tax_year: Number(e.target.value) })} /></div>
            </div>
            <div><Label>Rule Name</Label><Input value={form.rule_name} onChange={(e) => setForm({ ...form, rule_name: e.target.value })} /></div>
            <Button onClick={() => createMutation.mutate()} disabled={createMutation.isPending}>
              {createMutation.isPending ? "Creating…" : "Create"}
            </Button>
          </CardContent>
        </Card>
      )}

      {isLoading ? <div className="text-slate-400">Loading…</div> : (
        <div className="space-y-3">
          {rules?.map((rule: { id: number; country: string; rule_name: string; rule_type: string; tax_year: number; brackets: unknown[] }) => (
            <Card key={rule.id}>
              <CardContent className="p-4 flex items-center justify-between">
                <div>
                  <p className="font-medium">{rule.rule_name}</p>
                  <p className="text-sm text-slate-500">{rule.country} · {rule.tax_year}</p>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant="outline">{rule.rule_type}</Badge>
                  <Badge variant="secondary">{(rule.brackets as unknown[]).length} brackets</Badge>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
