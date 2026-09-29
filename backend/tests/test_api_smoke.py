"""API smoke tests using FastAPI's TestClient. Runs without Hindsight / Groq
by depending on the memory-off / template fallback paths."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client() -> TestClient:
    from backend.app.main import app
    return TestClient(app)


def test_health(client: TestClient) -> None:
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True


def test_week(client: TestClient) -> None:
    r = client.get("/api/week")
    assert r.status_code == 200
    assert r.json()["current_week"] >= 1


@pytest.mark.integration
def test_shortlist_off(client: TestClient) -> None:
    # This test needs data/sim/snapshots.parquet — skipped in default test run.
    r = client.get("/api/shortlist?week=42&mode=off")
    assert r.status_code == 200
    body = r.json()
    assert body["week"] == 42
    assert isinstance(body["leads"], list)
