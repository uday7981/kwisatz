"use client";

import { useQuery } from "@tanstack/react-query";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  LineChart,
  Line,
  Legend,
} from "recharts";
import { api, type AnalyticsOut } from "@/lib/api";
import { angleLabel, categoryLabel, diagnosisLabel } from "@/lib/format";

const DIAGNOSIS_COLORS: Record<string, string> = {
  D1: "#0e6e6a", // signal
  D2: "#c7861a", // insight
  D3: "#b4461f", // risk
  D4: "#5b6573",
  D5: "#2f7a4f",
  D6: "#8a96a3",
};

const ANGLE_COLORS: Record<string, string> = {
  brand_protection: "#0e6e6a",
  inventory_planning: "#c7861a",
  listing_and_reviews: "#b4461f",
  map_enforcement: "#5b6573",
  advertising: "#2f7a4f",
  growth_partnership: "#8a96a3",
};

export default function Analytics() {
  const q = useQuery({ queryKey: ["analytics"], queryFn: api.analytics });

  return (
    <div className="space-y-10">
      <header>
        <div className="text-xs uppercase tracking-wider text-ink-muted">Analytics</div>
        <h1 className="font-display text-4xl font-semibold leading-none">Season overview</h1>
        <div className="text-sm text-ink-muted mt-2">
          Aggregated across weeks {q.data?.weeks[0] ?? "-"}–{q.data?.weeks.at(-1) ?? "-"}
        </div>
      </header>

      {q.isLoading && <div className="text-ink-muted text-sm">Computing season stats…</div>}
      {q.error && <div className="text-risk text-sm">Failed to load analytics.</div>}

      {q.data && (
        <>
          <TotalsRow data={q.data} />
          <DiagnosisChart data={q.data} />
          <AngleBreakdown data={q.data} />
          <CategoryBreakdown data={q.data} />
        </>
      )}
    </div>
  );
}

function TotalsRow({ data }: { data: AnalyticsOut }) {
  const items = [
    { label: "Unique brands watched", value: data.totals.unique_brands, hint: "in the seed universe" },
    { label: "Signal scans", value: data.totals.brands_scanned, hint: "brand-weeks scored" },
    { label: "Diagnoses fired", value: data.totals.diagnoses_fired, hint: "D1-D5 triggers this season" },
    { label: "Shortlist slots", value: data.totals.shortlisted, hint: "brand-weeks pitched" },
    { label: "Memory events", value: data.memory_events_total, hint: "retain / recall / reflect logged" },
  ];
  return (
    <div className="grid grid-cols-2 md:grid-cols-5 gap-8 pb-6 border-b border-rule">
      {items.map((i) => (
        <div key={i.label}>
          <div className="text-xs uppercase tracking-wider text-ink-muted">{i.label}</div>
          <div className="font-display text-3xl tabular mt-1 leading-none">{i.value}</div>
          <div className="text-xs text-ink-muted mt-1">{i.hint}</div>
        </div>
      ))}
    </div>
  );
}

