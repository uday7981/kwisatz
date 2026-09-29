"use client";

import { motion, AnimatePresence } from "framer-motion";
import type { BeliefOut, BeliefDiff as DiffType } from "@/lib/api";

const REVEAL = { duration: 0.6, ease: [0.2, 0.8, 0.2, 1] as const };

type Tone = "new" | "strengthened" | "weakened" | "reversed" | "steady";

function toneFor(id: string, diff: DiffType | undefined): Tone {
  if (!diff) return "steady";
  if (diff.new?.includes(id)) return "new";
  if (diff.reversed?.includes(id)) return "reversed";
  if (diff.strengthened?.includes(id)) return "strengthened";
  if (diff.weakened?.includes(id)) return "weakened";
  return "steady";
}

const TONE_META: Record<Tone, { label: string; dot: string; text: string }> = {
  new: { label: "new", dot: "bg-signal", text: "text-signal" },
  strengthened: { label: "stronger", dot: "bg-insight", text: "text-insight" },
  weakened: { label: "weaker", dot: "bg-neutral-series", text: "text-neutral-series" },
  reversed: { label: "reversed", dot: "bg-risk", text: "text-risk" },
  steady: { label: "", dot: "", text: "" },
};

export function BeliefCard({ b, diff }: { b: BeliefOut; diff?: DiffType }) {
  const tone = toneFor(b.id, diff);
  const meta = TONE_META[tone];
  const changed = tone !== "steady";

  return (
    <motion.article
      layout
      key={b.id}
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -4 }}
      transition={REVEAL}
      className="group relative bg-surface-raised border border-rule rounded-lg p-5 flex flex-col gap-4 min-h-[9rem]"
    >
      {changed && (
        <motion.div
          key={`${b.id}-${tone}`}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={REVEAL}
          className="absolute top-3 right-3 inline-flex items-center gap-1.5 text-[10px] uppercase tracking-wider"
        >
          <span className={`inline-block w-1.5 h-1.5 rounded-full ${meta.dot}`} />
          <span className={meta.text}>{meta.label}</span>
        </motion.div>
      )}
      <p className="font-display text-[15px] leading-snug flex-1">{b.statement}</p>
      <div className="flex items-center gap-3 pt-2 border-t border-rule/60">
        <div className="flex-1 h-1 rounded-full bg-rule/60 overflow-hidden">
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${Math.round(b.confidence * 100)}%` }}
            transition={REVEAL}
            className="h-full bg-signal"
          />
        </div>
        <div className="tabular text-[11px] text-ink-muted">
          {(b.confidence * 100).toFixed(0)}% · {b.evidence_count} {b.evidence_count === 1 ? "outcome" : "outcomes"}
        </div>
      </div>
    </motion.article>
  );
}

export function BeliefDiffSummary({ diff }: { diff?: DiffType }) {
  if (!diff || !diff._prev_week) return null;
  const items: { label: string; count: number; tone: Tone }[] = (
    [
      { label: "new", count: diff.new?.length ?? 0, tone: "new" as const },
      { label: "stronger", count: diff.strengthened?.length ?? 0, tone: "strengthened" as const },
      { label: "weaker", count: diff.weakened?.length ?? 0, tone: "weakened" as const },
      { label: "reversed", count: diff.reversed?.length ?? 0, tone: "reversed" as const },
    ]
  ).filter((i) => i.count > 0);
  if (items.length === 0) return null;
  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: -4 }}
        animate={{ opacity: 1, y: 0 }}
        transition={REVEAL}
        className="flex items-center gap-4 text-xs text-ink-muted"
      >
        <span className="uppercase tracking-wider">Since week {diff._prev_week}</span>
        {items.map((i) => (
          <span key={i.label} className="inline-flex items-center gap-1.5">
            <span className={`inline-block w-1.5 h-1.5 rounded-full ${TONE_META[i.tone].dot}`} />
            <span className="tabular">{i.count}</span>
            <span>{i.label}</span>
          </span>
        ))}
      </motion.div>
    </AnimatePresence>
  );
}

export { toneFor };
