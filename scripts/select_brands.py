"""
Select underdog brands from per-category raw parquet.

Per SPEC 5.4:
  - Group meta by `store` (== brand).
  - Keep brands with 3-40 products AND 50-5000 total ratings.
  - Compute monthly verified review counts per brand; keep brands whose last-6-mo
    velocity is >= 20% higher than prior-6-mo velocity (rising).
  - Sample ~60 per category (180 total), stratified by price band and product count,
    including some flat/declining distractors.

Output: data/prepared/brand_candidates.parquet
        (real store names still present; anonymisation happens next.)
"""

from __future__ import annotations

import os
from datetime import UTC, datetime

import polars as pl

from backend.app.config import CATEGORIES, PREPARED_ROOT, RAW_ROOT
from scripts._log import get_logger

log = get_logger("select_brands")

MIN_PRODUCTS = 3
MAX_PRODUCTS = 40
MIN_RATINGS = 50
MAX_RATINGS = 5000
GROWTH_THRESHOLD = 0.20
TARGET_PER_CATEGORY = 60
DISTRACTOR_FRACTION = 0.10  # 10% flat/declining brands survive as distractors


def _categories() -> list[str]:
    if os.getenv("UNDERDOG_SLIM"):
        return ["Pet_Supplies"]
    return list(CATEGORIES)


def _brand_size_ok(row: dict[str, object]) -> bool:
    n = int(row["n_products"] or 0)
    ratings = int(row["total_ratings"] or 0)
    return MIN_PRODUCTS <= n <= MAX_PRODUCTS and MIN_RATINGS <= ratings <= MAX_RATINGS


def _rising(velocity_last: float, velocity_prev: float) -> bool:
    if velocity_prev < 5:
        return velocity_last >= 10  # low base — require modest absolute lift
    return (velocity_last / velocity_prev) >= (1 + GROWTH_THRESHOLD)


