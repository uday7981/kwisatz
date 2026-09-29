"""
Seed the Hindsight bank with weeks 1..8: retain material changes, run pitches,
retain outcomes as they arrive. This runs against `HINDSIGHT_SEED_BANK`, then clones
into `HINDSIGHT_BANK` so a fresh demo can start from week 9 quickly.

Requires HINDSIGHT_API_KEY and network access. `SEED_LIMIT_BRANDS` env caps how
many brands per week are processed (default 40) to conserve Hindsight credit.
"""

from __future__ import annotations

import os

import polars as pl

from backend.app.adapters.simulated import SimulatedAdapter
from backend.app.config import get_settings
from backend.app.engine.diagnosis import DX_TO_ANGLE, diagnose_brand, primary_diagnosis
from backend.app.engine.loop import _brand_signals
from backend.app.memory.bank_setup import setup_bank
from backend.app.memory.service import MemoryService
from scripts._log import get_logger
from sim.simulator import week_to_date

log = get_logger("seed_bank")

SEED_WEEK_START = 20  # start where diagnoses begin firing regularly
SEED_WEEK_END = 40  # seed weeks 20..40 so memory has real history right before demo (41..52)
MATERIAL_EVERY_N_WEEKS = 4  # per SPEC: retain every 4th week even without threshold moves


def _material_snapshots(week: int, adapter: SimulatedAdapter, brand_meta: dict) -> list[dict]:
    sigs = _brand_signals(week, adapter)
    out: list[dict] = []
    for sig in sigs:
        meta = brand_meta.get(sig.brand_alias)
        if not meta:
            continue  # brand outside the seed subset
        hits = diagnose_brand(sig)
        dx = primary_diagnosis(hits)
        # material if a diagnosis fires OR every 4th week
        if not dx and week % MATERIAL_EVERY_N_WEEKS != 0:
            continue
        out.append({
            "brand_alias": sig.brand_alias,
            "category": meta["category"],
            "n_products": int(meta["n_products"]),
            "dx_code": dx.code if dx else "D6",
            "severity": dx.severity if dx else 0.0,
            "evidence": (dx.evidence if dx else {"velocity_growth": round(sig.velocity_growth, 3)}),
        })
    return out


def main() -> None:
    settings = get_settings()
    if not settings.hindsight_api_key:
        raise SystemExit("HINDSIGHT_API_KEY not set; cannot seed.")

    limit = int(os.getenv("SEED_LIMIT_BRANDS", "0"))  # 0 = all brands
    per_week_pitches = int(os.getenv("SEED_PITCHES_PER_WEEK", "20"))
    adapter = SimulatedAdapter()

    brands = adapter.brands().sort("alias")
    if limit:
        brands = brands.head(limit)
    brand_meta = {row["alias"]: row for row in brands.iter_rows(named=True)}

    outcomes_df = adapter._outcomes_df()
    # Index outcomes by (alias, week_sent, angle) so we can look them up cheaply
    # when retaining only the outcomes that match a real pitch we sent.
    outcome_by_key: dict[tuple[str, int, str], dict] = {}
    for row in outcomes_df.iter_rows(named=True):
        outcome_by_key[(row["brand_alias"], int(row["week_sent"]), row["angle"])] = row

    # Track pitches we sent so we can retain their outcomes with the right dx tag.
    pitches_sent: dict[tuple[str, int], tuple[str, str]] = {}

    with MemoryService.from_env() as svc:
        # Ensure the SEED bank exists (not the live one).
        svc.bank_id = settings.hindsight_seed_bank
        setup_bank(svc)

        for week in range(SEED_WEEK_START, SEED_WEEK_END + 1):
            log.info("=== seeding week %d ===", week)
            sim_date = week_to_date(week)

            material = _material_snapshots(week, adapter, brand_meta)
            svc.retain_material_changes(week=week, sim_date=sim_date, snapshots=material)

            # Pitch top 12 per SPEC using the fixed diagnosis-to-angle mapping
            # (memory-off style — the seed is what the agent would do without memory).
            sigs = _brand_signals(week, adapter)
            ranked = []
            for sig in sigs:
                hits = diagnose_brand(sig)
                dx = primary_diagnosis(hits)
                meta = brand_meta.get(sig.brand_alias)
                if not meta:
                    continue
                angle = DX_TO_ANGLE.get(dx.code, "growth_partnership") if dx else "growth_partnership"
                base = dx.severity if dx else 0.3
                ranked.append((sig.brand_alias, meta, dx.code if dx else "D6", angle, base))
            ranked.sort(key=lambda t: t[4], reverse=True)
            top = ranked[:per_week_pitches]
            for rank_i, (alias, meta, dx_code, angle, base_score) in enumerate(top, start=1):
                svc.retain_pitch(
                    week=week, sim_date=sim_date, brand_alias=alias,
                    category=meta["category"], dx_code=dx_code, angle=angle,
                    base_score=base_score, rank=rank_i, top_of=len(top),
                    reason=f"rule-based pick for {dx_code}",
                )
                pitches_sent[(alias, week)] = (dx_code, angle)

            # Retain outcomes arriving THIS week — but ONLY for pitches we actually
            # sent (so the memory reflects real learning signal, not every angle).
            arriving = outcomes_df.filter(pl.col("week_arrived") == week)
            for row in arriving.iter_rows(named=True):
                pitch = pitches_sent.get((row["brand_alias"], int(row["week_sent"])))
                if pitch is None:
                    continue
                sent_dx, sent_angle = pitch
                if row["angle"] != sent_angle:
                    continue  # this outcome is for an angle we did not send
                meta = brand_meta.get(row["brand_alias"])
                if not meta:
                    continue
                svc.retain_outcome(
                    week=week, sim_date=sim_date,
                    brand_alias=row["brand_alias"], category=meta["category"],
                    dx_code=sent_dx,
                    angle=row["angle"],
                    outcome_type=row["type"], reason_text=row.get("reason_text", ""),
                    revisit_after=(str(row["revisit_after_week"]) if row.get("revisit_after_week") else None),
                )

        log.info("seed pass complete; cloning %s -> %s", settings.hindsight_seed_bank, settings.hindsight_bank)
        svc.bank_id = settings.hindsight_seed_bank  # ensure source
        svc.seed_bank_id = settings.hindsight_seed_bank
        clone_op = svc.reset_from_seed(settings.hindsight_bank)
        log.info("clone op id: %s (poll operations for completion)", clone_op)


if __name__ == "__main__":
    main()
