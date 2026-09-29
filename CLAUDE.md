# CLAUDE.md

Project: **Underdog**, a prospecting agent for Amazon growth agencies that learns from outreach outcomes using Hindsight agent memory. The full specification is `docs/SPEC.md`. It is the source of truth; read the relevant section before starting any task.

## Non-negotiables

1. **Hindsight memory is the product.** Every feature must make memory central and visible. If a feature works equally well without memory, it is low priority.
2. **Numbers in code, memory in Hindsight, words from the LLM.** Signals, diagnoses and scores are computed deterministically in Python. The LLM only explains and writes. Never let an LLM produce a number the app relies on.
3. **All Hindsight calls go through `backend/app/memory/service.py`.** No other module imports `hindsight_client`.
4. **All LLM calls go through `backend/app/llm/client.py`**, with Pydantic schema validation, one repair retry, fallback model, then a deterministic template. The demo must never crash because of an LLM.
5. **Never show real brand names.** Only anonymised aliases appear in the UI, fixtures, screenshots, logs and seed data. `brand_alias.csv` is gitignored.
6. **The agent never reads `sim/ground_truth.yaml`.** Only the simulator and the eval harness may load it.
7. **Simulated clock:** pass the simulated date as `timestamp` on every retain and as `query_timestamp` on recall; state it in the text of every reflect query.
8. **No em dashes** in any user-facing copy, email drafts, README or generated content.
9. **Secrets only from environment variables.** Never commit keys. Keep `.env.example` current.

## Verify, do not assume

- The Hindsight method names and parameters in the spec come from the v0.10 docs. Before writing MemoryService, check the installed `hindsight-client` package (inspect signatures) and https://hindsight.vectorize.io/ and adapt. Record any differences in `docs/DECISIONS.md`.
- Check dataset column names by loading a small sample before writing transforms.

## Working style

- Work in the phases defined in the kickoff plan. Finish one phase, run its checks, commit, then summarise what changed and what is next.
- Write tests alongside code (pytest). Keep them fast. Mark tests that hit real APIs with `@pytest.mark.integration`.
- Prefer small, readable modules with type hints. No dead code, no placeholder TODOs left in finished phases.
- Log every Hindsight call (operation, latency, short summary) to the `memory_event` table so the UI memory feed can show it.
- When a spec detail is ambiguous, choose the simplest option that keeps memory central, note it in `docs/DECISIONS.md`, and continue.

## Commands (keep this section updated)

- `make data`   download and prepare real data
- `make sim`    generate simulated snapshots and outcomes
- `make seed`   build the Hindsight seed bank (weeks 1 to 8)
- `make eval`   run memory on / off / oracle evaluation
- `make dev`    run backend and frontend locally
- `make test`   run unit tests
