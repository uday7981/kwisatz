"""
Evaluation harness. Runs the 12-week demo season three ways with the same seed and
writes a JSON summary + PNG chart to `eval/`.

Modes:
  off    — memory-off pipeline (fixed diagnosis-to-angle mapping)
  on     — memory-on pipeline (needs Hindsight; passed via `memory_prioritise` callback)
  oracle — knows the hidden ground_truth.yaml; upper bound
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import polars as pl

from ..adapters.simulated import SimulatedAdapter
from ..config import REPO_ROOT
from ..engine.loop import Lead, run_week
from .oracle import oracle_angle_for, oracle_score

DEMO_WEEK_START = 41
DEMO_WEEK_END = 52
TOP_N = 10


@dataclass(frozen=True)
class WeekMetrics:
    week: int
    mode: str
    reply_rate: float
    meeting_rate: float
    angle_accuracy: float


def _outcome_lookup(adapter: SimulatedAdapter) -> dict[tuple[str, int, str], str]:
    df = adapter._outcomes_df()
    if df.is_empty():
        return {}
    return {
        (r["brand_alias"], r["week_sent"], r["angle"]): r["type"]
        for r in df.iter_rows(named=True)
    }


def _archetype_by_alias(adapter: SimulatedAdapter) -> dict[str, str]:
    b = adapter.brands()
    return dict(zip(b["alias"].to_list(), b["archetype_hidden"].to_list(), strict=True))


def _oracle_leads(adapter: SimulatedAdapter, week: int) -> list[Lead]:
    """Compute an 'oracle' ranking that uses the hidden ground truth."""
    brands = adapter.brands()
    # Best severity per brand this week (from real diagnosis rules, so oracle still
    # uses the deterministic signals -> diagnosis path but picks the perfect angle).
    from ..engine.diagnosis import diagnose_brand, primary_diagnosis
    from ..engine.loop import _brand_signals

    sigs = _brand_signals(week, adapter)
    ranking: list[Lead] = []
    archetype = _archetype_by_alias(adapter)
    for sig in sigs:
        brand_row = brands.filter(pl.col("alias") == sig.brand_alias).row(0, named=True)
        arch = archetype[sig.brand_alias]
        best_angle = oracle_angle_for(arch)
        dx = primary_diagnosis(diagnose_brand(sig))
        severity = dx.severity if dx else 0.3
        score = oracle_score(arch, brand_row["category"], int(brand_row["total_ratings"]), severity, best_angle)
        ranking.append(
            Lead(
                brand_alias=sig.brand_alias, week=week, category=brand_row["category"],
                diagnosis=(dx.code if dx else "D6"), severity=severity,
                base_score=score, memory_adj=0.0, final_score=score, rank=0,
                angle=best_angle, reason="oracle",
            )
        )
    ranking.sort(key=lambda l: l.final_score, reverse=True)
    return [Lead(**{**c.__dict__, "rank": i + 1}) for i, c in enumerate(ranking[:TOP_N])]


def evaluate_mode(
    adapter: SimulatedAdapter,
    mode: str,
    memory_prioritise: Callable | None = None,
) -> list[WeekMetrics]:
    outcomes = _outcome_lookup(adapter)
    archetype = _archetype_by_alias(adapter)
    metrics: list[WeekMetrics] = []
    positive_types = {"reply", "meeting", "signed"}
    meeting_types = {"meeting", "signed"}

    for week in range(DEMO_WEEK_START, DEMO_WEEK_END + 1):
        if mode == "oracle":
            leads = _oracle_leads(adapter, week)
        else:
            leads, _ = run_week(week, adapter, mode=mode, memory_prioritise=memory_prioritise)
            leads = leads[:TOP_N]

        if not leads:
            metrics.append(WeekMetrics(week=week, mode=mode, reply_rate=0.0, meeting_rate=0.0, angle_accuracy=0.0))
            continue

        replies = 0
        meetings = 0
        correct_angle = 0
        for lead in leads:
            typ = outcomes.get((lead.brand_alias, week, lead.angle), "no_reply")
            if typ in positive_types:
                replies += 1
            if typ in meeting_types:
                meetings += 1
            best_angle = oracle_angle_for(archetype[lead.brand_alias])
            if lead.angle == best_angle:
                correct_angle += 1

        n = len(leads)
        metrics.append(
            WeekMetrics(
                week=week, mode=mode,
                reply_rate=round(replies / n, 3),
                meeting_rate=round(meetings / n, 3),
                angle_accuracy=round(correct_angle / n, 3),
            )
        )
    return metrics


def run_all(
    memory_prioritise: Callable | None = None,
    out_dir: Path = REPO_ROOT / "eval",
) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    adapter = SimulatedAdapter()
    off = evaluate_mode(adapter, "off")
    oracle = evaluate_mode(adapter, "oracle")
    on = evaluate_mode(adapter, "on", memory_prioritise=memory_prioritise) if memory_prioritise else []

    out = {
        "top_n": TOP_N,
        "weeks": list(range(DEMO_WEEK_START, DEMO_WEEK_END + 1)),
        "off": [m.__dict__ for m in off],
        "oracle": [m.__dict__ for m in oracle],
        "on": [m.__dict__ for m in on],
    }
    (out_dir / "results.json").write_text(json.dumps(out, indent=2))
    _write_chart(out, out_dir / "results.png")
    return out


def _write_chart(results: dict, path: Path) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return
    weeks = results["weeks"]

    def _series(mode: str, key: str) -> list[float]:
        rows = results.get(mode) or []
        by_week = {r["week"]: r[key] for r in rows}
        return [by_week.get(w, 0.0) for w in weeks]

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(weeks, _series("off", "meeting_rate"), label="memory off", color="#8A96A3", linewidth=1.5)
    if results.get("on"):
        ax.plot(weeks, _series("on", "meeting_rate"), label="memory on", color="#C7861A", linewidth=1.5)
    ax.plot(weeks, _series("oracle", "meeting_rate"), label="oracle", color="#0F1B2D", linewidth=1.5, linestyle="--")
    ax.set_xlabel("simulated week")
    ax.set_ylabel("meeting rate (top 10)")
    ax.set_ylim(0.0, max(0.5, max(_series("oracle", "meeting_rate") or [0.5]) + 0.1))
    ax.set_title("Meeting rate of weekly top 10")
    ax.grid(alpha=0.15, linestyle=":")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)


def print_summary(results: dict) -> None:
    for mode in ("off", "on", "oracle"):
        rows = results.get(mode) or []
        if not rows:
            continue
        avg_reply = sum(r["reply_rate"] for r in rows) / len(rows)
        avg_meet = sum(r["meeting_rate"] for r in rows) / len(rows)
        avg_angle = sum(r["angle_accuracy"] for r in rows) / len(rows)
        print(f"  {mode:6}  reply={avg_reply:.2f}  meeting={avg_meet:.2f}  angle_acc={avg_angle:.2f}")
