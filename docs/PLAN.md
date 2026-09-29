# Underdog — Build Plan

> Approved 2026-09-29. Live source of truth for phased execution. Deltas to SPEC live in `docs/DECISIONS.md`.

## Context

We are building **Underdog** (see `docs/SPEC.md`), a prospecting agent for Amazon growth
agencies that learns from outreach outcomes using Hindsight agent memory. The judging bar
is Innovation (30%), Hindsight use (25%), Technical (20%), UX (15%), Impact (10%).
Non-negotiable per `CLAUDE.md`: Hindsight is the product, numbers in code / memory in
Hindsight / words from LLM, all Hindsight calls go through `backend/app/memory/service.py`,
and `sim/ground_truth.yaml` is invisible to the agent.

---

## 1. Environment inspection

| Check | Result | Action |
| --- | --- | --- |
| `python3` | 3.14.6 (Homebrew) | Do **not** use — no wheels for hindsight-client, polars, etc. |
| `python3.12` | 3.12 installed at `/opt/homebrew/bin/python3.12` | **Use this** for backend venv |
| `node` | v22.20.0 (nvm), npm 10.9.3 | Fine for Next.js 15 |
| `hindsight-client` on PyPI | latest `0.10.1` (only via Py 3.12 index; Py 3.14 has no wheels) | Pin `hindsight-client==0.10.1` |
| `groq`, `polars`, `datasets`, `sqlmodel` | All available on Py 3.12 | Standard install |
| `.env` at repo root | Already has `HINDSIGHT_API_KEY`, `HINDSIGHT_URL`, `GROQ_API_KEY` | Do not commit; add `.env.example` |
| Local skill `hindsight-docs` | Present at `.agents/skills/hindsight-docs/` (v0.10 SDK docs, openapi.json) | Read from here instead of web fetches |

## 2. Hindsight SDK reality check (vs SPEC §6.5)

Verified against `.agents/skills/hindsight-docs/references/sdks/python.md` and
`references/developer/api/{retain,memory-banks,mental-models,reflect,recall}.md`. Key
differences to codify in `docs/DECISIONS.md`:

| SPEC §6.5 assumption | Actual `hindsight-client` v0.10.1 | Adjustment |
| --- | --- | --- |
| `hs.create_bank(bank_id, name, mission, disposition)` | Matches. Sync helper. | None. |
| `hs.update_bank_config(..., retain_mission=, observations_mission=, reflect_mission=)` | **No sync helper of that exact name.** Config is set via `client.update_bank(...)` sync helper (see docs tool list line 370 of api/memory-banks.md) or `PATCH /v1/default/banks/{bank_id}` (fields `retain_mission`, `observations_mission`, `reflect_mission`, plus extraction/observation toggles). | Wrap it as `MemoryService.configure_bank(...)` calling the correct helper. Verify the actual sync method name by `dir(client)` when the venv is up. |
| `hs.create_directive(...)` list of rule strings | Sync helper is `client.create_directive(bank_id, name, content)` — one directive per call, each with a name + content string. Directives can carry `tags` for scoping. | Create one directive per rule in `bank_setup.py`; store the returned ids for later reference. |
| `hs.retain(...)` with per-call `tags`, `observation_scopes`, `metadata` | Simple `retain(bank_id, content, context, timestamp, document_id, metadata, retain_async)` exposes tags via kwargs but the safer path is `retain_batch` where each item accepts `tags`, `observation_scopes`, `metadata`, `document_id`. | Route every write through `retain_batch` (even single items) so scopes/tags travel per-memory. |
| `retain_batch(items=[...], retain_async=True)` + `operation_id` for idempotency | Confirmed. Endpoint: `POST /v1/default/banks/{bank}/memories` with `async` and `operation_id`. | Use it as spec'd; make `operation_id` stable per (week, kind). |
| `hs.reflect(response_schema=..., include_facts=True)` returns `structured_output` + `based_on.memories` | Confirmed via reflect.md and openapi.json. Also accepts `budget`, `tags`, `tags_match`, `exclude_mental_models`, `fact_types`. | Pass `response_schema=Model.model_json_schema()`; parse with `Model.model_validate(resp.structured_output)`. Include `include.facts=True` (or the equivalent structured include object) so we can render memory chips. |
| `hs.recall(..., tags_match="any", query_timestamp=..., include_source_facts=True)` | Endpoint supports `tags`, `tags_match`, `tag_groups`, `temporal_window`, `include.chunks`, `include.source_facts`. Sync helper covers common cases; use async namespace `client.memory.recall` for full body if needed. | Wrap into `MemoryService.recall(...)` with typed kwargs; always pass `query_timestamp` set to the simulated date. |
| `hs.create_mental_model(bank_id, id=..., name=..., source_query=..., trigger=...)` | Available via async namespace `client.mental_models.create_mental_model(...)` (also sync `client.create_mental_model` per SDK). Accepts `id, name, source_query, tags, trigger, max_tokens`. Trigger fields: `mode` (`delta`|`full`), `refresh_after_consolidation`, `min_refresh_interval_seconds`, cron. | Use the sync helper for setup; live in async namespace only if needed. Pass `trigger={"mode":"delta","refresh_after_consolidation":true,"min_refresh_interval_seconds":120}` per SPEC. |
| `hs.get_mental_model_history(...)` | Endpoint `GET .../mental-models/{id}/history` — accessible via `client.mental_models` async namespace. | Call `await client.mental_models.get_mental_model_history(bank_id, model_id)` in an async wrapper. |
| Bank clone by `hs.clone_bank(...)` | Actual: `await client.aclone_bank(source_bank_id, target_bank_id)` (**async only** in the helper set). Endpoint: `POST /v1/default/banks/{bank}/clone?target_bank_id=...`, returns `operation_id`; poll operations. | `MemoryService.reset_from_seed()` will use `aclone_bank` inside an `asyncio.run(...)` block and poll the operation. |
| `observation_scopes` per-memory | Docs confirm per-item `observation_scopes` in retain batches: `"combined"` (default), `"shared"`, `"per_tag"`, `"all_combinations"`, or explicit `[[tag,...], ...]`. **Warning:** empty `[]` silently means "combined" — must use `"shared"` or `[[]]`. | Use explicit custom lists per SPEC (`[[dx], [angle], [dx, angle], [cat]`, plus `[brand]` for brand rows). Never pass `[]`. |

