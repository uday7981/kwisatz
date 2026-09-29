"use client";

import { useQuery } from "@tanstack/react-query";
import { AnimatePresence } from "framer-motion";
import { useState } from "react";
import { api, type BeliefOut, type BeliefDiff } from "@/lib/api";
import { BeliefCard, BeliefDiffSummary } from "@/components/belief-diff";
import { useKey } from "@/lib/keys";

type GroupKey = "who_converts" | "which_angle" | "avoid" | "my_mistakes";

const GROUPS: { key: GroupKey; label: string; hint: string }[] = [
  { key: "which_angle", label: "Angles that work", hint: "which pitch converts which diagnosis" },
  { key: "who_converts", label: "Who converts", hint: "which brand segments reply" },
  { key: "avoid", label: "What to avoid", hint: "segments and behaviours to stop" },
  { key: "my_mistakes", label: "My mistakes", hint: "where the scoring was wrong" },
];

export default function Learned() {
  const [week, setWeek] = useState(44);
  const beliefs = useQuery({
    queryKey: ["beliefs", week],
    queryFn: () => api.beliefs(week),
  });

  useKey("[", () => setWeek((w) => Math.max(41, w - 1)));
  useKey("]", () => setWeek((w) => Math.min(52, w + 1)));

  const diff = beliefs.data?.diff as BeliefDiff | undefined;
  const all = beliefs.data?.beliefs ?? [];

  return (
    <div className="space-y-10">
      <header className="flex items-end gap-6">
        <div>
          <div className="text-xs uppercase tracking-wider text-ink-muted">Beliefs</div>
          <h1 className="font-display text-4xl font-semibold leading-none">
            What I&apos;ve learned
          </h1>
        </div>
        <div className="pb-1 text-sm text-ink-muted">
          consolidated in week {week}
        </div>
        <div className="ml-auto inline-flex items-center gap-1 text-sm text-ink-muted pb-1">
          <button
            onClick={() => setWeek((w) => Math.max(41, w - 1))}
            className="px-2 py-0.5 hover:text-ink"
            aria-label="Previous week"
          >
            ←
          </button>
          <span className="tabular text-ink px-1">wk {week}</span>
          <button
            onClick={() => setWeek((w) => Math.min(52, w + 1))}
            className="px-2 py-0.5 hover:text-ink"
            aria-label="Next week"
          >
            →
          </button>
        </div>
      </header>

      <BeliefDiffSummary diff={diff} />

      {beliefs.isLoading && (
        <div className="text-ink-muted text-sm">Consolidating memory...</div>
      )}
      {beliefs.data && all.length === 0 && (
        <div className="text-sm text-ink-muted">
          No beliefs yet. Seed the bank with <code>make seed</code>, then advance a week.
        </div>
      )}

      <div className="space-y-10">
        {GROUPS.map((g) => {
          const items = all.filter((b) => b.group === g.key);
          if (items.length === 0) return null;
          return (
            <BeliefSection
              key={g.key}
              label={g.label}
              hint={g.hint}
              beliefs={items}
              diff={diff}
            />
          );
        })}
      </div>
    </div>
  );
}

function BeliefSection({
  label, hint, beliefs, diff,
}: {
  label: string;
  hint: string;
  beliefs: BeliefOut[];
  diff?: BeliefDiff;
}) {
  return (
    <section className="space-y-4">
      <div className="flex items-baseline gap-3">
        <div className="text-xs uppercase tracking-wider text-ink font-medium">{label}</div>
        <div className="text-xs text-ink-muted">{hint}</div>
        <div className="ml-auto text-xs text-ink-muted tabular">
          {beliefs.length} {beliefs.length === 1 ? "belief" : "beliefs"}
        </div>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <AnimatePresence mode="popLayout">
          {beliefs.map((b) => (
            <BeliefCard key={b.id} b={b} diff={diff} />
          ))}
        </AnimatePresence>
      </div>
    </section>
  );
}
