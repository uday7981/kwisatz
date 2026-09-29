"use client";

/**
 * Dev-only replay page. A scrubber walks through the demo season week-by-week
 * with a memory-on / memory-off split view so judges can *see* what memory
 * changes on the shortlist. Not linked from the nav rail.
 */

import { useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { api, type LeadOut } from "@/lib/api";
import { angleLabel, categoryLabel, diagnosisLabel, score } from "@/lib/format";
import { SeverityBar } from "@/components/severity-bar";
import { useKey } from "@/lib/keys";

const MIN_WEEK = 41;
const MAX_WEEK = 52;

export default function Replay() {
  const [week, setWeek] = useState(41);
  const [playing, setPlaying] = useState(false);
  const [splitMode, setSplitMode] = useState<"split" | "on" | "off">("split");

  const onQuery = useQuery({
    queryKey: ["shortlist", week, "on"],
    queryFn: () => api.shortlist(week, "on"),
    enabled: splitMode !== "off",
  });
  const offQuery = useQuery({
    queryKey: ["shortlist", week, "off"],
    queryFn: () => api.shortlist(week, "off"),
    enabled: splitMode !== "on",
  });

  useEffect(() => {
    if (!playing) return;
    const timer = window.setInterval(() => {
      setWeek((w) => {
        if (w >= MAX_WEEK) {
          setPlaying(false);
          return w;
        }
        return w + 1;
      });
    }, 1500);
    return () => window.clearInterval(timer);
  }, [playing]);

  useKey("[", () => setWeek((w) => Math.max(MIN_WEEK, w - 1)));
  useKey("]", () => setWeek((w) => Math.min(MAX_WEEK, w + 1)));
  useKey(" ", (e) => { e.preventDefault(); setPlaying((p) => !p); });

  const onLeads = onQuery.data?.leads ?? [];
  const offLeads = offQuery.data?.leads ?? [];

  const overlapNote = useMemo(() => {
    if (!onLeads.length || !offLeads.length) return null;
    const onSet = new Set(onLeads.slice(0, 10).map((l) => l.brand_alias));
    const offSet = new Set(offLeads.slice(0, 10).map((l) => l.brand_alias));
    const diff = onLeads.slice(0, 10).filter((l) => !offSet.has(l.brand_alias)).length;
    const angleFlips = onLeads.slice(0, 10).reduce((acc, l) => {
      const off = offLeads.find((o) => o.brand_alias === l.brand_alias);
      return acc + (off && off.angle !== l.angle ? 1 : 0);
    }, 0);
    void onSet;
    return { diff, angleFlips };
  }, [onLeads, offLeads]);

  return (
    <div className="space-y-6">
      <header className="flex items-baseline gap-4">
        <h1 className="font-display text-3xl font-semibold">Replay</h1>
        <span className="text-ink-muted">Dev tool. Watch a season play out.</span>
        <Link href="/" className="ml-auto text-xs text-signal hover:underline">Back to app</Link>
      </header>

      <section className="rounded-md border border-rule bg-surface-raised p-4 space-y-3">
        <div className="flex items-center gap-4">
          <button
            onClick={() => setPlaying((p) => !p)}
            className="text-sm px-3 py-1 rounded bg-signal text-white"
            aria-label="Play / pause (space)"
          >
            {playing ? "Pause" : "Play"}
          </button>
          <input
            type="range"
            min={MIN_WEEK}
            max={MAX_WEEK}
            value={week}
            onChange={(e) => setWeek(Number(e.target.value))}
            className="flex-1"
            aria-label="Week"
          />
          <span className="tabular text-sm w-24 text-right">wk {week}</span>
          <div role="tablist" className="inline-flex rounded border border-rule text-xs">
            {(["split", "on", "off"] as const).map((m) => (
              <button
                key={m}
                role="tab"
                aria-selected={splitMode === m}
                onClick={() => setSplitMode(m)}
                className={`px-2 py-1 tabular ${
                  splitMode === m ? "bg-signal text-white" : "text-ink"
                }`}
              >
                {m}
              </button>
            ))}
          </div>
        </div>
        {overlapNote && splitMode === "split" && (
          <div className="text-xs text-ink-muted">
            {overlapNote.diff === 0 && overlapNote.angleFlips === 0
              ? "Memory changed nothing this week."
              : `Memory swapped ${overlapNote.diff} of the top 10 brands and changed ${overlapNote.angleFlips} pitch angles.`}
          </div>
        )}
        <div className="text-xs text-ink-muted flex gap-4">
          <span><kbd className="kbd">Space</kbd> play/pause</span>
          <span><kbd className="kbd">[</kbd> <kbd className="kbd">]</kbd> step week</span>
        </div>
      </section>

      <div className={`grid gap-6 ${splitMode === "split" ? "grid-cols-2" : "grid-cols-1"}`}>
        {splitMode !== "off" && (
          <ShortlistPanel title="Memory ON" leads={onLeads} tone="signal" />
        )}
        {splitMode !== "on" && (
          <ShortlistPanel title="Memory OFF" leads={offLeads} tone="neutral" />
        )}
      </div>
    </div>
  );
}

function ShortlistPanel({
  title,
  leads,
  tone,
}: {
  title: string;
  leads: LeadOut[];
  tone: "signal" | "neutral";
}) {
  return (
    <section className="rounded-md border border-rule bg-surface-raised overflow-hidden">
      <div className={`px-3 py-2 text-xs uppercase tracking-wide ${tone === "signal" ? "text-signal" : "text-ink-muted"}`}>
        {title}
      </div>
      <table className="w-full text-sm">
        <thead className="text-xs uppercase tracking-wide text-ink-muted">
          <tr>
            <th className="px-3 py-2 text-left w-8">#</th>
            <th className="px-3 py-2 text-left">Brand</th>
            <th className="px-3 py-2 text-left">Diagnosis</th>
            <th className="px-3 py-2 text-left">Angle</th>
            <th className="px-3 py-2 text-right">Score</th>
          </tr>
        </thead>
        <tbody className="rule-divider">
          {leads.slice(0, 10).map((l) => (
            <tr key={l.brand_alias} className="hover:bg-black/[.02]">
              <td className="px-3 py-2 tabular text-ink-muted">{l.rank}</td>
              <td className="px-3 py-2">
                <div className="font-medium">{l.brand_alias}</div>
                <div className="text-xs text-ink-muted">{categoryLabel(l.category)}</div>
              </td>
              <td className="px-3 py-2">
                <div>{diagnosisLabel(l.diagnosis)}</div>
                <SeverityBar value={l.severity} />
              </td>
              <td className="px-3 py-2 text-ink-muted">{angleLabel(l.angle)}</td>
              <td className="px-3 py-2 text-right tabular">
                <div className="font-medium">{score(l.final_score)}</div>
                {l.memory_adj !== 0 && (
                  <div className="text-xs text-insight">
                    {l.memory_adj > 0 ? "+" : ""}
                    {(l.memory_adj * 100).toFixed(0)}%
                  </div>
                )}
              </td>
            </tr>
          ))}
          {leads.length === 0 && (
            <tr>
              <td colSpan={5} className="px-3 py-4 text-ink-muted text-center">
                Loading week...
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </section>
  );
}
