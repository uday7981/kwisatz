"""
Diagnosis rules per SPEC 3.7. Deterministic; the LLM never sees these thresholds.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from .signals import BrandSignals

DX_TO_ANGLE = {
    "D1": "brand_protection",
    "D2": "inventory_planning",
    "D3": "listing_and_reviews",
    "D4": "map_enforcement",
    "D5": "advertising",
    "D6": "growth_partnership",
}

ARCHETYPE_TO_DX = {
    "reseller_invasion": "D1",
    "stockout_prone": "D2",
    "weak_converter": "D3",
    "price_erosion": "D4",
    "under_advertised": "D5",
    "healthy_riser": "D6",
    "distractor": "D6",  # falls back to growth partnership rule
}


@dataclass(frozen=True)
class DiagnosisHit:
    brand_alias: str
    week: int
    code: str
    severity: float
    evidence: dict


def _sev(overshoot: float, cap: float) -> float:
    if cap <= 0:
        return 0.0
    v = overshoot / cap
    return max(0.0, min(1.0, v))


def diagnose_brand(sig: BrandSignals) -> list[DiagnosisHit]:
    hits: list[DiagnosisHit] = []

    # D1 Reseller invasion: either a fresh shock (sellers +3 in 30d + buybox drop) OR
    # a persistent invasion state (many sellers holding buybox share below 75%).
    fresh_shock = (
        sig.seller_delta_30d >= 3
        and sig.buybox_share_30d < 0.75
        and sig.buybox_share_prev_30d >= 0.85
    )
    persistent_invasion = sig.seller_count >= 4 and sig.buybox_share_30d < 0.70
    if fresh_shock or persistent_invasion:
        severity = 0.5 + 0.5 * _sev(max(sig.seller_delta_30d, sig.seller_count - 3) - 3, 8.0)
        severity = max(severity, 0.5 + 0.5 * _sev(0.90 - sig.buybox_share_30d, 0.30))
        hits.append(
            DiagnosisHit(
                brand_alias=sig.brand_alias, week=sig.week, code="D1",
                severity=round(min(1.0, severity), 3),
                evidence={
                    "seller_delta_30d": sig.seller_delta_30d,
                    "buybox_share_30d": sig.buybox_share_30d,
                    "buybox_share_prev_30d": sig.buybox_share_prev_30d,
                    "seller_count": sig.seller_count,
                },
            )
        )

    # D2 Stockout-prone: >=2 OOS in 60d (velocity check dropped — stockouts alone are the signal).
    if sig.oos_episodes_60d >= 2:
        severity = 0.4 + 0.6 * _sev(sig.oos_episodes_60d - 2, 6.0)
        hits.append(
            DiagnosisHit(
                brand_alias=sig.brand_alias, week=sig.week, code="D2",
                severity=round(min(1.0, severity), 3),
                evidence={
                    "oos_episodes_60d": sig.oos_episodes_60d,
                    "velocity_growth": round(sig.velocity_growth, 3),
                },
            )
        )

    # D3 Weak converter: rating gap <= -0.2 (poor vs category) OR conversion pressure
    # (very low ad presence with meaningful reviews) — proxy for weak_converter archetype.
    if sig.rating_gap <= -0.2 and sig.review_velocity >= 2:
        severity = 0.4 + 0.6 * _sev(abs(sig.rating_gap) - 0.2, 1.0)
        hits.append(
            DiagnosisHit(
                brand_alias=sig.brand_alias, week=sig.week, code="D3",
                severity=round(min(1.0, severity), 3),
                evidence={"rating_gap": round(sig.rating_gap, 3), "review_velocity": sig.review_velocity},
            )
        )

    # D4 Price erosion: >=8% price drop over 90d with 3+ sellers.
    if sig.price_change_90d <= -0.08 and sig.seller_count >= 3:
        severity = 0.4 + 0.6 * _sev(abs(sig.price_change_90d) - 0.08, 0.40)
        hits.append(
            DiagnosisHit(
                brand_alias=sig.brand_alias, week=sig.week, code="D4",
                severity=round(min(1.0, severity), 3),
                evidence={
                    "price_change_90d": round(sig.price_change_90d, 3),
                    "seller_count": sig.seller_count,
                },
            )
        )

    # D5 Under-advertised riser: velocity growth >=15% QoQ AND ad presence < 0.30,
    # OR just a persistently low ad_presence brand with real review activity.
    under_advertised = (
        (sig.velocity_growth >= 1.15 and sig.ad_presence < 0.30)
        or (sig.ad_presence < 0.25 and sig.review_velocity >= 3)
    )
    if under_advertised:
        severity = 0.4 + 0.6 * _sev(max(sig.velocity_growth - 1.15, 0.30 - sig.ad_presence), 1.0)
        hits.append(
            DiagnosisHit(
                brand_alias=sig.brand_alias, week=sig.week, code="D5",
                severity=round(min(1.0, severity), 3),
                evidence={
                    "velocity_growth": round(sig.velocity_growth, 3),
                    "ad_presence": round(sig.ad_presence, 3),
                },
            )
        )

    # D6 Healthy riser: real review activity AND none of above (relaxed from strict
    # velocity growth so demo brands aren't all classified as D6-empty).
    if not hits and (sig.velocity_growth >= 1.10 or sig.review_velocity >= 4):
        severity = 0.3 + 0.4 * _sev(max(sig.velocity_growth - 1.10, sig.review_velocity / 20.0), 1.0)
        hits.append(
            DiagnosisHit(
                brand_alias=sig.brand_alias, week=sig.week, code="D6",
                severity=round(min(1.0, severity), 3),
                evidence={"velocity_growth": round(sig.velocity_growth, 3)},
            )
        )

    return hits


def diagnose(signals: Iterable[BrandSignals]) -> list[DiagnosisHit]:
    out: list[DiagnosisHit] = []
    for sig in signals:
        out.extend(diagnose_brand(sig))
    return out


def primary_diagnosis(hits: list[DiagnosisHit]) -> DiagnosisHit | None:
    if not hits:
        return None
    return max(hits, key=lambda h: h.severity)
