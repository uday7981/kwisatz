from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ANGLES = Literal[
    "brand_protection",
    "inventory_planning",
    "listing_and_reviews",
    "map_enforcement",
    "advertising",
    "growth_partnership",
]


class LeadAdjustment(BaseModel):
    model_config = ConfigDict(extra="ignore")
    brand_id: str = Field(description="Anonymised brand alias (e.g. 'copperleaf-kitchen').")
    score_adjustment: float = Field(ge=-0.6, le=0.6, description="Multiplicative bump to base score.")
    recommended_angle: ANGLES
    reason: str = Field(max_length=240)
    skip: bool = False
    revisit: bool = False


class PrioritisationResult(BaseModel):
    model_config = ConfigDict(extra="ignore")
    adjustments: list[LeadAdjustment] = Field(default_factory=list)
    beliefs_used: list[str] = Field(default_factory=list)


class Belief(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(description="Stable slug, e.g. 'angle-reseller-invasion'.")
    group: Literal["who_converts", "which_angle", "avoid", "my_mistakes"]
    statement: str
    confidence: float = Field(ge=0.0, le=1.0)
    evidence_count: int = Field(ge=0)


class BeliefSet(BaseModel):
    model_config = ConfigDict(extra="ignore")
    beliefs: list[Belief] = Field(default_factory=list)


class EmailDraft(BaseModel):
    model_config = ConfigDict(extra="ignore")
    subject: str = Field(min_length=1, max_length=120)
    body: str = Field(min_length=1)
