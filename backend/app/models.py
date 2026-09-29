from __future__ import annotations

from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Brand(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    alias: str = Field(index=True, unique=True)
    category: str = Field(index=True)
    n_products: int
    total_ratings: int
    avg_rating: float
    price_min: float
    price_max: float
    archetype_hidden: str = Field(index=True)


class Product(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    brand_id: int = Field(index=True, foreign_key="brand.id")
    parent_asin_hash: str = Field(index=True)
    title: str
    category_path: str
    price: float
    avg_rating: float
    rating_number: int


class Snapshot(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    product_id: int = Field(index=True, foreign_key="product.id")
    week: int = Field(index=True)
    date: datetime
    demand_index: float
    bsr: int
    seller_count: int
    buybox_share: float
    buybox_price: float
    in_stock: bool
    ad_presence: float
    review_count: int


class BrandSignal(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    brand_id: int = Field(index=True, foreign_key="brand.id")
    week: int = Field(index=True)
    signal_name: str = Field(index=True)
    value: float


class Diagnosis(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    brand_id: int = Field(index=True, foreign_key="brand.id")
    week: int = Field(index=True)
    code: str = Field(index=True)
    severity: float
    evidence_json: str


class Lead(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    brand_id: int = Field(index=True, foreign_key="brand.id")
    week: int = Field(index=True)
    base_score: float
    memory_adj: float
    final_score: float
    rank: int
    angle: str
    reason: str
    evidence_memory_ids: str
    mode: str = Field(index=True)


class Pitch(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    lead_id: int = Field(index=True, foreign_key="lead.id")
    sent_week: int
    angle: str
    draft_text: str
    approved: bool = Field(default=False)


class Outcome(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    pitch_id: int = Field(index=True, foreign_key="pitch.id")
    week: int = Field(index=True)
    type: str = Field(index=True)
    reason_text: str = Field(default="")
    revisit_after: datetime | None = Field(default=None)


class BeliefSnapshot(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    week: int = Field(index=True, unique=True)
    beliefs_json: str
    diff_json: str


class MemoryEvent(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    ts: datetime = Field(default_factory=_utcnow, index=True)
    op: str = Field(index=True)
    bank_id: str
    summary: str
    latency_ms: int
    payload_ref: str = Field(default="")


class SimClock(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    current_week: int
    season_id: str
    seed: int
