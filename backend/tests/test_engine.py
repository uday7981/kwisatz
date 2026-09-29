from __future__ import annotations

from backend.app.engine.diagnosis import diagnose_brand, primary_diagnosis
from backend.app.engine.scoring import (
    _norm_velocity_growth,
    _size_fit,
    apply_memory_adjustment,
    compute_base_score,
)
from backend.app.engine.signals import BrandSignals


def _sig(**overrides) -> BrandSignals:
    defaults = dict(
        brand_alias="TestBrand",
        week=42,
        review_velocity=20.0,
        velocity_growth=1.10,
        seller_delta_30d=0,
        seller_count=2,
        buybox_share_30d=0.90,
        buybox_share_prev_30d=0.92,
        oos_episodes_60d=0,
        price_change_90d=0.0,
        ad_presence=0.5,
        rating_gap=0.0,
    )
    defaults.update(overrides)
    return BrandSignals(**defaults)


class TestDiagnosisD1Reseller:
    def test_fires_at_threshold(self) -> None:
        sig = _sig(seller_delta_30d=3, buybox_share_30d=0.60, buybox_share_prev_30d=0.95)
        hits = diagnose_brand(sig)
        codes = [h.code for h in hits]
        assert "D1" in codes

    def test_no_fire_without_buybox_drop(self) -> None:
        sig = _sig(seller_delta_30d=3, buybox_share_30d=0.80, buybox_share_prev_30d=0.95)
        assert "D1" not in [h.code for h in diagnose_brand(sig)]

    def test_no_fire_without_seller_spike(self) -> None:
        sig = _sig(seller_delta_30d=2, buybox_share_30d=0.60, buybox_share_prev_30d=0.95)
        assert "D1" not in [h.code for h in diagnose_brand(sig)]

    def test_severity_monotonic(self) -> None:
        milder = diagnose_brand(_sig(seller_delta_30d=3, buybox_share_30d=0.72, buybox_share_prev_30d=0.95))
        worse = diagnose_brand(_sig(seller_delta_30d=8, buybox_share_30d=0.50, buybox_share_prev_30d=0.95))
        milder_d1 = next(h for h in milder if h.code == "D1")
        worse_d1 = next(h for h in worse if h.code == "D1")
        assert worse_d1.severity >= milder_d1.severity


class TestDiagnosisOthers:
    def test_d2_stockout(self) -> None:
        assert "D2" in [
            h.code for h in diagnose_brand(_sig(oos_episodes_60d=3, velocity_growth=1.30))
        ]

    def test_d3_weak_converter(self) -> None:
        assert "D3" in [
            h.code for h in diagnose_brand(_sig(rating_gap=-0.5, review_velocity=25))
        ]

    def test_d4_price_erosion(self) -> None:
        assert "D4" in [
            h.code for h in diagnose_brand(_sig(price_change_90d=-0.18, seller_count=4))
        ]

    def test_d5_under_advertised(self) -> None:
        assert "D5" in [
            h.code for h in diagnose_brand(_sig(velocity_growth=1.6, ad_presence=0.20))
        ]

    def test_d6_healthy_only_when_nothing_else(self) -> None:
        sig = _sig(velocity_growth=1.5, seller_delta_30d=0, oos_episodes_60d=0, rating_gap=0.0, price_change_90d=0.0, ad_presence=0.6)
        codes = [h.code for h in diagnose_brand(sig)]
        assert codes == ["D6"]

    def test_primary_picks_highest_severity(self) -> None:
        hits = [
            *diagnose_brand(_sig(seller_delta_30d=5, buybox_share_30d=0.55, buybox_share_prev_30d=0.95)),
            *diagnose_brand(_sig(oos_episodes_60d=2, velocity_growth=1.15)),
        ]
        best = primary_diagnosis(hits)
        assert best is not None
        assert best.severity == max(h.severity for h in hits)


class TestScoring:
    def test_size_fit_sweet_spot(self) -> None:
        assert _size_fit(150) == 1.0
        assert _size_fit(50) == 1.0
        assert _size_fit(300) == 1.0
        assert 0 < _size_fit(25) < 1
        assert 0 < _size_fit(1000) < 1

    def test_norm_velocity_growth_bounds(self) -> None:
        assert _norm_velocity_growth(0.5) == 0.0
        assert _norm_velocity_growth(2.5) == 1.0
        assert 0 < _norm_velocity_growth(1.2) < 1

    def test_base_score_bounded(self) -> None:
        sig = _sig(velocity_growth=2.0, seller_delta_30d=5)
        dx = diagnose_brand(_sig(seller_delta_30d=6, buybox_share_30d=0.50, buybox_share_prev_30d=0.95))[0]
        b = compute_base_score(sig, dx, total_ratings=100)
        assert 0.0 <= b.base_score <= 1.0

    def test_apply_memory_clamps(self) -> None:
        final, was_skipped = apply_memory_adjustment(0.5, 2.0)  # 2.0 > 0.6, gets clamped
        assert 0 <= final <= 1
        assert not was_skipped

    def test_skip_returns_zero(self) -> None:
        final, was_skipped = apply_memory_adjustment(0.9, 0.0, skip=True)
        assert final == 0.0
        assert was_skipped

    def test_revisit_floor(self) -> None:
        final, _ = apply_memory_adjustment(0.4, 0.0, revisit=True, problem_worsened=True)
        assert final >= 0.7
