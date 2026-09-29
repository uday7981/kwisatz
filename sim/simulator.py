"""
Simulator — writes 52 weeks of marketplace snapshots per product per brand, given the
hidden archetype assigned in `data/prepared/brands.parquet` and anchored on the real
weekly review velocity from `data/prepared/review_velocity.parquet`.

Deterministic given seed. The 12 demo weeks are indices 41..52 (1-based, inclusive).
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import polars as pl
import yaml

from backend.app.config import PREPARED_ROOT, SIM_ROOT
from scripts._log import get_logger

log = get_logger("simulator")

WEEKS = 52
DEMO_WEEK_START = 41  # inclusive
DEMO_WEEK_END = 52  # inclusive

SIM_START_DATE = datetime(2026, 3, 30, tzinfo=UTC)  # sim week 1


def week_to_date(week: int) -> datetime:
    return SIM_START_DATE + timedelta(days=(week - 1) * 7)


@dataclass(frozen=True)
class Archetype:
    name: str
    seller_growth: float = 0.0  # avg new sellers per week
    seller_shock_week: int | None = None
    buybox_erosion: float = 0.0  # per week during shock window
    price_erosion: float = 0.0  # weekly % drop
    stockout_probability: float = 0.0  # per week
    conversion_index: float = 1.0  # multiplier on demand-index
    ad_presence_base: float = 0.5
    review_growth_multiplier: float = 1.0


ARCHETYPES = {
    "reseller_invasion": Archetype(
        name="reseller_invasion",
        seller_growth=0.4,
        seller_shock_week=38,
        buybox_erosion=0.05,
        price_erosion=0.005,
        ad_presence_base=0.5,
        review_growth_multiplier=1.05,
    ),
    "stockout_prone": Archetype(
        name="stockout_prone",
        seller_growth=0.02,
        stockout_probability=0.15,
        ad_presence_base=0.4,
        review_growth_multiplier=1.2,
    ),
    "weak_converter": Archetype(
        name="weak_converter",
        seller_growth=0.01,
        conversion_index=0.55,
        ad_presence_base=0.35,
        review_growth_multiplier=1.0,
    ),
    "price_erosion": Archetype(
        name="price_erosion",
        seller_growth=0.05,
        buybox_erosion=0.005,
        price_erosion=0.008,
        ad_presence_base=0.55,
        review_growth_multiplier=1.05,
    ),
    "under_advertised": Archetype(
        name="under_advertised",
        seller_growth=0.02,
        ad_presence_base=0.18,
        review_growth_multiplier=1.35,
    ),
    "healthy_riser": Archetype(
        name="healthy_riser",
        seller_growth=0.01,
        ad_presence_base=0.7,
        review_growth_multiplier=1.15,
    ),
    "distractor": Archetype(
        name="distractor",
        seller_growth=0.0,
        ad_presence_base=0.5,
        review_growth_multiplier=1.0,
    ),
}


def _load_ground_truth() -> dict:
    path = Path(__file__).with_name("ground_truth.yaml")
    with path.open() as fh:
        return yaml.safe_load(fh)


def _demand_from_velocity(v_week: int) -> float:
    return max(1.0, float(v_week))


def _bsr_from_demand(demand: float, rng: random.Random) -> int:
    # Real BSR is inverse to demand. Add lognormal noise.
    if demand <= 0:
        demand = 1
    base = 10_000_000.0 / (demand ** 1.3 + 1.0)
    noise = math.exp(rng.gauss(0.0, 0.25))
    return int(max(50, base * noise))


def simulate_product(
    product_row: dict,
    velocity_by_week: dict[int, int],
    archetype: Archetype,
    rng: random.Random,
) -> list[dict]:
    """Return one dict per week for a single product."""
    weeks: list[dict] = []

    starting_price = float(product_row["price"] or 20.0) or 20.0
    starting_sellers = 1
    seller_count = starting_sellers
    price = starting_price
    buybox_share = 0.95
    ad_presence = archetype.ad_presence_base + rng.gauss(0.0, 0.04)
    ad_presence = min(0.95, max(0.05, ad_presence))
    in_stock = True
    consecutive_oos = 0

    for w in range(1, WEEKS + 1):
        # Sellers gradually grow, then a shock for reseller_invasion.
        new_sellers = 0.0
        if archetype.seller_shock_week is not None and w >= archetype.seller_shock_week:
            weeks_in_shock = w - archetype.seller_shock_week
            new_sellers = 1.4 if weeks_in_shock < 4 else 0.35
        else:
            new_sellers = archetype.seller_growth
        seller_count = int(round(seller_count + rng.gauss(new_sellers, 0.4)))
        seller_count = max(1, min(seller_count, 25))

        # Buybox share erodes once resellers show up in force.
        if seller_count > 3:
            buybox_share = max(0.40, buybox_share - archetype.buybox_erosion - rng.uniform(0.0, 0.02))
        else:
            buybox_share = min(0.98, buybox_share + rng.uniform(0.0, 0.01))

        # Price erosion follows buybox share loss for price_erosion / reseller_invasion.
        price = max(starting_price * 0.5, price * (1 - archetype.price_erosion + rng.gauss(0.0, 0.002)))

        # Stock episodes.
        if archetype.stockout_probability and rng.random() < archetype.stockout_probability:
            in_stock = False
            consecutive_oos += 1
        else:
            in_stock = True
            consecutive_oos = 0

        # Demand: real velocity scaled by conversion index; drop hard while OOS.
        vel = velocity_by_week.get(w, 0)
        demand = _demand_from_velocity(int(vel * archetype.review_growth_multiplier))
        demand *= archetype.conversion_index
        if not in_stock:
            demand *= 0.15

        bsr = _bsr_from_demand(demand, rng)

        # Small random glitch: 1% chance of null price/demand (missing week).
        if rng.random() < 0.01:
            missing = True
        else:
            missing = False

        weeks.append(
            {
                "product_id_key": product_row["parent_asin_hash"],
                "brand_alias": product_row["brand_alias"],
                "week": w,
                "date": week_to_date(w),
                "demand_index": None if missing else round(demand, 2),
                "bsr": None if missing else bsr,
                "seller_count": seller_count,
                "buybox_share": round(buybox_share, 3),
                "buybox_price": None if missing else round(price, 2),
                "in_stock": in_stock,
                "ad_presence": round(min(0.95, max(0.05, ad_presence + rng.gauss(0.0, 0.02))), 3),
                "review_count": int(vel),
            }
        )
    return weeks


def build_snapshots() -> pl.DataFrame:
    brands_path = PREPARED_ROOT / "brands.parquet"
    products_path = PREPARED_ROOT / "products.parquet"
    velocity_path = PREPARED_ROOT / "review_velocity.parquet"

    if not brands_path.exists() or not products_path.exists() or not velocity_path.exists():
        raise SystemExit("Missing prepared parquet. Run `make data` first.")

    brands = pl.read_parquet(brands_path)
    products = pl.read_parquet(products_path)
    velocity = pl.read_parquet(velocity_path)

    archetype_by_alias = dict(zip(brands["alias"].to_list(), brands["archetype_hidden"].to_list(), strict=True))
    velocity_by_asin_week: dict[tuple[str, int], int] = {}
    for row in velocity.iter_rows(named=True):
        # anonymise.py names the column `sim_week`.
        wk = row.get("sim_week") if "sim_week" in row else row.get("week")
        if wk is None:
            continue
        velocity_by_asin_week[(row["parent_asin_hash"], int(wk))] = int(row["review_count"])

    gt = _load_ground_truth()
    seed = int(gt.get("seed", 42))
    rng = random.Random(seed)

    rows: list[dict] = []
    for prod in products.iter_rows(named=True):
        arch_name = archetype_by_alias.get(prod["brand_alias"], "healthy_riser")
        archetype = ARCHETYPES[arch_name]
        vel_by_week = {
            w: velocity_by_asin_week.get((prod["parent_asin_hash"], w), 0)
            for w in range(1, WEEKS + 1)
        }
        product_rng = random.Random(seed ^ hash(prod["parent_asin_hash"]))
        rows.extend(simulate_product(prod, vel_by_week, archetype, product_rng))
        _ = rng.random()  # consume from master rng for reproducibility

    return pl.DataFrame(rows)


def main() -> None:
    SIM_ROOT.mkdir(parents=True, exist_ok=True)
    snapshots = build_snapshots()
    out = SIM_ROOT / "snapshots.parquet"
    snapshots.write_parquet(out, compression="zstd")
    log.info("wrote %s (%d rows)", out, len(snapshots))


if __name__ == "__main__":
    main()
