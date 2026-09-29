from __future__ import annotations

from backend.app.llm.prompts import (
    EmailPromptInput,
    fallback_email,
    has_number,
    has_optout,
    strip_em_dashes,
    word_count,
)


def test_strip_em_dashes_replaces_all_variants() -> None:
    txt = "First part — second – third -- fourth."
    out = strip_em_dashes(txt)
    assert "—" not in out and "–" not in out
    assert " -- " not in out


def test_has_number_and_optout() -> None:
    body = "We saw 7 resellers join in 30 days. Reply STOP and I won't email again."
    assert has_number(body)
    assert has_optout(body)


def test_fallback_email_meets_rules() -> None:
    inp = EmailPromptInput(
        brand_alias="Copperleaf Kitchen",
        first_name="Alex",
        diagnosis="Reseller invasion",
        signals_summary="7 resellers joined in 30 days.",
        angle="brand protection",
        memory_context="",
    )
    draft = fallback_email(inp)
    assert word_count(draft["body"]) < 120
    assert has_optout(draft["body"])
    assert has_number(draft["body"])
    assert "—" not in draft["body"]
