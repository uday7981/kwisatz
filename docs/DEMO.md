# Demo script (3 minutes)

Pre-flight (do this before the room fills up):

- `POST /api/demo/reset?to_week=44` — instantly clones the seed bank onto the live one.
- Browser at `http://localhost:3000`, light theme, zoom 110%, memory-feed drawer closed.
- Backend + frontend both running (`make dev`); `.env` populated.

| Time | Say | Show |
| --- | --- | --- |
| 0:00-0:20 | "Amazon agencies cold-email the same brands with the same pitch, and never learn which ones say yes. Underdog fixes that." | `/` (This week screen, week 44) |
| 0:20-0:45 | "Here is a real product's review growth. On top of it, resellers pile onto the listing and the brand loses the Buy Box. The brand needs help and does not know it yet." | Click top lead. Show the sparkline; the diagnosis card. |
| 0:45-1:05 | "Without memory, this is what you get." | Flip memory toggle to OFF. Top rows change; supplement brands rise. |
| 1:05-1:40 | "With memory, Underdog learned from 20 weeks of outcomes. It skips supplements (zero of thirty replied). It picks brand protection for this pattern (six of eleven replied). And this brand said 'after Q4', its resellers doubled, so it is back." | Flip toggle to ON. Point at "Skipping" tray. Show revisit badge. Open memory chips. |
| 1:40-2:20 | "Let us run next week live." Log one surprising outcome. | Open the Memory feed drawer with `M`. Approve a draft (`A`). Log "meeting" (`3`). Watch retain events land. Advance a week (`]`) and open `/learned`; the belief card animates with a `NEW` or `STRONGER` badge. |
| 2:20-2:45 | "And it is measurable. Same data, memory on versus off versus an oracle that knows the hidden rules." | `/learning`. Point at the on-vs-off gap and the oracle line. |
| 2:45-3:00 | "Hindsight is the brain: every timeline, every pitch, every outcome, turned into beliefs that change what the agent does next week." | Back to `/learned`. |

## Backup plan

- 3-minute pre-recorded video on the laptop desktop.
- `DEMO_MODE=true` — every LLM call has cached responses; failing Groq mid-demo is transparent.
- If Hindsight is unreachable, switch to the recorded video rather than demoing memory-off.

## Judge questions we should have crisp answers for

1. **"Did you plant the pattern?"** Yes, deliberately, so learning can be *measured*. The agent never reads `ground_truth.yaml`. Memory-off with the same data does not find the pattern. In production the simulator is replaced by Keepa through the adapter.
2. **"Why not a spreadsheet of reply rates?"** Outcomes arrive late, reasons are text ("after Q4", "in-house"), and the same lesson has to transfer across brands and categories. Hindsight consolidates text outcomes into observations with tracked evidence and keeps history when beliefs change.
3. **"Is this spam?"** Tiny targeted volumes, human approves every email, opt-out in every draft, never uses Amazon messaging, directives enforce it.
4. **"What is real?"** Product catalogue, prices, ratings, review timelines. Marketplace dynamics and outcomes are simulated. Names are anonymised.
