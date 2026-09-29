from __future__ import annotations

from scripts.select_brands import (
    GROWTH_THRESHOLD,
    MAX_PRODUCTS,
    MAX_RATINGS,
    MIN_PRODUCTS,
    MIN_RATINGS,
    _brand_size_ok,
    _rising,
)


def test_size_ok_boundaries() -> None:
    assert _brand_size_ok({"n_products": MIN_PRODUCTS, "total_ratings": MIN_RATINGS})
    assert _brand_size_ok({"n_products": MAX_PRODUCTS, "total_ratings": MAX_RATINGS})
    assert not _brand_size_ok({"n_products": MIN_PRODUCTS - 1, "total_ratings": MIN_RATINGS})
    assert not _brand_size_ok({"n_products": MAX_PRODUCTS + 1, "total_ratings": MAX_RATINGS})
    assert not _brand_size_ok({"n_products": MIN_PRODUCTS, "total_ratings": MIN_RATINGS - 1})
    assert not _brand_size_ok({"n_products": MIN_PRODUCTS, "total_ratings": MAX_RATINGS + 1})


def test_rising_threshold() -> None:
    # At threshold -> qualifies.
    assert _rising(velocity_last=120.0, velocity_prev=100.0) is True
    # Just under threshold with meaningful prev base -> doesn't qualify.
    assert _rising(velocity_last=119.0, velocity_prev=100.0) is False
    # Low base gets absolute-lift rule.
    assert _rising(velocity_last=12.0, velocity_prev=2.0) is True
    assert _rising(velocity_last=8.0, velocity_prev=2.0) is False


def test_growth_threshold_constant() -> None:
    assert 0 < GROWTH_THRESHOLD < 1