function DiagnosisChart({ data }: { data: AnalyticsOut }) {
  const codes = Object.keys(data.diagnosis_totals).sort();
  const chartData = data.by_week.map((w) => {
    const row: Record<string, number> = { week: w.week };
    codes.forEach((c) => {
      row[c] = w.by_diagnosis[c] ?? 0;
    });
    return row;
  });

  return (
    <section className="space-y-3">
      <div className="flex items-baseline gap-3">
        <div className="text-xs uppercase tracking-wider text-ink font-medium">Shortlist mix by diagnosis</div>
        <div className="text-xs text-ink-muted">how many of each problem type reach the top 12 each week</div>
      </div>
      <div className="h-[280px]">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} margin={{ top: 10, right: 24, left: 0, bottom: 10 }}>
            <CartesianGrid stroke="var(--rule)" strokeDasharray="3 6" vertical={false} />
            <XAxis dataKey="week" stroke="var(--ink-muted)" fontSize={11} tickLine={false} />
            <YAxis stroke="var(--ink-muted)" fontSize={11} tickLine={false} axisLine={false} />
            <Tooltip
              formatter={(v, name) => {
                const n = Number(v ?? 0);
                return [`${n} brand${n === 1 ? "" : "s"}`, diagnosisLabel(String(name))];
              }}
              contentStyle={{ fontSize: 12, borderColor: "var(--rule)" }}
            />
            {codes.map((c) => (
              <Bar key={c} dataKey={c} stackId="a" fill={DIAGNOSIS_COLORS[c] ?? "#8a96a3"} name={c} />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div className="flex gap-4 text-xs text-ink-muted flex-wrap">
        {codes.map((c) => (
          <span key={c} className="inline-flex items-center gap-1.5">
            <span className="inline-block w-2 h-2 rounded-sm" style={{ background: DIAGNOSIS_COLORS[c] ?? "#8a96a3" }} />
            {diagnosisLabel(c)}
            <span className="tabular text-ink">{data.diagnosis_totals[c]}</span>
          </span>
        ))}
      </div>
    </section>
  );
}

function AngleBreakdown({ data }: { data: AnalyticsOut }) {
  const entries = Object.entries(data.angle_totals).sort((a, b) => b[1] - a[1]);
  const max = Math.max(1, ...entries.map(([, v]) => v));
  return (
    <section className="space-y-3">
      <div className="flex items-baseline gap-3">
        <div className="text-xs uppercase tracking-wider text-ink font-medium">Pitch angles chosen this season</div>
        <div className="text-xs text-ink-muted">how often each angle appears in the shortlist</div>
      </div>
      <div className="space-y-2 pt-2">
        {entries.map(([angle, count]) => (
          <div key={angle} className="flex items-center gap-4">
            <div className="w-48 text-sm text-ink">{angleLabel(angle)}</div>
            <div className="flex-1 h-3 rounded-full bg-rule/40 overflow-hidden">
              <div
                className="h-full rounded-full"
                style={{
                  width: `${(count / max) * 100}%`,
                  background: ANGLE_COLORS[angle] ?? "#8a96a3",
                }}
              />
            </div>
            <div className="w-14 text-right text-sm tabular text-ink-muted">{count}</div>
          </div>
        ))}
      </div>
    </section>
  );
}

function CategoryBreakdown({ data }: { data: AnalyticsOut }) {
  const chartData = data.by_week.map((w) => {
    const row: Record<string, number> = { week: w.week };
    Object.keys(data.category_totals).forEach((c) => {
      row[c] = w.by_category[c] ?? 0;
    });
    return row;
  });
  const categories = Object.keys(data.category_totals).sort();
  const palette = ["#0e6e6a", "#c7861a", "#5b6573"];
  return (
    <section className="space-y-3">
      <div className="flex items-baseline gap-3">
        <div className="text-xs uppercase tracking-wider text-ink font-medium">Category rotation across the season</div>
        <div className="text-xs text-ink-muted">shortlist mix week by week</div>
      </div>
      <div className="h-[240px]">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData} margin={{ top: 10, right: 24, left: 0, bottom: 10 }}>
            <CartesianGrid stroke="var(--rule)" strokeDasharray="3 6" vertical={false} />
            <XAxis dataKey="week" stroke="var(--ink-muted)" fontSize={11} tickLine={false} />
            <YAxis stroke="var(--ink-muted)" fontSize={11} tickLine={false} axisLine={false} />
            <Tooltip
              formatter={(v, name) => [`${Number(v ?? 0)}`, categoryLabel(String(name))]}
              contentStyle={{ fontSize: 12, borderColor: "var(--rule)" }}
            />
            <Legend
              iconType="plainline"
              wrapperStyle={{ fontSize: 12, color: "var(--ink-muted)" }}
              formatter={(name: string) => categoryLabel(name)}
            />
            {categories.map((c, i) => (
              <Line
                key={c}
                type="monotone"
                dataKey={c}
                stroke={palette[i % palette.length]}
                strokeWidth={2}
                dot={false}
                name={c}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}
