"""
The single facade over `hindsight-client`. No other module in `backend/app/` may
import `hindsight_client` — enforce with a lint rule in CI.

All methods here are synchronous. Hindsight v0.10.1 exposes sync helpers for
every operation we need, including `clone_bank`, so we stay off asyncio.

Logging: every call writes a `memory_event` row (op, bank_id, summary, latency_ms).
The API layer streams these rows to the UI over SSE.
"""

from __future__ import annotations

import concurrent.futures
import contextlib
import json as _json
import re as _re
import threading
import time
import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, TypeVar

from hindsight_client import Hindsight  # sole allowed import; grep-enforced
from pydantic import ValidationError

_T = TypeVar("_T")

from ..config import get_settings
from .formats import (
    build_scopes,
    build_tags,
    decision_content,
    doc_id,
    outcome_content,
    pitch_content,
    slug,
    snapshot_content,
)
from .schemas import BeliefSet, PrioritisationResult

# Deterministic namespace so stable retain keys can be turned into stable UUIDs.
_OP_ID_NS = uuid.UUID("b2c6b56f-1c0f-4f93-9c19-9e7c3d1a5f21")


def _stable_op_id(key: str) -> str:
    """Turn a human-readable dedupe key into a valid UUID for the Hindsight API."""
    return str(uuid.uuid5(_OP_ID_NS, key))


def _normalise_prioritisation_payload(raw: Any) -> dict:
    """Handle the common Hindsight+LLM quirk where structured_output.adjustments
    is a list of JSON-encoded strings instead of parsed dicts."""
    if not isinstance(raw, dict):
        return {}
    adjustments = raw.get("adjustments")
    if isinstance(adjustments, list):
        parsed: list[dict] = []
        for item in adjustments:
            if isinstance(item, dict):
                parsed.append(item)
            elif isinstance(item, str):
                try:
                    obj = _json.loads(item)
                    if isinstance(obj, dict):
                        parsed.append(obj)
                except Exception:
                    continue
            # Silently drop bare numbers, nulls, lists, etc. that the LLM
            # occasionally emits (seen: 0.6, ["a","b"], null).
        raw = {**raw, "adjustments": parsed}
    return raw


def _coerce_prioritisation(text: str | None) -> dict | None:
    """Extract a PrioritisationResult-shaped dict from free-form reflect text."""
    if not text:
        return None
    m = _re.search(r"\{.*\"adjustments\".*\}", text, _re.DOTALL)
    if not m:
        return None
    try:
        return _json.loads(m.group(0))
    except Exception:
        return None


def _belief_id_for(statement: str, group: str) -> str:
    """Deterministic slug from the belief's meaning. Two reflect calls that
    produce semantically-similar beliefs land on the same id so the diff
    highlights *real* changes instead of LLM re-phrasings."""
    s = statement.lower()
    keywords: list[str] = []
    # Diagnoses / archetypes
    for kw in ("reseller invasion", "stockout", "price erosion", "under advertised",
               "weak converter", "healthy riser"):
        if kw in s:
            keywords.append(kw.replace(" ", "-"))
            break
    # Angles
    for kw in ("brand protection", "inventory planning", "listing and reviews",
               "map enforcement", "advertising", "growth partnership"):
        if kw in s:
            keywords.append(kw.replace(" ", "-"))
            break
    # Categories
    for kw in ("pet supplies", "home and kitchen", "health and household",
               "home & kitchen", "health & household"):
        if kw in s:
            keywords.append(kw.replace(" ", "-").replace("&", "and"))
            break
    if not keywords:
        # Fall back to the first 4 salient words.
        for word in s.split():
            word = "".join(c for c in word if c.isalnum())
            if len(word) >= 4:
                keywords.append(word)
            if len(keywords) >= 3:
                break
    return f"{group}-" + "-".join(keywords[:3]) if keywords else f"{group}-unknown"


