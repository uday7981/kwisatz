"use client";

import { useQuery, useMutation } from "@tanstack/react-query";
import { useState, use as usePromise } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import { angleLabel, categoryLabel, diagnosisLabel, pct, score } from "@/lib/format";
import { Sparkline } from "@/components/sparkline";
import { useKey } from "@/lib/keys";

const OUTCOME_KEYS: [string, string, string][] = [
  ["1", "no_reply", "no reply"],
  ["2", "reply", "reply"],
  ["3", "meeting", "meeting"],
  ["4", "signed", "signed"],
  ["5", "declined", "declined"],
  ["6", "not_now", "not now"],
];

const KIND_META: Record<string, { label: string; color: string }> = {
  outcome: { label: "outcome", color: "text-signal" },
  pitch: { label: "pitch history", color: "text-ink-muted" },
  snapshot: { label: "signal", color: "text-insight" },
  observation: { label: "observation", color: "text-ink-muted" },
  other: { label: "note", color: "text-ink-muted" },
};

function MemoryItem({ m }: { m: { text: string; kind?: string } }) {
  const meta = KIND_META[m.kind ?? "other"] ?? KIND_META.other;
  return (
    <li className="text-sm border-l-2 border-rule pl-3 space-y-1">
      <div className={`text-[10px] uppercase tracking-wider ${meta.color}`}>
        {meta.label}
      </div>
      <div className="text-ink-muted leading-snug">{m.text}</div>
    </li>
  );
}

