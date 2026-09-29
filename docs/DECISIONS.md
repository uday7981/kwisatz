# DECISIONS

Running log of choices that differ from `docs/SPEC.md` or resolve spec ambiguity. Each
entry: date, decision, reason, alternatives considered.

---

## 2026-09-29 · D-001 Build in place at `kwisatz/`; do not rename the parent directory

**Decision.** Build Underdog inside the existing `/Users/udaykiran/hyd-hack/kwisatz/`
directory. Keep SPEC §6.3 tree (`backend/`, `frontend/`, `sim/`, `scripts/`, `data/`) but
do not rename the containing directory to `underdog/`.

**Reason.** The git root turned out to be `$HOME` (`/Users/udaykiran`), not the hackathon
folder. `git mv kwisatz underdog` at that level would touch every path under `$HOME`
tracked in that repo — many files unrelated to this project. The physical directory name
is not user-visible in the shipped product; SPEC §6.3 shows a repo *shape*, not a
required parent name.

**Alternatives.**
1. Rename via `git mv` at `$HOME`. Rejected — too broad blast radius.
2. Rename inside a subfolder `kwisatz/underdog/`. Rejected — deeper nesting for no gain.

**Follow-up.** When publishing to GitHub for submission, we will `git init` a fresh
dedicated repo at `kwisatz/` and name the remote `underdog`. Documented in Phase 6.

---

## 2026-09-29 · D-002 Pin Python 3.12; system `python3` (3.14) unusable

**Decision.** `pyproject.toml` requires Python `>=3.12,<3.13`. `.python-version` pins
`3.12`. All dev commands go through the `.venv` created from `/opt/homebrew/bin/python3.12`.

**Reason.** `pip index versions hindsight-client` under 3.14 returns `No matching
distribution`; under 3.12 returns `0.10.1` and back. Polars, `datasets`, and several other
deps also lack 3.14 wheels today (Jan 2026 tooling still catching up).

---

## 2026-09-29 · D-003 Hindsight SDK signature reality (v0.10.1)

Verified by `inspect.signature` on installed `hindsight-client==0.10.1`. `MemoryService`
is the only importer.

| SPEC §6.5 call | Actual v0.10.1 (sync helper on `Hindsight`) |
| --- | --- |
| `create_bank(bank_id, name, mission, disposition)` | `create_bank(bank_id, name=None, mission=None, disposition_skepticism=None, disposition_literalism=None, disposition_empathy=None, disposition=None, retain_mission=None, retain_extraction_mode=None, retain_custom_instructions=None, retain_chunk_size=..., enable_observations=None, observations_mission=None, enable_text_search=None, enable_temporal_retrieval=None, enable_graph_retrieval=None, enable_reranking=None, reflect_mission=None, background=None) -> BankProfileResponse`. Missions can be set at creation. |
| `update_bank_config(...)` | Exists exactly: `update_bank_config(bank_id, *, reflect_mission=None, retain_mission=None, observations_mission=None, entity_labels=None, memory_defense=None, disposition_skepticism=None, ...)`. Returns `dict`. **SPEC drift is nil.** |
| `create_directive` | `create_directive(bank_id, name, content, priority=0, is_active=True, tags=None)` — one call per rule. |
| `retain_batch` | `retain_batch(bank_id, items, document_id=None, document_tags=None, retain_async=False, operation_id=None) -> RetainResponse`. Each item dict supports `content, context, timestamp, document_id, tags, observation_scopes, metadata, entities, resolve_entities, update_mode`. |
| `recall` | Sync helper covers all fields we need: `recall(bank_id, query, types=None, max_tokens=4096, budget='mid', trace=False, query_timestamp=None, include_entities=False, include_chunks=False, include_source_facts=False, tags=None, tags_match='any', tag_groups=None, prefer_observations=False, min_scores=None, temporal_window=None) -> RecallResponse`. `query_timestamp` accepted directly — no async wrap needed. |
| `reflect` | Sync helper: `reflect(bank_id, query, budget='low', context=None, max_tokens=None, response_schema=None, tags=None, tags_match='any', include_facts=False, include_tool_calls=False, include_tool_call_output=True, tag_groups=None, apply_all_directives=False, fact_types=None, exclude_mental_models=False, exclude_mental_model_ids=None, ...) -> ReflectResponse`. **No `query_timestamp`** — state the simulated date inline in the query. |
| `create_mental_model` | `create_mental_model(bank_id, name, source_query, tags=None, max_tokens=None, trigger=None, id=None)`. |
| `get_mental_model_history` | Sync helper exists: `get_mental_model_history(bank_id, mental_model_id)`. |
| Bank clone | `clone_bank(bank_id, target_bank_id, *, include_data=True, include_bank_config=True, include_history=False) -> str` — returns `operation_id`. Sync. No asyncio wrap needed. |
| `observation_scopes` per-memory | Per-item values on retain_batch items: `"combined"` (default), `"shared"`, `"per_tag"`, `"all_combinations"`, or explicit list-of-lists. Never pass `[]` — silently degrades to `combined`. |

