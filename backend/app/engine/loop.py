"""
Weekly agent loop. `mode` controls whether Hindsight is used.

Deterministic paths:
  mode == "off"    — no Hindsight; base score only; fixed diagnosis-to-angle mapping.
  mode == "oracle" — memory-off scoring but the eval harness scores against oracle rules.
  mode == "on"     — MemoryService adjusts scores and picks angles.

The loop returns a list of Lead objects (in memory) so the eval harness can
compare rankings without touching SQL. Persisting to SQLite is opt-in.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..adapters.simulated import SimulatedAdapter
from .diagnosis import DX_TO_ANGLE, DiagnosisHit, diagnose_brand, primary_diagnosis
from .scoring import apply_memory_adjustment, compute_base_score
from .signals import BrandSignals, compute_brand_signals

MAX_LEADS_PER_WEEK = 12
MAX_PER_CATEGORY = 5
MAX_PER_DIAGNOSIS = 4  # ensures the shortlist isn't 12 identical Brand Protection rows


@dataclass(frozen=True)
class Lead:
    brand_alias: str
    week: int
    category: str
    diagnosis: str
    severity: float
    base_score: float
    memory_adj: float
    final_score: float
    rank: int
    angle: str
    reason: str
    evidence_memory_ids: tuple[str, ...] = ()
    skipped: bool = False


@dataclass(frozen=True)
class Skip:
    brand_alias: str
    category: str
    reason: str


def _dedupe_top_n(candidates: list[Lead]) -> list[Lead]:
    """Keep top MAX_LEADS_PER_WEEK with per-category AND per-diagnosis caps so
    the shortlist shows a variety of problem types, not 12 copies of the same
    diagnosis crowding out weaker signals."""
    candidates.sort(key=lambda c: c.final_score, reverse=True)
    kept: list[Lead] = []
    seen_by_cat: dict[str, int] = {}
    seen_by_dx: dict[str, int] = {}
    for c in candidates:
        if c.skipped:
            continue
        if seen_by_cat.get(c.category, 0) >= MAX_PER_CATEGORY:
            continue
        if seen_by_dx.get(c.diagnosis, 0) >= MAX_PER_DIAGNOSIS:
            continue
        kept.append(c)
        seen_by_cat[c.category] = seen_by_cat.get(c.category, 0) + 1
        seen_by_dx[c.diagnosis] = seen_by_dx.get(c.diagnosis, 0) + 1
        if len(kept) >= MAX_LEADS_PER_WEEK:
            break
    return kept


def _brand_signals(week: int, adapter: SimulatedAdapter) -> list[BrandSignals]:
    snapshots_all = adapter._snapshots_df()
    products = adapter.products()
    brands = adapter.brands()
    return compute_brand_signals(week, snapshots_all, products, brands)


def _base_reason(sig: BrandSignals, dx: DiagnosisHit | None) -> str:
    if dx is None:
        return f"Growth (velocity ×{sig.velocity_growth:.2f})."
    ev = dx.evidence
    if dx.code == "D1":
        return (
            f"Sellers on top listing rose by {ev['seller_delta_30d']} in 30 days; "
            f"Buy Box share is {int(ev['buybox_share_30d']*100)}% (was {int(ev['buybox_share_prev_30d']*100)}%)."
        )
    if dx.code == "D2":
        return f"{ev['oos_episodes_60d']} out-of-stock episodes in 60 days while demand is rising."
    if dx.code == "D3":
        return f"Rating is {abs(ev['rating_gap']):.2f} below category median with {ev['review_velocity']:.0f} reviews last month."
    if dx.code == "D4":
        return f"Buy Box price down {abs(ev['price_change_90d'])*100:.0f}% over 90 days with {ev['seller_count']} sellers."
    if dx.code == "D5":
        return f"Velocity up {(ev['velocity_growth']-1)*100:.0f}% QoQ but ad presence is only {ev['ad_presence']:.2f}."
    return f"Healthy growth (velocity ×{ev['velocity_growth']:.2f})."


TOP_N_FOR_MEMORY = 80  # candidates handed to reflect (widened so memory can promote revisits)


def run_week(
    week: int,
    adapter: SimulatedAdapter,
    *,
    mode: str = "off",
    memory_prioritise=None,
) -> tuple[list[Lead], list[Skip]]:
    """
    Compute weekly leads.

    `memory_prioritise` is a callable `(week, candidates: list[dict]) -> dict[brand_alias, dict]`
    only called when `mode == "on"`. It is invoked ONCE per week with the top-40
    base-scored candidates, not once per brand.
    """
    assert mode in {"off", "on", "oracle"}

    sigs = _brand_signals(week, adapter)
    if not sigs:
        return [], []

    brands = adapter.brands()
    brand_meta = {row["alias"]: row for row in brands.iter_rows(named=True)}

    base_rows: list[tuple[BrandSignals, DiagnosisHit | None, float]] = []
    for sig in sigs:
        hits = diagnose_brand(sig)
        dx = primary_diagnosis(hits)
        meta = brand_meta[sig.brand_alias]
        base = compute_base_score(sig, dx, total_ratings=int(meta["total_ratings"]))
        base_rows.append((sig, dx, base.base_score))

    base_rows.sort(key=lambda r: r[2], reverse=True)
    top = base_rows[:TOP_N_FOR_MEMORY]

    adj_map: dict[str, dict] = {}
    if mode == "on" and memory_prioritise is not None and top:
        snap_list = [candidates_snapshot(sig, dx, base_score) for sig, dx, base_score in top]
        try:
            adj_map = memory_prioritise(week=week, candidates=snap_list) or {}
        except Exception:
            adj_map = {}

    candidates: list[Lead] = []
    for sig, dx, base_score in base_rows:
        meta = brand_meta[sig.brand_alias]
        angle = DX_TO_ANGLE.get(dx.code, "growth_partnership") if dx else "growth_partnership"
        reason = _base_reason(sig, dx)
        memory_adj = 0.0
        skip = revisit = problem_worsened = False
        evidence_ids: tuple[str, ...] = ()

        entry = adj_map.get(sig.brand_alias)
        if entry:
            memory_adj = float(entry.get("score_adjustment", 0.0))
            angle = entry.get("recommended_angle", angle)
            skip = bool(entry.get("skip", False))
            revisit = bool(entry.get("revisit", False))
            evidence_ids = tuple(entry.get("evidence_ids", ()))
            if entry.get("reason"):
                reason = f"{reason}  Memory: {entry['reason']}"

        final, was_skipped = apply_memory_adjustment(
            base_score, memory_adj, revisit=revisit, problem_worsened=problem_worsened, skip=skip
        )

        candidates.append(
            Lead(
                brand_alias=sig.brand_alias,
                week=week,
                category=meta["category"],
                diagnosis=dx.code if dx else "D6",
                severity=dx.severity if dx else 0.0,
                base_score=base_score,
                memory_adj=round(memory_adj, 3),
                final_score=final,
                rank=0,
                angle=angle,
                reason=reason,
                evidence_memory_ids=evidence_ids,
                skipped=was_skipped,
            )
        )

    ranked = _dedupe_top_n(candidates)
    ranked = [Lead(**{**c.__dict__, "rank": i + 1}) for i, c in enumerate(ranked)]

    skipped = [
        Skip(brand_alias=c.brand_alias, category=c.category, reason="memory said skip")
        for c in candidates
        if c.skipped
    ]
    return ranked, skipped


def candidates_snapshot(sig: BrandSignals, dx: DiagnosisHit | None, base_score: float) -> dict:
    """A single-brand snapshot the memory layer can feed into a reflect prompt."""
    return {
        "brand_alias": sig.brand_alias,
        "diagnosis": dx.code if dx else "D6",
        "severity": dx.severity if dx else 0.0,
        "base_score": base_score,
        "review_velocity": sig.review_velocity,
        "seller_delta_30d": sig.seller_delta_30d,
        "buybox_share_30d": sig.buybox_share_30d,
    }
