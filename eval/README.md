# Evaluation

Underdog runs the same 12-week demo season (weeks 41 to 52) three ways with a fixed
seed so memory lift is directly comparable.

## Modes

| Mode | What it does |
| --- | --- |
| `off` | Deterministic pipeline: signals -> diagnosis rules -> fixed angle mapping. No Hindsight calls. |
| `on` | Same base pipeline, plus one `reflect` call per week that returns per-brand score adjustments + recommended angles + skip/revisit flags. |
| `oracle` | Reads the hidden `sim/ground_truth.yaml` to pick the perfect angle per archetype. Upper bound. The agent never runs this. |

All three modes rank a top-40 candidate pool (base-score) and pick the top-10 with a
per-category cap of 5. Memory-on widens the reflect input to 80 candidates so it can
promote revisit brands.

## What we measure per week

- `reply_rate`: fraction of the top-10 that produced any reply (`reply`, `meeting`, `signed`) based on the sim's ground-truth outcomes for the (brand, week, angle) tuple that mode picked.
- `meeting_rate`: fraction that produced `meeting` or `signed`.
- `angle_accuracy`: fraction whose chosen angle matches the archetype's perfect angle (from `ground_truth.yaml`).

## Current results (SIM_SEED=42)

Rebuild with `make sim && make eval`.

| Mode | Reply rate | Meeting rate | Angle accuracy |
| --- | --- | --- | --- |
| off | 0.34 +/- 0.14 | 0.14 +/- 0.11 | 0.79 |
| on | 0.38 +/- 0.19 | 0.17 +/- 0.10 | 0.79 |
| oracle | 0.48 +/- 0.17 | 0.20 +/- 0.13 | 1.00 |

Reading the numbers:

- Memory-on beats memory-off by ~4 points on reply rate and ~3 points on meeting rate season-average. The oracle ceiling adds another ~10 points on both.
- Memory-on ties memory-off on angle accuracy because the seed data taught memory to reproduce the diagnosis-to-angle mapping; the lift comes from *which brands* memory prioritises, not from angle changes.
- Per-week lift is uneven: week 43 sees the biggest ON win (+30 points reply, +20 points meeting) because memory correctly promotes a batch of revisit brands. Weeks 46-50 are ties because top-40 base rankings already contain the right brands.

Full per-week series lives in `eval/results.json`. Chart: `eval/results.png`.

## Reproducing

```bash
make sim          # regenerate snapshots + outcomes deterministically
make seed         # re-seed underdog-seed-w8 then clone to underdog-lanternfish
                  # (uses Hindsight Cloud credit; skip if the bank is already seeded)
make eval         # writes eval/results.json + results.png
```

`SIM_SEED=42` is baked into `sim/ground_truth.yaml` and published so results reproduce.
Set `SEED_LIMIT_BRANDS=0` (all brands) and `SEED_PITCHES_PER_WEEK=20` at seed time to
get the wide-memory configuration; the ranker will still see all 180 brands each week.

## Notes on determinism

- The signals -> diagnosis -> scoring pipeline is fully deterministic.
- Simulator outcomes are seeded (Python `random.Random(seed)`).
- Memory-on adds non-determinism from the Groq LLM inside `reflect`. A single run's per-week numbers can vary by 5-10 points; the season averages are stable within 2-3 points across reruns.

For a more rigorous claim we would run 5 independent seeds and report medians. That
knob is `SIM_SEED` in `sim/ground_truth.yaml`; re-seeding the Hindsight bank per seed
is not free, so the current chart uses a single seed.

## What the agent does not see

`sim/ground_truth.yaml` is invisible to `backend/app/`. The only importers are
`sim/simulator.py`, `sim/outcomes.py`, and `backend/app/eval/oracle.py` (which is
part of the eval harness, not the agent). Enforced by the `make lint` grep guard.
