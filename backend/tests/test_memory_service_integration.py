"""Integration test — hits real Hindsight (or local Docker via HINDSIGHT_URL).

Marked `integration` so `make test` skips it by default.
"""

from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime

import pytest

from backend.app.config import get_settings
from backend.app.memory.formats import build_scopes, build_tags, doc_id
from backend.app.memory.service import MemoryService


@pytest.mark.integration
def test_retain_recall_roundtrip() -> None:
    s = get_settings()
    if not s.hindsight_api_key:
        pytest.skip("HINDSIGHT_API_KEY not set")

    with MemoryService.from_env() as svc:
        svc.bank_id = f"underdog-it-{uuid.uuid4().hex[:8]}"
        svc.ensure_bank(
            mission="integration test bank",
            retain_mission="retain outreach outcomes verbatim",
            observations_mission="none",
            reflect_mission="answer briefly",
        )
        try:
            item = {
                "content": "Copperleaf Kitchen replied on 2026-08-14 and booked a call. Angle: brand protection.",
                "context": "outreach outcome",
                "timestamp": datetime(2026, 8, 14, tzinfo=UTC),
                "document_id": doc_id("outcome", "Copperleaf Kitchen", week=6, angle="brand_protection"),
                "tags": build_tags(brand_alias="Copperleaf Kitchen", dx_code="D1",
                                   angle="brand_protection", outcome_type="meeting", kind="outcome"),
                "observation_scopes": build_scopes(brand_alias="Copperleaf Kitchen", dx_code="D1", angle="brand_protection"),
            }
            svc.client.retain_batch(bank_id=svc.bank_id, items=[item], retain_async=False)
            time.sleep(3)
            resp = svc.client.recall(
                bank_id=svc.bank_id, query="What happened with Copperleaf Kitchen?",
                budget="low", tags=["brand:copperleaf-kitchen"], tags_match="any",
                query_timestamp="2026-08-14T00:00:00Z",
            )
            assert len(resp.results) >= 1
            found = any("Copperleaf" in getattr(m, "text", "") for m in resp.results)
            assert found
        finally:
            try:
                svc.client.delete_bank(svc.bank_id)
            except Exception:
                pass