**Simulated clock reminder:** the `reflect` endpoint has **no** `query_timestamp` — the
simulated date must be stated inline in the query text. `recall` does take `query_timestamp`.

## 3. Real dataset confirmation (Amazon Reviews 2023)

Verified via ranged GET against
`https://huggingface.co/datasets/McAuley-Lab/Amazon-Reviews-2023/resolve/main/raw/meta_categories/meta_Pet_Supplies.jsonl`
and `.../raw/review_categories/Pet_Supplies.jsonl` (each ~1.57 GB, plain `.jsonl`, not `.gz`;
served over HTTP with byte ranges).

**Meta fields (raw_meta_Pet_Supplies, first record):**
`average_rating, bought_together, categories, description, details, features, images, main_category, parent_asin, price, rating_number, store, title, videos`.
Example: `store="Hurtta"`, `main_category="Pet Supplies"`, `price=24.95`,
`average_rating=4.4`, `rating_number=166`, `parent_asin="B00XJG2SLG"`.

**Review fields (raw_review_Pet_Supplies):**
`asin, helpful_vote, images, parent_asin, rating, text, timestamp, title, user_id, verified_purchase`.
Example: `rating=4.0`, `verified_purchase=True`, `timestamp=1675529329744`.

**Important gotcha:** `timestamp` is **Unix milliseconds**, not seconds
(`1675529329744` → `2023-02-04T16:48:49Z`). SPEC snippets treat it as generic `timestamp`;
loader must divide by 1000.

