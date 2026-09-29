"""FastAPI routers. One file for now since routes are small."""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sse_starlette.sse import EventSourceResponse

from sim.simulator import week_to_date

from ..engine.loop import Lead, run_week
from ..llm.prompts import EmailPromptInput
from ..schemas import (
    BeliefOut,
    BeliefsOut,
    DraftOut,
    DraftRequest,
    HealthOut,
    LeadDetail,
    LeadOut,
    AnalyticsOut,
    AnalyticsWeek,
    MetricsOut,
    OutcomeIn,
    PipelineStats,
    ShortlistOut,
    SignalPoint,
    WeekInfo,
)
from ..state import AppState, get_state

router = APIRouter()


def _lead_out(lead: Lead) -> LeadOut:
    return LeadOut(
        brand_alias=lead.brand_alias,
        week=lead.week,
        category=lead.category,
        diagnosis=lead.diagnosis,
        severity=lead.severity,
        base_score=lead.base_score,
        memory_adj=lead.memory_adj,
        final_score=lead.final_score,
        rank=lead.rank,
        angle=lead.angle,
        reason=lead.reason,
        evidence_memory_ids=list(lead.evidence_memory_ids),
    )


# ---------- Meta ----------


@router.get("/api/health", response_model=HealthOut)
def health(state: AppState = Depends(get_state)) -> HealthOut:
    groq_ok = state.llm.client is not None
    hs_ok = state.memory.is_reachable() if state.memory is not None else False
    return HealthOut(
        ok=True, hindsight_reachable=hs_ok, groq_reachable=groq_ok,
        demo_mode=state.settings.demo_mode,
    )


@router.get("/api/week", response_model=WeekInfo)
def week(state: AppState = Depends(get_state)) -> WeekInfo:
    # Current week is the last completed demo week. Persistence to SimClock table is
    # deferred to Phase 5; for now derive from a query param or default to 8.
    return WeekInfo(
        current_week=44, season_id="s2026", seed=state.settings.sim_seed,
        memory_available=state.memory_available(),
    )


@router.post("/api/week/advance", response_model=WeekInfo)
def advance_week(
    to_week: int = Query(45, ge=1, le=52),
    state: AppState = Depends(get_state),
) -> WeekInfo:
    """Kick the memory-on loop for a single week. Live-demo button."""
    prioritise = _memory_prioritise_factory(state)
    _leads, _ = run_week(to_week, state.adapter, mode="on" if prioritise else "off",
                         memory_prioritise=prioritise)
    return WeekInfo(current_week=to_week, season_id="s2026",
                    seed=state.settings.sim_seed, memory_available=state.memory_available())


@router.post("/api/demo/reset")
def demo_reset(to_week: int = Query(44, ge=1, le=52), state: AppState = Depends(get_state)) -> dict:
    if state.memory is None:
        return {"ok": False, "reason": "Hindsight unavailable"}
    op = state.memory.reset_from_seed()
    return {"ok": True, "operation_id": op, "to_week": to_week}


# ---------- Shortlist / Leads ----------


def _memory_prioritise_factory(state: AppState):
    if not state.memory_available():
        return None
    from ..memory.formats import slug as _slug
    brand_meta = {row["alias"]: row for row in state.adapter.brands().iter_rows(named=True)}
    alias_by_slug = {_slug(a): a for a in brand_meta}

    def _prioritise(*, week: int, candidates):
        if isinstance(candidates, dict):
            candidates = [candidates]
        payload = []
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
        result = state.memory.prioritise(week=week, sim_date=week_to_date(week), candidates=payload)
        by_key: dict[str, dict] = {}
        for a in result.adjustments:
            entry = a.model_dump()
            by_key[a.brand_id] = entry
            by_key[alias_by_slug.get(a.brand_id, a.brand_id)] = entry

        # LLM non-determinism: reflect sometimes returns zero adjustments.
        # If we have a cached non-empty result for this week, fall back to it
        # so the UI does not oscillate between "memory reranked N" and 0.
        if by_key:
            state.last_adjustments_by_week[week] = by_key
        elif week in state.last_adjustments_by_week:
            by_key = state.last_adjustments_by_week[week]

        return by_key

    return _prioritise


