"""
Anonymise selected brands and materialise the prepared dataset.

Inputs:
  data/prepared/brand_candidates.parquet
  data/raw/{cat}_meta.parquet
  data/raw/{cat}_reviews.parquet

Outputs:
  brand_alias.csv                                 (gitignored: real store -> alias)
  data/prepared/brands.parquet                    (public: alias, category, aggregates)
  data/prepared/products.parquet                  (public: brand_alias, product data)
  data/prepared/review_velocity.parquet           (public: weekly review counts per product)

Aliases are deterministic given SIM_SEED so runs reproduce.
"""

from __future__ import annotations

import csv
import hashlib
import os
import random
from datetime import UTC, datetime

import polars as pl
from faker import Faker

from backend.app.config import CATEGORIES, PREPARED_ROOT, RAW_ROOT, REPO_ROOT, get_settings
from scripts._log import get_logger

log = get_logger("anonymise")

ALIAS_FILE = REPO_ROOT / "brand_alias.csv"


NATURE_STEMS = [
    "Copperleaf",
    "Hearthline",
    "Pawsmith",
    "Northwind",
    "Riverstone",
    "Wildmoor",
    "Ashwood",
    "Foxglade",
    "Ironbark",
    "Wisteria",
    "Willowford",
    "Thornbury",
    "Marshall",
    "Cinderpeak",
    "Braemar",
    "Elderfen",
    "Kestrel",
    "Loomcraft",
    "Rowanhill",
    "Silverbrook",
    "Meadowlark",
    "Nightowl",
    "Amberfall",
    "Slatehaven",
    "Timberkin",
    "Cloverdale",
    "Foxwater",
    "Junegrove",
    "Sablecrest",
    "Yarrowmere",
]
SUFFIXES_HK = ["Kitchen", "Home", "Studio", "Works", "Foundry", "Table", "Hearth", "Provisions", "Craft"]
SUFFIXES_PET = ["Paws", "Trail", "Meadow", "Pack", "Perch", "Den", "Kibble", "Pet Co", "Barn"]
SUFFIXES_HH = ["Wellness", "Botanicals", "Apothecary", "Living", "Balance", "Remedies", "Restore", "Elements"]

SUFFIX_BY_CATEGORY: dict[str, list[str]] = {
    "Home_and_Kitchen": SUFFIXES_HK,
    "Pet_Supplies": SUFFIXES_PET,
    "Health_and_Household": SUFFIXES_HH,
}


def _categories() -> list[str]:
    if os.getenv("UNDERDOG_SLIM"):
        return ["Pet_Supplies"]
    return list(CATEGORIES)


def _slug(alias: str) -> str:
    return alias.lower().replace(" ", "-").replace(".", "").replace("&", "and")


def _make_alias(rng: random.Random, category: str, used: set[str], faker: Faker) -> str:
    for _ in range(200):
        stem = rng.choice(NATURE_STEMS)
        suffix = rng.choice(SUFFIX_BY_CATEGORY.get(category, SUFFIXES_HK))
        alias = f"{stem} {suffix}"
        if alias not in used:
            return alias
    # fallback: append a colour word
    for _ in range(200):
        stem = rng.choice(NATURE_STEMS)
        colour = faker.color_name()
        alias = f"{stem} {colour}"
        if alias not in used:
            return alias
    raise RuntimeError("alias space exhausted")


def _hash_asin(asin: str, salt: str) -> str:
    return hashlib.blake2s(f"{salt}:{asin}".encode(), digest_size=8).hexdigest()


def load_alias_map() -> dict[str, str]:
    if not ALIAS_FILE.exists():
        return {}
    with ALIAS_FILE.open() as fh:
        return {row["store"]: row["alias"] for row in csv.DictReader(fh)}


def save_alias_map(mapping: dict[str, str]) -> None:
    ALIAS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with ALIAS_FILE.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["store", "alias"])
        writer.writeheader()
        for store, alias in sorted(mapping.items()):
            writer.writerow({"store": store, "alias": alias})
    log.info("wrote %s (%d aliases)", ALIAS_FILE, len(mapping))


