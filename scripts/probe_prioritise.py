"""Ad-hoc probe: call prioritise() once and dump the raw reflect response.

Purpose: diagnose why memory-on ≈ memory-off in eval/results.json.
Usage: python -m scripts.probe_prioritise [week]
"""

from __future__ import annotations

import json
import sys

from backend.app.adapters.simulated import SimulatedAdapter
from backend.app.engine.diagnosis import diagnose_brand, primary_diagnosis
from backend.app.engine.loop import _brand_signals
from backend.app.engine.scoring import compute_base_score
from backend.app.memory.service import MemoryService
from sim.simulator import week_to_date


def main() -> None:
    week = int(sys.argv[1]) if len(sys.argv) > 1 else 44

    adapter = SimulatedAdapter()
    brands = adapter.brands()
    brand_meta = {row["alias"]: row for row in brands.iter_rows(named=True)}

    sigs = _brand_signals(week, adapter)
    rows = []
    for sig in sigs:
        meta = brand_meta.get(sig.brand_alias)
        if not meta:
            continue
        dx = primary_diagnosis(diagnose_brand(sig))
        base = compute_base_score(sig, dx, total_ratings=int(meta["total_ratings"]))
        rows.append({
            "brand_alias": sig.brand_alias,
            "category": meta["category"],
            "n_products": int(meta["n_products"]),
            "total_ratings": int(meta["total_ratings"]),
            "diagnosis": dx.code if dx else "D6",
            "severity": dx.severity if dx else 0.0,
            "base_score": base.base_score,
        })
    rows.sort(key=lambda r: r["base_score"], reverse=True)
    candidates = rows[:40]
    print(f"Week {week}: top-40 candidates prepared. Now calling reflect()...")

    svc = MemoryService.from_env()
    sim_date = week_to_date(week)

    prompt = (
        f"Today is {sim_date.date().isoformat()} (week {week} of the season).\n"
        f"You are prioritising which Amazon brands our agency should contact this week.\n"
        f"Use everything you have learned from past pitches and outcomes.\n"
        f"For each candidate below, return a `score_adjustment` between -0.6 and 0.6, the "
        f"pitch angle most likely to get a reply, a one-sentence reason with counts, and "
        f"whether to skip it or treat it as a revisit. Cite the beliefs you relied on.\n"
        f"Candidates:\n"
        + "\n".join(
            f"- {c['brand_alias']} | cat={c['category']} | products={c['n_products']} | "
            f"ratings={c['total_ratings']} | dx={c['diagnosis']} | "
            f"severity={c['severity']:.2f} | base_score={c['base_score']:.2f}"
            for c in candidates
        )
    )

    from backend.app.memory.schemas import PrioritisationResult
    resp = svc.client.reflect(
        bank_id=svc.bank_id,
        query=prompt,
        budget="mid",
        response_schema=PrioritisationResult.model_json_schema(),
        include_facts=True,
    )
    print("\n=== raw reflect response fields ===")
    for attr in ("text", "structured_output", "based_on", "usage"):
        v = getattr(resp, attr, None)
        if v is None:
            continue
        if attr == "text":
            print(f"\n--- text ({len(v) if v else 0} chars) ---")
            print(v[:1500] if v else "(empty)")
        elif attr == "structured_output":
            print(f"\n--- structured_output ---")
            print(json.dumps(v, indent=2)[:2500] if v else "(empty)")
        elif attr == "based_on":
            memories = getattr(v, "memories", None) or []
            print(f"\n--- based_on ({len(memories)} memories) ---")
            for m in memories[:5]:
                print("  -", getattr(m, "type", "?"), "|", (getattr(m, "text", "") or "")[:100])
        else:
            print(f"\n--- {attr} ---")
            print(v)

    print("\n=== parsed via PrioritisationResult ===")
    result = svc.prioritise(week=week, sim_date=sim_date, candidates=candidates)
    print(f"n_adjustments: {len(result.adjustments)}")
    for a in result.adjustments[:10]:
        print(f"  {a.brand_id} | adj={a.score_adjustment:+.2f} | angle={a.recommended_angle} | skip={a.skip} | revisit={a.revisit}")
        print(f"    reason: {a.reason}")

    svc.close()


if __name__ == "__main__":
    main()