@router.get("/api/shortlist", response_model=ShortlistOut)
def shortlist(
    week: int = Query(44, ge=1, le=52),
    mode: str = Query("on"),
    state: AppState = Depends(get_state),
) -> ShortlistOut:
    if mode not in {"on", "off"}:
        raise HTTPException(400, "mode must be 'on' or 'off'")
    prioritise = _memory_prioritise_factory(state) if mode == "on" else None
    leads, skipped = run_week(week, state.adapter, mode=mode if prioritise else "off",
                              memory_prioritise=prioritise)

    # Compute pipeline stats deterministically for the UI's discovery strip.
    from ..engine.diagnosis import diagnose_brand, primary_diagnosis
    from ..engine.loop import _brand_signals as _sigs_for_week
    sigs = _sigs_for_week(week, state.adapter)
    diagnosed = sum(1 for s in sigs if primary_diagnosis(diagnose_brand(s)))
    memory_adjusted = sum(1 for l in leads if l.memory_adj != 0)
    pipeline = PipelineStats(
        brands_scanned=len(sigs),
        diagnosed=diagnosed,
        memory_adjusted=memory_adjusted,
        ranked=len(leads),
    )

    return ShortlistOut(
        week=week,
        mode="on" if (mode == "on" and prioritise) else "off",
        memory_available=state.memory_available(),
        leads=[_lead_out(l) for l in leads],
        skipped=[{"brand_alias": s.brand_alias, "category": s.category, "reason": s.reason} for s in skipped],
        pipeline=pipeline,
    )


@router.get("/api/leads/{alias}", response_model=LeadDetail)
def lead_detail(
    alias: str,
    week: int = Query(44, ge=1, le=52),
    state: AppState = Depends(get_state),
) -> LeadDetail:
    all_leads, _ = run_week(week, state.adapter, mode="off")
    lead = next((l for l in all_leads if l.brand_alias == alias), None)
    if not lead:
        raise HTTPException(404, "brand not on this week's shortlist")

    snaps = state.adapter._snapshots_df()
    products = state.adapter.products(alias)
    if products.is_empty():
        raise HTTPException(404, "brand has no products")
    top_id = products.sort(by=["rating_number", "avg_rating"], descending=[True, True])["parent_asin_hash"].to_list()[0]
    brand_snaps = snaps.filter(snaps["product_id_key"] == top_id)
    signals = [
        SignalPoint(
            week=int(r["week"]), demand_index=r["demand_index"], seller_count=int(r["seller_count"]),
            buybox_share=float(r["buybox_share"]), buybox_price=r["buybox_price"],
            ad_presence=float(r["ad_presence"]), review_count=int(r["review_count"]),
        )
        for r in brand_snaps.iter_rows(named=True)
    ]

    memory_context: list[dict] = []
    if state.memory_available():
        try:
            brand_row = state.adapter.brands().filter(state.adapter.brands()["alias"] == alias).row(0, named=True)
            resp = state.memory.recall_for_lead(
                sim_date=week_to_date(week), brand_alias=alias,
                dx_code=lead.diagnosis, category=brand_row["category"], max_tokens=1500,
            )
            raw = list(getattr(resp, "results", []) or [])
            memory_context = _condense_memory(raw, brand_alias=alias)
        except Exception:
            pass

    brand_row = state.adapter.brands().filter(state.adapter.brands()["alias"] == alias).row(0, named=True)
    return LeadDetail(lead=_lead_out(lead), brand=dict(brand_row), signals=signals, memory_context=memory_context)


@router.post("/api/leads/{alias}/draft", response_model=DraftOut)
def draft(
    alias: str,
    body: DraftRequest,
    week: int = Query(44, ge=1, le=52),
    state: AppState = Depends(get_state),
) -> DraftOut:
    all_leads, _ = run_week(week, state.adapter, mode="off")
    lead = next((l for l in all_leads if l.brand_alias == alias), None)
    if not lead:
        raise HTTPException(404, "brand not on this week's shortlist")
    angle = body.angle_override or lead.angle
    inp = EmailPromptInput(
        brand_alias=alias, first_name="there",
        diagnosis=lead.diagnosis, signals_summary=lead.reason,
        angle=angle.replace("_", " "), memory_context="",
    )
    draft_dict = state.llm.draft_email(inp)
    return DraftOut(subject=draft_dict["subject"], body=draft_dict["body"], angle=angle)


