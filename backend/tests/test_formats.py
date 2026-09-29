from __future__ import annotations

from datetime import UTC, datetime

from backend.app.memory.formats import (
    build_scopes,
    build_tags,
    category_slug,
    doc_id,
    dx_slug,
    outcome_content,
    pitch_content,
    slug,
    snapshot_content,
)


def test_slug_and_category_and_dx() -> None:
    assert slug("Copperleaf Kitchen") == "copperleaf-kitchen"
    assert slug("Pawsmith & Co.") == "pawsmith-co"
    assert category_slug("Home_and_Kitchen") == "home-and-kitchen"
    assert dx_slug("D1") == "reseller-invasion"
    assert dx_slug("D9") == "d9"


def test_build_tags_full() -> None:
    tags = build_tags(
        brand_alias="Copperleaf Kitchen",
        category="Home_and_Kitchen",
        dx_code="D1",
        angle="brand_protection",
        kind="snapshot",
    )
    assert "kind:snapshot" in tags
    assert "brand:copperleaf-kitchen" in tags
    assert "cat:home-and-kitchen" in tags
    assert "dx:reseller-invasion" in tags
    assert "angle:brand-protection" in tags


def test_build_scopes_never_empty() -> None:
    # Even with nothing but the kind, scopes are non-empty (never triggers "combined" fallback).
    assert build_scopes() == [["kind:decision"]]
    scopes = build_scopes(brand_alias="Pawsmith", dx_code="D1", angle="brand_protection")
    assert scopes  # non-empty
    for s in scopes:
        assert s  # each inner list non-empty
        assert isinstance(s, list)


def test_doc_id_stable() -> None:
    a = doc_id("snapshot", "Copperleaf Kitchen", week=6)
    b = doc_id("snapshot", "Copperleaf Kitchen", week=6)
    assert a == b == "snapshot:copperleaf-kitchen:w06"


def test_snapshot_content_reseller() -> None:
    txt = snapshot_content(
        week=6,
        sim_date=datetime(2026, 8, 10, tzinfo=UTC),
        brand_alias="Copperleaf Kitchen",
        category="Home & Kitchen",
        n_products=14,
        dx_code="D1",
        severity=0.78,
        evidence={
            "seller_delta_30d": 7,
            "buybox_share_30d": 0.58,
            "buybox_share_prev_30d": 0.95,
            "seller_count": 9,
        },
    )
    assert "Copperleaf Kitchen" in txt
    assert "reseller invasion" in txt
    assert "0.78" in txt
    assert "—" not in txt  # no em-dash


def test_pitch_and_outcome_content() -> None:
    pitch = pitch_content(
        week=6,
        sim_date=datetime(2026, 8, 11, tzinfo=UTC),
        brand_alias="Copperleaf Kitchen",
        angle="brand_protection",
        base_score=0.71,
        rank=2,
        top_of=12,
        reason="Sellers on top listing rose by 7.",
    )
    assert "brand protection" in pitch
    assert "0.71" in pitch
    outcome = outcome_content(
        week=8,
        sim_date=datetime(2026, 8, 14, tzinfo=UTC),
        brand_alias="Copperleaf Kitchen",
        outcome_type="meeting",
        reason_text="Timing is good actually.",
    )
    assert "meeting" in outcome
    assert "Timing" in outcome
