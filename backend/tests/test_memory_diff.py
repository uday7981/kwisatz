from __future__ import annotations

from backend.app.memory.schemas import Belief, BeliefSet
from backend.app.memory.service import MemoryService


def _make() -> MemoryService:
    # Instantiate without any live client; we only test the pure diff method.
    class _StubClient:
        def close(self) -> None:
            pass

    svc = MemoryService(bank_id="test", seed_bank_id="test-seed", client=_StubClient())  # type: ignore[arg-type]
    return svc


def _b(id: str, statement: str, confidence: float, evidence: int = 5, group: str = "which_angle") -> Belief:
    return Belief(id=id, group=group, statement=statement, confidence=confidence, evidence_count=evidence)


def test_diff_new_and_removed() -> None:
    svc = _make()
    prev = BeliefSet(beliefs=[_b("a", "A", 0.5), _b("b", "B", 0.5)])
    cur = BeliefSet(beliefs=[_b("a", "A", 0.5), _b("c", "C", 0.7)])
    d = svc.diff_beliefs(prev, cur)
    assert d["new"] == ["c"]
    assert d["removed"] == ["b"]


def test_diff_strengthened_weakened() -> None:
    svc = _make()
    prev = BeliefSet(beliefs=[_b("a", "A", 0.4), _b("b", "B", 0.9)])
    cur = BeliefSet(beliefs=[_b("a", "A", 0.7), _b("b", "B", 0.6)])
    d = svc.diff_beliefs(prev, cur)
    assert "a" in d["strengthened"]
    assert "b" in d["weakened"]


def test_diff_stable_within_epsilon() -> None:
    svc = _make()
    prev = BeliefSet(beliefs=[_b("a", "A", 0.60)])
    cur = BeliefSet(beliefs=[_b("a", "A", 0.61)])
    d = svc.diff_beliefs(prev, cur)
    assert d["strengthened"] == []
    assert d["weakened"] == []
    assert d["new"] == []
    assert d["removed"] == []
