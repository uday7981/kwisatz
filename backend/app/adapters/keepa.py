from __future__ import annotations

from collections.abc import Iterator

import polars as pl

from ..config import get_settings


class KeepaAdapter:
    """
    Stub for a real Keepa-backed adapter. Documented in README.
    Instantiating without KEEPA_API_KEY set is fine; every read raises NotImplementedError
    so callers can detect and fall back.
    """

    def __init__(self) -> None:
        self.api_key = get_settings().keepa_api_key

    def _unimplemented(self) -> None:
        raise NotImplementedError(
            "KeepaAdapter is a stub. Wire the real client in backend/app/adapters/keepa.py "
            "once a Keepa API key is available."
        )

    def brands(self) -> pl.DataFrame:  # pragma: no cover
        self._unimplemented()

    def products(self, _brand_alias: str | None = None) -> pl.DataFrame:  # pragma: no cover
        self._unimplemented()

    def snapshots(self, _week: int, _brand_alias: str | None = None) -> pl.DataFrame:  # pragma: no cover
        self._unimplemented()

    def outcomes_arriving(self, _week: int) -> pl.DataFrame:  # pragma: no cover
        return pl.DataFrame()

    def all_snapshots(self) -> Iterator[pl.DataFrame]:  # pragma: no cover
        self._unimplemented()
