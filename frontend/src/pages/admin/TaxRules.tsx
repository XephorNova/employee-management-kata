import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { listTaxRules, createTaxRule, addTaxBracket, deleteTaxBracket } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

interface Bracket {
  id: number;
  min_income: number;
  max_income: number | null;
  rate_pct: number;
  currency: string;
}

interface TaxRule {
  id: number;
  country: string;
  rule_name: string;
  rule_type: string;
  tax_year: number;
  brackets: Bracket[];
}

const emptyBracket = { min_income: "", max_income: "", rate_pct: "", currency: "USD" };

function BracketRow({ bracket, onDelete }: { bracket: Bracket; onDelete: () => void }) {
  const fmt = (n: number) => new Intl.NumberFormat("en-US", { style: "currency", currency: bracket.currency, maximumFractionDigits: 0 }).format(n);
  return (
    <TableRow>
      <TableCell>{fmt(bracket.min_income)}</TableCell>
      <TableCell>{bracket.max_income != null ? fmt(bracket.max_income) : "∞"}</TableCell>
      <TableCell>{(bracket.rate_pct * 100).toFixed(1)}%</TableCell>
      <TableCell>{bracket.currency}</TableCell>
      <TableCell>
        <Button variant="ghost" size="sm" className="text-red-500 hover:text-red-700 h-7 px-2" onClick={onDelete}>
          ✕
        </Button>
      </TableCell>
    </TableRow>
  );
}

function RuleCard({ rule }: { rule: TaxRule }) {
  const qc = useQueryClient();
  const [expanded, setExpanded] = useState(false);
  const [showAdd, setShowAdd] = useState(false);
  const [form, setForm] = useState(emptyBracket);

  const addMutation = useMutation({
    mutationFn: () => addTaxBracket(rule.id, {
      min_income: Number(form.min_income),
      max_income: form.max_income !== "" ? Number(form.max_income) : null,
      rate_pct: Number(form.rate_pct),
      currency: form.currency,
    }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["tax-rules"] });
      setForm(emptyBracket);
      setShowAdd(false);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (bracketId: number) => deleteTaxBracket(rule.id, bracketId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["tax-rules"] }),
  });

  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="font-medium">{rule.rule_name}</p>
            <p className="text-sm text-slate-500">{rule.country} · {rule.tax_year}</p>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant="outline">{rule.rule_type}</Badge>
            <Badge variant="secondary">{rule.brackets.length} brackets</Badge>
            <Button variant="ghost" size="sm" onClick={() => setExpanded((v) => !v)}>
              {expanded ? "Hide" : "Edit brackets"}
            </Button>
          </div>
        </div>

        {expanded && (
          <div className="mt-4 space-y-3">
            {rule.brackets.length > 0 ? (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Min Income</TableHead>
                    <TableHead>Max Income</TableHead>
                    <TableHead>Rate</TableHead>
                    <TableHead>Currency</TableHead>
                    <TableHead></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {rule.brackets.map((b) => (
                    <BracketRow
                      key={b.id}
                      bracket={b}
                      onDelete={() => deleteMutation.mutate(b.id)}
                    />
                  ))}
                </TableBody>
              </Table>
            ) : (
              <p className="text-sm text-slate-400">No brackets yet.</p>
            )}

            {showAdd ? (
              <div className="border rounded-md p-3 space-y-3 bg-slate-50">
                <p className="text-sm font-medium">Add bracket</p>
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <Label className="text-xs">Min Income</Label>
                    <Input type="number" placeholder="0" value={form.min_income}
                      onChange={(e) => setForm({ ...form, min_income: e.target.value })} />
                  </div>
                  <div>
                    <Label className="text-xs">Max Income (blank = unlimited)</Label>
                    <Input type="number" placeholder="∞" value={form.max_income}
                      onChange={(e) => setForm({ ...form, max_income: e.target.value })} />
                  </div>
                  <div>
                    <Label className="text-xs">Rate (0–1, e.g. 0.20 = 20%)</Label>
                    <Input type="number" step="0.01" min="0" max="1" placeholder="0.20" value={form.rate_pct}
                      onChange={(e) => setForm({ ...form, rate_pct: e.target.value })} />
                  </div>
                  <div>
                    <Label className="text-xs">Currency</Label>
                    <Input placeholder="USD" value={form.currency}
                      onChange={(e) => setForm({ ...form, currency: e.target.value })} />
                  </div>
                </div>
                <div className="flex gap-2">
                  <Button size="sm" onClick={() => addMutation.mutate()} disabled={addMutation.isPending || !form.min_income || !form.rate_pct}>
                    {addMutation.isPending ? "Adding…" : "Add"}
                  </Button>
                  <Button size="sm" variant="ghost" onClick={() => { setShowAdd(false); setForm(emptyBracket); }}>
                    Cancel
                  </Button>
                </div>
              </div>
            ) : (
              <Button size="sm" variant="outline" onClick={() => setShowAdd(true)}>+ Add bracket</Button>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

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
          {rules?.map((rule: TaxRule) => <RuleCard key={rule.id} rule={rule} />)}
        </div>
      )}
    </div>
  );
}
