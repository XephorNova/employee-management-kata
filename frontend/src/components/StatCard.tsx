import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

interface StatCardProps {
  label: string;
  value: string | number;
  icon: ReactNode;
  iconBg: string;        // Tailwind bg class, e.g. "bg-amber-100"
  change?: string;       // e.g. "↑ 12% this month"
  changeUp?: boolean;    // true → green text, false/undefined → slate
}

export default function StatCard({ label, value, icon, iconBg, change, changeUp }: StatCardProps) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-4 flex flex-col gap-3">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-2xl font-bold text-slate-900">{value}</p>
          <p className="text-sm text-slate-500 mt-0.5">{label}</p>
        </div>
        <div className={cn("w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0", iconBg)}>
          {icon}
        </div>
      </div>
      {change && (
        <p className={cn("text-xs font-medium", changeUp ? "text-green-500" : "text-slate-400")}>
          {change}
        </p>
      )}
    </div>
  );
}
