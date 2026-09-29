export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:8000";

export type LeadOut = {
  brand_alias: string;
  week: number;
  category: string;
  diagnosis: string;
  severity: number;
  base_score: number;
  memory_adj: number;
  final_score: number;
  rank: number;
  angle: string;
  reason: string;
  evidence_memory_ids: string[];
};

export type PipelineStats = {
  brands_scanned: number;
  diagnosed: number;
  memory_adjusted: number;
  ranked: number;
};

export type ShortlistOut = {
  week: number;
  mode: "on" | "off";
  memory_available: boolean;
  leads: LeadOut[];
  skipped: { brand_alias: string; category: string; reason: string }[];
  pipeline?: PipelineStats;
};

export type SignalPoint = {
  week: number;
  demand_index: number | null;
  seller_count: number;
  buybox_share: number;
  buybox_price: number | null;
  ad_presence: number;
  review_count: number;
};

export type MemoryContextItem = {
  text: string;
  doc_id: string;
  type: string;
  kind?: "outcome" | "pitch" | "snapshot" | "observation" | "other";
};

export type LeadDetail = {
  lead: LeadOut;
  brand: Record<string, unknown>;
  signals: SignalPoint[];
  memory_context: MemoryContextItem[];
};

export type BeliefOut = {
  id: string;
  group: "who_converts" | "which_angle" | "avoid" | "my_mistakes";
  statement: string;
  confidence: number;
  evidence_count: number;
};

export type BeliefDiff = {
  new?: string[];
  removed?: string[];
  strengthened?: string[];
  weakened?: string[];
  reversed?: string[];
  _prev_week?: number;
};

export type BeliefsOut = {
  week: number;
  beliefs: BeliefOut[];
  diff: BeliefDiff;
};

export type MetricsOut = {
  weeks: number[];
  off: WeekMetric[];
  on: WeekMetric[];
  oracle: WeekMetric[];
};

export type WeekMetric = {
  week: number;
  mode: string;
  reply_rate: number;
  meeting_rate: number;
  angle_accuracy: number;
};

export type AnalyticsWeek = {
  week: number;
  scanned: number;
  diagnosed: number;
  shortlisted: number;
  by_diagnosis: Record<string, number>;
  by_angle: Record<string, number>;
  by_category: Record<string, number>;
};

export type AnalyticsOut = {
  weeks: number[];
  totals: Record<string, number>;
  by_week: AnalyticsWeek[];
  diagnosis_totals: Record<string, number>;
  angle_totals: Record<string, number>;
  category_totals: Record<string, number>;
  memory_events_total: number;
};

async function j<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    cache: "no-store",
  });
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}: ${await r.text()}`);
  return r.json() as Promise<T>;
}

export const api = {
  week: () => j<{ current_week: number; season_id: string; seed: number; memory_available: boolean }>("/api/week"),
  shortlist: (week: number, mode: "on" | "off") =>
    j<ShortlistOut>(`/api/shortlist?week=${week}&mode=${mode}`),
  lead: (alias: string, week: number) =>
    j<LeadDetail>(`/api/leads/${encodeURIComponent(alias)}?week=${week}`),
  draft: (alias: string, week: number, angle_override?: string) =>
    j<{ subject: string; body: string; angle: string }>(
      `/api/leads/${encodeURIComponent(alias)}/draft?week=${week}`,
      { method: "POST", body: JSON.stringify({ angle_override }) },
    ),
  approve: (alias: string, week: number) =>
    j<{ ok: boolean }>(
      `/api/leads/${encodeURIComponent(alias)}/approve?week=${week}`,
      { method: "POST", body: "{}" },
    ),
  outcome: (alias: string, week: number, type: string, reason_text = "", revisit_after_week?: number) =>
    j<{ ok: boolean }>(
      `/api/pitches/${encodeURIComponent(alias)}/outcome?week=${week}`,
      { method: "POST", body: JSON.stringify({ type, reason_text, revisit_after_week }) },
    ),
  advance: (to_week: number) =>
    j<{ current_week: number }>(`/api/week/advance?to_week=${to_week}`, { method: "POST", body: "{}" }),
  reset: (to_week = 44) =>
    j<{ ok: boolean; operation_id?: string }>(
      `/api/demo/reset?to_week=${to_week}`,
      { method: "POST", body: "{}" },
    ),
  beliefs: (week: number) => j<BeliefsOut>(`/api/beliefs?week=${week}`),
  metrics: () => j<MetricsOut>("/api/metrics/learning"),
  analytics: () => j<AnalyticsOut>("/api/analytics"),
  health: () => j<{ ok: boolean; hindsight_reachable: boolean; groq_reachable: boolean; demo_mode: boolean }>("/api/health"),
};