def process_category(cat: str, seed: int) -> pl.DataFrame:
    meta_path = RAW_ROOT / f"{cat}_meta.parquet"
    review_path = RAW_ROOT / f"{cat}_reviews.parquet"
    if not meta_path.exists() or not review_path.exists():
        log.warning("skip %s (raw parquet missing)", cat)
        return pl.DataFrame()

    meta = pl.read_parquet(meta_path)
    if meta.is_empty():
        return pl.DataFrame()

    # brand-level aggregates
    agg = (
        meta.group_by("store")
        .agg(
            [
                pl.len().alias("n_products"),
                pl.col("rating_number").sum().alias("total_ratings"),
                pl.col("average_rating").mean().alias("avg_rating"),
                pl.col("price").drop_nulls().min().alias("price_min"),
                pl.col("price").drop_nulls().max().alias("price_max"),
                pl.col("parent_asin").alias("asins"),
            ]
        )
        .filter(pl.col("n_products").is_between(MIN_PRODUCTS, MAX_PRODUCTS))
        .filter(pl.col("total_ratings").is_between(MIN_RATINGS, MAX_RATINGS))
        .filter(pl.col("price_min").is_not_null())
    )
    log.info("[%s] brands passing size filter: %d", cat, len(agg))

    # Explode to parent_asin, then compute velocity buckets from reviews.
    brand_asin = agg.select(["store", "asins"]).explode("asins").rename({"asins": "parent_asin"})

    reviews = pl.read_parquet(review_path).filter(pl.col("verified_purchase"))
    # Real reviews end in 2023-09; use 2023-09-30 as the anchor.
    anchor = int(datetime(2023, 9, 30, tzinfo=UTC).timestamp())
    six_mo = 60 * 60 * 24 * 30 * 6
    reviews = reviews.with_columns(
        [
            pl.col("timestamp_s").alias("ts"),
        ]
    ).filter(pl.col("ts") <= anchor).filter(pl.col("ts") >= anchor - 2 * six_mo)

    joined = reviews.join(brand_asin, on="parent_asin", how="inner")
    if joined.is_empty():
        log.warning("[%s] no reviews joined; skipping category", cat)
        return pl.DataFrame()

    joined = joined.with_columns(
        pl.when(pl.col("ts") >= anchor - six_mo)
        .then(pl.lit("last"))
        .otherwise(pl.lit("prev"))
        .alias("bucket"),
    )
    velocity = (
        joined.group_by(["store", "bucket"])
        .agg(pl.len().alias("count"))
        .pivot(values="count", index="store", on="bucket")
    )
    # Ensure both bucket columns exist even if all reviews land in one.
    for col in ("last", "prev"):
        if col not in velocity.columns:
            velocity = velocity.with_columns(pl.lit(0).alias(col))
    velocity = velocity.with_columns([pl.col("last").fill_null(0), pl.col("prev").fill_null(0)])
    velocity = velocity.with_columns(
        [
            (pl.col("last") + pl.col("prev")).alias("velocity_total"),
            (
                pl.when(pl.col("prev") == 0)
                .then(pl.when(pl.col("last") == 0).then(0.0).otherwise(2.0))
                .otherwise(pl.col("last") / pl.col("prev"))
            ).alias("velocity_ratio"),
        ]
    )

    merged = (
        agg.drop("asins")
        .join(velocity, on="store", how="left")
        .fill_null(0)
        .with_columns(pl.lit(cat).alias("category"))
    )

    rising = merged.filter(pl.col("velocity_ratio") >= 1 + GROWTH_THRESHOLD)
    flat = merged.filter((pl.col("velocity_ratio") < 1 + GROWTH_THRESHOLD) & (pl.col("velocity_total") > 0))
    log.info(
        "[%s] after velocity: rising=%d, flat/declining=%d",
        cat,
        len(rising),
        len(flat),
    )

    # Stratified sample: price bands x product count.
    def stratified(df: pl.DataFrame, n: int) -> pl.DataFrame:
        if df.is_empty() or n <= 0:
            return df.head(0)
        # 3 price bands, 2 size buckets = 6 strata.
        with_strata = df.with_columns(
            [
                pl.when(pl.col("price_min") < 15)
                .then(pl.lit("cheap"))
                .when(pl.col("price_min") < 40)
                .then(pl.lit("mid"))
                .otherwise(pl.lit("premium"))
                .alias("price_band"),
                pl.when(pl.col("n_products") <= 10).then(pl.lit("small")).otherwise(pl.lit("big")).alias("size_band"),
            ]
        )
        strata = with_strata.partition_by(["price_band", "size_band"], as_dict=True)
        per_strat = max(1, n // max(1, len(strata)))
        pieces = [df_strat.sample(min(per_strat, len(df_strat)), seed=seed) for df_strat in strata.values()]
        picked = pl.concat(pieces) if pieces else with_strata.head(0)
        if len(picked) > n:
            picked = picked.sample(n, seed=seed)
        elif len(picked) < n and len(with_strata) > len(picked):
            extra = with_strata.join(picked.select("store"), on="store", how="anti").sample(
                min(n - len(picked), len(with_strata) - len(picked)), seed=seed
            )
            picked = pl.concat([picked, extra])
        return picked.drop(["price_band", "size_band"])

    keep_rising = int(TARGET_PER_CATEGORY * (1 - DISTRACTOR_FRACTION))
    keep_distractor = TARGET_PER_CATEGORY - keep_rising
    picked_rising = stratified(rising, keep_rising)
    # If our review sample is too sparse to identify growth, backfill the rising slot
    # from the flat pool so downstream stages still see ~60 brands per category.
    if len(picked_rising) < keep_rising:
        need = keep_rising - len(picked_rising) + keep_distractor
        picked_flat = stratified(flat, need)
    else:
        picked_flat = stratified(flat, keep_distractor)
    picked = pl.concat([picked_rising, picked_flat])
    log.info("[%s] picked %d brands (%d rising, %d flat)", cat, len(picked), len(picked_rising), len(picked_flat))
    return picked


def main() -> None:
    PREPARED_ROOT.mkdir(parents=True, exist_ok=True)
    from backend.app.config import get_settings

    seed = get_settings().sim_seed

    frames = [process_category(cat, seed=seed) for cat in _categories()]
    frames = [f for f in frames if not f.is_empty()]
    if not frames:
        raise SystemExit("No brand candidates produced. Did `make data` run?")

    all_brands = pl.concat(frames)
    out = PREPARED_ROOT / "brand_candidates.parquet"
    all_brands.write_parquet(out, compression="zstd")
    log.info("wrote %s (%d rows)", out, len(all_brands))
    log.info(
        "counts by category:\n%s",
        all_brands.group_by("category").agg(pl.len().alias("n")).sort("category"),
    )


if __name__ == "__main__":
    main()