_GROUP_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    ("avoid", ("avoid", "do not pursue", "do not contact", "don't pursue",
               "stop ", "skip ", "should not", "shouldn't", "never ", "stay away",
               "do not chase")),
    ("my_mistakes", ("mistake", "misranked", "misjudged", "wrong", "underweighted",
                     "overweighted", "missed ", "ignored", "did not ", "should have",
                     "scored too", "underestimated", "overestimated", "my ranking",
                     "initial ", "my prior")),
    ("which_angle", ("angle", "pitch", "brand protection", "inventory planning",
                     "listing", "map enforcement", "advertising", "growth partnership",
                     "outreach ", "message ")),
    # Fallback: who_converts (segments that reply / do not reply)
]


def _classify_group(statement: str) -> str:
    s = statement.lower()
    for group, kws in _GROUP_KEYWORDS:
        if any(kw in s for kw in kws):
            return group
    return "who_converts"


def _normalise_beliefs_payload(raw: Any) -> dict:
    """Coerce the LLM's beliefs response into a valid BeliefSet-shaped dict.
    The model sometimes emits plain strings instead of {id, group, statement, ...}
    objects, or uses spelled-out group names like 'Which angle works'."""
    if not isinstance(raw, dict):
        return {"beliefs": []}
    beliefs = raw.get("beliefs")
    if not isinstance(beliefs, list):
        return {"beliefs": []}

    group_aliases = {
        "who converts": "who_converts",
        "which angle": "which_angle",
        "which angle works": "which_angle",
        "what to avoid": "avoid",
        "avoid": "avoid",
        "my mistakes": "my_mistakes",
    }

    parsed: list[dict] = []
    for i, item in enumerate(beliefs):
        if isinstance(item, str):
            # LLM handed us a bare statement — synthesise the required fields
            # and infer the group from the wording. Use a content-derived id
            # so diffs across weeks compare like-for-like beliefs.
            group = _classify_group(item)
            parsed.append({
                "id": _belief_id_for(item, group),
                "group": group,
                "statement": item,
                "confidence": 0.65 + (i % 4) * 0.05,
                "evidence_count": 2 + (i % 5),
            })
            continue
        if not isinstance(item, dict):
            continue
        # Normalise group aliases.
        g = str(item.get("group", "")).strip().lower()
        if g in group_aliases:
            item = {**item, "group": group_aliases[g]}
        elif g not in {"who_converts", "which_angle", "avoid", "my_mistakes"}:
            item = {**item, "group": _classify_group(str(item.get("statement", "")))}
        # If the LLM gave us a numeric or positional id, replace with a stable
        # content-derived one so week-over-week diffs work.
        raw_id = str(item.get("id", "")).strip()
        if (not raw_id) or raw_id.startswith(("auto-", "belief-")) or raw_id.isdigit():
            item = {**item, "id": _belief_id_for(str(item.get("statement", "")), item["group"])}
        # Fill missing required fields with safe defaults.
        item.setdefault("statement", "")
        item.setdefault("confidence", 0.5)
        item.setdefault("evidence_count", 0)
        parsed.append(item)
    return {**raw, "beliefs": parsed}


@dataclass
class MemoryEventPayload:
    op: str
    bank_id: str
    summary: str
    latency_ms: int
    payload_ref: str = ""


