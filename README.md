# Underdog

> The prospecting agent that learns which Amazon brands say yes. Built on [Hindsight](https://github.com/vectorize-io/hindsight) agent memory.

**Marketplace data shows you every brand. Underdog remembers which ones say yes.**

Underdog is a weekly workflow for Amazon growth agencies. Each week it:

1. **Observes**: reads public marketplace signals (reseller counts, Buy Box share, review velocity, price, stock, ad presence) for a watched set of brands.
2. **Diagnoses**: applies deterministic rules to classify what is actually wrong (reseller invasion, stockout-prone, weak converter, price erosion, under-advertised riser, or healthy).
3. **Prioritises**: combines a base score with what Hindsight has learned from past outcomes.
4. **Pitches**: drafts an email using the angle memory recommends, cites specific numbers from the brand's own data, and asks for approval.
5. **Learns**: when outcomes arrive they retain to memory, consolidate into observations, and refresh the belief cards the agent shows.

## How Hindsight is used

Every Hindsight call goes through `backend/app/memory/service.py` (grep-enforced). The rest of the code never imports the client. Map:

| Feature | Hindsight operation | File |
| --- | --- | --- |
| Bank + directives + mental-model setup | `create_bank`, `update_bank_config`, `create_directive`, `create_mental_model` | `backend/app/memory/bank_setup.py` |
| Retain material changes each week | `retain_batch` with per-item `tags` + `observation_scopes` + stable `document_id` | `MemoryService.retain_material_changes` |
| Retain a pitch (agent's own action) | `retain_batch` (single item), tags include `angle:*`, scope includes `[dx, angle]` | `MemoryService.retain_pitch` |
| Retain an outcome | `retain_batch`, tags add `outcome:reply` / `outcome:signed` / etc. | `MemoryService.retain_outcome` |
| Lead drawer "What memory says" | `recall` with `query_timestamp` = simulated date and `tags=[brand:*]` | `MemoryService.recall_for_lead` |
| Weekly prioritisation (structured) | `reflect` with `response_schema=PrioritisationResult.model_json_schema()`, `include_facts=True` | `MemoryService.prioritise` |
| Belief cards (structured) | `reflect` with `response_schema=BeliefSet.model_json_schema()`, budget=`high` | `MemoryService.extract_beliefs` |
| Mental models (living pages) | `create_mental_model` on setup, `get_mental_model_history` for the "was X in week 4" line | `bank_setup.py`, `service.py` |
| Reset a demo to week 44 instantly | `clone_bank(seed_bank_id, target_bank_id)` | `MemoryService.reset_from_seed` |
| Directives (hard rules on reflect) | `create_directive`. See `DIRECTIVES` in `bank_setup.py` | `backend/app/memory/bank_setup.py` |

Prompts and simulated clock invariants:

- Every `retain` carries the simulated `timestamp` and a stable `document_id`, so re-runs are idempotent.
- Every `recall` carries `query_timestamp = simulated_date`, so temporal ranking works against the demo clock.
- `reflect` has no `query_timestamp` parameter, so we always prepend `"Today is {sim_date} (week {week} of the season)."` to the query.
- Every retain item passes an explicit non-empty `observation_scopes` list of lists. Never `[]` (which would silently mean "combined").

## Numbers in code, memory in Hindsight, words from the LLM

- Signals, diagnosis rules, base score, angle mapping: Python, deterministic, tested.
- Hindsight holds every brand memory, pitch, outcome, and the beliefs consolidated from them.
- Groq drafts the emails and returns validated JSON for the priority adjustments and belief cards. Every LLM call has schema validation + one repair retry + a fallback model + a deterministic template.

## Data

- Product catalogue, prices, ratings, and review timelines come from the public [Amazon Reviews 2023](https://huggingface.co/datasets/McAuley-Lab/Amazon-Reviews-2023) dataset (McAuley Lab, UCSD). We stream three categories: Home_and_Kitchen, Pet_Supplies, Health_and_Household.
- Marketplace dynamics (seller counts, Buy Box share, stock, ads) and outreach outcomes are **simulated** from rules in `sim/ground_truth.yaml`. The agent never reads that file; only the simulator and the eval harness do.
- Brand names are anonymised into `brand_alias.csv` (gitignored). Every screenshot, log, and generated email refers only to the aliases.

## Quick start

Requires Python 3.12, Node 22+, a Hindsight Cloud API key ([MEMHACK99](https://hindsight.vectorize.io) $50 credit), and a Groq API key.

```bash
make venv install                 # Python 3.12 .venv + deps
cp .env.example .env              # fill HINDSIGHT_API_KEY and GROQ_API_KEY
make data                         # stream real Amazon data + prepare (~10 min)
make sim                          # simulator snapshots + outcomes
make seed                         # populate underdog-seed-w8 (weeks 20-40), then clone
make eval                         # memory on/off/oracle across the 12-week demo window
make dev                          # backend :8000 + frontend :3000
```

Environment knobs used by `make data` for iteration:

| Var | Meaning | Typical |
| --- | --- | --- |
| `UNDERDOG_SLIM=1` | Only load Pet_Supplies (fast CI mode) | dev |
| `UNDERDOG_MAX_META=N` | Cap per-category meta rows kept | 15000 |
| `UNDERDOG_MAX_REVIEWS=N` | Cap per-category reviews kept | 80000 |
| `SEED_LIMIT_BRANDS=N` | Cap brands considered by `make seed` (0 = all) | 0 |
| `SEED_PITCHES_PER_WEEK=N` | Pitches retained per seeded week | 20 |

The demo landing week is 44 (the eval covers weeks 41-52). Change with `?week=` in the
URL or `POST /api/demo/reset?to_week=44` to clone the seed bank onto the live one.

## Architecture

```
  Real data (Hugging Face)                     ground_truth.yaml (hidden)
          |                                           |
          v                                           v
  scripts/load_real_data --> data/prepared/ --> sim/simulator --> data/sim/
                                                              |
                                                MarketplaceAdapter
                                     (SimulatedAdapter / KeepaAdapter stub)
                                                              |
        +------------------------ FastAPI backend ------------+
        |  Signals -> Diagnosis -> Scoring -> Weekly loop      |
        |         |                    |             |         |
        |     SQLite            MemoryService   LLMClient      |
        |                     (hindsight-client) (Groq)        |
        |  Eval harness (on / off / oracle)   |                |
        +--------------------------------------|---------------+
                                               v
                                       Hindsight Cloud
                     retain / recall / reflect / observations /
                     mental models / directives / clone
                                               ^
   Next.js frontend  <---- REST + SSE (memory feed) ---- FastAPI
```

## Robustness

| Failure | Behaviour |
| --- | --- |
| Hindsight unreachable | Shortlist falls back to memory-off; UI shows "Memory unreachable" banner |
| `reflect` returns 500 | One retry, then empty adjustments; base score used |
| Groq schema validation fails | One repair prompt, then fallback model, then template |
| Groq rate-limited | Deterministic template email; cached responses reused |
| Duplicate retain on rerun | `document_id` = `snapshot:{brand}:w{NN}` upserts cleanly |
| Reply text contains prompt-injection | Retained verbatim as quoted data; directives keep the agent aligned |

## Tests and evaluation

```bash
make test                # unit + format lint (no external calls)
make test-integration    # hits a live Hindsight and Groq (requires creds)
python -m scripts.run_eval
```

`eval/results.json` has weekly metrics for the on/off/oracle modes.

## Path to production

- `backend/app/adapters/keepa.py` implements the same `MarketplaceAdapter` protocol; wire in your Keepa API key and skip the simulator.
- `POST /api/leads/{alias}/approve` is the human-in-the-loop step; a Gmail integration is a small addition.

## Credits

- **Dataset:** Hou, Y., Li, J., He, Z., Yan, A., Chen, X., McAuley, J. (2024). *Bridging Language and Items for Retrieval and Recommendation.* arXiv:2403.03952. `McAuley-Lab/Amazon-Reviews-2023` on Hugging Face.
- **Memory:** [Hindsight](https://github.com/vectorize-io/hindsight) by Vectorize. Docs: <https://hindsight.vectorize.io>. Overview: <https://vectorize.io/what-is-agent-memory>.
- **LLM:** [Groq](https://groq.com) (`openai/gpt-oss-120b`, `qwen/qwen3-32b`).
- **License:** MIT.