export default function BrandDossier(props: {
  params: Promise<{ alias: string }>;
}) {
  const { alias: aliasEnc } = usePromise(props.params);
  const alias = decodeURIComponent(aliasEnc);
  const search = useSearchParams();
  const router = useRouter();
  const week = Number(search.get("week") ?? 44);

  const lead = useQuery({ queryKey: ["lead", alias, week], queryFn: () => api.lead(alias, week) });
  const [draft, setDraft] = useState<{ subject: string; body: string; angle: string } | null>(null);

  const mDraft = useMutation({
    mutationFn: (angle?: string) => api.draft(alias, week, angle),
    onSuccess: (d) => setDraft(d),
  });
  const mApprove = useMutation({ mutationFn: () => api.approve(alias, week) });
  const mOutcome = useMutation({
    mutationFn: (t: string) => api.outcome(alias, week, t, ""),
  });

  useKey("a", () => {
    if (draft && !mApprove.isPending && !mApprove.isSuccess) mApprove.mutate();
    else if (!draft && !mDraft.isPending) mDraft.mutate(undefined);
  }, [draft, mApprove.isPending, mApprove.isSuccess, mDraft.isPending]);
  useKey(
    OUTCOME_KEYS.map(([k]) => k),
    (e) => {
      if (!mApprove.isSuccess) return;
      const pair = OUTCOME_KEYS.find(([k]) => k === e.key);
      if (pair) mOutcome.mutate(pair[1]);
    },
    [mApprove.isSuccess, mOutcome.mutate],
  );
  useKey("[", () => router.push(`?week=${Math.max(41, week - 1)}`), [week, router]);
  useKey("]", () => router.push(`?week=${Math.min(52, week + 1)}`), [week, router]);
  useKey("Escape", () => router.push("/"), [router]);

  if (lead.isLoading) return <div className="text-ink-muted text-sm">Loading dossier...</div>;
  if (lead.error || !lead.data) return <div className="text-risk text-sm">Not found for this week.</div>;

  const { lead: l, brand, signals, memory_context } = lead.data;
  const buyboxSeries = signals.map((s) => s.buybox_share);
  const sellerSeries = signals.map((s) => s.seller_count);
  const reviewSeries = signals.map((s) => s.review_count);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_300px] gap-12">
      <div className="space-y-10">
        <header>
          <button
            onClick={() => router.push("/")}
            className="text-xs text-ink-muted hover:text-ink mb-3"
          >
            ← back
          </button>
          <h1 className="font-display text-4xl font-semibold leading-tight">{alias}</h1>
          <div className="text-sm text-ink-muted mt-2">
            {categoryLabel(String(brand.category))} · {String(brand.n_products)} products ·{" "}
            avg rating <span className="tabular">{Number(brand.avg_rating).toFixed(2)}</span> ·{" "}
            price <span className="tabular">${Number(brand.price_min).toFixed(0)}–${Number(brand.price_max).toFixed(0)}</span>
          </div>
        </header>

        <section className="space-y-2">
          <div className="text-xs uppercase tracking-wider text-ink-muted">Diagnosis</div>
          <div className="font-display text-2xl leading-tight">{diagnosisLabel(l.diagnosis)}</div>
          <p className="text-sm text-ink-muted max-w-prose">{l.reason}</p>
        </section>

        <section className="space-y-4">
          <div className="text-xs uppercase tracking-wider text-ink-muted">Signals · last 12 weeks</div>
          <div className="grid grid-cols-3 gap-8">
            <SignalCard title="Buy Box share" value={pct(buyboxSeries.at(-1) ?? 0)} series={buyboxSeries} color="var(--risk)" />
            <SignalCard title="Sellers" value={String(sellerSeries.at(-1) ?? 0)} series={sellerSeries} />
            <SignalCard title="Reviews / wk" value={String(reviewSeries.at(-1) ?? 0)} series={reviewSeries} color="var(--signal)" />
          </div>
        </section>

        <section className="space-y-3">
          <div className="flex items-baseline gap-3">
            <div className="text-xs uppercase tracking-wider text-ink-muted">Draft</div>
            <div className="text-xs text-ink-muted">
              angle: <span className="text-ink">{angleLabel(draft?.angle ?? l.angle)}</span>
            </div>
            <div className="ml-auto flex gap-3">
              <button
                onClick={() => mDraft.mutate(undefined)}
                className="text-xs text-ink-muted hover:text-ink"
              >
                {draft ? "regenerate" : "generate"}
              </button>
              <button
                onClick={() => mApprove.mutate()}
                disabled={!draft || mApprove.isPending}
                className="text-xs px-3 py-1 rounded bg-signal text-white disabled:opacity-40"
              >
                {mApprove.isSuccess ? "approved" : "approve · A"}
              </button>
            </div>
          </div>
          {draft ? (
            <div className="space-y-2 text-sm">
              <div className="font-medium">{draft.subject}</div>
              <div className="whitespace-pre-wrap max-w-[64ch] leading-relaxed text-ink-muted">
                {draft.body}
              </div>
            </div>
          ) : (
            <div className="text-sm text-ink-muted italic">Press A to generate.</div>
          )}
          {mApprove.isSuccess && (
            <div className="pt-4">
              <div className="text-xs uppercase tracking-wider text-ink-muted mb-2">Log outcome</div>
              <div className="flex gap-1.5 flex-wrap">
                {OUTCOME_KEYS.map(([key, t, label]) => (
                  <button
                    key={t}
                    onClick={() => mOutcome.mutate(t)}
                    className="text-xs px-2 py-1 rounded border border-rule hover:bg-black/[.03] inline-flex items-center gap-1.5"
                  >
                    <span className="kbd">{key}</span>
                    <span>{label}</span>
                  </button>
                ))}
              </div>
              {mOutcome.isSuccess && <div className="text-xs text-positive mt-2">logged</div>}
            </div>
          )}
        </section>
      </div>

      <aside className="space-y-8">
        <div>
          <div className="text-xs uppercase tracking-wider text-ink-muted">Score</div>
          <div className="font-display text-4xl tabular mt-1 leading-none">{score(l.final_score)}</div>
          <div className="text-xs text-ink-muted mt-1.5">
            base {score(l.base_score)}
            {l.memory_adj !== 0 && (
              <>
                {" · "}
                <span className={l.memory_adj > 0 ? "text-signal" : "text-ink-muted"}>
                  memory {l.memory_adj > 0 ? "+" : ""}{(l.memory_adj * 100).toFixed(0)}%
                </span>
              </>
            )}
          </div>
        </div>

        <div>
          <div className="text-xs uppercase tracking-wider text-ink-muted mb-3">What memory says</div>
          {memory_context.length === 0 ? (
            <div className="text-sm text-ink-muted">
              No memory on this brand yet. Log an outcome to start the loop.
            </div>
          ) : (
            <ul className="space-y-3">
              {memory_context.map((m, i) => (
                <MemoryItem key={i} m={m} />
              ))}
            </ul>
          )}
        </div>
      </aside>
    </div>
  );
}

function SignalCard({
  title,
  value,
  series,
  color,
}: {
  title: string;
  value: string;
  series: number[];
  color?: string;
}) {
  return (
    <div className="space-y-1.5">
      <div className="text-xs text-ink-muted">{title}</div>
      <div className="font-display text-2xl tabular leading-none">{value}</div>
      <Sparkline values={series} color={color} />
    </div>
  );
}
