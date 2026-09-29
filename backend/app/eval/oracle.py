"""Oracle mode: reads ground_truth.yaml and produces the "best" ranking directly."""

from __future__ import annotations

import yaml

from ..config import REPO_ROOT

GT_PATH = REPO_ROOT / "sim" / "ground_truth.yaml"


def load_ground_truth() -> dict:
    with GT_PATH.open() as fh:
        return yaml.safe_load(fh)


def oracle_angle_for(archetype: str) -> str:
    gt = load_ground_truth()
    fit = gt["angle_fit"].get(archetype, {})
    if not fit:
        return "growth_partnership"
    return max((a for a in fit if a != "other"), key=lambda a: fit[a], default="growth_partnership")


def oracle_score(archetype: str, category: str, total_ratings: int, severity: float, chosen_angle: str) -> float:
    gt = load_ground_truth()
    fit = gt["angle_fit"].get(archetype, {})
    mult = fit.get(chosen_angle) or fit.get("other", 1.0)
    p = gt["base_reply_rate"] * mult
    p *= gt["category_modifier"].get(category, 1.0)
    if gt["size_sweet_spot"]["min_ratings"] <= total_ratings <= gt["size_sweet_spot"]["max_ratings"]:
        p *= gt["size_sweet_spot"]["multiplier"]
    p *= 1.0 + gt["severity_effect_slope"] * severity
    return min(1.0, p)
