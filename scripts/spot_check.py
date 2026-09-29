"""Quick spot-check to eyeball 10 prepared brands. Run: `python -m scripts.spot_check`."""

from __future__ import annotations

import polars as pl

from backend.app.config import PREPARED_ROOT


def main() -> None:
    brands_path = PREPARED_ROOT / "brands.parquet"
    if not brands_path.exists():
        raise SystemExit("Run `make data` first.")
    brands = pl.read_parquet(brands_path)
    print(f"{len(brands)} brands in prepared/brands.parquet")
    print(brands.group_by("category").agg(pl.len().alias("n")).sort("category"))
    print()
    sample = brands.sample(min(10, len(brands)), seed=42)
    for row in sample.iter_rows(named=True):
        print(
            f"  {row['alias']:32}  [{row['category']:22}] "
            f"products={row['n_products']:>3}  ratings={row['total_ratings']:>5}  "
            f"price ${row['price_min']:>6.2f}-${row['price_max']:>6.2f}  "
            f"avg★ {row['avg_rating']:.2f}  (hidden: {row['archetype_hidden']})"
        )


if __name__ == "__main__":
    main()
