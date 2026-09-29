"""
Prompt templates and post-checks. All user-facing copy must avoid em dashes and
match the acceptance rules in SPEC 3.6 / 4.5.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

EMAIL_SYSTEM = (
    "You write short, specific outreach emails for an Amazon growth agency. "
    "Rules: under 120 words; plain language; no em dashes; cite one or two numbers "
    "from the brand's data; never name another client; one clear question; include "
    "the line 'Reply STOP and I won't email again.' Return JSON {subject, body}."
)


@dataclass(frozen=True)
class EmailPromptInput:
    brand_alias: str
    first_name: str
    diagnosis: str            # human-readable
    signals_summary: str      # one or two numbers
    angle: str                # e.g. 'brand protection'
    memory_context: str       # what memory says (may be empty)


def email_user_prompt(inp: EmailPromptInput) -> str:
    ctx = inp.memory_context.strip() or "(no memory yet)"
    return (
        f"Brand: {inp.brand_alias}. Contact first name: {inp.first_name}. "
        f"Diagnosis: {inp.diagnosis}. Evidence: {inp.signals_summary}. "
        f"Angle: {inp.angle}. What memory says: {ctx}"
    )


EM_DASH_PATTERNS = ("—", "–", " -- ")


def strip_em_dashes(text: str) -> str:
    out = text
    for ch in EM_DASH_PATTERNS:
        out = out.replace(ch, ", ")
    return out


def word_count(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text))


def has_optout(body: str) -> bool:
    return "reply stop" in body.lower() or "opt out" in body.lower() or "unsubscribe" in body.lower()


def has_number(body: str) -> bool:
    return bool(re.search(r"\b\d", body))


REPAIR_TEMPLATE = (
    "Your last response failed validation with error: {error}\n"
    "Return JSON exactly matching this schema:\n{schema}\n"
    "Only return the JSON object, nothing else."
)


def fallback_email(inp: EmailPromptInput) -> dict[str, str]:
    """Deterministic template used when Groq is unavailable."""
    subject = f"About {inp.brand_alias} on Amazon"
    body = (
        f"Hi {inp.first_name}, I looked at {inp.brand_alias} this morning. "
        f"{inp.signals_summary} That pattern usually calls for {inp.angle}. "
        f"Would a quick call this week make sense? "
        f"Reply STOP and I won't email again."
    )
    return {"subject": subject, "body": strip_em_dashes(body)}
