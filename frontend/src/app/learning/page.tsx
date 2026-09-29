"use client";

import { useQuery } from "@tanstack/react-query";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
import { api, type WeekMetric } from "@/lib/api";
import { pct } from "@/lib/format";

export default function Learning() {
  const metrics = useQuery({ queryKey: ["metrics"], queryFn: api.metrics });

  const chartData = (metrics.data?.weeks ?? []).map((w) => ({
    week: w,
    off: pctOr(metrics.data?.off, w, "meeting_rate"),
    on: pctOr(metrics.data?.on, w, "meeting_rate"),
    oracle: pctOr(metrics.data?.oracle, w, "meeting_rate"),
  }));

  const avg = (rows: WeekMetric[] | undefined, key: keyof WeekMetric) => {
    if (!rows || !rows.length) return 0;
    const nums = rows.map((r) => Number(r[key] ?? 0));
    return nums.reduce((a, b) => a + b, 0) / nums.length;
  };
  const replyLift = () => {
    if (!metrics.data?.on?.length || !metrics.data?.off?.length) return 0;
    return avg(metrics.data.on, "reply_rate") - avg(metrics.data.off, "reply_rate");
  };

  return (
    <div className="space-y-8">
      <header>
        <div className="text-xs uppercase tracking-wider text-ink-muted">Evaluation</div>
        <h1 className="font-display text-4xl font-semibold leading-none">Learning</h1>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-8 pb-4 border-b border-rule">
        <Metric label="Reply-rate lift" value={pct(replyLift(), 1)} sub="memory on vs off" />
        <Metric
          label="Meeting rate"
          value={pct(avg(metrics.data?.on, "meeting_rate"), 1)}
          sub="memory on, top 10"
        />
        <Metric
          label="Angle accuracy"
          value={pct(avg(metrics.data?.on, "angle_accuracy"), 0)}
          sub="memory on"
        />
      </div>

      <div className="space-y-3">
        <div className="text-xs uppercase tracking-wider text-ink-muted">
          Meeting rate of top 10, by week
        </div>
        <div className="h-[320px]">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData} margin={{ top: 10, right: 24, left: 0, bottom: 20 }}>
              <CartesianGrid stroke="var(--rule)" strokeDasharray="3 6" vertical={false} />
              <XAxis dataKey="week" stroke="var(--ink-muted)" fontSize={11} tickLine={false} />
              <YAxis stroke="var(--ink-muted)" fontSize={11} tickLine={false} axisLine={false} tickFormatter={(v) => `${(v * 100).toFixed(0)}%`} />
              <Tooltip formatter={(v) => `${(Number(v ?? 0) * 100).toFixed(0)}%`} />
              <Line type="monotone" dataKey="off" stroke="var(--neutral-series)" strokeWidth={1.5} dot={false} name="memory off" />
              <Line type="monotone" dataKey="on" stroke="var(--insight)" strokeWidth={2} dot={false} name="memory on" />
              <Line type="monotone" dataKey="oracle" stroke="var(--ink)" strokeWidth={1} strokeDasharray="4 4" dot={false} name="oracle (upper bound)" />
            </LineChart>
          </ResponsiveContainer>
        </div>
        <div className="flex gap-6 text-xs text-ink-muted pt-2">
          <span><span className="inline-block w-2 h-0.5 bg-neutral-series mr-1.5 align-middle" />memory off</span>
          <span><span className="inline-block w-2 h-0.5 bg-insight mr-1.5 align-middle" />memory on</span>
          <span><span className="inline-block w-2 border-t border-dashed border-ink mr-1.5 align-middle" />oracle (upper bound)</span>
        </div>
      </div>
    </div>
  );
}

function pctOr(rows: WeekMetric[] | undefined, w: number, key: keyof WeekMetric) {
  if (!rows) return 0;
  const row = rows.find((r) => r.week === w);
  return Number(row?.[key] ?? 0);
}

function Metric({ label, value, sub }: { label: string; value: string; sub: string }) {
  return (
    <div>
      <div className="text-xs uppercase tracking-wider text-ink-muted">{label}</div>
      <div className="font-display text-3xl tabular mt-1 leading-none">{value}</div>
      <div className="text-xs text-ink-muted mt-1">{sub}</div>
    </div>
  );
}
