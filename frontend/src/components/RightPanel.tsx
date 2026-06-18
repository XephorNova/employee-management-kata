import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { bulkGenerateSalarySlips } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { FileText, Plus, Pencil, AlertCircle } from "lucide-react";

interface BulkResult {
  generated: number;
  errors: { employee_id: number; error: string }[];
  total: number;
}

interface RightPanelProps {
  employeeCount?: number;
}

export default function RightPanel({ employeeCount }: RightPanelProps) {
  const navigate = useNavigate();
  const { user } = useAuth();

  const now = new Date();
  const dateStr = now.toLocaleDateString("en-GB", {
    weekday: "short",
    day: "numeric",
    month: "short",
    year: "numeric",
  });

  const nextMonth = now.getMonth() === 11 ? 1 : now.getMonth() + 2;
  const nextYear = now.getMonth() === 11 ? now.getFullYear() + 1 : now.getFullYear();

  const [dialogOpen, setDialogOpen] = useState(false);
  const [month, setMonth] = useState(nextMonth);
  const [year, setYear] = useState(nextYear);
  const [result, setResult] = useState<BulkResult | null>(null);

  const bulkMutation = useMutation({
    mutationFn: () => bulkGenerateSalarySlips(month, year),
    onSuccess: (data: BulkResult) => setResult(data),
  });

  function handleDialogChange(open: boolean) {
    setDialogOpen(open);
    if (!open) {
      setResult(null);
      bulkMutation.reset();
    }
  }

  return (
    <div className="w-56 flex-shrink-0 bg-white rounded-xl border border-slate-200 p-4 flex flex-col gap-5 overflow-y-auto self-start sticky top-0">
      {/* Date */}
      <p className="text-xs font-semibold text-slate-900 border-b border-slate-100 pb-3">
        {dateStr}
      </p>

      {/* Quick Actions */}
      <div className="flex flex-col gap-2">
        <p className="text-[10px] font-semibold uppercase tracking-widest text-slate-400 mb-1">
          Quick Actions
        </p>

        {user?.role === "admin" && (
          <Dialog open={dialogOpen} onOpenChange={handleDialogChange}>
            <DialogTrigger asChild>
              <Button size="sm" className="w-full justify-start gap-2 text-xs h-8">
                <FileText className="w-3.5 h-3.5" />
                Generate Slips
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Generate Salary Slips</DialogTitle>
              </DialogHeader>
              <div className="flex flex-col gap-4 pt-2">
                <div className="flex gap-3 items-end">
                  <div className="flex flex-col gap-1.5">
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
                  <div className="flex flex-col gap-1.5">
                    <Label>Year</Label>
                    <Input
                      type="number"
                      value={year}
                      onChange={(e) => setYear(Number(e.target.value))}
                      className="w-28"
                    />
                  </div>
                </div>
                <Button
                  onClick={() => { setResult(null); bulkMutation.mutate(); }}
                  disabled={bulkMutation.isPending}
                >
                  {bulkMutation.isPending ? "Generating…" : "Generate for all active employees"}
                </Button>
                {bulkMutation.isError && (
                  <p className="text-red-500 text-sm">
                    Failed to generate. Check permissions or try again.
                  </p>
                )}
                {result && (
                  <div className="text-sm space-y-1">
                    <p className="text-green-600 font-medium">
                      Generated {result.generated} of {result.total} slips.
                    </p>
                    {result.errors.length > 0 && (
                      <details>
                        <summary className="text-red-500 cursor-pointer text-xs">
                          {result.errors.length} error(s)
                        </summary>
                        <ul className="mt-1 text-slate-500 text-xs space-y-1">
                          {result.errors.map((e) => (
                            <li key={e.employee_id}>
                              #{e.employee_id}: {e.error}
                            </li>
                          ))}
                        </ul>
                      </details>
                    )}
                  </div>
                )}
              </div>
            </DialogContent>
          </Dialog>
        )}

        <Button
          variant="outline"
          size="sm"
          className="w-full justify-start gap-2 text-xs h-8"
          onClick={() => navigate("/employees")}
        >
          <Plus className="w-3.5 h-3.5" />
          Add Employee
        </Button>
        <Button
          variant="outline"
          size="sm"
          className="w-full justify-start gap-2 text-xs h-8"
          onClick={() => navigate("/admin/tax-rules")}
        >
          <Pencil className="w-3.5 h-3.5" />
          Edit Tax Rules
        </Button>
      </div>

      {/* Employee count badge */}
      {employeeCount !== undefined && (
        <div className="flex flex-col gap-2">
          <p className="text-[10px] font-semibold uppercase tracking-widest text-slate-400 mb-1">
            Active Employees
          </p>
          <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 flex items-center justify-between">
            <div>
              <p className="text-xl font-bold text-amber-600">{employeeCount}</p>
              <p className="text-xs text-amber-700 mt-0.5 leading-tight">employees on record</p>
            </div>
            <AlertCircle className="w-5 h-5 text-amber-400 flex-shrink-0" />
          </div>
        </div>
      )}

      {/* System status */}
      <div className="mt-auto flex flex-col gap-2">
        <p className="text-[10px] font-semibold uppercase tracking-widest text-slate-400 mb-1">
          System
        </p>
        <div className="flex items-center gap-2 text-xs text-slate-500">
          <span className="w-2 h-2 rounded-full bg-green-500 flex-shrink-0" />
          Backend online
        </div>
      </div>
    </div>
  );
}