**Effect on plan.** `MemoryService` stays fully sync — no `asyncio.run` needed anywhere.
Bank config can be pushed either at `create_bank` time or via `update_bank_config`; we
prefer `create_bank(retain_mission=..., observations_mission=..., reflect_mission=...)`
in one call.

**Simulated-clock caveat still applies.** `recall` accepts `query_timestamp`;
`reflect` does not — `MemoryService.prioritise(...)` and `extract_beliefs(...)` prepend
`"Today is {sim_date} (week {week} of the season)."` to every reflect query.

---

## 2026-09-29 · D-004 Amazon Reviews 2023: timestamp is Unix milliseconds

**Decision.** `scripts/load_real_data.py` divides `timestamp` by 1000 during parquet
write so downstream code treats them as seconds (or converts to `datetime`).

**Reason.** Verified from real data pull:
`timestamp=1675529329744` → `2023-02-04T16:48:49Z`. SPEC snippets treat it as generic
epoch time without specifying unit.

**Also confirmed.** The HuggingFace repo stores files as plain `.jsonl` (not `.jsonl.gz`)
under `raw/meta_categories/meta_{Category}.jsonl` and
`raw/review_categories/{Category}.jsonl`. Each category meta is ~200 MB – 12 GB; reviews
are similar size. Streaming is mandatory.

---

## 2026-09-29 · D-005 Deploy targets and Hindsight environments

**Decision.**
- Frontend: **Vercel**.
- Backend: **Fly.io** (persistent instance, `fly.toml` in Phase 6).
- Hindsight: **Cloud** for seed bank + rehearsal + submission (funded by MEMHACK99);
  **Docker (local)** as fallback for offline iteration.

**Reason.** Vercel is the path of least resistance for Next.js App Router. Fly.io keeps
SSE working without proxy weirdness and avoids cold starts that Render's free tier
suffers from. Hindsight Cloud is required for judges to touch a live URL; Docker keeps
inner-loop iteration free.

**Env switch.** `HINDSIGHT_URL` chooses; `HINDSIGHT_API_KEY` empty means local Docker
default.

---

## 2026-09-29 · D-006 Categories, seed, and reset flow

- **Categories loaded:** `Home_and_Kitchen`, `Pet_Supplies`, `Health_and_Household`.
  ~60 brands per category = ~180 total.
- **Simulator seed:** `SIM_SEED=42`, published in README.
- **Bank naming:** live agency bank `underdog-lanternfish`; seed bank `underdog-seed-w8`.
- **Reset flow:** `POST /api/demo/reset?to_week=8` calls
  `aclone_bank("underdog-seed-w8", "underdog-lanternfish")`, polls the operation, then
  wipes the SQLite `lead`/`pitch`/`outcome`/`belief_snapshot` rows for week ≥ 9.

---

## 2026-09-29 · D-007 Node/Frontend versions

- Node.js 22.20.0 (nvm) — good for Next.js 15.
- Next.js 15 App Router, TypeScript strict, Tailwind CSS v4, shadcn/ui, Recharts, Framer
  Motion, TanStack Query — exactly SPEC §4.7.

---

## 2026-09-29 · D-008 Data pull caps for the demo dataset

