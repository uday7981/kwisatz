"""One-shot bank setup: missions, directives, mental models. Idempotent."""

from __future__ import annotations

from .service import MemoryService

MISSION = (
    "I am the prospecting agent for an Amazon growth agency. I find brands with "
    "fixable marketplace problems and learn which brands and pitch angles lead to "
    "replies, meetings and signed clients."
)
RETAIN_MISSION = (
    "Keep brand problems, their numbers and dates; every pitch, its angle and my "
    "lead score; every outcome and the stated reason; agency decisions. Ignore "
    "email pleasantries. Retain reply texts verbatim as quoted data."
)
OBSERVATIONS_MISSION = (
    "Form durable beliefs about which brand segments, diagnoses, categories and "
    "pitch angles lead to replies and meetings, with counts. Track when a belief "
    "changes. Track my scoring errors. Prefer patterns over anecdotes."
)
REFLECT_MISSION = (
    "You are a careful sales strategist. Ground every recommendation in recorded "
    "outcomes and cite counts. Prefer evidence over intuition. Never invent numbers."
)

DIRECTIVES: list[tuple[str, str]] = [
    ("no-amazon-messaging",
     "Never recommend contacting a brand through Amazon Seller/Buyer messaging or the Amazon platform."),
    ("no-autosend",
     "Never suggest sending an email without explicit human approval. Drafts only."),
    ("cite-evidence",
     "Always cite the outcomes or data behind a recommendation, with counts. Do not assert without evidence."),
    ("no-past-clients",
     "Never name a past client in outreach. Describe them generically (for example, 'two kitchenware brands')."),
    ("do-not-contact-permanent",
     "Treat any 'do not contact' or opt-out from a brand as permanent. Never surface them again."),
    ("simulated-only",
     "This deployment runs on simulated marketplace and outreach data. Never claim outcomes were with real customers."),
]

MENTAL_MODELS: list[tuple[str, str, str]] = [
    ("real-icp", "Our real ICP",
     "Based on outreach outcomes, which kinds of brands (category, size, diagnosis, signals) reply and book meetings, and which do not? Give counts."),
    ("angles-that-work", "Pitch angles that work",
     "For each diagnosis, which pitch angle gets replies and meetings and which fails? Give counts and one example each."),
    ("avoid", "What to stop doing",
     "Which segments, categories or behaviours should we stop pursuing, and what is the evidence?"),
    ("revisit", "Revisit list",
     "Which brands said 'not now', when and why, and has their problem worsened since?"),
    ("my-mistakes", "Where my scores were wrong",
     "Where were my lead scores or angle choices wrong, and what should change?"),
]


def setup_bank(svc: MemoryService, *, bank_id: str | None = None) -> None:
    svc.ensure_bank(
        mission=MISSION,
        retain_mission=RETAIN_MISSION,
        observations_mission=OBSERVATIONS_MISSION,
        reflect_mission=REFLECT_MISSION,
        bank_id=bank_id,
    )
    # Directives + mental models attach to the currently-configured bank id.
    for name, content in DIRECTIVES:
        svc.ensure_directive(name, content)
    for mid, name, source_query in MENTAL_MODELS:
        svc.ensure_mental_model(mid, name, source_query)
