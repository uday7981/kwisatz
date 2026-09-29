"""
Lead scoring. `numbers in code`: base score is purely deterministic; memory adjustment
is a bounded multiplier from `MemoryService.prioritise(...)` when memory is on.
"""

from __future__ import annotations

from dataclasses import dataclass

from .diagnosis import DiagnosisHit
from .signals import BrandSignals


@dataclass(frozen=True)
class BaseScore:
    brand_alias: str
    week: int
    severity: float
    velocity_growth_norm: float
    size_fit: float
    recency_of_change: float
    base_score: float


def _norm_velocity_growth(g: float) -> float:
    # Map growth ratio 0.7..2.0 -> 0..1.
    lo, hi = 0.7, 2.0
    return max(0.0, min(1.0, (g - lo) / (hi - lo)))


def _size_fit(total_ratings: int) -> float:
    # Sweet spot 50..300; drop off outside.
    if total_ratings <= 0:
        return 0.0
    if 50 <= total_ratings <= 300:
        return 1.0
    if total_ratings < 50:
        return max(0.0, total_ratings / 50.0)
    return max(0.0, 1.0 - (total_ratings - 300) / 4700.0)


def _recency_of_change(seller_delta_30d: int, buybox_delta: float) -> float:
    # Both mean "something moved recently" -> higher score.
    seller_component = min(1.0, max(0, seller_delta_30d) / 6.0)
    buybox_component = min(1.0, max(0.0, buybox_delta) / 0.30)
    return round(max(seller_component, buybox_component), 3)


def compute_base_score(
    sig: BrandSignals, dx: DiagnosisHit | None, total_ratings: int
) -> BaseScore:
    severity = dx.severity if dx else 0.0
    vgn = _norm_velocity_growth(sig.velocity_growth)
    sf = _size_fit(total_ratings)
    rc = _recency_of_change(sig.seller_delta_30d, sig.buybox_share_prev_30d - sig.buybox_share_30d)
    base = 0.45 * severity + 0.25 * vgn + 0.15 * sf + 0.15 * rc
    return BaseScore(
        brand_alias=sig.brand_alias,
        week=sig.week,
        severity=round(severity, 3),
        velocity_growth_norm=round(vgn, 3),
        size_fit=round(sf, 3),
        recency_of_change=rc,
        base_score=round(base, 3),
    )


def apply_memory_adjustment(
    base: float,
    memory_adjustment: float,
    *,
    revisit: bool = False,
    problem_worsened: bool = False,
    skip: bool = False,
) -> tuple[float, bool]:
    """Returns (final_score, was_skipped)."""
    if skip:
        return 0.0, True
    memory_adjustment = max(-0.6, min(0.6, memory_adjustment))
    final = base * (1.0 + memory_adjustment)
    final = max(0.0, min(1.0, final))
    if revisit and problem_worsened:
        final = max(final, 0.70)
    return round(final, 3), False
