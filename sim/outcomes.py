"""
Outreach outcome simulator. Reads the hidden ground_truth.yaml and applies its rules
to per-week candidate pitches. Only the eval harness and the simulator call this.

Interface: the outcomes here are pre-generated for every (brand_alias, week_sent, angle)
tuple the agent *might* pick, so the eval harness can look them up by key without
re-sampling. This keeps memory-on and memory-off runs directly comparable.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path

import polars as pl
import yaml

from backend.app.config import PREPARED_ROOT, SIM_ROOT
from scripts._log import get_logger

log = get_logger("outcomes")

DEMO_WEEK_START = 41
DEMO_WEEK_END = 52
# Outcomes are generated for the whole season so seeding weeks 1-40 has real outcome
# retentions to consolidate. Eval still measures the demo window (41..52).
OUTCOME_WEEK_START = 1
OUTCOME_WEEK_END = 52
ANGLES = (
    "brand_protection",
    "inventory_planning",
    "listing_and_reviews",
    "map_enforcement",
    "advertising",
    "growth_partnership",
)

REPLY_TEXT_POSITIVE = "Timing is good actually. Can you do Thursday?"
REPLY_TEXT_NOT_NOW = "Not the right time, we're stretched until after {period}."
REPLY_TEXT_DECLINED_INHOUSE = "We manage Amazon in-house, thanks."
REPLY_TEXT_DECLINED_AGENCY = "We already work with an agency."


@dataclass(frozen=True)
class Outcome:
    brand_alias: str
    week_sent: int
    week_arrived: int
    angle: str
    type: str  # no_reply | reply | meeting | signed | declined | not_now
    reason_text: str
    revisit_after_week: int


def _load_gt() -> dict:
    path = Path(__file__).with_name("ground_truth.yaml")
    with path.open() as fh:
        return yaml.safe_load(fh)


def _reply_probability(gt: dict, archetype: str, angle: str, category: str, severity: float, total_ratings: int) -> float:
    fit = gt["angle_fit"].get(archetype, {})
    mult = fit.get(angle) or fit.get("other", 1.0)
    p = gt["base_reply_rate"] * mult
    p *= gt["category_modifier"].get(category, 1.0)
    if gt["size_sweet_spot"]["min_ratings"] <= total_ratings <= gt["size_sweet_spot"]["max_ratings"]:
        p *= gt["size_sweet_spot"]["multiplier"]
    p *= 1.0 + gt["severity_effect_slope"] * severity
    return max(0.0, min(0.95, p))


def simulate_outcomes(
    seed: int,
    brands: pl.DataFrame,
    diagnoses_by_week: dict[tuple[str, int], tuple[str, float]],
) -> list[Outcome]:
    """
    Generate outcomes for every (brand, demo_week, angle) tuple. For each tuple we
    sample a reply Bernoulli; if reply, sample meeting/signed conditionals; noise
    slope is applied at the end.
    """
    gt = _load_gt()
    rng = random.Random(seed)

    total_ratings_by_alias = dict(zip(brands["alias"].to_list(), brands["total_ratings"].to_list(), strict=True))
    category_by_alias = dict(zip(brands["alias"].to_list(), brands["category"].to_list(), strict=True))
    archetype_by_alias = dict(zip(brands["alias"].to_list(), brands["archetype_hidden"].to_list(), strict=True))

    in_house = {a for a in brands["alias"].to_list() if rng.random() < gt["in_house_flag_rate"]}

    delay_lo, delay_hi = gt["reply_delay_weeks"]
    outcomes: list[Outcome] = []

    for alias in brands["alias"].to_list():
        for week in range(OUTCOME_WEEK_START, OUTCOME_WEEK_END + 1):
            dx_severity = diagnoses_by_week.get((alias, week), ("D6", 0.3))
            _dx_code, severity = dx_severity
            for angle in ANGLES:
                p = _reply_probability(
                    gt,
                    archetype_by_alias[alias],
                    angle,
                    category_by_alias[alias],
                    severity,
                    total_ratings_by_alias[alias],
                )
                # In-house rejection except when angle is the correct fit.
                fit_map = gt["angle_fit"].get(archetype_by_alias[alias], {})
                is_perfect_fit = (fit_map.get(angle) or 0) >= 3.0
                if alias in in_house and not is_perfect_fit:
                    p *= 0.15

                # Noise floor: coin flip on ~noise fraction of samples that inverts p.
                if rng.random() < gt["noise"]:
                    p = max(0.02, 1 - p if p > 0.5 else p * 1.5)

                replied = rng.random() < p
                delay = rng.randint(delay_lo, delay_hi)
                week_arrived = min(OUTCOME_WEEK_END, week + delay)

                if not replied:
                    outcomes.append(
                        Outcome(
                            brand_alias=alias, week_sent=week, week_arrived=week_arrived,
                            angle=angle, type="no_reply", reason_text="",
                            revisit_after_week=0,
                        )
                    )
                    continue

                # Reply path
                r = rng.random()
                if r < gt["not_now_share_of_replies"]:
                    period = rng.choice(["Q4", "January", "the launch", "the freeze"])
                    outcomes.append(
                        Outcome(
                            brand_alias=alias, week_sent=week, week_arrived=week_arrived,
                            angle=angle, type="not_now",
                            reason_text=REPLY_TEXT_NOT_NOW.format(period=period),
                            revisit_after_week=week + rng.randint(6, 16),
                        )
                    )
                    continue
                if r < gt["not_now_share_of_replies"] + gt["declined_share_of_replies"]:
                    reason = REPLY_TEXT_DECLINED_INHOUSE if alias in in_house else REPLY_TEXT_DECLINED_AGENCY
                    outcomes.append(
                        Outcome(
                            brand_alias=alias, week_sent=week, week_arrived=week_arrived,
                            angle=angle, type="declined", reason_text=reason,
                            revisit_after_week=0,
                        )
                    )
                    continue
                # Positive reply — maybe meeting -> maybe signed.
                if rng.random() < gt["meeting_given_reply"]:
                    if rng.random() < gt["signed_given_meeting"]:
                        outcomes.append(
                            Outcome(
                                brand_alias=alias, week_sent=week, week_arrived=week_arrived,
                                angle=angle, type="signed", reason_text=REPLY_TEXT_POSITIVE,
                                revisit_after_week=0,
                            )
                        )
                    else:
                        outcomes.append(
                            Outcome(
                                brand_alias=alias, week_sent=week, week_arrived=week_arrived,
                                angle=angle, type="meeting", reason_text=REPLY_TEXT_POSITIVE,
                                revisit_after_week=0,
                            )
                        )
                else:
                    outcomes.append(
                        Outcome(
                            brand_alias=alias, week_sent=week, week_arrived=week_arrived,
                            angle=angle, type="reply", reason_text=REPLY_TEXT_POSITIVE,
                            revisit_after_week=0,
                        )
                    )
    return outcomes


def compute_all_diagnoses(snapshots: pl.DataFrame, products: pl.DataFrame, brands: pl.DataFrame) -> dict[tuple[str, int], tuple[str, float]]:
    """Pre-compute (dx, severity) for every (alias, week) so outcomes can key off them."""
    from backend.app.engine.diagnosis import primary_diagnosis
    from backend.app.engine.signals import compute_brand_signals

    out: dict[tuple[str, int], tuple[str, float]] = {}
    for week in range(1, 53):
        sigs = compute_brand_signals(week, snapshots, products, brands)
        from backend.app.engine.diagnosis import diagnose_brand
        for sig in sigs:
            hits = diagnose_brand(sig)
            dx = primary_diagnosis(hits)
            if dx:
                out[(sig.brand_alias, week)] = (dx.code, dx.severity)
    return out


def main() -> None:
    SIM_ROOT.mkdir(parents=True, exist_ok=True)
    brands = pl.read_parquet(PREPARED_ROOT / "brands.parquet")
    products = pl.read_parquet(PREPARED_ROOT / "products.parquet")
    snapshots = pl.read_parquet(SIM_ROOT / "snapshots.parquet")

    dx_by_week = compute_all_diagnoses(snapshots, products, brands)
    log.info("computed %d (alias, week) diagnoses", len(dx_by_week))

    gt = _load_gt()
    outcomes = simulate_outcomes(seed=gt.get("seed", 42), brands=brands, diagnoses_by_week=dx_by_week)
    df = pl.DataFrame([o.__dict__ for o in outcomes])
    out = SIM_ROOT / "outcomes.parquet"
    df.write_parquet(out, compression="zstd")
    log.info("wrote %s (%d outcome rows)", out, len(df))


if __name__ == "__main__":
    main()
