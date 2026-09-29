# Architecture

Underdog is a small FastAPI + Next.js app. The interesting parts are the deterministic
signal/diagnosis pipeline (numbers) and the Hindsight facade (memory). Everything else
is glue.

```mermaid
flowchart LR
  subgraph Data["Real + simulated data"]
    HF["Hugging Face<br/>Amazon Reviews 2023"]
    GT["sim/ground_truth.yaml<br/>(hidden from agent)"]
  end

  subgraph Prep["Preparation (offline)"]
    LOAD["scripts/load_real_data.py"]
    SELECT["scripts/select_brands.py"]
    ANON["scripts/anonymise.py"]
    SIM["sim/simulator.py<br/>sim/outcomes.py"]
  end

  subgraph Agent["Weekly loop"]
    ADAPT["MarketplaceAdapter<br/>(SimulatedAdapter / KeepaAdapter stub)"]
    SIGNALS["engine/signals.py"]
    DIAG["engine/diagnosis.py"]
    SCORE["engine/scoring.py"]
    LOOP["engine/loop.py"]
    LLM["llm/client.py<br/>Groq + JSON validation + fallback"]
  end

  subgraph Memory["Hindsight facade"]
    MEM["memory/service.py<br/>(only importer of hindsight_client)"]
    FORMATS["memory/formats.py<br/>tags + document_ids + scopes"]
    BANK["memory/bank_setup.py<br/>directives + mental models"]
  end

  subgraph API["FastAPI"]
    ROUTES["/api/shortlist /api/leads /api/beliefs<br/>/api/metrics /api/memory/feed (SSE)"]
    STATE["state.py<br/>event bus + belief cache"]
  end

  subgraph UI["Next.js 15"]
    THISWEEK["/ Shortlist"]
    DOSSIER["/brands/[alias]"]
    LEARNED["/learned Belief cards + diff"]
    LEARNING["/learning on vs off vs oracle"]
    REPLAY["/replay Dev scrubber"]
    FEED["Memory feed drawer (M)"]
  end

  HF --> LOAD --> SELECT --> ANON
  ANON --> SIM
  GT --> SIM

  ANON --> ADAPT
  SIM --> ADAPT

  ADAPT --> SIGNALS --> DIAG --> SCORE --> LOOP
  LOOP -.reflect.-> MEM
  LOOP --> LLM
  LOOP --> ROUTES

  MEM --> BANK
  MEM --> FORMATS

  ROUTES --> STATE
  STATE -.events.-> FEED

  ROUTES --> THISWEEK
  ROUTES --> DOSSIER
  ROUTES --> LEARNED
  ROUTES --> LEARNING
  ROUTES --> REPLAY

  MEM <==> HINDSIGHT["Hindsight Cloud<br/>retain / recall / reflect<br/>observations / mental models"]
```

## Invariants

- `grep -R "hindsight_client" backend/app/` -> only `memory/service.py`.
- `grep -R "ground_truth" backend/app/` -> only `backend/app/eval/oracle.py`.
- Every `retain*` call carries a stable `document_id` and the simulated `timestamp`.
- Every `recall` carries `query_timestamp = sim_date`.
- Every `reflect` prompt starts with `"Today is {sim_date} (week {week} of the season)."` because `reflect` has no `query_timestamp` parameter.
- Every retain item passes an explicit non-empty `observation_scopes` list-of-lists.
- No em dashes in generated content, docs, or the frontend.
- No real brand names anywhere — everything goes through `brand_alias.csv` (gitignored).

## Numbers -> memory -> words

- **Numbers** (signals, diagnosis rules, base score, angle mapping) live in Python and are unit-tested. The LLM never emits a number the app relies on.
- **Memory** (every snapshot, pitch, outcome, and the beliefs they consolidate into) lives in Hindsight. Directives and mental models are set once at bank setup.
- **Words** (email drafts, per-lead reasons, belief summaries) come from Groq with JSON-mode + Pydantic validation + one repair retry + a deterministic template fallback. The demo cannot crash because of the LLM.
