from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import polars as pl

from ..config import PREPARED_ROOT, SIM_ROOT


class SimulatedAdapter:
    """Reads pre-generated parquet artefacts produced by `sim/`."""

    def __init__(self, sim_root: Path = SIM_ROOT, prepared_root: Path = PREPARED_ROOT) -> None:
        self.sim_root = sim_root
        self.prepared_root = prepared_root
        self._snapshots: pl.DataFrame | None = None
        self._outcomes: pl.DataFrame | None = None
        self._products: pl.DataFrame | None = None
        self._brands: pl.DataFrame | None = None

    # ---------- Loading ----------

    def _snapshots_df(self) -> pl.DataFrame:
        if self._snapshots is None:
            path = self.sim_root / "snapshots.parquet"
            if not path.exists():
                raise FileNotFoundError(f"{path} missing; run `make sim` first.")
            self._snapshots = pl.read_parquet(path)
        return self._snapshots

    def _outcomes_df(self) -> pl.DataFrame:
        if self._outcomes is None:
            path = self.sim_root / "outcomes.parquet"
            if not path.exists():
                self._outcomes = pl.DataFrame(schema={
                    "brand_alias": pl.Utf8, "week_sent": pl.Int32,
                    "week_arrived": pl.Int32, "type": pl.Utf8,
                    "reason_text": pl.Utf8, "revisit_after_week": pl.Int32,
                    "angle": pl.Utf8,
                })
            else:
                self._outcomes = pl.read_parquet(path)
        return self._outcomes

    def _products_df(self) -> pl.DataFrame:
        if self._products is None:
            self._products = pl.read_parquet(self.prepared_root / "products.parquet")
        return self._products

    def _brands_df(self) -> pl.DataFrame:
        if self._brands is None:
            self._brands = pl.read_parquet(self.prepared_root / "brands.parquet")
        return self._brands

    # ---------- Protocol implementation ----------

    def brands(self) -> pl.DataFrame:
        return self._brands_df()

    def products(self, brand_alias: str | None = None) -> pl.DataFrame:
        df = self._products_df()
        if brand_alias:
            df = df.filter(pl.col("brand_alias") == brand_alias)
        return df

    def snapshots(self, week: int, brand_alias: str | None = None) -> pl.DataFrame:
        df = self._snapshots_df().filter(pl.col("week") == week)
        if brand_alias:
            df = df.filter(pl.col("brand_alias") == brand_alias)
        return df

    def outcomes_arriving(self, week: int) -> pl.DataFrame:
        return self._outcomes_df().filter(pl.col("week_arrived") == week)

    def all_snapshots(self) -> Iterator[pl.DataFrame]:
        yield self._snapshots_df()
