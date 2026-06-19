import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import {
  calculateNetSalary,
  type CalculatorRequest,
  type CalculatorResponse,
} from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

function fmt(n: number, currency = "USD") {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    maximumFractionDigits: 0,
  }).format(n);
}

export default function Calculator() {
  const [country, setCountry] = useState("");
  const [baseSalary, setBaseSalary] = useState("");
  const [payFrequency, setPayFrequency] = useState<"monthly" | "annual">("monthly");
  const [allowances, setAllowances] = useState("0");
  const [otherDeductions, setOtherDeductions] = useState("0");
  const [currency, setCurrency] = useState("USD");

  const mutation = useMutation({
    mutationFn: (data: CalculatorRequest) => calculateNetSalary(data),
  });

  function handleCountryChange(v: string) { setCountry(v); mutation.reset(); }
  function handleCurrencyChange(v: string) { setCurrency(v); mutation.reset(); }
  function handleBaseSalaryChange(v: string) { setBaseSalary(v); mutation.reset(); }
  function handleFrequencyChange(v: "monthly" | "annual") { setPayFrequency(v); mutation.reset(); }
  function handleAllowancesChange(v: string) { setAllowances(v); mutation.reset(); }
  function handleOtherDeductionsChange(v: string) { setOtherDeductions(v); mutation.reset(); }

  function handleSubmit() {
    mutation.mutate({
      country: country.trim().toUpperCase(),
      base_salary: Number(baseSalary),
      pay_frequency: payFrequency,
      allowances: Number(allowances) || 0,
      other_deductions: Number(otherDeductions) || 0,
      currency: currency.trim().toUpperCase() || "USD",
    });
  }

  const result: CalculatorResponse | undefined = mutation.data;
  const canSubmit = country.trim().length > 0 && Number(baseSalary) > 0 && currency.trim().length === 3;

  return (
    <div className="max-w-3xl space-y-4">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
        {/* Inputs */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Inputs</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label htmlFor="calc-country">Country (ISO code)</Label>
              <Input
                id="calc-country"
                placeholder="e.g. USA, IND"
                value={country}
                onChange={(e) => handleCountryChange(e.target.value)}
                maxLength={3}
              />
            </div>
            <div>
              <Label htmlFor="calc-currency">Currency (ISO code)</Label>
              <Input
                id="calc-currency"
                placeholder="e.g. USD, INR"
                value={currency}
                onChange={(e) => handleCurrencyChange(e.target.value)}
                maxLength={3}
              />
            </div>
            <div>
              <Label htmlFor="calc-salary">Base Salary</Label>
              <Input
                id="calc-salary"
                type="number"
                placeholder="0"
                value={baseSalary}
                onChange={(e) => handleBaseSalaryChange(e.target.value)}
              />
            </div>
            <div>
              <Label>Pay Frequency</Label>
              <div className="flex gap-2 mt-1">
                <Button
                  size="sm"
                  variant={payFrequency === "monthly" ? "default" : "outline"}
                  onClick={() => handleFrequencyChange("monthly")}
                >
                  Monthly
                </Button>
                <Button
                  size="sm"
                  variant={payFrequency === "annual" ? "default" : "outline"}
                  onClick={() => handleFrequencyChange("annual")}
                >
                  Annual
                </Button>
              </div>
            </div>
            <div>
              <Label htmlFor="calc-allowances">Allowances (monthly)</Label>
              <Input
                id="calc-allowances"
                type="number"
                placeholder="0"
                value={allowances}
                onChange={(e) => handleAllowancesChange(e.target.value)}
              />
            </div>
            <div>
              <Label htmlFor="calc-deductions">Other Deductions (monthly)</Label>
              <Input
                id="calc-deductions"
                type="number"
                placeholder="0"
                value={otherDeductions}
                onChange={(e) => handleOtherDeductionsChange(e.target.value)}
              />
            </div>
            <Button
              className="w-full"
              onClick={handleSubmit}
              disabled={!canSubmit || mutation.isPending}
            >
              {mutation.isPending ? "Calculating…" : "Calculate"}
            </Button>
            {mutation.isError && (
              <p className="text-sm text-red-600">
                Calculation failed. Please try again.
              </p>
            )}
          </CardContent>
        </Card>

        {/* Results */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Result</CardTitle>
          </CardHeader>
          <CardContent>
            {!result ? (
              <p className="text-slate-400 text-sm">
                Enter your details and click Calculate.
              </p>
            ) : (
              <div className="space-y-4">
                {result.no_rules_warning && (
                  <div className="rounded-md bg-amber-50 border border-amber-200 px-3 py-2 text-sm text-amber-700">
                    No tax or PF rules found for{" "}
                    <strong>{country.toUpperCase()}</strong> — result shows
                    gross only.
                  </div>
                )}
                <div>
                  <p className="text-xs text-slate-500 uppercase tracking-wide">
                    Net Take-Home / mo
                  </p>
                  <p className="text-3xl font-bold text-indigo-600">
                    {fmt(result.net_take_home, result.currency)}
                  </p>
                </div>
                <table className="w-full text-sm">
                  <tbody className="divide-y divide-slate-100">
                    <tr>
                      <td className="py-1.5 text-slate-600">Gross Salary</td>
                      <td className="py-1.5 text-right font-medium">
                        {fmt(result.gross_salary, result.currency)}
                      </td>
                    </tr>
                    <tr>
                      <td className="py-1.5 text-slate-600">− PF (Employee)</td>
                      <td className="py-1.5 text-right text-red-600">
                        −{fmt(result.pf_employee_contribution, result.currency)}
                      </td>
                    </tr>
                    <tr>
                      <td className="py-1.5 text-slate-600">− Income Tax</td>
                      <td className="py-1.5 text-right text-red-600">
                        −{fmt(result.tax_deducted, result.currency)}
                      </td>
                    </tr>
                    <tr>
                      <td className="py-1.5 text-slate-600">
                        − Other Deductions
                      </td>
                      <td className="py-1.5 text-right text-red-600">
                        −{fmt(result.other_deductions, result.currency)}
                      </td>
                    </tr>
                    <tr className="border-t-2 border-slate-300 font-semibold">
                      <td className="py-1.5">= Net Take-Home</td>
                      <td className="py-1.5 text-right text-indigo-600">
                        {fmt(result.net_take_home, result.currency)}
                      </td>
                    </tr>
                  </tbody>
                </table>
                {result.pf_employer_contribution > 0 && (
                  <p className="text-xs text-slate-500">
                    Your employer contributes an additional{" "}
                    {fmt(result.pf_employer_contribution, result.currency)} to
                    your PF.
                  </p>
                )}
                {(result.tax_rule_applied || result.pf_rule_applied) && (
                  <p className="text-xs text-slate-400">
                    Rules applied:{" "}
                    {[result.tax_rule_applied, result.pf_rule_applied]
                      .filter(Boolean)
                      .join(" · ")}
                  </p>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
