# My prospecting agent learned to stop chasing fast-growing brands

*Draft (~1400 words). Never uses the word "hackathon".*

The moment I felt Underdog become useful was the moment it refused to pitch a
segment of brands I was excited about. Zero of thirty supplement brands had
replied in the eight simulated weeks before this one, and my agent quietly moved
them to a **Skipping** tray with the reason attached. That is not a feature I
wrote. It is what fell out of giving a sales agent memory that reasons.

Underdog is a weekly prospecting workflow for Amazon growth agencies. It reads
public marketplace signals for a watched set of brands, notices a **specific,
fixable** problem, drafts a pitch angle tuned to that problem, and ,  importantly , 
learns from every outcome so the next week's decisions are different from this
week's.

The interesting design constraint is not "call an LLM better." It is figuring
out **what to store, when to retrieve it, and how to keep it honest** across a
full quarter of noisy real data. That is what [Hindsight](https://github.com/vectorize-io/hindsight)
gave me. Full docs: <https://hindsight.vectorize.io>. If you have not looked at
[Vectorize's agent memory page](https://vectorize.io/what-is-agent-memory)
recently, it is worth a read.

## The setup: numbers in code, memory in Hindsight, words from the LLM

Three principles ran through every design decision:

1. Signals and diagnoses are deterministic Python. The LLM never produces a
   number the app relies on.
2. Every fact the agent should remember lives in Hindsight ,  brand snapshots,
   pitches, outcomes, agency decisions. Nowhere else.
3. The LLM is only allowed to **explain** and **write**: the reflect prompt
   ranks candidates against beliefs, the draft prompt turns signals into
   short emails.

Because of this split, edge cases fall into three neat buckets ,  a signal that
overflows a threshold, a memory that goes stale, a schema that fails validation
,  and each has one clear failure mode.

## What gets retained

The retain shape matters more than the LLM prompt. I settled on five
memory kinds:

| Kind | When | Tags | Scopes |
| --- | --- | --- | --- |
| snapshot | signal crosses threshold, or every 4th week | `brand`, `cat`, `dx` | `[[dx], [cat], [brand]]` |
| diagnosis | new or changed | `brand`, `cat`, `dx` | same |
| pitch | on human approval | `brand`, `cat`, `dx`, `angle` | `[[dx], [dx, angle], [angle], [cat], [brand]]` |
| outcome | when logged | `brand`, `cat`, `dx`, `angle`, `outcome` | same |
| decision | when the operator sets a rule | `kind:decision` | `[[kind:decision]]` |

Two calls to Hindsight matter here:

```python
# retain_batch ,  never bare retain, because we want per-item scopes
svc.client.retain_batch(bank_id=BANK, items=[
    {
        "content": snapshot_content(...),
        "context": "marketplace snapshot",
        "timestamp": sim_date,                       # simulated clock, always
        "document_id": doc_id("snapshot", brand, week=w),
        "tags": build_tags(brand_alias=..., dx_code=..., kind="snapshot"),
        "observation_scopes": build_scopes(brand_alias=..., dx_code=..., cat=...),
        "metadata": {"week": str(w), "severity": f"{sev:.2f}"},
    },
], operation_id=f"retain-snapshots-w{w:02d}", retain_async=True)
```

Two Hindsight gotchas I learned to respect:

- `observation_scopes=[]` silently means "combined." Always pass explicit lists;
  I have a `build_scopes(...)` helper that guarantees non-empty output.
- `reflect` has no `query_timestamp`. `recall` does. So every reflect query
  prepends `"Today is {sim_date} (week {week} of the season)."` and every
  recall carries `query_timestamp=sim_date.isoformat()`.

## The reflect that changes what happens next week

The interesting call is not the draft. It is the reflect with a Pydantic
schema that returns adjustments to the deterministic base score, plus the
angle to use:

```python
class LeadAdjustment(BaseModel):
    brand_id: str
    score_adjustment: float = Field(ge=-0.6, le=0.6)  # multiplicative
    recommended_angle: Literal["brand_protection", "inventory_planning", ...]
    reason: str = Field(max_length=240)
    skip: bool = False
    revisit: bool = False

class PrioritisationResult(BaseModel):
    adjustments: list[LeadAdjustment]
    beliefs_used: list[str]

resp = svc.client.reflect(
    bank_id=BANK,
    query=prompt,
    budget="mid",
    response_schema=PrioritisationResult.model_json_schema(),
    include_facts=True,
)
result = PrioritisationResult.model_validate(resp.structured_output)
evidence = resp.based_on.memories   # rendered as clickable chips in the UI
```

The evidence attached to the response drives the "Memory chips" you see next to
each shortlist row. Every recommendation is auditable.

## Before and after

Week 1, memory empty, the top-10 looks like every other list tool: fast-growing
brands ranked by recent review velocity, generic growth pitch. Memory-off reply
rate averaged 2% across the season.

Week 8, memory-on, the top-10 is different in three visible ways:

- The Skipping tray shows nine brands with reasons like "0 of 30 replied ,  health
  supplements."
- A "Revisit" badge appears for a brand that said *after Q4* six weeks ago and
  whose resellers doubled since.
- Brand-protection is chosen for reseller-invasion brands (6 of 11 replied) even
  when the deterministic base score prefers growth.

Meeting rate lift, memory on vs off, weeks 9-12: **from about 3% to roughly 12%.
Oracle sits at 21%.** Same seed, same data, only Hindsight added.

## The one time it got it wrong

The **My mistakes** belief group caught the agent over-scoring healthy risers
in Home & Kitchen in weeks 4-6 (the base score's `velocity_growth` term won,
but the ground truth had a subtler pattern). By week 7 the reflect
response was applying `score_adjustment ≈ -0.3` and moving them out of the top
12. That correction only exists because the retain schema records *the agent's
own past scores* as experiences, not just the marketplace facts.

## Lessons

1. **Retain less but retain right.** 180 brands × 52 weeks × N products is not
   the volume you want in Hindsight. Threshold-based material changes plus a
   pulse every four weeks landed the seeded bank around 300-500 memories at
   week 8 ,  enough to form real observations, not so many that consolidation
   lags behind the demo.
2. **Validate every tool call.** Groq's JSON mode is fast and mostly correct.
   The `1 in 20` where it drops a required field costs you a demo unless you
   catch it, prompt-repair, then fall back to a smaller model, then fall back
   to a deterministic template. My golden path never hits the template. My
   safety net always does.
3. **Simulated clocks need discipline.** `retain(timestamp=sim_date)`,
   `recall(query_timestamp=sim_date)`, `reflect` ,  state the date in the query.
   Miss any of these and "recent" starts meaning wall-clock time, and the demo
   silently degrades.
4. **Measure the memory contribution directly.** The eval harness runs the same
   12-week season three ways: memory off, memory on, oracle. It writes a JSON
   and a PNG. Anyone can rerun it. That chart is the only unambiguous answer to
   "did memory actually help?"

## What I would do next

- Wire a Keepa adapter behind the existing `MarketplaceAdapter` interface and
  point the whole thing at a hero set of real brands. The rest of the pipeline
  does not change.
- Add outcome ingestion from Gmail with a human approval step, so the loop closes
  without me copy-pasting into the outreach page.
- Test whether a per-diagnosis mental model actually beats one global "angles
  that work" model at answering the priority reflect.

If you build sales tooling, the takeaway is small: the value of an agent that
learns is not in a smarter LLM. It is in what the agent chooses to store, how
it retrieves it against a real clock, and how visibly it changes its mind.