@router.post("/api/leads/{alias}/approve")
def approve(
    alias: str,
    week: int = Query(44, ge=1, le=52),
    state: AppState = Depends(get_state),
) -> dict:
    """Approve current draft: retain the pitch in memory."""
    all_leads, _ = run_week(week, state.adapter, mode="off")
    lead = next((l for l in all_leads if l.brand_alias == alias), None)
    if not lead:
        raise HTTPException(404)
    if state.memory_available():
        state.memory.retain_pitch(
            week=week, sim_date=week_to_date(week), brand_alias=alias,
            category=lead.category, dx_code=lead.diagnosis, angle=lead.angle,
            base_score=lead.base_score, rank=lead.rank, top_of=12,
            reason=lead.reason,
        )
    return {"ok": True}


@router.post("/api/pitches/{alias}/outcome")
def log_outcome(
    alias: str,
    body: OutcomeIn,
    week: int = Query(44, ge=1, le=52),
    state: AppState = Depends(get_state),
) -> dict:
    if state.memory_available():
        # Look up lead so tags carry the right category/dx/angle.
        all_leads, _ = run_week(week, state.adapter, mode="off")
        lead = next((l for l in all_leads if l.brand_alias == alias), None)
        if lead:
            state.memory.retain_outcome(
                week=week, sim_date=week_to_date(week), brand_alias=alias,
                category=lead.category, dx_code=lead.diagnosis, angle=lead.angle,
                outcome_type=body.type, reason_text=body.reason_text,
                revisit_after=(str(body.revisit_after_week) if body.revisit_after_week else None),
            )
    return {"ok": True}


# ---------- Beliefs / Metrics / Feed ----------


@router.get("/api/beliefs", response_model=BeliefsOut)
def beliefs(week: int = Query(44, ge=1, le=52), state: AppState = Depends(get_state)) -> BeliefsOut:
    if not state.memory_available():
        return BeliefsOut(week=week, beliefs=[], diff={})
    bs = state.memory.extract_beliefs(week=week, sim_date=week_to_date(week))

    # Diff against the most recent prior week we have cached, if any.
    prev_week = max((w for w in state.beliefs_by_week if w < week), default=None)
    diff: dict = {}
    if prev_week is not None:
        diff = state.memory.diff_beliefs(state.beliefs_by_week[prev_week], bs)
        diff["_prev_week"] = prev_week

    state.beliefs_by_week[week] = bs

    return BeliefsOut(
        week=week,
        beliefs=[BeliefOut(**b.model_dump()) for b in bs.beliefs],
        diff=diff,
    )


@router.get("/api/metrics/learning", response_model=MetricsOut)
def learning_metrics(state: AppState = Depends(get_state)) -> MetricsOut:
    from ..eval.harness import run_all
    prioritise = _memory_prioritise_factory(state)
    results = run_all(memory_prioritise=prioritise)
    return MetricsOut(weeks=results["weeks"], off=results["off"], on=results["on"], oracle=results["oracle"])


@router.get("/api/analytics", response_model=AnalyticsOut)
def analytics(state: AppState = Depends(get_state)) -> AnalyticsOut:
    """Season-wide aggregation of the deterministic shortlist across all 12
    demo weeks. Fast (no reflect calls) so the page loads in seconds."""
    from collections import Counter
    from ..engine.diagnosis import diagnose_brand, primary_diagnosis
    from ..engine.loop import _brand_signals

    weeks = list(range(41, 53))
    by_week: list[AnalyticsWeek] = []
    dx_totals: Counter[str] = Counter()
    angle_totals: Counter[str] = Counter()
    cat_totals: Counter[str] = Counter()
    scanned_total = 0
    diagnosed_total = 0
    shortlisted_total = 0

    for w in weeks:
        leads, _skipped = run_week(w, state.adapter, mode="off")
        sigs = _brand_signals(w, state.adapter)
        diagnosed = sum(1 for s in sigs if primary_diagnosis(diagnose_brand(s)))
        scanned_total += len(sigs)
        diagnosed_total += diagnosed
        shortlisted_total += len(leads)

        dx: Counter[str] = Counter()
        angle: Counter[str] = Counter()
        cat: Counter[str] = Counter()
        for l in leads:
            dx[l.diagnosis] += 1
            angle[l.angle] += 1
            cat[l.category] += 1
            dx_totals[l.diagnosis] += 1
            angle_totals[l.angle] += 1
            cat_totals[l.category] += 1

        by_week.append(AnalyticsWeek(
            week=w,
            scanned=len(sigs),
            diagnosed=diagnosed,
            shortlisted=len(leads),
            by_diagnosis=dict(dx),
            by_angle=dict(angle),
            by_category=dict(cat),
        ))

    memory_events_total = len(state.event_bus.history)

    return AnalyticsOut(
        weeks=weeks,
        totals={
            "brands_scanned": scanned_total,
            "diagnoses_fired": diagnosed_total,
            "shortlisted": shortlisted_total,
            "unique_brands": len({row["alias"] for row in state.adapter.brands().iter_rows(named=True)}),
        },
        by_week=by_week,
        diagnosis_totals=dict(dx_totals),
        angle_totals=dict(angle_totals),
        category_totals=dict(cat_totals),
        memory_events_total=memory_events_total,
    )


