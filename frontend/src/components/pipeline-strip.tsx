"use client";

/**
 * Visual breadcrumb showing the discovery pipeline that produced the shortlist.
 * Reads live counts from the shortlist response and renders each stage.
 */

type Props = {
  brandsScanned: number;
  diagnosed: number;
  memoryAdjusted: number;
  ranked: number;
  loading?: boolean;
};

const STAGES = [
  { key: "scanned", label: "Signals", hint: "brands scanned from marketplace snapshots" },
  { key: "diagnosed", label: "Diagnosis", hint: "brands with a fireable diagnosis rule (D1–D5)" },
  { key: "memory", label: "Memory", hint: "reflected against 20 weeks of retained outcomes" },
  { key: "ranked", label: "Shortlist", hint: "top brands worth contacting today" },
] as const;

export function PipelineStrip({ brandsScanned, diagnosed, memoryAdjusted, ranked, loading }: Props) {
  const counts: Record<string, number> = {
    scanned: brandsScanned,
    diagnosed,
    memory: memoryAdjusted,
    ranked,
  };
  return (
    <div className="flex items-stretch gap-0 text-xs border border-rule rounded-md overflow-hidden bg-surface-raised">
      {STAGES.map((s, i) => (
        <div
          key={s.key}
          className={`flex-1 px-4 py-3 ${i < STAGES.length - 1 ? "border-r border-rule" : ""} group relative`}
        >
          <div className="uppercase tracking-wider text-[10px] text-ink-muted flex items-center gap-1.5">
            <span className={`inline-block w-1 h-1 rounded-full ${i === STAGES.length - 1 ? "bg-signal" : "bg-ink-muted"}`} />
            {s.label}
          </div>
          <div className="font-display text-xl tabular mt-0.5 leading-none">
            {loading ? <span className="text-ink-muted">…</span> : counts[s.key]}
          </div>
          <div className="text-[10px] text-ink-muted mt-1 leading-tight">
            {s.hint}
          </div>
        </div>
      ))}
    </div>
  );
}