**Decision.** For demo prep we run `make data` with `UNDERDOG_MAX_META=15000` and
`UNDERDOG_MAX_REVIEWS=80000` (defaults are 200k / 5M). This gives roughly 60 brands per
category (180 total) with enough per-brand review activity to seed the simulator's
velocity anchor.

**Reason.** With the full stream, meta+reviews for the three categories take 40+ minutes
and the review keep-rate against a 15k parent_asin subset is only ~4-6%, so 200k kept
requires scanning ~4M lines. The tighter caps still yield real brand aggregates and
sufficient sim behaviour, at ~2 minutes per category.

**Follow-up.** For final submission, run once with defaults for a richer review velocity
signal. The env vars are documented in the README.

---

## 2026-09-29 · D-009 Retain `operation_id` must be a UUID

**Decision.** All `retain_batch` calls pass `operation_id` as a stable UUID5 derived
from a deterministic key (`_stable_op_id` in `memory/service.py`), not a human-readable
string.

**Reason.** The Hindsight API validator rejects non-UUID operation_ids with HTTP 422
(`operation_id must be a valid UUID`), even though the docs describe it as an
"idempotency key" of type string. Using a UUID5 with a fixed namespace keeps the
idempotency behaviour (same input → same op id) while satisfying the validator.

**File.** `backend/app/memory/service.py:_stable_op_id`.

---

## 2026-09-29 · D-010 Clone is a background operation; poll before use

**Decision.** `MemoryService.reset_from_seed(..., wait=True)` polls `list_memories`
on the target bank every 3s (up to 120s) and returns once the clone becomes visible.
`scripts/seed_bank.py` now calls it with `wait=True` before exiting.

**Reason.** `clone_bank` returns an `operation_id` and runs in the background on the
Hindsight side. Immediately calling `list_memories` returns 404 for tens of seconds
after the API call. Without polling, downstream steps (eval, live demo reset) touch an
empty bank and appear indistinguishable from memory-off.

**Follow-up.** Consolidation of retained memories into observations happens
independently after the clone becomes visible. Reflect calls made immediately after a
clone may still see raw facts without consolidated observations for another 60-120s;
the demo script accounts for this by running the belief-card animation only after
`GET /api/beliefs` returns a non-empty set.

---

## 2026-09-29 · D-011 Demo pivot to week 44; loosen diagnosis rules; widen seed

Three linked decisions taken while the first end-to-end eval showed memory-on == memory-off:

**a. Demo starts at week 44, not week 8.**
The eval harness always used weeks 41-52, but the UI defaulted to week 8. At week 8
the simulator has not yet hit the reseller-invasion shock (week 38+), so no diagnosis
fires and every brand defaults to `growth_partnership`. This made memory-off look
uniform and gave memory-on nothing to learn from. All API and frontend defaults now
point at week 44. `POST /api/demo/reset?to_week=44`.

**b. Diagnosis rules trigger on persistent state, not just fresh shocks.**
Original D1 required `buybox_share_prev_30d >= 0.90` (a fresh shock signature). By
demo weeks the shock has plateaued so this never fired. Rules now also fire on
persistent invasion (`seller_count >= 4 and buybox_share_30d < 0.70`), and D2/D4/D5
were relaxed similarly. Effect: at week 41 the reseller_invasion archetype detects
100% (was 0-5%), and memory-off angle accuracy jumps from ~10% to ~79%.

**c. Seed all brands, 20 pitches per week, weeks 20-40.**
The first re-seed only covered the top-30 brands alphabetically; only 2 of the 21
demo-relevant brands were in memory. Now `SEED_LIMIT_BRANDS=0` (all) and
`SEED_PITCHES_PER_WEEK=20`, seeding weeks 20-40 (SEED_WEEK_START/END). Outcome
generation extended in `sim/outcomes.py` from just the demo window to all 52 weeks
(`OUTCOME_WEEK_START=1`, `OUTCOME_WEEK_END=52`) so seed weeks 20-40 have real
outcomes to retain.

**Result.** Memory-on now beats memory-off by ~4 points reply / ~3 points meeting
season-average (weekly high +30 points reply, +20 meeting on week 43).
