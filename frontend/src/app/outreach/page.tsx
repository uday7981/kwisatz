"use client";

import { useQuery, useMutation } from "@tanstack/react-query";
import { useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { angleLabel, diagnosisLabel } from "@/lib/format";

const OUTCOMES: [string, string][] = [
  ["reply", "reply"],
  ["meeting", "meeting"],
  ["signed", "signed"],
  ["declined", "declined"],
  ["not_now", "not now"],
  ["no_reply", "no reply"],
];

export default function Outreach() {
  const [week] = useState(44);
  const shortlist = useQuery({
    queryKey: ["shortlist", week, "on"],
    queryFn: () => api.shortlist(week, "on"),
  });

  return (
    <div className="space-y-8">
      <header>
        <div className="text-xs uppercase tracking-wider text-ink-muted">Outreach</div>
        <h1 className="font-display text-4xl font-semibold leading-none">Log outcomes</h1>
        <div className="text-sm text-ink-muted mt-2">Week {week}</div>
      </header>

      <ul className="rule-divider">
        {(shortlist.data?.leads ?? []).map((l) => (
          <OutcomeRow
            key={l.brand_alias}
            alias={l.brand_alias}
            week={week}
            diagnosis={l.diagnosis}
            angle={l.angle}
          />
        ))}
      </ul>
    </div>
  );
}

function OutcomeRow({
  alias, week, diagnosis, angle,
}: { alias: string; week: number; diagnosis: string; angle: string }) {
  const m = useMutation({
    mutationFn: (t: string) => api.outcome(alias, week, t, ""),
  });
  return (
    <li className="py-4 flex items-center gap-6">
      <div className="flex-1 min-w-0">
        <Link
          href={`/brands/${encodeURIComponent(alias)}?week=${week}`}
          className="font-medium hover:text-signal"
        >
          {alias}
        </Link>
        <div className="text-xs text-ink-muted mt-0.5">
          {diagnosisLabel(diagnosis)} · {angleLabel(angle)}
        </div>
      </div>
      <div className="flex gap-1 flex-wrap justify-end">
        {OUTCOMES.map(([t, label]) => (
          <button
            key={t}
            onClick={() => m.mutate(t)}
            className="text-xs px-2 py-1 rounded border border-rule hover:bg-black/[.03]"
          >
            {label}
          </button>
        ))}
      </div>
      {m.isSuccess && <span className="text-xs text-positive w-14 text-right">logged</span>}
    </li>
  );
}
