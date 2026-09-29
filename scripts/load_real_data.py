"""
Stream Amazon Reviews 2023 metadata + reviews for our three categories to parquet.

Confirmed via ranged HTTP GET (2026-09-29):
  Meta URL:    https://huggingface.co/datasets/McAuley-Lab/Amazon-Reviews-2023/resolve/main/raw/meta_categories/meta_{Category}.jsonl
  Review URL:  https://huggingface.co/datasets/McAuley-Lab/Amazon-Reviews-2023/resolve/main/raw/review_categories/{Category}.jsonl

  Meta fields kept: parent_asin, title, store, main_category, categories, price,
                    average_rating, rating_number.
  Review fields kept: parent_asin, rating, timestamp (ms -> s), verified_purchase.

The datasets library streaming API is used so we never fully download 12 GB of
meta or reviews. We keep only rows whose `store` is a real brand (non-empty,
non-generic), and (for reviews) only reviews on parent_asins we saw in meta.

Env override:
  UNDERDOG_SLIM=1     Only load Pet_Supplies (fast CI mode)
  UNDERDOG_MAX_META=N Cap per-category meta rows to N (defaults 200k)
  UNDERDOG_MAX_REVIEWS=N Cap per-category reviews (defaults 5M)
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import polars as pl

from backend.app.config import CATEGORIES, RAW_ROOT
from scripts._log import get_logger

log = get_logger("load_real_data")

META_FIELDS = (
    "parent_asin",
    "title",
    "store",
    "main_category",
    "categories",
    "price",
    "average_rating",
    "rating_number",
)
REVIEW_FIELDS = (
    "parent_asin",
    "rating",
    "timestamp",
    "verified_purchase",
)

GENERIC_STORES = frozenset(
    {"", "Amazon", "AMAZON", "Generic", "Unknown", "N/A", "unknown", "generic"}
)

META_URL = (
    "https://huggingface.co/datasets/McAuley-Lab/Amazon-Reviews-2023/"
    "resolve/main/raw/meta_categories/meta_{cat}.jsonl"
)
REVIEW_URL = (
    "https://huggingface.co/datasets/McAuley-Lab/Amazon-Reviews-2023/"
    "resolve/main/raw/review_categories/{cat}.jsonl"
)


def _categories() -> tuple[str, ...]:
    if os.getenv("UNDERDOG_SLIM"):
        return ("Pet_Supplies",)
    return CATEGORIES


def _stream_jsonl(url: str) -> Iterator[dict[str, Any]]:
    """Iterate JSON records from a remote .jsonl file without buffering the whole file."""
    import json

    import httpx

    with httpx.stream(
        "GET",
        url,
        follow_redirects=True,
        timeout=httpx.Timeout(30.0, read=None),
    ) as resp:
        resp.raise_for_status()
        buf = ""
        for chunk in resp.iter_text():
            buf += chunk
            while True:
                idx = buf.find("\n")
                if idx == -1:
                    break
                line = buf[:idx]
                buf = buf[idx + 1 :]
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue
        if buf.strip():
            try:
                yield json.loads(buf)
            except json.JSONDecodeError:
                pass


def _normalise_price(raw: Any) -> float | None:
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return float(raw)
    if isinstance(raw, str):
        s = raw.strip().lstrip("$")
        s = s.split("-")[0].strip()  # some prices are "9.99 - 12.99"
        s = s.replace(",", "")
        try:
            return float(s)
        except ValueError:
            return None
    return None


def _flatten_meta_row(row: dict[str, Any]) -> dict[str, Any] | None:
    store = (row.get("store") or "").strip()
    if store in GENERIC_STORES:
        return None
    parent = row.get("parent_asin")
    if not parent:
        return None
    price = _normalise_price(row.get("price"))
    cats = row.get("categories") or []
    if isinstance(cats, list):
        cats_str = " > ".join(str(c) for c in cats if c)
    else:
        cats_str = str(cats)
    return {
        "parent_asin": str(parent),
        "title": (row.get("title") or "")[:400],
        "store": store,
        "main_category": row.get("main_category") or "",
        "categories": cats_str,
        "price": price,
        "average_rating": float(row.get("average_rating") or 0.0),
        "rating_number": int(row.get("rating_number") or 0),
    }


def _flatten_review_row(row: dict[str, Any], allowed: set[str]) -> dict[str, Any] | None:
    parent = row.get("parent_asin")
    if not parent or parent not in allowed:
        return None
    ts = row.get("timestamp")
    if ts is None:
        return None
    return {
        "parent_asin": str(parent),
        "rating": float(row.get("rating") or 0.0),
        "timestamp_s": int(ts) // 1000,  # Confirmed unit: milliseconds
        "verified_purchase": bool(row.get("verified_purchase")),
    }


def _write_parquet(rows: Iterator[dict[str, Any]], target: Path, batch: int = 50_000) -> int:
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(".tmp.parquet")
    if tmp.exists():
        tmp.unlink()

    written = 0
    buffer: list[dict[str, Any]] = []
    part_paths: list[Path] = []

    def _flush() -> None:
        nonlocal written
        if not buffer:
            return
        df = pl.DataFrame(buffer)
        part = target.parent / f"{target.stem}.part{len(part_paths):04d}.parquet"
        df.write_parquet(part, compression="zstd")
        part_paths.append(part)
        written += len(buffer)
        buffer.clear()

    for row in rows:
        buffer.append(row)
        if len(buffer) >= batch:
            _flush()
    _flush()

    if not part_paths:
        # Write an empty schema-friendly parquet so downstream reads never fail.
        pl.DataFrame([]).write_parquet(target)
        return 0

    lazy = pl.concat([pl.scan_parquet(p) for p in part_paths], how="vertical_relaxed")
    lazy.sink_parquet(target, compression="zstd")
    for p in part_paths:
        p.unlink()
    log.info("wrote %s (%d rows)", target.relative_to(target.parents[2]), written)
    return written


def load_category(cat: str, max_meta: int, max_reviews: int) -> None:
    log.info("=== %s ===", cat)

    meta_target = RAW_ROOT / f"{cat}_meta.parquet"
    reviews_target = RAW_ROOT / f"{cat}_reviews.parquet"

    if meta_target.exists() and reviews_target.exists() and not os.getenv("UNDERDOG_FORCE"):
        log.info("skip %s (already present; set UNDERDOG_FORCE=1 to redo)", cat)
        return

    # 1) meta
    meta_url = META_URL.format(cat=cat)
    log.info("streaming meta from %s (cap %d)", meta_url, max_meta)

    def meta_rows() -> Iterator[dict[str, Any]]:
        count = 0
        kept = 0
        for raw in _stream_jsonl(meta_url):
            count += 1
            flat = _flatten_meta_row(raw)
            if flat is not None:
                kept += 1
                yield flat
                if kept >= max_meta:
                    break
            if count % 100_000 == 0:
                log.info("  meta scanned %d, kept %d", count, kept)

    _write_parquet(meta_rows(), meta_target)

    # 2) filter reviews to seen parent_asins
    allowed = set(
        pl.read_parquet(meta_target, columns=["parent_asin"])["parent_asin"].to_list()
    )
    log.info("meta kept %d parent_asins for review filter", len(allowed))
    if not allowed:
        return

    review_url = REVIEW_URL.format(cat=cat)
    log.info("streaming reviews from %s (cap %d)", review_url, max_reviews)

    def review_rows() -> Iterator[dict[str, Any]]:
        count = 0
        kept = 0
        for raw in _stream_jsonl(review_url):
            count += 1
            flat = _flatten_review_row(raw, allowed)
            if flat is not None:
                kept += 1
                yield flat
                if kept >= max_reviews:
                    break
            if count % 500_000 == 0:
                log.info("  reviews scanned %d, kept %d", count, kept)

    _write_parquet(review_rows(), reviews_target, batch=100_000)


def main() -> None:
    RAW_ROOT.mkdir(parents=True, exist_ok=True)
    max_meta = int(os.getenv("UNDERDOG_MAX_META", "200000"))
    max_reviews = int(os.getenv("UNDERDOG_MAX_REVIEWS", "5000000"))
    for cat in _categories():
        load_category(cat, max_meta=max_meta, max_reviews=max_reviews)
    log.info("done. raw parquet under %s", RAW_ROOT)


if __name__ == "__main__":
    main()