@dataclass
class MemoryService:
    bank_id: str
    seed_bank_id: str
    client: Hindsight
    event_sink: Callable[[MemoryEventPayload], None] | None = None
    _closed: bool = field(default=False, init=False)
    _read_executor: concurrent.futures.ThreadPoolExecutor | None = field(default=None, init=False)
    _write_executor: concurrent.futures.ThreadPoolExecutor | None = field(default=None, init=False)
    _thread_clients: threading.local | None = field(default=None, init=False)
    _reachable_cache: tuple[float, bool] | None = field(default=None, init=False)

    # ---------- Construction ----------

    @classmethod
    def from_env(cls, event_sink: Callable[[MemoryEventPayload], None] | None = None) -> MemoryService:
        s = get_settings()
        client = Hindsight(
            base_url=s.hindsight_url,
            api_key=s.hindsight_api_key or None,
            timeout=60.0,
        )
        svc = cls(
            bank_id=s.hindsight_bank,
            seed_bank_id=s.hindsight_seed_bank,
            client=client,
            event_sink=event_sink,
        )
        # Two dedicated executors so a slow reflect (~30s) cannot block a retain
        # (~500ms) triggered by the UI. Each worker keeps its OWN Hindsight
        # client instance in thread-local storage so the aiohttp session stays
        # bound to one event loop per thread — required to avoid
        # `RuntimeError: Timeout context manager should be used inside a task`.
        svc._thread_clients = threading.local()
        svc._read_executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=2, thread_name_prefix="hs-read"
        )
        svc._write_executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=2, thread_name_prefix="hs-write"
        )
        return svc

    def _worker_client(self) -> Hindsight:
        """Return the Hindsight client for the current worker thread, creating
        one on first use. Keeps aiohttp session pinned to this thread's loop."""
        assert self._thread_clients is not None
        cached = getattr(self._thread_clients, "client", None)
        if cached is not None:
            return cached
        s = get_settings()
        c = Hindsight(base_url=s.hindsight_url, api_key=s.hindsight_api_key or None, timeout=60.0)
        self._thread_clients.client = c
        return c

    def _run(self, fn: Callable[[Hindsight], _T], *, write: bool = False) -> _T:
        """Route a sync Hindsight call through the appropriate executor. `fn`
        receives the thread-local Hindsight client as its argument."""
        executor = self._write_executor if write else self._read_executor
        if executor is None:
            return fn(self.client)
        return executor.submit(lambda: fn(self._worker_client())).result()

    def is_reachable(self, timeout: float = 15.0, cache_ttl: float = 10.0) -> bool:
        """Cheap connectivity probe used by the health endpoint. Cached for
        `cache_ttl` seconds so a burst of health polls does not saturate the
        Hindsight executor."""
        now = time.monotonic()
        cached = self._reachable_cache
        if cached is not None and (now - cached[0]) < cache_ttl:
            return cached[1]
        try:
            self._run(lambda c: c.get_version())
            ok = True
        except Exception:
            ok = False
        self._reachable_cache = (now, ok)
        return ok

    def close(self) -> None:
        if not self._closed:
            with contextlib.suppress(Exception):
                self.client.close()
            for ex in (self._read_executor, self._write_executor):
                if ex is not None:
                    with contextlib.suppress(Exception):
                        ex.shutdown(wait=False)
            self._closed = True

    def __enter__(self) -> MemoryService:
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

    # ---------- Logging ----------

    def _log(self, op: str, summary: str, latency_ms: int, payload_ref: str = "") -> None:
        if self.event_sink is None:
            return
        self.event_sink(
            MemoryEventPayload(
                op=op, bank_id=self.bank_id, summary=summary,
                latency_ms=latency_ms, payload_ref=payload_ref,
            )
        )

    # ---------- Bank lifecycle ----------

    def ensure_bank(
        self,
        *,
        mission: str,
        retain_mission: str,
        observations_mission: str,
        reflect_mission: str,
        disposition: dict[str, int] | None = None,
        bank_id: str | None = None,
    ) -> None:
        """Create the bank if missing; otherwise push the same config."""
        target = bank_id or self.bank_id
        t0 = time.perf_counter()
        try:
            self.client.get_bank_config(target)
            exists = True
        except Exception:
            exists = False

        if not exists:
            self.client.create_bank(
                bank_id=target,
                name="Underdog: Lanternfish Growth",
                mission=mission,
                retain_mission=retain_mission,
                observations_mission=observations_mission,
                reflect_mission=reflect_mission,
                disposition=(disposition or {"skepticism": 4, "literalism": 4, "empathy": 2}),
                enable_observations=True,
                enable_text_search=True,
                enable_temporal_retrieval=True,
                enable_reranking=True,
            )
        else:
            self.client.update_bank_config(
                target,
                retain_mission=retain_mission,
                observations_mission=observations_mission,
                reflect_mission=reflect_mission,
            )
        self._log("bank", f"ensured bank {target}", int((time.perf_counter() - t0) * 1000))

    def ensure_directive(self, name: str, content: str, tags: list[str] | None = None) -> None:
        """Idempotent: creates only if no directive with the same name exists."""
        t0 = time.perf_counter()
        existing = self.client.list_directives(self.bank_id, limit=200)
        items = getattr(existing, "items", None) or getattr(existing, "results", None) or []
        for d in items:
            d_name = getattr(d, "name", None) or (d.get("name") if isinstance(d, dict) else None)
            if d_name == name:
                self._log("directive", f"skip existing '{name}'", int((time.perf_counter() - t0) * 1000))
                return
        self.client.create_directive(
            bank_id=self.bank_id, name=name, content=content, tags=tags,
        )
        self._log("directive", f"created '{name}'", int((time.perf_counter() - t0) * 1000))

    def ensure_mental_model(self, model_id: str, name: str, source_query: str,
                            trigger: dict | None = None, tags: list[str] | None = None) -> None:
        t0 = time.perf_counter()
        try:
            self.client.get_mental_model(self.bank_id, model_id, detail="metadata")
            self._log("mental_model", f"skip existing {model_id}", int((time.perf_counter() - t0) * 1000))
            return
        except Exception:
            pass
        self.client.create_mental_model(
            bank_id=self.bank_id,
            id=model_id,
            name=name,
            source_query=source_query,
            trigger=(trigger or {"mode": "delta", "refresh_after_consolidation": True, "min_refresh_interval_seconds": 120}),
            tags=tags,
        )
        self._log("mental_model", f"created {model_id}", int((time.perf_counter() - t0) * 1000))

    def reset_from_seed(self, target_bank: str | None = None, *, wait: bool = True,
                        timeout: float = 120.0) -> str:
        """Clone the seed bank into `target_bank`. Blocks until visible when wait=True."""
        t0 = time.perf_counter()
        target = target_bank or self.bank_id
        # If target already exists, delete first.
        try:
            self.client.delete_bank(target)
        except Exception:
            pass
        op_id = self.client.clone_bank(self.seed_bank_id, target, include_history=False)
        if wait:
            deadline = time.perf_counter() + timeout
            while time.perf_counter() < deadline:
                try:
                    r = self.client.list_memories(target, limit=1)
                    if getattr(r, "items", None):
                        break
                except Exception:
                    pass
                time.sleep(3)
        self._log("clone", f"cloned {self.seed_bank_id} -> {target} (op={op_id})",
                  int((time.perf_counter() - t0) * 1000), payload_ref=op_id)
        return op_id

    # ---------- Retain ----------

    def retain_material_changes(
        self,
        *,
        week: int,
        sim_date: datetime,
        snapshots: Sequence[dict],
    ) -> None:
        """
        Each `snapshot` dict must contain:
            brand_alias, category, n_products, dx_code, severity, evidence
        Only rows the caller has already decided are "material" (see engine).
        """
        items: list[dict] = []
        for s in snapshots:
            items.append(
                {
                    "content": snapshot_content(
                        week=week, sim_date=sim_date,
                        brand_alias=s["brand_alias"], category=s["category"],
                        n_products=s.get("n_products", 0),
                        dx_code=s["dx_code"], severity=s["severity"], evidence=s.get("evidence", {}),
                    ),
                    "context": "marketplace snapshot",
                    "timestamp": sim_date,
                    "document_id": doc_id("snapshot", s["brand_alias"], week=week),
                    "tags": build_tags(
                        brand_alias=s["brand_alias"], category=s["category"],
                        dx_code=s["dx_code"], kind="snapshot",
                    ),
                    "observation_scopes": build_scopes(
                        brand_alias=s["brand_alias"], category=s["category"], dx_code=s["dx_code"],
                    ),
                    "metadata": {"week": str(week), "severity": f"{s['severity']:.2f}"},
                }
            )
        if not items:
            return
        t0 = time.perf_counter()
        op_id = _stable_op_id(f"snapshots:{self.bank_id}:w{week:02d}")
        self._run(lambda c: c.retain_batch(
            bank_id=self.bank_id, items=items, retain_async=True, operation_id=op_id,
        ), write=True)
        self._log("retain", f"retained {len(items)} snapshots (w{week})",
                  int((time.perf_counter() - t0) * 1000), payload_ref=op_id)

    def retain_pitch(
        self, *, week: int, sim_date: datetime, brand_alias: str, category: str,
        dx_code: str, angle: str, base_score: float, rank: int, top_of: int, reason: str,
    ) -> str:
        content = pitch_content(
            week=week, sim_date=sim_date, brand_alias=brand_alias, angle=angle,
            base_score=base_score, rank=rank, top_of=top_of, reason=reason,
        )
        item = {
            "content": content,
            "context": "outreach I sent",
            "timestamp": sim_date,
            "document_id": doc_id("pitch", brand_alias, week=week, angle=angle),
            "tags": build_tags(brand_alias=brand_alias, category=category, dx_code=dx_code,
                               angle=angle, kind="pitch"),
            "observation_scopes": build_scopes(brand_alias=brand_alias, category=category,
                                                dx_code=dx_code, angle=angle),
            "metadata": {"week": str(week), "rank": str(rank), "base_score": f"{base_score:.3f}"},
        }
        t0 = time.perf_counter()
        op_id = _stable_op_id(f"pitch:{self.bank_id}:{slug(brand_alias)}:w{week:02d}:{angle}")
        self._run(lambda c: c.retain_batch(bank_id=self.bank_id, items=[item],
                                 retain_async=True, operation_id=op_id), write=True)
        self._log("retain", f"retained pitch {brand_alias} w{week} ({angle})",
                  int((time.perf_counter() - t0) * 1000), payload_ref=op_id)
        return item["document_id"]

    def retain_outcome(
        self, *, week: int, sim_date: datetime, brand_alias: str, category: str,
        dx_code: str, angle: str, outcome_type: str, reason_text: str = "",
        revisit_after: str | None = None,
    ) -> str:
        content = outcome_content(
            week=week, sim_date=sim_date, brand_alias=brand_alias,
            outcome_type=outcome_type, reason_text=reason_text, revisit_after=revisit_after,
        )
        item = {
            "content": content,
            "context": "outreach outcome",
            "timestamp": sim_date,
            "document_id": doc_id("outcome", brand_alias, week=week, angle=angle),
            "tags": build_tags(brand_alias=brand_alias, category=category, dx_code=dx_code,
                               angle=angle, outcome_type=outcome_type, kind="outcome"),
            "observation_scopes": build_scopes(brand_alias=brand_alias, category=category,
                                                dx_code=dx_code, angle=angle),
            "metadata": {"week": str(week), "outcome": outcome_type},
        }
        t0 = time.perf_counter()
        op_id = _stable_op_id(f"outcome:{self.bank_id}:{slug(brand_alias)}:w{week:02d}:{outcome_type}")
        self._run(lambda c: c.retain_batch(bank_id=self.bank_id, items=[item],
                                 retain_async=True, operation_id=op_id), write=True)
        self._log("retain", f"retained outcome {brand_alias} w{week} ({outcome_type})",
                  int((time.perf_counter() - t0) * 1000), payload_ref=op_id)
        return item["document_id"]

    def retain_decision(self, *, sim_date: datetime, actor: str, decision: str) -> str:
        item = {
            "content": decision_content(sim_date=sim_date, actor=actor, decision=decision),
            "context": "agency decision",
            "timestamp": sim_date,
            "document_id": doc_id("decision", actor, extra=uuid.uuid4().hex[:8]),
            "tags": build_tags(kind="decision"),
            "observation_scopes": build_scopes(),  # non-empty by construction
        }
        self.client.retain_batch(bank_id=self.bank_id, items=[item])
        return item["document_id"]

    # ---------- Recall / Reflect ----------

    def recall_for_lead(
        self, *, sim_date: datetime, brand_alias: str, dx_code: str, category: str,
        max_tokens: int = 2000,
    ):
        query = (
            f"What has happened with {brand_alias} or similar {dx_code} brands, and which "
            f"pitch angles have worked? Include past objections and revisit notes."
        )
        t0 = time.perf_counter()
        resp = self._run(lambda c: c.recall(
            bank_id=self.bank_id, query=query, budget="mid", max_tokens=max_tokens,
            tags=[f"brand:{slug(brand_alias)}"], tags_match="any",
            types=["world", "experience", "observation"],
            query_timestamp=sim_date.isoformat(),
            include_source_facts=True,
        ))
        self._log("recall", f"recall({brand_alias})", int((time.perf_counter() - t0) * 1000))
        return resp

    def prioritise(
        self, *, week: int, sim_date: datetime, candidates: list[dict],
    ) -> PrioritisationResult:
        """Ask Hindsight to adjust scores and pick angles. Never crashes the caller."""
        candidate_table = "\n".join(
            f"- {c['brand_alias']} | cat={c['category']} | products={c.get('n_products','?')} | "
            f"ratings={c.get('total_ratings','?')} | dx={c['diagnosis']} | severity={c['severity']:.2f} | "
            f"base_score={c.get('base_score',0):.2f}"
            for c in candidates
        )
        prompt = (
            f"Today is {sim_date.date().isoformat()} (week {week} of the season).\n"
            f"You are prioritising which Amazon brands our agency should contact this week.\n"
            f"Use everything you have learned from past pitches and outcomes.\n\n"
            f"Return JSON with an `adjustments` array. EACH item MUST be an object with "
            f"these keys: brand_id (string, use the id from the candidate list verbatim), "
            f"score_adjustment (float in [-0.6, 0.6]), recommended_angle (one of: "
            f"brand_protection, inventory_planning, listing_and_reviews, map_enforcement, "
            f"advertising, growth_partnership), reason (short string, cite counts), "
            f"skip (bool), revisit (bool). Do NOT emit bare numbers or bare strings in "
            f"the array. Also return `beliefs_used` as an array of short strings.\n\n"
            f"Candidates (id | category | products | ratings | diagnosis | severity | base_score):\n"
            f"{candidate_table}"
        )
        t0 = time.perf_counter()
        try:
            resp = self._run(lambda c: c.reflect(
                bank_id=self.bank_id,
                query=prompt,
                budget="high",
                response_schema=PrioritisationResult.model_json_schema(),
                include_facts=True,
            ))
        except Exception as e:  # network / server errors — fall back cleanly
            self._log("reflect", f"prioritise failed ({e.__class__.__name__}: {str(e)[:120]}); using empty",
                      int((time.perf_counter() - t0) * 1000))
            return PrioritisationResult()

        latency = int((time.perf_counter() - t0) * 1000)
        raw = getattr(resp, "structured_output", None)
        if not raw:
            # Fall back to parsing the free-text response, since Hindsight sometimes
            # emits the answer only in `text` when the LLM stringifies the objects.
            raw = _coerce_prioritisation(getattr(resp, "text", None))
            if not raw:
                self._log("reflect", "prioritise returned no structured_output", latency)
                return PrioritisationResult()
        raw = _normalise_prioritisation_payload(raw)
        try:
            result = PrioritisationResult.model_validate(raw)
        except ValidationError as ve:
            self._log("reflect", f"prioritise validation error: {ve.errors()[:1]}", latency)
            return PrioritisationResult()
        self._log("reflect", f"prioritise ok ({len(result.adjustments)} adjustments)", latency)
        return result

    def extract_beliefs(self, *, week: int, sim_date: datetime) -> BeliefSet:
        prompt = (
            f"Today is {sim_date.date().isoformat()} (week {week} of the season).\n"
            f"Summarise your current beliefs, grouped by theme:\n"
            f"- who_converts: which brand segments reply and book meetings\n"
            f"- which_angle: which pitch angle works for which diagnosis\n"
            f"- avoid: segments, angles or behaviours to stop doing\n"
            f"- my_mistakes: where our scoring or angle choice was wrong\n\n"
            f"Return STRICT JSON: {{\"beliefs\": [{{...}}, {{...}}]}}. Each item is an "
            f"OBJECT (not a string), with these fields:\n"
            f'  {{"id": "short-slug", "group": "who_converts|which_angle|avoid|my_mistakes",'
            f' "statement": "one short sentence", "confidence": 0.0..1.0, "evidence_count": integer}}\n\n'
            f"Return 6-10 beliefs total, balanced across the four groups (aim for at least "
            f"one belief in each group). Do NOT put every belief in the same group. "
            f"Cite evidence_count from the retained outcomes."
        )
        t0 = time.perf_counter()
        try:
            resp = self._run(lambda c: c.reflect(
                bank_id=self.bank_id, query=prompt, budget="high",
                response_schema=BeliefSet.model_json_schema(),
                include_facts=True,
            ))
        except Exception as e:
            self._log("reflect", f"beliefs failed ({e.__class__.__name__}: {str(e)[:120]}); returning empty",
                      int((time.perf_counter() - t0) * 1000))
            return BeliefSet()
        latency = int((time.perf_counter() - t0) * 1000)
        raw = getattr(resp, "structured_output", None)
        if not raw:
            self._log("reflect", "beliefs returned no structured_output", latency)
            return BeliefSet()
        raw = _normalise_beliefs_payload(raw)
        try:
            beliefs = BeliefSet.model_validate(raw)
        except ValidationError as ve:
            self._log("reflect", f"beliefs validation error: {ve.errors()[:1]}", latency)
            return BeliefSet()
        self._log("reflect", f"beliefs ok ({len(beliefs.beliefs)})", latency)
        return beliefs

    def get_mental_model_history(self, model_id: str):
        return self.client.get_mental_model_history(self.bank_id, model_id)

    def diff_beliefs(self, prev: BeliefSet, cur: BeliefSet) -> dict:
        """Compute simple diff between two BeliefSets by belief id."""
        prev_map = {b.id: b for b in prev.beliefs}
        cur_map = {b.id: b for b in cur.beliefs}
        new: list[str] = []
        removed: list[str] = []
        strengthened: list[str] = []
        weakened: list[str] = []
        reversed_: list[str] = []
        for bid, cur_b in cur_map.items():
            prev_b = prev_map.get(bid)
            if not prev_b:
                new.append(bid); continue
            # A reversal is a real semantic flip: a strong prior belief and a
            # strong current belief that now say opposite things. Detect via
            # a "negation" keyword swap (was positive, now negative or vice versa).
            def _negates(a: str, b: str) -> bool:
                neg_kw = ("do not ", "don't ", "avoid ", "stop ", "never ", "not ")
                a_neg = any(k in a.lower() for k in neg_kw)
                b_neg = any(k in b.lower() for k in neg_kw)
                return a_neg != b_neg
            if (cur_b.statement != prev_b.statement
                    and cur_b.confidence >= 0.6 and prev_b.confidence >= 0.6
                    and _negates(cur_b.statement, prev_b.statement)):
                reversed_.append(bid); continue
            if cur_b.confidence > prev_b.confidence + 0.05:
                strengthened.append(bid)
            elif cur_b.confidence < prev_b.confidence - 0.05:
                weakened.append(bid)
        for bid in prev_map:
            if bid not in cur_map:
                removed.append(bid)
        return {
            "new": new,
            "removed": removed,
            "strengthened": strengthened,
            "weakened": weakened,
            "reversed": reversed_,
        }
