"""Fail loudly if em-dashes or en-dashes creep into user-facing text."""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

TARGETS = [
    "README.md",
    "docs/ARTICLE_DRAFT.md",
    "docs/LINKEDIN_POST.md",
    "backend/app/llm/prompts.py",
    "backend/app/memory/formats.py",
    "backend/app/memory/bank_setup.py",
    "frontend/src",
]

BAD = ("—", "–")  # em-dash, en-dash
ALLOW_MARKERS = ("<!-- em-dash-ok -->", "EM_DASH_PATTERNS")


def scan(path: Path) -> list[str]:
    violations: list[str] = []
    for target in TARGETS:
        p = REPO / target
        if not p.exists():
            continue
        for f in _iter_files(p):
            try:
                content = f.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            if any(marker in content for marker in ALLOW_MARKERS):
                continue
            for lineno, line in enumerate(content.splitlines(), start=1):
                if any(ch in line for ch in BAD):
                    violations.append(f"{f.relative_to(REPO)}:{lineno}: {line.strip()[:80]}")
    return violations


def _iter_files(p: Path):
    if p.is_file():
        yield p
    else:
        for ext in ("*.md", "*.tsx", "*.ts", "*.py"):
            for f in p.rglob(ext):
                if any(seg in f.parts for seg in ("node_modules", ".next", ".venv")):
                    continue
                yield f


if __name__ == "__main__":
    v = scan(REPO)
    if v:
        print("FAIL: dashes found:")
        for line in v[:40]:
            print(" ", line)
        sys.exit(1)
    print("OK: no em-dashes in user-facing files.")
