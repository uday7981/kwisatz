from __future__ import annotations

from collections.abc import Iterator
from typing import Protocol

import polars as pl


class MarketplaceAdapter(Protocol):
    """Uniform read-only view of an Amazon marketplace over simulated weeks."""

    def brands(self) -> pl.DataFrame:  # alias, category, aggregates
        ...

    def products(self, brand_alias: str | None = None) -> pl.DataFrame:
        ...

    def snapshots(self, week: int, brand_alias: str | None = None) -> pl.DataFrame:
        ...

    def outcomes_arriving(self, week: int) -> pl.DataFrame:
        """Outcomes whose reply lands in this week (empty for real live adapters)."""
        ...

    def all_snapshots(self) -> Iterator[pl.DataFrame]:
        """Yield the full 52-week history per product (used by signal computation)."""
        ...
