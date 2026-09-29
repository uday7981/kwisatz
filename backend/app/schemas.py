from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class WeekInfo(BaseModel):
    current_week: int
    season_id: str
    seed: int
    memory_available: bool


class LeadOut(BaseModel):
    brand_alias: str
    week: int
    category: str
    diagnosis: str
    severity: float
    base_score: float
    memory_adj: float
    final_score: float
    rank: int
    angle: str
    reason: str
    evidence_memory_ids: list[str] = []


class PipelineStats(BaseModel):
    brands_scanned: int
    diagnosed: int
    memory_adjusted: int
    ranked: int


class ShortlistOut(BaseModel):
    week: int
    mode: Literal["on", "off"]
    memory_available: bool
    leads: list[LeadOut]
    skipped: list[dict]
    pipeline: PipelineStats | None = None


class SignalPoint(BaseModel):
    week: int
    demand_index: float | None = None
    seller_count: int
    buybox_share: float
    buybox_price: float | None = None
    ad_presence: float
    review_count: int


class LeadDetail(BaseModel):
    lead: LeadOut
    brand: dict
    signals: list[SignalPoint]
    memory_context: list[dict]  # {text, doc_id, ts}


class DraftRequest(BaseModel):
    angle_override: str | None = None


class DraftOut(BaseModel):
    subject: str
    body: str
    angle: str


class OutcomeIn(BaseModel):
    type: Literal["no_reply", "reply", "meeting", "signed", "declined", "not_now"]
    reason_text: str = ""
    revisit_after_week: int | None = None


class BeliefOut(BaseModel):
    id: str
    group: str
    statement: str
    confidence: float
    evidence_count: int


class BeliefsOut(BaseModel):
    week: int
    beliefs: list[BeliefOut]
    diff: dict


class MetricsOut(BaseModel):
    weeks: list[int]
    off: list[dict]
    on: list[dict]
    oracle: list[dict]


class HealthOut(BaseModel):
    ok: bool
    hindsight_reachable: bool
    groq_reachable: bool
    demo_mode: bool


class AnalyticsWeek(BaseModel):
    week: int
    scanned: int
    diagnosed: int
    shortlisted: int
    by_diagnosis: dict[str, int]
    by_angle: dict[str, int]
    by_category: dict[str, int]


class AnalyticsOut(BaseModel):
    weeks: list[int]
    totals: dict[str, int]
    by_week: list[AnalyticsWeek]
    diagnosis_totals: dict[str, int]
    angle_totals: dict[str, int]
    category_totals: dict[str, int]
    memory_events_total: int
