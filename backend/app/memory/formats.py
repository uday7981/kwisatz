"""
Templates + tag builders + observation-scope helpers for all Hindsight retains.

Kept small and pure so tests can pin every content string.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Literal

Kind = Literal["snapshot", "diagnosis", "pitch", "outcome", "decision"]


def slug(alias: str) -> str:
    """Stable slug for a brand alias (used in tags and document ids)."""
    s = alias.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s


def category_slug(category: str) -> str:
    return category.lower().replace("_", "-")


def dx_slug(code: str) -> str:
    mapping = {
        "D1": "reseller-invasion",
        "D2": "stockout-prone",
        "D3": "weak-converter",
        "D4": "price-erosion",
        "D5": "under-advertised",
        "D6": "healthy-riser",
    }
    return mapping.get(code, code.lower())


def build_tags(*, brand_alias: str | None = None, category: str | None = None,
               dx_code: str | None = None, angle: str | None = None,
               outcome_type: str | None = None, kind: Kind) -> list[str]:
    tags: list[str] = [f"kind:{kind}"]
    if brand_alias:
        tags.append(f"brand:{slug(brand_alias)}")
    if category:
        tags.append(f"cat:{category_slug(category)}")
    if dx_code:
        tags.append(f"dx:{dx_slug(dx_code)}")
    if angle:
        tags.append(f"angle:{angle.replace('_', '-')}")
    if outcome_type:
        tags.append(f"outcome:{outcome_type.replace('_', '-')}")
    return tags


def build_scopes(*, brand_alias: str | None = None, category: str | None = None,
                 dx_code: str | None = None, angle: str | None = None) -> list[list[str]]:
    """Observation scopes for a memory. Never returns []."""
    scopes: list[list[str]] = []
    if dx_code:
        scopes.append([f"dx:{dx_slug(dx_code)}"])
        if angle:
            scopes.append([f"dx:{dx_slug(dx_code)}", f"angle:{angle.replace('_', '-')}"])
    if angle:
        scopes.append([f"angle:{angle.replace('_', '-')}"])
    if category:
        scopes.append([f"cat:{category_slug(category)}"])
    if brand_alias:
        scopes.append([f"brand:{slug(brand_alias)}"])
    if not scopes:
        # never allow empty list; it silently becomes "combined" per Hindsight v0.10 docs.
        scopes = [["kind:decision"]]
    return scopes


def doc_id(kind: Kind, brand_alias: str, week: int | None = None, angle: str | None = None,
           extra: str | None = None) -> str:
    parts = [kind, slug(brand_alias)]
    if week is not None:
        parts.append(f"w{week:02d}")
    if angle:
        parts.append(angle.replace("_", "-"))
    if extra:
        parts.append(extra)
    return ":".join(parts)


def snapshot_content(*, week: int, sim_date: datetime, brand_alias: str, category: str,
                     n_products: int, dx_code: str, severity: float, evidence: dict) -> str:
    ev = evidence
    lead_line = f"Week {week} ({sim_date.date().isoformat()}): {brand_alias} ({category}, {n_products} products)."
    if dx_code == "D1":
        return (
            f"{lead_line} Sellers on its top listing rose by {ev.get('seller_delta_30d','?')} in 30 days. "
            f"The brand held the Buy Box "
            f"{int(round((ev.get('buybox_share_30d') or 0)*100))}% of the time, down from "
            f"{int(round((ev.get('buybox_share_prev_30d') or 0)*100))}%. "
            f"Diagnosis: reseller invasion, severity {severity:.2f}."
        )
    if dx_code == "D2":
        return (
            f"{lead_line} {ev.get('oos_episodes_60d','?')} out-of-stock episodes in the last 60 days while "
            f"review velocity kept rising. Diagnosis: stockout-prone, severity {severity:.2f}."
        )
    if dx_code == "D3":
        return (
            f"{lead_line} Rating gap {ev.get('rating_gap','?')} vs category median with "
            f"{int(ev.get('review_velocity',0))} recent reviews. Diagnosis: weak converter, severity {severity:.2f}."
        )
    if dx_code == "D4":
        return (
            f"{lead_line} Buy Box price down {abs(ev.get('price_change_90d',0))*100:.0f}% over 90 days with "
            f"{ev.get('seller_count','?')} sellers on the listing. Diagnosis: price erosion, severity {severity:.2f}."
        )
    if dx_code == "D5":
        return (
            f"{lead_line} Review velocity growth {(ev.get('velocity_growth',1)-1)*100:.0f}% quarter on quarter "
            f"but ad presence only {ev.get('ad_presence',0):.2f}. Diagnosis: under-advertised riser, severity {severity:.2f}."
        )
    return f"{lead_line} Healthy growth (velocity ×{ev.get('velocity_growth',1):.2f}); no fixable issue."


def pitch_content(*, week: int, sim_date: datetime, brand_alias: str, angle: str,
                  base_score: float, rank: int, top_of: int, reason: str) -> str:
    return (
        f"I pitched {brand_alias} on {sim_date.date().isoformat()} (week {week}) with the "
        f"{angle.replace('_', ' ')} angle, citing: {reason} "
        f"My lead score was {base_score:.2f}, rank {rank} of {top_of}."
    )


def outcome_content(*, week: int, sim_date: datetime, brand_alias: str, outcome_type: str,
                    reason_text: str, revisit_after: str | None = None) -> str:
    base = f"{brand_alias} on {sim_date.date().isoformat()} (week {week}): {outcome_type.replace('_', ' ')}."
    if reason_text:
        base += f" Message: '{reason_text}'."
    if revisit_after:
        base += f" Revisit after {revisit_after}."
    return base


def decision_content(*, sim_date: datetime, actor: str, decision: str) -> str:
    return f"Agency decision on {sim_date.date().isoformat()}: {actor} set rule: {decision}"
