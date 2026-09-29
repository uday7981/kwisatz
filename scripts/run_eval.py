"""Run memory on/off/oracle evaluation. Memory-on is skipped if no API key."""

from __future__ import annotations

from backend.app.adapters.simulated import SimulatedAdapter
from backend.app.config import get_settings
from backend.app.eval.harness import print_summary, run_all
from backend.app.memory.formats import slug
from backend.app.memory.service import MemoryService
from scripts._log import get_logger
from sim.simulator import week_to_date

log = get_logger("run_eval")


def _memory_prioritise_factory():
    """Return a callable the eval harness can pass into run_week."""
    settings = get_settings()
    if not settings.hindsight_api_key:
        log.info("HINDSIGHT_API_KEY not set — running eval without memory-on.")
        return None

    svc = MemoryService.from_env()
    adapter = SimulatedAdapter()
    brand_meta = {row["alias"]: row for row in adapter.brands().iter_rows(named=True)}

    def _prioritise(*, week: int, candidates):
        if not candidates:
            return {}
        sim_date = week_to_date(week)
        payload = []
        # candidates arg is a single dict-like snapshot per call in loop.py — normalise
        if isinstance(candidates, dict):
            candidates = [candidates]
        for c in candidates:
            m = brand_meta.get(c["brand_alias"], {})
            payload.append({
                "brand_alias": c["brand_alias"],
                "category": m.get("category", "?"),
                "n_products": int(m.get("n_products", 0)),
                "total_ratings": int(m.get("total_ratings", 0)),
                "diagnosis": c["diagnosis"],
                "severity": c["severity"],
                "base_score": c["base_score"],
            })
        result = svc.prioritise(week=week, sim_date=sim_date, candidates=payload)
        # Reflect may return brand_id as either the alias or its slug — key both ways.
        by_key: dict[str, dict] = {}
        alias_by_slug = {slug(a): a for a in brand_meta}
        for a in result.adjustments:
            entry = a.model_dump()
            by_key[a.brand_id] = entry
            resolved = alias_by_slug.get(a.brand_id, a.brand_id)
            by_key[resolved] = entry
        return by_key

    return _prioritise


def main() -> None:
    prioritise = _memory_prioritise_factory()
    log.info("Running eval: off + oracle%s.", " + on" if prioritise else " (memory-on skipped)")
    results = run_all(memory_prioritise=prioritise)
    print_summary(results)
    log.info("wrote eval/results.json (+ results.png)")


if __name__ == "__main__":
    main()
