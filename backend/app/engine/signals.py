"""
Deterministic signal computation from marketplace snapshots.

Signals are computed at the brand level per week from the top product per brand
(the highest-rated / most-reviewed product). Per SPEC 6.6.
"""

from __future__ import annotations

from dataclasses import dataclass

import polars as pl


@dataclass(frozen=True)
class BrandSignals:
    brand_alias: str
    week: int
    review_velocity: float           # verified reviews in last 4 weeks (top product)
    velocity_growth: float           # ratio last 13w vs prev 13w
    seller_delta_30d: int            # sellers now minus sellers 30d ago
    seller_count: int                # current
    buybox_share_30d: float          # share of days brand held Buy Box (last 30d)
    buybox_share_prev_30d: float     # previous 30 days
    oos_episodes_60d: int            # number of OOS episodes in last 60 days
    price_change_90d: float          # (price_now - price_90d_ago) / price_90d_ago
    ad_presence: float               # current ad presence index [0,1]
    rating_gap: float                # brand avg rating - category median avg rating


def _top_product_id(products_for_brand: pl.DataFrame) -> str | None:
    if products_for_brand.is_empty():
        return None
    ranked = products_for_brand.sort(
        by=["rating_number", "avg_rating"], descending=[True, True]
    )
    return ranked["parent_asin_hash"].to_list()[0]


def compute_brand_signals(
    week: int,
    snapshots_all: pl.DataFrame,
    products: pl.DataFrame,
    brands: pl.DataFrame,
) -> list[BrandSignals]:
    """
    snapshots_all: full 52-week snapshots for all products.
    products: prepared products table (brand_alias, parent_asin_hash, avg_rating, rating_number).
    brands: prepared brands table (alias, category, ...).
    """
    if snapshots_all.is_empty() or products.is_empty() or brands.is_empty():
        return []

    # Category rating median (over brands) for rating_gap.
    cat_medians = (
        brands.group_by("category")
        .agg(pl.col("avg_rating").median().alias("cat_median_rating"))
    )
    cat_median_by_cat = dict(
        zip(cat_medians["category"].to_list(), cat_medians["cat_median_rating"].to_list(), strict=True)
    )

    results: list[BrandSignals] = []
    for brand in brands.iter_rows(named=True):
        alias = brand["alias"]
        cat = brand["category"]
        brand_products = products.filter(pl.col("brand_alias") == alias)
        top_id = _top_product_id(brand_products)
        if not top_id:
            continue
        snaps = snapshots_all.filter(pl.col("product_id_key") == top_id).sort("week")
        if snaps.is_empty():
            continue

        # Windowed slices.
        window_last_4 = snaps.filter(pl.col("week").is_between(max(1, week - 3), week))
        window_last_13 = snaps.filter(pl.col("week").is_between(max(1, week - 12), week))
        window_prev_13 = snaps.filter(pl.col("week").is_between(max(1, week - 25), max(0, week - 13)))
        window_last_30d = snaps.filter(pl.col("week").is_between(max(1, week - 3), week))
        window_prev_30d = snaps.filter(pl.col("week").is_between(max(1, week - 7), max(0, week - 4)))
        window_last_60d = snaps.filter(pl.col("week").is_between(max(1, week - 8), week))
        window_this_week = snaps.filter(pl.col("week") == week)
        window_ago_30d = snaps.filter(pl.col("week") == max(1, week - 4))
        window_ago_90d = snaps.filter(pl.col("week") == max(1, week - 12))

        review_velocity = float(window_last_4["review_count"].sum() or 0)
        last_13_reviews = float(window_last_13["review_count"].sum() or 0)
        prev_13_reviews = float(window_prev_13["review_count"].sum() or 0)
        if prev_13_reviews < 2:
            velocity_growth = 2.0 if last_13_reviews >= 5 else 1.0
        else:
            velocity_growth = last_13_reviews / prev_13_reviews

        current_row = window_this_week.row(0, named=True) if not window_this_week.is_empty() else None
        past_row = window_ago_30d.row(0, named=True) if not window_ago_30d.is_empty() else None
        seller_count = int(current_row["seller_count"]) if current_row else 1
        past_sellers = int(past_row["seller_count"]) if past_row else seller_count
        seller_delta_30d = seller_count - past_sellers

        def _safe_share_mean(df: pl.DataFrame) -> float:
            vals = [v for v in df["buybox_share"].to_list() if v is not None]
            return float(sum(vals) / len(vals)) if vals else 0.0

        buybox_share_30d = _safe_share_mean(window_last_30d)
        buybox_share_prev_30d = _safe_share_mean(window_prev_30d)

        oos_episodes_60d = sum(1 for v in window_last_60d["in_stock"].to_list() if v is False)

        price_now_val = current_row["buybox_price"] if current_row else None
        price_ago_val = window_ago_90d.row(0, named=True)["buybox_price"] if not window_ago_90d.is_empty() else None
        if price_now_val and price_ago_val and price_ago_val > 0:
            price_change_90d = (price_now_val - price_ago_val) / price_ago_val
        else:
            price_change_90d = 0.0

        ad_presence = float(current_row["ad_presence"]) if current_row else 0.5

        rating_gap = float(brand["avg_rating"] or 0.0) - float(cat_median_by_cat.get(cat, 0.0) or 0.0)

        results.append(
            BrandSignals(
                brand_alias=alias,
                week=week,
                review_velocity=review_velocity,
                velocity_growth=velocity_growth,
                seller_delta_30d=seller_delta_30d,
                seller_count=seller_count,
                buybox_share_30d=buybox_share_30d,
                buybox_share_prev_30d=buybox_share_prev_30d,
                oos_episodes_60d=oos_episodes_60d,
                price_change_90d=price_change_90d,
                ad_presence=ad_presence,
                rating_gap=rating_gap,
            )
        )
    return results


def signals_to_df(signals: list[BrandSignals]) -> pl.DataFrame:
    if not signals:
        return pl.DataFrame()
    return pl.DataFrame([s.__dict__ for s in signals])
