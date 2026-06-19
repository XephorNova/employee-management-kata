import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { aiQuery, getAIUsage, type AIUsage } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from "recharts";

const COLORS = ["#6366f1", "#22c55e", "#f59e0b", "#ef4444", "#8b5cf6", "#06b6d4"];

const SUGGESTIONS = [
  "What is the average salary in Engineering?",
  "Which department has the most employees?",
  "Show me the top 5 earners",
  "What is the salary distribution?",
  "How many employees are in each country?",
];

interface Message {
  role: "user" | "assistant";
  content: string;
  data?: unknown;
  chart_type?: string;
  tool_used?: string | null;
  from_cache?: boolean;
}

function TokenGauge({ usage }: { usage: AIUsage | undefined }) {
  if (!usage) return null;
  const pct = (usage.tokens_used / usage.tokens_limit) * 100;
  const barColor = pct > 95 ? "bg-red-500" : pct > 80 ? "bg-amber-500" : "bg-indigo-500";
  const resetTime = new Date(usage.resets_at).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });
  return (
    <div className="space-y-1 p-3 rounded-lg border border-slate-200 bg-white">
      <div className="flex justify-between text-xs text-slate-500">
        <span>
          {usage.tokens_used.toLocaleString()} / {usage.tokens_limit.toLocaleString()} tokens used today
        </span>
        <span>Resets at {resetTime}</span>
      </div>
      <div className="h-1.5 w-full bg-slate-200 rounded-full overflow-hidden">
        <div
          className={`h-full ${barColor} rounded-full transition-all duration-500`}
          style={{ width: `${Math.min(pct, 100)}%` }}
        />
      </div>
    </div>
  );
}

function ChartBlock({ data, chartType }: { data: unknown; chartType: string }) {
  const arr = Array.isArray(data) ? data : [];
  if (!arr.length) return null;

  if (chartType === "bar") {
    const keys = Object.keys(arr[0] as Record<string, unknown>).filter(
      (k) => k !== "group" && k !== "department" && k !== "range_start" && k !== "range_end"
    );
    const xKey = Object.keys(arr[0] as Record<string, unknown>)[0];
    return (
      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={arr}>
          <XAxis dataKey={xKey} tick={{ fontSize: 11 }} />
          <YAxis tick={{ fontSize: 11 }} />
          <Tooltip />
          {keys.map((k, i) => (
            <Bar key={k} dataKey={k} fill={COLORS[i % COLORS.length]} radius={[3, 3, 0, 0]} />
          ))}
        </BarChart>
      </ResponsiveContainer>
    );
  }

  if (chartType === "pie") {
    return (
      <ResponsiveContainer width="100%" height={200}>
        <PieChart>
          <Pie data={arr} dataKey="count" nameKey="group" cx="50%" cy="50%" outerRadius={70}>
            {arr.map((_: unknown, i: number) => (
              <Cell key={String(i)} fill={COLORS[i % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip />
        </PieChart>
      </ResponsiveContainer>
    );
  }

  if (chartType === "table" && arr.length) {
    const headers = Object.keys(arr[0] as Record<string, unknown>);
    return (
      <div className="overflow-x-auto mt-2">
        <table className="text-xs w-full">
          <thead>
            <tr>
              {headers.map((h) => (
                <th key={h} className="text-left px-2 py-1 bg-slate-100 font-medium">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {arr.slice(0, 20).map((row: unknown, i: number) => (
              <tr key={i} className="border-t">
                {headers.map((h) => (
                  <td key={h} className="px-2 py-1">
                    {String((row as Record<string, unknown>)[h] ?? "")}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  return null;
}

export default function Insights() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [limitReached, setLimitReached] = useState(false);
  const queryClient = useQueryClient();

  const { data: usage } = useQuery({
    queryKey: ["ai-usage"],
    queryFn: getAIUsage,
    refetchInterval: 60_000,
  });

  const mutation = useMutation({
    mutationFn: (question: string) => aiQuery(question),
    onSuccess: (data, question) => {
      setMessages((prev) => [
        ...prev,
        { role: "user", content: question },
        {
          role: "assistant",
          content: data.answer,
          data: data.data,
          chart_type: data.chart_type,
          tool_used: data.tool_used,
          from_cache: data.from_cache,
        },
      ]);
      queryClient.invalidateQueries({ queryKey: ["ai-usage"] });
    },
    onError: (error: unknown) => {
      const status = (error as { response?: { status?: number } })?.response?.status;
      if (status === 429) {
        setLimitReached(true);
        queryClient.invalidateQueries({ queryKey: ["ai-usage"] });
      }
    },
  });

  function ask(question: string) {
    if (!question.trim() || limitReached) return;
    setInput("");
    mutation.mutate(question);
  }

  return (
    <div className="space-y-4 max-w-3xl">
      <h1 className="text-2xl font-bold">AI Insights</h1>
      <p className="text-slate-500 text-sm">
        Ask natural language questions about employee compensation and headcount.
      </p>

      <TokenGauge usage={usage} />

      {limitReached && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          Daily token limit reached. You can ask more questions tomorrow.
        </div>
      )}

      {messages.length === 0 && !limitReached && (
        <div className="space-y-2">
          <p className="text-xs text-slate-400 uppercase font-medium">Try asking…</p>
          <div className="flex flex-wrap gap-2">
            {SUGGESTIONS.map((s) => (
              <button
                key={s}
                onClick={() => ask(s)}
                className="text-sm px-3 py-1.5 rounded-full border border-slate-200 hover:border-indigo-300 hover:text-indigo-600 transition-colors"
              >
                {s}
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="space-y-4">
        {messages.map((msg, i) => (
          <div key={i} className={msg.role === "user" ? "text-right" : ""}>
            <Card className={msg.role === "user" ? "inline-block bg-indigo-600 text-white" : ""}>
              <CardContent className="p-3 text-sm whitespace-pre-wrap">
                {msg.content}
                {msg.role === "assistant" && !!msg.data && msg.chart_type !== "none" && (
                  <ChartBlock data={msg.data} chartType={msg.chart_type!} />
                )}
                {msg.role === "assistant" && msg.tool_used && (
                  <p className="text-xs text-slate-400 mt-2">Tool: {msg.tool_used}</p>
                )}
                {msg.role === "assistant" && msg.from_cache && (
                  <p className="text-xs text-slate-400 mt-1">Cached · 0 tokens used</p>
                )}
              </CardContent>
            </Card>
          </div>
        ))}
        {mutation.isPending && (
          <div className="text-slate-400 text-sm animate-pulse">Thinking…</div>
        )}
      </div>

      <div className="flex gap-2 sticky bottom-0 bg-slate-50 pt-2">
        <Input
          placeholder="Ask a question about salary data…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && ask(input)}
          disabled={mutation.isPending || limitReached}
        />
        <Button
          onClick={() => ask(input)}
          disabled={mutation.isPending || !input.trim() || limitReached}
        >
          Ask
        </Button>
      </div>
    </div>
  );
}