@router.get("/api/memory/feed")
async def memory_feed(request: Request, state: AppState = Depends(get_state)):
    """SSE stream of MemoryEvent payloads."""
    bus = state.event_bus

    async def event_gen():
        # Replay recent history.
        for evt in list(bus.history)[-20:]:
            yield {"event": "memory", "data": json.dumps(_evt_json(evt))}
        async for evt in bus.subscribe():
            if await request.is_disconnected():
                break
            yield {"event": "memory", "data": json.dumps(_evt_json(evt))}

    return EventSourceResponse(event_gen())


def _evt_json(evt: Any) -> dict:
    if is_dataclass(evt):
        return asdict(evt)
    return dict(evt)


# ---------- Memory display helpers ----------


_OUTCOME_KEYWORDS = ("replied", "meeting", "signed", "declined", "not_now",
                     "objected", "not the right time", "in-house", "already work")
_STRUCTURAL_NOISE = ("| involving:", "| when:", "outreach effort", "outreach campaign")


def _clean_line(text: str) -> str:
    """Trim the noisy metadata Hindsight appends after the actual content."""
    if not text:
        return ""
    # Strip anything after the first '|' — that's usually "When:", "Involving:", etc.
    head = text.split("|", 1)[0].strip()
    # If the head is empty (all metadata), keep the full text.
    return head or text.strip()


def _classify(text: str) -> str:
    """Return one of: outcome, pitch, snapshot, observation, other."""
    t = text.lower()
    if any(k in t for k in _OUTCOME_KEYWORDS):
        return "outcome"
    if t.startswith("pitched"):
        return "pitch"
    if "buy box" in t or "sellers" in t or "reseller" in t:
        return "snapshot"
    return "other"


def _condense_memory(raw: list, *, brand_alias: str) -> list[dict]:
    """Turn a raw recall response into a small human-readable list. Prefers
    outcome-flavoured memories and summarises duplicate pitch records so the UI
    is not swamped with a 20-line "we pitched them" observation."""
    seen: dict[str, dict] = {}  # doc_id or normalised text -> record
    pitch_count = 0
    latest_pitch_text = ""

    for m in raw:
        text = _clean_line(getattr(m, "text", "") or "")
        if not text:
            continue
        doc_id = getattr(m, "document_id", "") or ""
        mtype = getattr(m, "type", "") or ""
        kind = _classify(text)

        if kind == "pitch":
            pitch_count += 1
            latest_pitch_text = text
            continue  # collapse pitches into one summary at the end

        key = doc_id or text[:80]
        if key in seen:
            continue
        seen[key] = {
            "text": text,
            "doc_id": doc_id,
            "type": mtype,
            "kind": kind,
        }
        if len(seen) >= 5:
            break

    condensed = list(seen.values())

    if pitch_count > 0:
        condensed.append({
            "text": (
                f"We have pitched {brand_alias} {pitch_count} times before, most recently: "
                f"{latest_pitch_text}"
                if pitch_count > 1
                else latest_pitch_text
            ),
            "doc_id": "",
            "type": "observation",
            "kind": "pitch",
        })

    return condensed[:6]
