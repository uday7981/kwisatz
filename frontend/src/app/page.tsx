"use client";

import { useQuery } from "@tanstack/react-query";
import { forwardRef, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api, type LeadOut } from "@/lib/api";
import { angleLabel, categoryLabel, diagnosisLabel, score } from "@/lib/format";
import { useKey } from "@/lib/keys";
import { PipelineStrip } from "@/components/pipeline-strip";

const MIN_WEEK = 41;
const MAX_WEEK = 52;

export default function ThisWeek() {
  const router = useRouter();
  const [week, setWeek] = useState(44);
  const [cursor, setCursor] = useState(0);
  const rowRefs = useRef<Array<HTMLTableRowElement | null>>([]);

  const shortlist = useQuery({
    queryKey: ["shortlist", week, "on"],
    queryFn: () => api.shortlist(week, "on"),
  });

  const leads = shortlist.data?.leads ?? [];
  const pipeline = shortlist.data?.pipeline;

  useEffect(() => {
    setCursor((c) => Math.min(c, Math.max(0, leads.length - 1)));
  }, [leads.length]);

  useEffect(() => {
    const row = rowRefs.current[cursor];
    if (row) row.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }, [cursor]);

  useKey("j", () => setCursor((c) => Math.min(leads.length - 1, c + 1)), [leads.length]);
  useKey("k", () => setCursor((c) => Math.max(0, c - 1)), [leads.length]);
  useKey("Enter", () => {
    const lead = leads[cursor];
    if (lead) router.push(`/brands/${encodeURIComponent(lead.brand_alias)}?week=${week}`);
  }, [leads, cursor, week, router]);
  useKey("[", () => setWeek((w) => Math.max(MIN_WEEK, w - 1)));
  useKey("]", () => setWeek((w) => Math.min(MAX_WEEK, w + 1)));

  return (
    <div className="space-y-10">
      <header className="flex items-end gap-6">
        <div>
          <div className="text-xs uppercase tracking-wider text-ink-muted">Week</div>
          <h1 className="font-display text-4xl font-semibold tabular leading-none">{week}</h1>
        </div>
        <div className="pb-1 text-sm text-ink-muted">
          {leads.length || "-"} brands worth contacting today
        </div>
        <div className="ml-auto inline-flex items-center gap-1 text-sm text-ink-muted pb-1">
          <button
            onClick={() => setWeek((w) => Math.max(MIN_WEEK, w - 1))}
            className="px-2 py-0.5 hover:text-ink"
            aria-label="Previous week"
          >
            ←
          </button>
          <span className="tabular text-ink px-1">wk {week}</span>
          <button
            onClick={() => setWeek((w) => Math.min(MAX_WEEK, w + 1))}
            className="px-2 py-0.5 hover:text-ink"
            aria-label="Next week"
          >
            →
          </button>
        </div>
      </header>

      <PipelineStrip
        brandsScanned={pipeline?.brands_scanned ?? 0}
        diagnosed={pipeline?.diagnosed ?? 0}
        memoryAdjusted={pipeline?.memory_adjusted ?? 0}
        ranked={pipeline?.ranked ?? 0}
        loading={shortlist.isFetching || !pipeline}
      />

      {shortlist.isFetching && !shortlist.data && (
        <ShortlistSkeleton />
      )}
      {shortlist.error && (
        <div className="text-risk text-sm">
          Failed to load. Backend on {process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:8000"}?
        </div>
      )}

      {shortlist.data && (
        <div className="space-y-2">
          <div className="text-xs uppercase tracking-wider text-ink-muted mb-2">Today&apos;s shortlist</div>
          <ul className="rule-divider">
            {leads.map((lead, i) => (
              <LeadRow
                key={lead.brand_alias}
                lead={lead}
                week={week}
                active={i === cursor}
                onHover={() => setCursor(i)}
                ref={(el) => { rowRefs.current[i] = el; }}
              />
            ))}
          </ul>
          {shortlist.data.skipped.length > 0 && (
            <div className="pt-4 text-xs text-ink-muted">
              <span className="uppercase tracking-wider text-ink">Memory said skip</span>{" "}
              {shortlist.data.skipped
                .map((s) => s.brand_alias)
                .join(", ")}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function ShortlistSkeleton() {
  return (
    <div className="space-y-4">
      <div className="text-xs text-ink-muted flex items-center gap-2">
        <span className="inline-block w-1.5 h-1.5 rounded-full bg-signal animate-pulse" />
        <span>Consulting memory (15–30s on cold cache)…</span>
      </div>
      <ul className="rule-divider">
        {Array.from({ length: 8 }).map((_, i) => (
          <li key={i} className="py-4 flex items-center gap-6">
            <div className="w-6 shrink-0 text-right text-xs text-ink-muted tabular">{i + 1}</div>
            <div className="flex-1 min-w-0 space-y-1.5">
              <div className="h-3.5 w-40 rounded bg-rule/60 animate-pulse" />
              <div className="h-3 w-72 rounded bg-rule/40 animate-pulse" />
            </div>
            <div className="w-40 shrink-0 space-y-1.5">
              <div className="h-3.5 w-24 rounded bg-rule/60 animate-pulse" />
              <div className="h-3 w-28 rounded bg-rule/40 animate-pulse" />
            </div>
            <div className="w-16 shrink-0 text-right">
              <div className="h-5 w-10 ml-auto rounded bg-rule/60 animate-pulse" />
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

type LeadRowProps = {
  lead: LeadOut;
  week: number;
  active: boolean;
  onHover: () => void;
};

const LeadRow = forwardRef<HTMLTableRowElement, LeadRowProps>(function LeadRow(
  { lead, week, active, onHover },
  ref,
) {
  const memoryUp = lead.memory_adj > 0.02;
  const memoryDown = lead.memory_adj < -0.02;
  return (
    <li
      ref={ref as never}
      onMouseEnter={onHover}
      className={`transition-colors ${active ? "bg-signal/[.04]" : "hover:bg-black/[.02]"}`}
    >
      <Link
        href={`/brands/${encodeURIComponent(lead.brand_alias)}?week=${week}`}
        className="py-4 flex items-center gap-6 focus:outline-none focus-visible:bg-signal/[.06]"
      >
        <div className="w-6 shrink-0 text-right text-xs text-ink-muted tabular">
          {lead.rank}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-baseline gap-3">
            <span className="font-medium group-hover:text-signal">{lead.brand_alias}</span>
            <span className="text-xs text-ink-muted">{categoryLabel(lead.category)}</span>
          </div>
          <div className="text-sm text-ink-muted mt-0.5 line-clamp-1">
            {lead.reason}
          </div>
        </div>
        <div className="w-40 shrink-0 text-sm">
          <div className="text-ink">{diagnosisLabel(lead.diagnosis)}</div>
          <div className="text-xs text-ink-muted mt-0.5">{angleLabel(lead.angle)}</div>
        </div>
        <div className="w-20 shrink-0 text-right">
          <div className="font-display text-lg tabular">{score(lead.final_score)}</div>
          {(memoryUp || memoryDown) && (
            <div
              className={`text-[10px] uppercase tracking-wide inline-flex items-center gap-1 ${
                memoryUp ? "text-signal" : "text-ink-muted"
              }`}
              title={`Memory ${memoryUp ? "boosted" : "damped"} by ${Math.abs(lead.memory_adj * 100).toFixed(0)}%`}
            >
              <span>{memoryUp ? "↑" : "↓"}</span>
              <span>memory {memoryUp ? "+" : ""}{(lead.memory_adj * 100).toFixed(0)}%</span>
            </div>
          )}
        </div>
      </Link>
    </li>
  );
});