def main() -> None:
    PREPARED_ROOT.mkdir(parents=True, exist_ok=True)
    settings = get_settings()
    seed = settings.sim_seed

    candidates_path = PREPARED_ROOT / "brand_candidates.parquet"
    if not candidates_path.exists():
        raise SystemExit("Missing brand_candidates.parquet. Run `make data` first.")
    candidates = pl.read_parquet(candidates_path)

    rng = random.Random(seed)
    faker = Faker(); Faker.seed(seed)

    alias_map = load_alias_map()
    used = set(alias_map.values())

    # Assign aliases (stable across runs given seed + same brand order).
    picked = candidates.sort("store")
    aliases: list[str] = []
    for store, category in zip(picked["store"].to_list(), picked["category"].to_list(), strict=True):
        alias = alias_map.get(store)
        if alias is None:
            alias = _make_alias(rng, category, used, faker)
            alias_map[store] = alias
            used.add(alias)
        aliases.append(alias)
    picked = picked.with_columns(pl.Series("alias", aliases))
    save_alias_map(alias_map)

    # Assign hidden archetypes (agent never sees these).
    archetypes = [
        ("reseller_invasion", 0.20),
        ("stockout_prone", 0.15),
        ("weak_converter", 0.15),
        ("price_erosion", 0.10),
        ("under_advertised", 0.15),
        ("healthy_riser", 0.15),
        ("distractor", 0.10),
    ]
    archetype_names = [a for a, _ in archetypes]
    archetype_weights = [w for _, w in archetypes]
    hidden = [
        rng.choices(archetype_names, weights=archetype_weights, k=1)[0]
        for _ in range(len(picked))
    ]
    picked = picked.with_columns(pl.Series("archetype_hidden", hidden))

    brand_out = picked.select(
        [
            "alias",
            "category",
            "n_products",
            "total_ratings",
            "avg_rating",
            "price_min",
            "price_max",
            "archetype_hidden",
        ]
    )
    brand_path = PREPARED_ROOT / "brands.parquet"
    brand_out.write_parquet(brand_path, compression="zstd")
    log.info("wrote %s (%d brands)", brand_path, len(brand_out))

    # Build products + review velocity (weekly) tables per selected brand.
    store_to_alias = dict(zip(picked["store"].to_list(), picked["alias"].to_list(), strict=True))
    stores_kept = set(store_to_alias.keys())

    product_frames: list[pl.DataFrame] = []
    velocity_frames: list[pl.DataFrame] = []
    for cat in _categories():
        meta_path = RAW_ROOT / f"{cat}_meta.parquet"
        review_path = RAW_ROOT / f"{cat}_reviews.parquet"
        if not meta_path.exists() or not review_path.exists():
            continue

        meta = pl.read_parquet(meta_path).filter(pl.col("store").is_in(stores_kept))
        if meta.is_empty():
            continue
        meta = meta.with_columns(
            [
                pl.col("store").map_elements(lambda s: store_to_alias.get(s, s), return_dtype=pl.Utf8).alias("brand_alias"),
                pl.col("parent_asin").map_elements(lambda a: _hash_asin(a, salt=str(seed)), return_dtype=pl.Utf8).alias("parent_asin_hash"),
            ]
        )
        prods = meta.select(
            [
                "brand_alias",
                "parent_asin_hash",
                pl.col("title").alias("title"),
                pl.col("categories").alias("category_path"),
                pl.col("price").fill_null(0.0),
                pl.col("average_rating").alias("avg_rating"),
                pl.col("rating_number"),
                pl.lit(cat).alias("category"),
            ]
        )
        product_frames.append(prods)

        # Weekly velocity per parent_asin: aggregate verified reviews by ISO week.
        reviews = pl.read_parquet(review_path).filter(pl.col("verified_purchase"))
        keep_asins = set(meta["parent_asin"].to_list())
        reviews = reviews.filter(pl.col("parent_asin").is_in(keep_asins))
        if reviews.is_empty():
            continue
        # Re-base into simulated season: keep last 52 weeks ending 2023-09-30.
        anchor = int(datetime(2023, 9, 30, tzinfo=UTC).timestamp())
        year = 60 * 60 * 24 * 7 * 52
        reviews = reviews.filter(pl.col("timestamp_s") >= anchor - year)
        reviews = reviews.with_columns(
            (
                (pl.lit(anchor) - pl.col("timestamp_s")) // (60 * 60 * 24 * 7)
            ).cast(pl.Int32).alias("weeks_before_anchor")
        )
        # weeks_before_anchor: 0 = most recent week, 51 = oldest. Map so sim week 52 = most recent.
        reviews = reviews.with_columns((52 - pl.col("weeks_before_anchor")).alias("sim_week"))

        asin_to_hash = dict(zip(meta["parent_asin"].to_list(), meta["parent_asin_hash"].to_list(), strict=True))
        asin_to_alias = dict(zip(meta["parent_asin"].to_list(), meta["brand_alias"].to_list(), strict=True))
        vel = (
            reviews.group_by(["parent_asin", "sim_week"])
            .agg(pl.len().alias("review_count"))
            .filter(pl.col("sim_week").is_between(1, 52))
            .with_columns(
                [
                    pl.col("parent_asin")
                    .map_elements(lambda a: asin_to_hash.get(a, ""), return_dtype=pl.Utf8)
                    .alias("parent_asin_hash"),
                    pl.col("parent_asin")
                    .map_elements(lambda a: asin_to_alias.get(a, ""), return_dtype=pl.Utf8)
                    .alias("brand_alias"),
                ]
            )
            .drop("parent_asin")
        )
        velocity_frames.append(vel)

    if not product_frames:
        raise SystemExit("No products written; nothing to anonymise.")

    products = pl.concat(product_frames)
    products_path = PREPARED_ROOT / "products.parquet"
    products.write_parquet(products_path, compression="zstd")
    log.info("wrote %s (%d products)", products_path, len(products))

    if velocity_frames:
        velocity = pl.concat(velocity_frames)
        velocity_path = PREPARED_ROOT / "review_velocity.parquet"
        velocity.write_parquet(velocity_path, compression="zstd")
        log.info("wrote %s (%d rows)", velocity_path, len(velocity))
    else:
        log.warning("no review velocity data produced")


if __name__ == "__main__":
    main()