**Path shape differs from SPEC snippet:** SPEC's `load_dataset(..., f"raw_meta_{cat}",
streaming=True, trust_remote_code=True)` still works, but the direct URL is
`raw/meta_categories/meta_{Category}.jsonl` and `raw/review_categories/{Category}.jsonl` —
**not** `{cat}_meta` as some snippets suggest. Use the datasets library streaming API to
avoid manual range logic.

## 4. Build plan — six phases

Each phase ends with a runnable acceptance check. Phase 6 is polish only; earlier phases
must not slip into it.

### Phase 1 — Repo rename + real data pipeline (Day 1)

**Rename first:** `git mv` `kwisatz/*` under a fresh `underdog/` directory (or rename the working
tree in place if the hackathon repo is the whole `hyd-hack/kwisatz/`). Update `CLAUDE.md`
project name references, `.env` path, and any absolute paths in scripts. Verify with
`git status` clean and re-run `pytest -q` (no tests yet → 0 collected).

**Files to create**
- `pyproject.toml` (Python 3.12, hindsight-client==0.10.1, groq, polars, pyarrow, datasets, sqlmodel, fastapi, pydantic v2, httpx, pytest, hypothesis, ruff, mypy)
- `Makefile` (`make data`, `make sim`, `make seed`, `make eval`, `make dev`, `make test`)
- `.env.example` mirroring the private `.env` keys
- `.gitignore` (adds `data/raw/`, `brand_alias.csv`, `.env`)
- `scripts/load_real_data.py` — streams 3 categories (`Home_and_Kitchen`, `Pet_Supplies`, `Health_and_Household`) via `datasets` in streaming mode; writes `data/raw/{cat}_meta.parquet` and `data/raw/{cat}_reviews.parquet` chunked; divides timestamp by 1000 during write; keeps only fields we need (spec §5.3)
- `scripts/select_brands.py` — brand selection per SPEC §5.4 (3–40 products, 50–5000 ratings, ≥20% velocity growth last 6mo vs prior 6mo); stratified sample 60/category = 180 total
- `scripts/anonymise.py` — Faker-based deterministic alias generator; writes `brand_alias.csv` (gitignored) and `data/prepared/brands.parquet`, `data/prepared/products.parquet`, `data/prepared/review_velocity.parquet`
- `backend/app/models.py` — SQLModel tables per SPEC §6.4 (brand, product, snapshot, brand_signal, diagnosis, lead, pitch, outcome, belief_snapshot, memory_event, sim_clock)
- `backend/app/config.py` — pydantic-settings loader for env

**Acceptance checks**
- `make data` runs end-to-end offline of Hindsight/Groq. Produces `data/prepared/brands.parquet` with ≈150–200 rows (target 180) and correct alias mapping.
- `python -m scripts.spot_check` prints 10 random brands with real category, size, price range → visually sane.
- Unit tests: `pytest backend/tests/test_selection.py` covers filter edges (`ratings=49`, `ratings=5001`, exactly 3 products, growth threshold).

**Risks**
- HuggingFace throttles first-run download → mitigate with `datasets` cache + resumable streaming; document a "slim mode" (Pet_Supplies only) for CI.
- Home_and_Kitchen meta file is 12 GB → require streaming, never full download.
- Row loss from missing `store` / empty categories → tests enforce ≥90% keep rate after cleanup.

### Phase 2 — Simulator, signals, diagnoses, memory-off loop (Day 2)

**Files to create**
- `sim/ground_truth.yaml` — hidden rules per SPEC §5.6 (angle_fit, category_modifier, size_sweet_spot, severity_effect, noise, delays)
- `sim/simulator.py` — deterministic, seeded; generates 52 weeks of snapshots per product per SPEC archetype shares (reseller_invasion 20%, stockout 15%, weak_converter 15%, price_erosion 10%, under_advertised 15%, healthy 15%, distractor 10%); writes `data/sim/snapshots.parquet`
- `sim/outcomes.py` — samples reply/meeting/signed outcomes from `ground_truth.yaml` for the 12 demo weeks; delays 1–3 weeks; templated reply texts stored in `data/sim/reply_texts.parquet`
- `backend/app/adapters/base.py` — `MarketplaceAdapter` protocol
- `backend/app/adapters/simulated.py` — reads sim parquets
- `backend/app/adapters/keepa.py` — stub raising `NotImplementedError` with the correct interface (documented)
- `backend/app/engine/signals.py` — deterministic per SPEC §6.6 (velocity, velocity_growth, seller_delta_30d, buybox_share_30d, oos_episodes_60d, price_change_90d, ad_presence, rating_gap)
- `backend/app/engine/diagnosis.py` — six rules D1–D6, severity computation
- `backend/app/engine/scoring.py` — base score formula and clamp
- `backend/app/engine/loop.py` — `run_week(week, mode)` skeleton; `mode="off"` path works end-to-end without touching Hindsight
- `backend/app/eval/harness.py` — runs 12-week season with `mode ∈ {off, oracle}` first (memory=on stubbed until Phase 3); writes `eval/results.json` and PNGs
- `scripts/build_sim.py`, `scripts/run_eval.py`

**Acceptance checks**
- `make sim` produces `data/sim/snapshots.parquet` (≈180 × 52 rows minimum) and `outcomes.parquet`. Hypothesis property tests: buybox_share ∈ [0,1], price > 0, seeded runs identical hash.
- `make eval` (memory-off only mode) prints weekly reply/meeting rates; baseline is realistic (not accidentally near-oracle).
- Unit tests: reseller rule fires at exactly (+3 sellers AND buybox <75%), severity monotonic in signal excess, scoring bounded [0,1].

**Risks**
- Simulator too clean → judges suspect planted pattern. Mitigate with `noise: 0.15` and 10% distractors; report variance across 5 seeds.
- Category volume asymmetry (Home ~ 3.7M items) → sample cap at brand-selection stage before sim.

### Phase 3 — Memory layer (Day 3)

**Files to create**
- `backend/app/memory/service.py` — **the only** module importing `hindsight_client`. Class `MemoryService` with sync facade: `configure_bank()`, `retain_material_changes()`, `retain_pitch()`, `retain_outcome()`, `recall_for_lead()`, `prioritise(week, candidates)`, `extract_beliefs(week)`, `wait_for_consolidation(timeout=90)`, `reset_from_seed(target_bank)`. Each call logs a `memory_event` row.
- `backend/app/memory/formats.py` — retain content templates (SPEC §6.5 examples), tag builders (`brand:<slug>`, `cat:<cat>`, `dx:<code>`, `angle:<angle>`, `kind:<type>`), document_id builders, per-item `observation_scopes` builder (custom lists — never `[]`).
- `backend/app/memory/bank_setup.py` — creates the bank, sets missions via `update_bank`, creates the six directives (SPEC §6.5), creates the five mental models (`real-icp`, `angles-that-work`, `avoid`, `revisit`, `my-mistakes`) with `trigger={"mode":"delta","refresh_after_consolidation":true,"min_refresh_interval_seconds":120}`, enables Memory Defense (redaction + prompt_injection blocking) per SPEC §6.11.
- `backend/app/memory/schemas.py` — `LeadAdjustment`, `PrioritisationResult`, `Belief`, `BeliefSet` (SPEC §6.5)
- `scripts/seed_bank.py` — runs weeks 1–8 via `MemoryService` against `underdog-seed-w8`; ends by cloning into `underdog-lanternfish` for a clean starting demo state
- `backend/app/eval/oracle.py` — reads `ground_truth.yaml` and produces oracle rankings (only for eval)
- Complete `loop.py` for `mode="on"`: retain material changes, call `prioritise`, apply adjustments, retain pitches, retain outcomes, extract beliefs, diff against prior week

**Acceptance checks**
- Integration test against **local Hindsight Docker** (spun up in test fixture): retain → wait → recall round-trips the fact; idempotent document_id verified.
- `make seed` completes without unhandled exceptions; produces `underdog-seed-w8` bank with expected memory counts (≈300–500 by week 8) and at least 2 populated mental models.
- `make eval` (with all three modes now) shows memory-on beating memory-off on top-10 meeting rate by ≥5 points across 3 seeds by week 10.
- Unit tests: schemas round-trip; observation_scope builder never returns `[]`; document_ids are collision-free across the seeded season.

**Risks**
- `update_bank_config` signature differs across client versions → inspect at implementation time; write a thin `client_shim.py` if needed and note in `docs/DECISIONS.md`.
- Consolidation lag on cloud → `wait_for_consolidation` polls the operations endpoint (SPEC §6.10) with 90 s timeout and shows "learning" UI state on timeout instead of crashing.
- Hindsight credit burn during seeding → seed once and clone for each demo reset (`aclone_bank`); do not seed live during rehearsal.

### Phase 4 — API and LLM layer (Day 4)

**Files to create**
- `backend/app/main.py` — FastAPI app, CORS locked to frontend origin, shared-secret header
- `backend/app/api/{week,leads,brands,beliefs,metrics,feed}.py` — every endpoint in SPEC §6.7
- `backend/app/llm/client.py` — Groq wrapper: primary `openai/gpt-oss-120b`, fallback `qwen/qwen3-32b`, JSON mode, pydantic validation, one repair retry, exponential backoff on 429/5xx, 20 s timeout, deterministic template fallback (SPEC §6.8). Input-hash caching in `data/cache/llm/`.
- `backend/app/llm/prompts.py` — Appendix A templates; post-check for `<120 words`, no em dashes, includes ≥1 numeric signal, opt-out line, no historical client names
- `backend/app/schemas.py` — Pydantic request/response models
- `backend/app/api/feed.py` — SSE endpoint reading from `memory_event` table; MemoryService pushes new rows via an in-process pub/sub
- Edge-case coverage per SPEC §6.9 (all 11 rows): reflect-500 fallback banner, structured_output error retry, do-not-contact filter, prompt-injection retention as quoted data, memory-off auto mode when Hindsight unreachable

**Acceptance checks**
- Playwright-style API smoke via httpx: every endpoint returns 200 with real week-8 data.
- Failure injection: kill Hindsight base URL → `GET /api/shortlist` returns memory-off ranking with a banner flag; kill Groq → drafts fall back to templates. Neither returns 500.
- Cached LLM responses persist; second identical call is <20 ms.
- `pytest -m "not integration"` full suite green in <60 s.

**Risks**
- Groq JSON mode occasional schema drift → repair prompt with concrete `ValidationError`; test with recorded malformed fixtures.
- SSE breakage behind Vercel/Render proxies → local demo runs backend direct; if deployed, use polling fallback.

### Phase 5 — Frontend (Day 5)

**Files to create** (Next.js 15 App Router in `frontend/`)
- Design tokens: `styles/tokens.css` (SPEC §4.2), `tailwind.config.ts` reading them
- Fonts via `next/font/google`: Bricolage Grotesque + IBM Plex Sans
- Routes: `/` (This week / Shortlist), `/brands/[id]` (Dossier), `/outreach`, `/learned`, `/learning`
- Components (SPEC §4.7): `WeekHeader`, `ShortlistTable`, `LeadRow`, `MemoryChip`, `SeverityBar`, `Sparkline`, `LeadDrawer`, `SignalChart`, `DraftEditor`, `BeliefCard`, `BeliefDiff` (the signature 600 ms animation), `LearningChart`, `SkipTray`, `OutcomeButtons`, `ReplayBar`, `MemoryToggle`, `MemoryFeed`
- Data layer: TanStack Query; per-week cache keyed by `(week, mode)`; SSE hook for memory feed
- Keyboard shortcuts (J/K/Enter/A/1–6/M/[/]); focus rings; reduced-motion fallback for belief-card animation
- One dev-only page `/replay` that drives the replay scrubber + memory toggle

**Acceptance checks**
- `make dev` starts backend + frontend; `http://localhost:3000` renders week 8 shortlist in <2 s (cached).
- Manual golden path: open lead drawer → see memory chips linking to real memories; approve draft; log a "Replied" outcome; advance week; belief card animates with new evidence count.
- Playwright smoke: shortlist renders, scrubber changes week, memory toggle splits view, revisit badge appears when appropriate.
- Lighthouse a11y ≥ 95 on `/` at 1440 px; every colour pair meets WCAG AA.

**Risks**
- Framer Motion + prefers-reduced-motion gaps → test both explicitly.
- Recharts styling churn → keep to one thin-line theme; direct labels; no gridline clutter.
- Belief-card timing feels off during live demo → back off animation to 500 ms if judges' network is slow.

### Phase 6 — Eval polish, README, demo, video (Day 6)

**Files to create**
- `eval/results.json`, `eval/results.png`, `eval/README.md` (methodology + variance across 5 seeds)
- `README.md` per SPEC §11 outline. **Section "How Hindsight is used"** links every feature → the exact `backend/app/memory/` line and cites the retain/recall/reflect docs.
- `docs/architecture.png` (auto-render via mermaid or hand-draw), `docs/eval-curve.png`, `docs/screenshots/*.png`
- `docs/DECISIONS.md` — running log; seeded with the Hindsight SDK deltas above and any others discovered during Phase 3
- `docker-compose.yml` — backend + optional local Hindsight image for offline dev
- Rehearsal notes: `demo.md` — the 3-minute script from SPEC §9 with exact keystrokes

**Acceptance checks**
- `make dev` on a fresh clone (only `.env` filled) reaches the demo path in <10 min including data + seed.
- Demo rehearsed 3× under 3 minutes each; the belief-card change lands live at ~1:40.
- Backup video recorded (2–5 min, 1080p, YouTube public) with no real brand names.
- Article draft (~1400 words) linted for banned words ("hackathon" not present anywhere including hashtags).

## 5. Cross-cutting invariants (enforced by tests / CI)

- `grep -R "hindsight_client" backend/app/` returns only `memory/service.py`.
- `grep -R "ground_truth" backend/app/` returns 0 matches (agent must not read it).
- No em dashes in `frontend/`, `backend/app/llm/prompts.py`, or any content file (script in CI).
- Every `retain*` call carries `timestamp` (simulated date) and stable `document_id`; every `recall*` carries `query_timestamp`; every `reflect` query includes the simulated date string.
- No real brand names: `pytest tests/test_alias_leak.py` scans generated draft fixtures against `brand_alias.csv`.

## 6. Critical files map

| Concern | File |
| --- | --- |
| Hindsight facade (only importer) | `backend/app/memory/service.py` |
| Bank/directives/mental-model setup | `backend/app/memory/bank_setup.py` |
| Retain templates + tags + scopes | `backend/app/memory/formats.py` |
| LLM wrapper w/ fallback | `backend/app/llm/client.py` |
| Deterministic signals & rules | `backend/app/engine/{signals,diagnosis,scoring}.py` |
| Weekly loop | `backend/app/engine/loop.py` |
| Simulator + hidden rules | `sim/simulator.py`, `sim/outcomes.py`, `sim/ground_truth.yaml` |
| Eval harness (on/off/oracle) | `backend/app/eval/harness.py` |
| Belief-card animation | `frontend/components/BeliefDiff.tsx` |

## 7. Resolved decisions and remaining defaults

**Confirmed by user:**
1. **Repo layout**: rename `kwisatz/` → `underdog/` to match SPEC §6.3. First step of Phase 1: `git mv` the existing tracked files, update the working directory, update `CLAUDE.md` path references.
2. **Hindsight env**: Cloud for seed + rehearsal (funded by MEMHACK99); Docker local for offline iteration. Wired through `HINDSIGHT_URL`.
3. **Categories**: 3 — Home_and_Kitchen + Pet_Supplies + Health_and_Household, ~180 brands total.
4. **Deploy**: Vercel (frontend) + Fly.io (backend); Hindsight Cloud.

**Remaining defaults (proceeding unless you object):**
5. Pin Python to 3.12.x via `pyproject.toml` / `.python-version`.
6. Frontend stack exactly as SPEC §4.7 (Next.js 15 App Router, Tailwind, shadcn/ui, Recharts, Framer Motion, TanStack Query).
7. `update_bank_config` → use `client.update_bank(...)` sync helper; log the SDK drift in `docs/DECISIONS.md`.
8. `aclone_bank` is async-only → wrap in `asyncio.run(...)` inside `MemoryService.reset_from_seed()`.
9. Seed weeks 1–8 into `underdog-seed-w8`, clone into `underdog-lanternfish` on `POST /api/demo/reset?to_week=8`, advance to w9 live.
10. `SIM_SEED=42`; publish it in the README so results reproduce.

## 8. What I will NOT do without a green light

- Send real emails (Gmail integration stays a stub / manual approval only).
- Query live Amazon or Keepa data (adapter stub is the path-to-production story).
- Add auth / multi-tenancy beyond the shared-secret header.
- Any UI feature outside SPEC §4 (no dark-mode polish, no theming controls).

## 9. Verification (end-to-end)

After Phase 6:
1. `git clean -xdf && cp .env.example .env && $EDITOR .env` (fill keys) → `make data && make sim && make seed && make eval && make dev`.
2. Browser at `http://localhost:3000`, run through the SPEC §9 demo script; watch a belief card change live between week 8 → 9.
3. `curl http://localhost:8000/api/metrics/learning` → JSON shows memory-on > memory-off across seeds.
4. `pytest -q` green including the alias-leak, em-dash, and reflect-timestamp lint tests.

---

**Next step:** on your approval, I will (a) copy this plan to `docs/PLAN.md`, (b) start Phase 1
(pyproject, Makefile, data loader), and (c) open `docs/DECISIONS.md` with the SDK deltas from
§2 above.
