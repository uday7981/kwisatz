"""Guard that real brand names never leak into generated content.

Reads `brand_alias.csv` (real store -> alias) if present, and asserts that no
draft/template ever mentions a real store name.
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

import pytest

from backend.app.llm.prompts import EmailPromptInput, fallback_email

REPO = Path(__file__).resolve().parents[2]
ALIAS_FILE = REPO / "brand_alias.csv"


def _real_stores() -> list[str]:
    if not ALIAS_FILE.exists():
        return []
    with ALIAS_FILE.open() as fh:
        return [row["store"] for row in csv.DictReader(fh) if row.get("store")]


@pytest.mark.skipif(not ALIAS_FILE.exists(), reason="brand_alias.csv not present")
def test_fallback_email_does_not_mention_real_stores() -> None:
    real = _real_stores()
    for store in real[:20]:
        inp = EmailPromptInput(
            brand_alias="Copperleaf Kitchen",  # a made-up alias
            first_name="Alex",
            diagnosis="Reseller invasion",
            signals_summary="7 resellers joined in 30 days.",
            angle="brand protection",
            memory_context="",
        )
        draft = fallback_email(inp)
        for text in (draft["subject"], draft["body"]):
            assert not re.search(rf"\b{re.escape(store)}\b", text, re.IGNORECASE), (
                f"Real store '{store}' leaked into template output: {text}"
            )
