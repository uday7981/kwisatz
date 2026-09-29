# UNDERDOG: Product and Technical Specification

The prospecting agent that learns which Amazon brands say yes. Project brief, PRD, TRD, UI/UX spec, data plan (Option B), implementation plan and submission checklist. Built on Hindsight agent memory.

Version 1.0, 29 September 2026. Owner: Uday.

# 0. How to use this document

This is the single source of truth for building and submitting Underdog. It is written so that one person, or a team of up to four, can build it end to end without needing any other document.

| Section | Read it when | Primary reader |
| --- | --- | --- |
| 1. Project brief | You need the idea in two minutes | Everyone, judges |
| 2. What the organisers want | Checking any decision against the rules and scoring | Everyone |
| 3. PRD | Deciding what the product does and why | Product, frontend, demo lead |
| 4. UI/UX specification | Designing and building screens | Frontend |
| 5. Data plan (Option B) | Sourcing datasets and building the simulator | Data / backend |
| 6. TRD | Building the backend, memory layer and APIs | Backend |
| 7. Implementation plan | Planning the days and splitting work | Everyone |
| 8. Judging criteria map | Before the demo and before submission | Demo lead |
| 9. Demo script | Rehearsing and recording | Demo lead |
| 10. Content deliverables | Writing the article, post and video | Every team member |
| 11. README outline | Writing the GitHub repo | Backend |
| 12. Submission checklist | The final day | Everyone |

> **Two rules that override everything**
> 1. Hindsight memory must be central and visible. If a feature would work equally well without memory, it is not a priority.
> 2. The word "hackathon" must not appear anywhere in the article, the social post or their hashtags. Doing so disqualifies the content.

# 1. Project brief

## 1.1 One line

**Underdog** is an AI prospecting agent for Amazon growth agencies. It finds rising brands that have a specific, fixable problem in their marketplace data, pitches each brand the right fix, and **learns from every reply which brands actually become clients and which pitch works**.

Tagline: **"Marketplace data shows you every brand. Underdog remembers which ones say yes."**

## 1.2 The problem

Amazon growth agencies (PPC management, brand protection, inventory planning, listing optimisation) live on new clients. Their prospecting is weak in three specific ways:

- **They pitch blindly.** They buy generic lead lists and send the same growth pitch to every brand, without knowing which brand has a problem the agency can fix right now.
- **They forget.** Who said "not now", why, and when to come back lives in someone's inbox and gets lost.
- **They never learn.** Nobody measures which kinds of brands actually sign or which pitch angle gets replies, so every quarter starts from guesswork.

Meanwhile, small brands on Amazon get hurt by problems they often notice late: resellers undercutting their listings, repeated stockouts, weak conversion, price erosion and under-investment in advertising. All of these show up in public marketplace data long before the brand asks for help.

## 1.3 The solution

Underdog runs a weekly loop: **discover, watch, diagnose, prioritise, pitch, learn**. Code computes the marketplace signals. An LLM explains and writes. **Hindsight** remembers every brand's timeline, every pitch and every outcome, consolidates them into beliefs, and uses those beliefs to change what the agent does next week.

| Week | What Underdog says | Why |
| --- | --- | --- |
| Week 1 | "50 brands with rising demand. Here are standard emails." | No memory yet. Generic. |
| Week 4 | "Brands losing Buy Box share reply far more than healthy risers. Prioritising those." | First observations formed from outcomes. |
| Week 8 | "12 brands this week. Skipping supplements (0 of 30 replied). Brand-protection angle wins for this pattern. The brand that said 'after Q4' now has twice the resellers; re-pitch." | Beliefs, revisit memory and self-correction working together. |

## 1.4 Who it is for

Primary persona: the partnerships or business development lead at a 5 to 30 person Amazon agency serving US or UK brands. Secondary: agency founders who do sales themselves. Adjacent buyers: brand protection firms and wholesale partners who pitch brands.

## 1.5 Why it can win

- **Fresh angle.** Storefront and catalogue research is normally used to copy products. Underdog flips it to find brands that need help. Nobody else in the room will pitch this.
- **Memory is load-bearing.** Remove Hindsight and it becomes a static list with generic emails. With Hindsight, it changes its targeting and pitch every week, with evidence.
- **Real data.** Product catalogue, prices, ratings and review timelines come from a real public Amazon dataset. Only marketplace dynamics and outreach outcomes are simulated, and that is stated openly.
- **Provable learning.** Because the simulator has hidden ground-truth rules, Underdog can show a measured learning curve: memory on versus memory off versus an oracle.
- **Clear money.** One signed client is worth thousands a month to an agency.

## 1.6 Data approach (Option B) in one paragraph

Real product data (titles, brands/stores, categories, prices, ratings, and timestamped reviews) comes from the public **Amazon Reviews 2023** dataset on Hugging Face (McAuley Lab, UCSD). Review velocity over time is used as a real demand signal. On top of that, a simulator generates weekly sales rank, reseller counts, Buy Box share, stock and price histories, plus agency outreach outcomes, all driven by hidden rules kept in a ground-truth file. Brand names are anonymised on screen so no real company is shown with a fictional problem. Everything sits behind a data adapter so a live Keepa feed can replace the simulator later without changing the app.

> **Non-negotiable honesty line (use it in the README, demo and article)**
> "Product catalogue and review timelines are real public Amazon data. Marketplace dynamics and outreach outcomes are simulated from documented rules so learning can be measured. Brand names are anonymised."

# 2. What the organisers want

This section distils both source documents (the Problem Statement and the Content Guide) into requirements. Every design decision later in this document traces back to a row here.

## 2.1 Theme and required technology

- Build AI agents that **learn using Hindsight**: persistent memory and improvement from past interactions, not conversations that are forgotten.
- All projects must use **Hindsight** (Cloud or open source). Hindsight Cloud promo code: **MEMHACK99** for $50 of credit, added in the billing section after registering.
- Any LLM is allowed. Groq is recommended for speed and free tier, with models **openai/gpt-oss-120b** and **qwen/qwen3-32b**. The brief explicitly warns to handle **function-calling errors**.
- Avoid student-centric projects. Build something a real business would pay for ("Would someone pay $50/month for this?").
- Keep scope tight: one workflow, one persona, one clear value proposition.
- Use realistic data (Kaggle, Hugging Face, or realistic synthetic data). The brief calls data the #1 thing that makes a project look real.

## 2.2 Judging criteria

| Criterion | Weight | What judges look for | Underdog's answer |
| --- | --- | --- | --- |
| Innovation | 30% | Fresh take on a real problem, beyond chatbots | Flipped storefront research to find brands in trouble; outcome-learning prospecting; not a chat UI |
| Use of Hindsight memory | 25% | Memory central to the value; agent clearly improves over time | Brand timelines, outcome learning, self-correcting scores, living ICP pages; measured learning curve |
| Technical implementation | 20% | Clean, well-architected, functional; handles edge cases | Typed adapters, deterministic signal engine, schema-validated LLM calls with retries and fallback, eval harness, tests |
| User experience | 15% | Intuitive; demo tells a compelling story | Weekly shortlist, belief cards that visibly change, replay scrubber, memory on/off split |
| Real-world impact | 10% | Genuine problem, path to adoption | Agencies pay per client; clear pricing; Keepa adapter as the path to production |

## 2.3 Submission requirements

| Deliverable | Detail | Owner |
| --- | --- | --- |
| GitHub repository | Clean, documented code; public | Team |
| Demo video | 2 to 5 minutes, screen recording with voiceover (talking head plus screen preferred), 1080p minimum, public on YouTube (not Drive), thumbnail made with Nano Banana | One per team |
| Live demo to judges | Working product | Team |
| Article | Public technical write-up on Medium, Dev.to, Hashnode, Substack or LinkedIn Articles. English. Guide gives 800 to 1,500 words in one place and 1,200 to 2,000 in the prompt; aim for about 1,300 to 1,500 to satisfy both. Must include the three Hindsight links, a real code snippet, a before/after example, an honest lesson, and screenshots | Every team member |
| Social post | LinkedIn post under 800 characters, repo link in the main post, article URL as first comment, then a comment linking the Hindsight GitHub repo | Every team member |
| Reddit | Share the article as a link post in r/llmdevs, r/sideproject, r/aiagents or r/aimemory | Every team member |
| Hindsight explanation | Clear explanation of how Hindsight memory is used | Team (README section) |
| Tagging | Tag Code.in on LinkedIn and in articles | Every team member |

## 2.4 Content rules that disqualify if broken

- No mention of "hackathon" in the article title or body, the social post, or any hashtag.
- Do not use #Hackathon or student-related tags. Suggested hashtags: #AIAgents, #AI, #Hindsight, #AgentMemory, #AIMemory, #LLM (3 to 5, last line only).
- Do not share Google Drive links for the article or video. Publish them properly.
- Frame the project as a real product, not a demo or event project.

## 2.5 What the brief says makes a winning demo

- Tell a story: "Imagine you run partnerships at an Amazon agency..."
- Show the learning curve: generic at first, personalised later.
- Make value obvious within 60 seconds.
- Show retain and recall happening live.
- Build something you would proudly post on LinkedIn tomorrow.

# 3. Product Requirements Document (PRD)

## 3.1 Problem statement

Amazon agencies waste most of their outbound effort on brands that are not a fit or not ready, and they cannot tell which brands will be, because they do not connect marketplace signals to their own outreach outcomes over time. Every quarter they repeat the same mistakes.

## 3.2 Goals

| ID | Goal | Measured by |
| --- | --- | --- |
| G1 | Find brands with a specific, fixable marketplace problem each week | Every shortlisted brand has a diagnosis with computed evidence |
| G2 | Pitch each brand with the angle most likely to work | Angle-match accuracy vs ground truth rises over simulated weeks |
| G3 | Learn which brands convert and adjust targeting | Reply and meeting rate of the weekly top 10 rises; gap to oracle narrows |
| G4 | Never lose context on a brand | Every brand dossier shows full timeline and interactions; 'not now' brands resurface when their problem worsens |
| G5 | Make the learning visible and trustworthy | Every belief and recommendation cites the memories it came from |

## 3.3 Non-goals (for this build)

- Sending real emails automatically. Drafts only; a human approves. (Optional Gmail integration is a stretch goal and still requires approval.)
- Contacting sellers through Amazon messaging. Never.
- Live Keepa or Amazon API integration. The adapter is ready; the simulator is used for the build.
- PPC management, repricing or any action on a brand's account.
- Multi-agency tenancy, billing or authentication beyond a single demo agency.

## 3.4 Personas

| Persona | Context | Needs | Frustrations today |
| --- | --- | --- | --- |
| Meera, Head of Partnerships at 'Lanternfish Growth' (fictional, 14-person Amazon agency) | Owns the pipeline; sends 40 to 60 outbound emails a week; reports to founder weekly | A short weekly list of brands worth contacting now, a reason for each, a draft she can send in a minute | Generic lists, no memory of past conversations, no idea which pitch works |
| Dev, founder of the same agency | Signs off strategy; wants predictable growth | Evidence of what converts; where to focus the team | Opinions instead of data; lost 'not now' leads |

## 3.5 Core concepts (glossary for the whole team)

| Term | Meaning in Underdog |
| --- | --- |
| Brand | A store/brand on Amazon with one or more products (from the dataset's `store` field) |
| Signal | A number computed in code from data, for example reseller count trend or review velocity |
| Diagnosis | A named, fixable problem inferred from signals (six types, see 3.7) |
| Angle | The pitch theme matched to a diagnosis (brand protection, inventory planning, listing and reviews, MAP enforcement, advertising, growth partnership) |
| Lead | A brand shortlisted in a given week, with a score, diagnosis and angle |
| Outcome | What happened after a pitch: no reply, reply, meeting, proposal, signed, declined (with reason), not now (with timing) |
| Belief | A consolidated, evidence-backed statement the agent holds, for example 'brand-protection pitches work for reseller-invasion brands (6 of 11 replied)' |
| Simulated week | One tick of the simulation clock. The demo runs 12 weeks |
| Memory on / off | Same pipeline with and without Hindsight, used for the split screen and evaluation |

## 3.6 User stories and acceptance criteria

| ID | As Meera, I want to... | Acceptance criteria |
| --- | --- | --- |
| US-01 | see this week's shortlist of brands worth contacting | 10 to 15 ranked brands; each shows diagnosis, severity, a 12-week sparkline, score and a one-line 'why now'; loads in under 2 s from cache |
| US-02 | understand why a brand is on the list | Opening a lead shows computed signals, the diagnosis rule that fired, and memory evidence chips that link to the underlying memories |
| US-03 | get a draft email using the best angle | Draft cites the brand's own data, uses the angle chosen from memory, is under 120 words, has no em dashes, and is editable before approval |
| US-04 | log what happened after a pitch in one click | Buttons: No reply, Replied, Meeting, Not now (asks when), Declined (asks reason), Signed; each writes an outcome to memory and updates the lead |
| US-05 | see what the agent has learned | 'What I've learned' shows 5 to 8 belief cards with confidence, evidence count, and what changed since last week |
| US-06 | be reminded to revisit brands at the right time | Brands that said 'not now' reappear in the shortlist with a 'Revisit' badge when timing arrives or their problem worsens, with the original objection quoted |
| US-07 | stop wasting time on segments that never convert | After enough evidence, low-converting segments are down-ranked and shown in a 'Skipping' tray with the reason |
| US-08 | see a brand's full history | Brand dossier shows signal timeline, every diagnosis, every email and outcome, and the agent's notes |
| US-09 | trust the agent | Every recommendation and belief lists its sources; nothing is sent without approval |
| US-10 (Dev) | see whether the agent is actually getting better | Learning dashboard: reply and meeting rate by week, memory on vs off, lead-score accuracy, and beliefs formed over time |
| US-11 (demo) | replay the season and toggle memory | Replay scrubber moves weeks 1 to 12; toggle splits the screen into memory off and memory on with the same data |

## 3.7 Diagnosis catalogue

Diagnoses are computed deterministically in code from signals. The LLM never decides a number; it only explains.

| Code | Diagnosis | Signal rule (default thresholds) | Angle offered |
| --- | --- | --- | --- |
| D1 | Reseller invasion | Seller count on top listing up at least 3 in 30 days AND brand Buy Box share below 75% (from above 90%) | Brand protection and authorised-seller strategy |
| D2 | Stockout-prone | At least 2 out-of-stock episodes in 60 days while review velocity is rising | Inventory and FBA planning |
| D3 | Weak converter | Demand proxy in top 40% of peers but rating at least 0.3 below category median, or reviews under 50 on a top-seller | Listing and review strategy |
| D4 | Price erosion | Buy Box price down at least 12% over 90 days with 3 or more sellers | MAP (minimum advertised price) enforcement |
| D5 | Under-advertised riser | Review velocity up at least 40% quarter on quarter but ad presence index below 0.3 | Advertising (PPC) management |
| D6 | Healthy riser | Growth with none of the above | Growth partnership |

Severity is a 0 to 1 score per diagnosis based on how far past the threshold the signal is and how fast it is worsening. A brand can have more than one diagnosis; the primary one is the highest severity.

## 3.8 The learning loop (functional specification)

1. **Observe.** Each simulated week, compute signals for all watched brands and write material changes to memory (not every tick; only when a signal moves past a threshold or every fourth week).
2. **Diagnose.** Apply rules; write new or changed diagnoses to memory.
3. **Prioritise.** Compute a base score in code. Ask Hindsight (reflect) to adjust scores and pick angles using what it has learned, returning structured output with evidence IDs. Combine and clamp.
4. **Pitch.** Draft emails for the top brands with the chosen angle. Record the agent's own score and angle as an experience memory ("I scored X at 0.71 and pitched brand protection").
5. **Learn.** Outcomes arrive 1 to 3 weeks later (simulated or logged by the user). Each is written to memory with its reason. Hindsight consolidates them into observations; mental models (living pages) refresh.
6. **Reflect.** Weekly, extract the current beliefs as structured output, diff them against last week, and show the change in the UI.

## 3.9 Functional requirements

| ID | Requirement | Priority |
| --- | --- | --- |
| FR-01 | Load real product and review data for 3 categories into the app database via a repeatable script | Must |
| FR-02 | Select 120 to 180 underdog brands using defined filters; anonymise names with a stable mapping | Must |
| FR-03 | Simulator generates 12 months of weekly marketplace history per product, anchored on real review velocity | Must |
| FR-04 | Signal engine computes all signals deterministically from snapshots | Must |
| FR-05 | Diagnosis engine applies rules and severity | Must |
| FR-06 | Hindsight bank configured with missions, disposition, directives, and mental models | Must |
| FR-07 | Weekly retain of material changes, pitches and outcomes with timestamps, tags and document IDs | Must |
| FR-08 | Weekly prioritisation using reflect with a response schema; deterministic fallback if it fails | Must |
| FR-09 | Email drafting via Groq with schema validation, retries and model fallback | Must |
| FR-10 | Outcome simulator with hidden ground truth, noise and delays | Must |
| FR-11 | Memory-off baseline pipeline (same data, no Hindsight) | Must |
| FR-12 | Evaluation harness producing learning curves and a summary table | Must |
| FR-13 | UI: Shortlist, Lead drawer, What I've learned, Learning dashboard, Replay scrubber with memory toggle | Must |
| FR-14 | UI: Brand dossier with full timeline | Should |
| FR-15 | UI: Outreach inbox with manual outcome logging | Should |
| FR-16 | Revisit logic for 'not now' brands | Should |
| FR-17 | Live memory feed drawer (retain and recall events streamed) | Should |
| FR-18 | Demo reset by cloning a pre-seeded Hindsight bank | Should |
| FR-19 | Keepa adapter stub with the same interface as the simulator | Could |
| FR-20 | Gmail draft creation with explicit approval | Could |

## 3.10 Success metrics

| Metric | Definition | Target in demo |
| --- | --- | --- |
| Reply rate lift | Reply rate of weekly top 10, weeks 9 to 12 vs weeks 1 to 4 (memory on) | At least 2x |
| Memory advantage | Meeting rate memory on minus memory off, weeks 9 to 12 | Clearly positive, shown on chart |
| Gap to oracle | Share of oracle meetings captured (oracle knows the hidden rules) | Rises from under 40% to over 70% |
| Angle accuracy | Share of pitches where chosen angle equals ground-truth best angle | Rises over weeks |
| Evidence coverage | Share of recommendations with at least one cited memory | 100% after week 2 |
| Latency | Shortlist load from cache / fresh reflect | Under 2 s / under 20 s |

_Targets depend on the simulator settings. Tune noise so the result is convincing but not suspiciously perfect._

## 3.11 Scope by priority (MoSCoW)

| Must have | Should have | Could have | Won't have (now) |
| --- | --- | --- | --- |
| Data pipeline, simulator, signals, diagnoses, Hindsight loop, drafting, eval harness, Shortlist, Learned, Dashboard, Replay with memory toggle | Brand dossier, outreach inbox, revisits, memory feed, bank clone reset | Keepa adapter, Gmail drafts, dark mode polish | Auto-send, Amazon messaging, account actions, multi-tenant auth |

## 3.12 Risks and mitigations

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Judges think it is 'another cold email bot' | High | Lead the demo with the agent changing its mind; emails appear late and small |
| Judges suspect the planted pattern | High | Say it upfront; show the eval harness, memory off baseline and noise; show a belief the agent got wrong then corrected |
| Hindsight consolidation lag during live demo | Medium | Pre-seed weeks 1 to 8; show live learning on a single outcome; poll operations and show a 'learning' state |
| Groq rate limits or tool-call failures | Medium | Cache drafts; schema validation, retries, fallback model; demo mode serves cached responses |
| Dataset too large to download | Medium | Stream and sample by category; ship a small prepared parquet in the repo (derived, anonymised) |
| Real brand shown with a fake problem | High | Always anonymise names on screen; never show real store names in UI, video or article |
| Dataset licence limits | Medium | Use for research/demo only; do not redistribute raw data; include download script and attribution |
| Scope creep | High | Freeze scope at the Must list; everything else is post-demo |

# 4. UI/UX specification

The product should feel like a calm, precise instrument that a sharp operator uses every Monday morning, not a chatbot and not a generic SaaS dashboard. The one memorable element is the **belief card**: the place where the agent visibly changes its mind, with evidence.

## 4.1 Design direction

| Principle | What it means in practice |
| --- | --- |
| Evidence over decoration | Every number, badge and sentence can be traced to a signal or a memory. No ornamental gradients, no stock illustrations. |
| One loud moment | Belief cards are the only element that animates on their own. Everything else is still and quiet so the learning moment stands out. |
| Weekly rhythm | The whole product is organised around 'this week'. The week is always visible and the replay scrubber can move it. |
| Operator density | Information-dense like a trading desk, but with generous line height and clear grouping. No tiny text below 12 px. |
| Plain language | Say 'resellers joined your listing', not 'offer count delta'. Jargon lives in tooltips. |

## 4.2 Design tokens

### Colour (light theme, default for demo and projector)

| Token | Hex | Use |
| --- | --- | --- |
| surface-base | #F2F5F4 | App background (cool mineral grey, not cream) |
| surface-raised | #FFFFFF | Panels, drawers, tables |
| ink | #0F1B2D | Primary text, primary buttons |
| ink-muted | #5B6573 | Secondary text, axis labels |
| rule | #D5DCDF | Dividers, table lines, card borders |
| signal | #0E6E6A | Primary accent: selected state, links, focus ring, 'memory on' |
| insight | #C7861A | Reserved for learning: belief changes, 'learned' badges, the memory-on uplift line |
| risk | #B4461F | Problems in brand data (reseller spikes, stockouts) |
| positive | #2F7A4F | Replies, meetings, signed |
| neutral-series | #8A96A3 | Memory-off series, baselines |

_Dark theme mirrors the same roles: base #0E141B, raised #151D26, ink #E8EDF0, muted #9AA6B2, rule #26313C, signal #3FB3AB, insight #E3A63B. Check every text/background pair for WCAG AA contrast (4.5:1 body, 3:1 large)._

### Typography

| Role | Typeface | Size / weight / line height |
| --- | --- | --- |
| Display (brand name, week title, big numbers) | Bricolage Grotesque | 32 / 600 / 1.1; numbers 40 / 600 |
| Belief statements | Bricolage Grotesque | 18 / 500 / 1.35 |
| UI and body | IBM Plex Sans | 14 / 400 / 1.5; labels 12 / 500 |
| Tables and metrics | IBM Plex Sans with tabular numerals | 13 / 400; font-variant-numeric: tabular-nums |
| Email drafts | IBM Plex Sans | 15 / 400 / 1.6, max 68 characters per line |

Rules: sentence case everywhere; no all-caps labels; no labels above headings unless they carry information; two families only.

### Space, shape, depth, motion

- **Spacing scale:** 4, 8, 12, 16, 24, 32, 48. Page gutter 24 px desktop, 16 px mobile.
- **Radius hierarchy (deliberately not uniform):** tables and panels 6 px; chips 999 px; belief cards 14 px; buttons 8 px.
- **Depth:** borders first. Only drawers and the command menu get a shadow (0 12px 32px rgba(15,27,45,0.14)).
- **Motion:** respect prefers-reduced-motion. Durations 120 ms (hover/press), 220 ms (drawers), 600 ms (belief change sequence only). Easing cubic-bezier(0.2, 0.8, 0.2, 1).
- **Charts:** thin 1.5 px lines, no gridline clutter (one baseline plus 3 light horizontal guides), direct labels instead of legends where possible, memory-on in insight colour, memory-off in neutral-series.

## 4.3 Information architecture

```
Left rail (icons + labels)          Top bar
  This week   (default)               Agency name | Week 7 of 12 | Memory: ON | Replay
  Brands
  Outreach
  What I've learned
  Learning
Global: Memory feed drawer (right, toggled by 'M'), Command menu (Cmd/Ctrl+K)
```

## 4.4 Screens

### Screen 1: This week (the shortlist)

Purpose: answer 'who should I contact this week, and why?' in under 10 seconds.

```
+--------------------------------------------------------------------------+
| Week 7   12 brands worth contacting    3 revisits    9 skipped (why?)    |
|--------------------------------------------------------------------------|
| # Brand              Diagnosis           Severity  12-wk trend  Score    |
| 1 Copperleaf Kitchen Reseller invasion   ####--    /\_/--\__   0.86 >  |
|   Why now: 7 resellers joined in 30 days; Buy Box share 58% (was 95%)    |
|   Memory: [brand-protection wins 6/11] [2 similar brands signed]         |
| 2 Pawsmith           Stockout-prone      ###---    __/--\_/    0.79 >  |
| 3 Hearthline (REVISIT) Reseller invasion ####--    ...         0.74 >  |
|   Said 'after Q4' on 12 Aug. Resellers doubled since.                    |
+--------------------------------------------------------------------------+
| Skipping: 9 supplement brands (0 of 30 replied), 4 healthy fast-growers |
+--------------------------------------------------------------------------+
```

- Rows are compact (56 px) and expand on hover to show 'Why now' and memory chips.
- Memory chips are clickable and open the exact memories behind them.
- Score shows base score faintly and final score strongly, with a small arrow when memory moved it. Hover: 'Memory raised this from 0.61 because...'.
- The 'Skipping' tray is critical to the story: it shows the agent learned what not to do.

### Screen 2: Lead drawer (opens from the shortlist)

```
+--------------------------------------------+
| Copperleaf Kitchen            Home & Kitchen|
| 14 products  |  4.3 avg rating  |  $18-$42  |
|--------------------------------------------|
| [chart] resellers (risk)  vs  Buy Box share |
|--------------------------------------------|
| Diagnosis: Reseller invasion (0.78)         |
|  - Sellers on top listing 2 -> 9 (30 days)  |
|  - Buy Box share 95% -> 58%                 |
|--------------------------------------------|
| What memory says                            |
|  Angle: Brand protection (6 of 11 replied)  |
|  Similar: 2 kitchenware brands signed (Aug) |
|  Caution: founder said 'we handle Amazon    |
|  in-house' in June; open with the new data |
|--------------------------------------------|
| Draft email (editable)                      |
|  [Regenerate] [Change angle v] [Approve]    |
+--------------------------------------------+
```

### Screen 3: What I've learned (the signature screen)

Five to eight belief cards, grouped: Who converts, Which angle works, What to avoid, My mistakes.

```
+-------------------------------------------------------------+
| Which angle works                         Updated in week 7 |
|                                                             |
|  For reseller-invasion brands, brand-protection pitches    |
|  get replies; growth pitches do not.                        |
|                                                             |
|  Confidence  [=========---]   Evidence  11 outcomes         |
|  Changed: was 'unclear' in week 4 (+5 new outcomes)         |
|  [see evidence]                                             |
+-------------------------------------------------------------+
```

**The signature motion (the only orchestrated animation in the product):** when the week advances and a belief changes, the old statement fades to 40% and gets a thin strike line, the new statement types in beneath it over 600 ms in ink with an insight-coloured underline, the confidence bar eases to its new length, and a small badge reads 'Learned from 3 new outcomes'. Reduced-motion users see the final state with the badge.

### Screen 4: Learning dashboard

- Hero chart: meeting rate of weekly top 10 by week, memory on (insight) vs memory off (neutral) vs oracle (dashed ink).
- Three supporting numbers: reply rate lift, share of oracle captured, angle accuracy. Big number with a short label, only here.
- Timeline of beliefs formed (small markers on the chart where a belief changed, hover shows the statement).
- Table: lead score calibration (predicted vs actual reply rate by score bucket).

### Screen 5: Brand dossier

Full-page view of a brand: 12-month signal timeline with annotated events (reseller spike, stockout, pitch sent, reply), diagnoses over time, every email and outcome, and the agent's notes. This is where recall across time is visible.

### Screen 6: Outreach

A table of pitches with status. Each row has one-click outcome buttons. Logging 'Not now' asks 'When should I check back?' (date or 'after Q4'). Logging 'Declined' asks for a reason from a short list plus free text.

### Screen 7: Replay and memory toggle (demo control)

- Bottom bar scrubber: weeks 1 to 12 with small dots where learning events happened. Dragging it re-renders every screen for that week from cached state.
- Memory toggle: 'Memory on', 'Memory off', 'Side by side'. Side by side splits the shortlist into two columns with identical data and different rankings, differences highlighted.
- 'Advance one week' button runs the live loop for the next week (used once in the live demo).

### Memory feed drawer

A right-side drawer streaming Hindsight activity in plain language: 'Retained: Pawsmith replied, booked a call', 'Recalled 6 memories for Copperleaf Kitchen', 'Belief updated: supplements rarely reply'. Each entry expands to show the raw API call and latency. This is how judges see retain and recall happening live.

## 4.5 States and microcopy

| State | Copy |
| --- | --- |
| Empty shortlist (week 1, before data) | No brands yet. Load marketplace data to start this week's shortlist. |
| Loading reflect | Checking what I've learned about brands like these... |
| Consolidation in progress | Learning from 4 new outcomes. Beliefs will update in a moment. |
| LLM draft failed | Couldn't draft this email. Try again, or switch angle. |
| Hindsight unreachable | Memory is offline, so this shortlist uses base scores only. Reconnect to use what I've learned. |
| Approve button / toast | Approve draft / Draft approved |
| Outcome logged | Logged: meeting booked. I'll use this next week. |

## 4.6 Accessibility and responsiveness

- Keyboard: J/K to move through the shortlist, Enter to open, A to approve, 1 to 6 to log outcomes, M for memory feed, [ and ] to move weeks.
- Visible focus ring (2 px signal colour, 2 px offset). All icons have labels or aria-labels.
- Colour is never the only carrier of meaning: severity uses bars plus numbers; chart series are directly labelled.
- Layout works at 1440, 1280 and 390 px widths. On mobile, the shortlist becomes a list of cards and drawers become full screen.

## 4.7 Frontend stack and components

| Layer | Choice | Notes |
| --- | --- | --- |
| Framework | Next.js (App Router) + TypeScript | Server components for data fetching; client components for charts and motion |
| Styling | Tailwind CSS with CSS variables for tokens | Tokens from 4.2 as variables; light and dark |
| Primitives | Radix UI primitives (via shadcn/ui), restyled | Dialog, Drawer, Tooltip, Tabs, Toggle Group, Command |
| Charts | Recharts or visx | Custom thin-line theme; sparklines as inline SVG |
| Motion | Framer Motion | Belief change sequence only, plus drawer transitions |
| Data fetching | TanStack Query | Cache per week; SSE for memory feed |
| Fonts | Google Fonts: Bricolage Grotesque, IBM Plex Sans | Load with next/font |

Core components: WeekHeader, ShortlistTable, LeadRow, MemoryChip, SeverityBar, Sparkline, LeadDrawer, SignalChart, DraftEditor, BeliefCard, BeliefDiff, LearningChart, SkipTray, OutcomeButtons, ReplayBar, MemoryToggle, MemoryFeed.

# 5. Data plan (Option B)

Real product data plus simulated marketplace dynamics and outcomes. The aim is data that looks and behaves like the real thing, with ground truth you control so learning can be measured.

## 5.1 Recommended datasets

| Dataset | Where | What you use from it | Notes |
| --- | --- | --- | --- |
| Amazon Reviews 2023 (primary) | Hugging Face: McAuley-Lab/Amazon-Reviews-2023 (also amazon-reviews-2023.github.io) | Item metadata: title, store (brand), main_category, categories, price, average_rating, rating_number, details, parent_asin, bought_together. Reviews: rating, timestamp, verified_purchase, helpful_vote | 571.54M reviews and 48.19M items across 33 categories, interactions May 1996 to Sep 2023. Download per category. Research dataset: cite the paper, do not redistribute raw files |
| Amazon Products Dataset 2023 (1.4M products) | Kaggle: asaniczka/amazon-products-dataset-2023-1-4m-products | A price and popularity snapshot (for example list price vs price, best seller flag, 'bought in last month') to calibrate price bands and demand tiers | Scraped Sep 2023. Confirm exact columns and licence on the dataset page before use. Sister datasets exist for UK, Canada and India |
| Amazon Products Sales Dataset 2023 | Kaggle: lokeshparab/amazon-products-dataset | Discount price vs actual price across 142 categories, to calibrate discount and price-erosion ranges | 300K+ products; columns include name, main_category, sub_category, ratings, no of ratings, discount_price, actual_price |
| Amazon Best Sellers (Mexico and Brazil) | Kaggle: edwardtoledolpez/amazon-mexico-top-50-best-sellers | Hourly best-seller rank movements, to make simulated rank curves realistic in shape and volatility | Aug to Sep 2020; used only for calibration, not displayed |
| Keepa API (optional, later) | keepa.com API | Real rank, offers, Buy Box and seller storefronts for a few hero brands | Starts at EUR 49/month; plug into the adapter only if time and budget allow |

## 5.2 Category choice

| Category (dataset name) | Why | Items / ratings in dataset |
| --- | --- | --- |
| Home_and_Kitchen | Many small brands, clear reseller and price-erosion stories | 3.7M items / 67.4M ratings (stream and sample) |
| Pet_Supplies | Loyal repeat buyers, stockout stories, strong small-brand scene | 492.7K items / 16.8M ratings |
| Health_and_Household | Provides the 'supplements rarely reply' negative pattern | 797.4K items / 25.6M ratings |

_Sizes are from the dataset card. Home_and_Kitchen is large, so stream it and keep only brands that pass the underdog filter._

## 5.3 Loading the data

The Hugging Face dataset uses a loading script (its viewer is disabled), so either load with `trust_remote_code=True` in streaming mode, or download the per-category JSONL.GZ files linked on the dataset card directly. Streaming avoids downloading the full 750 GB.

```
# scripts/load_real_data.py (sketch)
from datasets import load_dataset

CATS = ["Home_and_Kitchen", "Pet_Supplies", "Health_and_Household"]
for cat in CATS:
    meta = load_dataset("McAuley-Lab/Amazon-Reviews-2023", f"raw_meta_{cat}",
                        split="full", streaming=True, trust_remote_code=True)
    # keep: parent_asin, title, store, main_category, categories, price,
    #       average_rating, rating_number, details
    # write rows to data/raw/{cat}_meta.parquet in chunks

    reviews = load_dataset("McAuley-Lab/Amazon-Reviews-2023", f"raw_review_{cat}",
                           split="full", streaming=True, trust_remote_code=True)
    # keep only: parent_asin, rating, timestamp, verified_purchase
    # filter to parent_asins of candidate brands (second pass)
```

## 5.4 Selecting underdog brands

1. Group item metadata by `store` (treat store as brand). Drop empty or generic stores (for example 'Amazon', 'Generic', 'Unknown').
2. Keep brands with **3 to 40 products** and **50 to 5,000 total ratings** (small but real).
3. Compute monthly verified review counts per brand from review timestamps (a real demand proxy).
4. Keep brands whose review velocity in the last 6 months of data is at least 20% higher than the prior 6 months (rising).
5. Sample about **60 per category** (about 180 total), stratified by price band and size, and deliberately include some flat or declining brands as distractors.
6. Anonymise: map each store to a generated name (for example 'Copperleaf Kitchen', 'Pawsmith', 'Hearthline') stored in `brand_alias.csv`. The UI, video and article only ever show aliases.

## 5.5 Time re-basing

Reviews end in September 2023. The simulation uses its own clock: the last 12 months of real review data are mapped onto simulated months 1 to 12 ending in the current demo season. The mapping is linear and documented in the README. Relative timing, seasonality and growth are preserved.

## 5.6 The simulator

The simulator produces weekly snapshots per product for 52 weeks (the last 12 are the demo season) and outreach outcomes for the 12 demo weeks. It is deterministic given a seed.

### Hidden archetypes

| Archetype | Share | What happens in the data |
| --- | --- | --- |
| Reseller invasion | 20% | Seller count jumps (for example 2 to 9) over 3 to 6 weeks; Buy Box share falls from above 90% to 50 to 70%; Buy Box price drops 5 to 15% a week or two later |
| Stockout-prone | 15% | Rank improves with demand, then repeated out-of-stock gaps of 3 to 10 days; rank worsens during and after each gap |
| Weak converter | 15% | Decent demand proxy but rating below category median or thin reviews; conversion index low |
| Price erosion | 10% | Buy Box price drifts down 15 to 25% over 3 to 5 months with 3 or more sellers |
| Under-advertised riser | 15% | Review velocity rising fast, ad presence index low, rank lags peers of similar velocity |
| Healthy riser | 15% | Steady improvement, stable sellers, no problems |
| Distractor | 10% | Flat or declining, noisy data |

### Generating signals (anchored on real data)

- **Demand index** per product per week = smoothed real verified review velocity scaled by a random conversion factor (reviews are a small fraction of sales).
- **Sales rank (BSR)** = category-specific inverse function of demand index, plus noise calibrated from the best-seller dataset's rank volatility, plus Prime Day and Q4 seasonality bumps.
- **Seller count, Buy Box share, Buy Box price, stock status, ad presence index** = generated from the archetype with causal links: sellers join, then Buy Box share falls within days, then price falls a week later.
- **Price** starts from the real `price` field; distribution of discounts calibrated from the Kaggle price datasets.
- Add missing values and small glitches (a week with no data) so the pipeline must handle them.

### Outreach outcomes (hidden ground truth)

For each pitch, the reply probability is computed from hidden rules, then an outcome is sampled. The agent never sees these rules.

```
# ground_truth.yaml (kept out of the app and memory; used only by simulator and eval)
base_reply_rate: 0.06
angle_fit:            # multiplier when angle matches the brand's real problem
  reseller_invasion: {brand_protection: 5.0, growth_partnership: 0.6, other: 1.2}
  stockout_prone:    {inventory_planning: 4.0, other: 1.1}
  weak_converter:    {listing_and_reviews: 3.5, other: 1.0}
  price_erosion:     {map_enforcement: 4.0, brand_protection: 2.5, other: 1.0}
  under_advertised:  {advertising: 4.0, other: 1.0}
  healthy_riser:     {growth_partnership: 1.2, other: 0.8}
category_modifier: {home_kitchen: 1.0, pet_supplies: 1.3, health_household: 0.25}
size_sweet_spot: {min_ratings: 50, max_ratings: 300, multiplier: 1.6}
severity_effect: 1.0 + 1.5 * severity          # worse problems reply more
in_house_flag_rate: 0.15                       # these decline generic pitches
reply_delay_weeks: [1, 3]
meeting_given_reply: 0.45
signed_given_meeting: 0.25
not_now_share_of_replies: 0.2                  # with a 'come back after X' reason
noise: 0.15                                    # random flips so patterns are not perfect
```

Reply texts are generated from templates with light LLM variation, for example 'Not the right time, we're stretched until after Q4' or 'We manage Amazon in-house, thanks'. Store them so replies are identical across runs.

## 5.7 Evaluation harness

- Run the 12-week season three ways with the same seed: **memory off** (base scores, fixed angle by diagnosis rule), **memory on** (Underdog), **oracle** (knows ground truth).
- Metrics per week: reply rate and meeting rate of the top 10, share of oracle meetings captured, angle accuracy, calibration (Brier score of predicted reply probability).
- Output `eval/results.json` and PNG charts used in the README and article. Run it in CI on a small seed to catch regressions.
- Report variance across 5 seeds so the result is not a lucky run.

## 5.8 Dataset outputs in the repo

| File | Contents | Committed? |
| --- | --- | --- |
| data/raw/* | Downloaded dataset files | No (gitignored; download script provided) |
| data/prepared/brands.parquet | Selected brands, anonymised, with real aggregates | Yes (derived, small) |
| data/prepared/products.parquet | Products for selected brands (title, category, price, rating), anonymised brand field | Yes |
| data/prepared/review_velocity.parquet | Weekly review counts per product (real) | Yes |
| data/sim/snapshots.parquet | Weekly simulated signals | Generated by script |
| data/sim/outcomes.parquet | Simulated outcomes per pitch | Generated by script |
| sim/ground_truth.yaml | Hidden rules | Yes, but never loaded by the agent |
| brand_alias.csv | Real store to alias mapping | No (private); ship only aliases |

# 6. Technical Requirements Document (TRD)

## 6.1 Architecture

```
  Real data (Hugging Face / Kaggle)            ground_truth.yaml (hidden)
          |                                           |
          v                                           v
  [Data prep scripts] --> prepared parquet --> [Simulator] --> snapshots + outcomes
                                                      |
                                     MarketplaceAdapter interface
                                  (SimulatedAdapter | KeepaAdapter)
                                                      |
  +---------------------------- FastAPI backend ------------------------------+
  |  Signal engine -> Diagnosis engine -> Scoring -> Agent loop (weekly)      |
  |        |                                   |            |                 |
  |     SQLite (app state)          MemoryService       LLMService           |
  |                                (hindsight-client)   (Groq, fallback)      |
  |  Eval harness (memory on / off / oracle)   |                              |
  +--------------------------------------------|------------------------------+
                                               v
                                   Hindsight Cloud (bank per agency)
                            retain / recall / reflect / observations /
                            mental models / directives / clone
                                               ^
  Next.js frontend  <---- REST + SSE (memory feed) ---- FastAPI
```

Key principle: **numbers in code, memory in Hindsight, words from the LLM.** SQLite holds structured app state (brands, snapshots, leads). Hindsight holds everything the agent should remember and learn from. The LLM explains and writes, and never computes a signal.

## 6.2 Technology stack

| Area | Choice | Why |
| --- | --- | --- |
| Language (backend) | Python 3.12 | Hindsight Python client, data tooling |
| API | FastAPI + Pydantic v2 + Uvicorn | Typed schemas shared with LLM validation |
| Data | Polars (or pandas) + PyArrow; SQLite via SQLModel | Fast local processing; zero-ops state |
| Memory | Hindsight Cloud via `hindsight-client` (Python) | Required; managed; clone and mental models |
| Memory (local dev) | Hindsight Docker image (optional) | Offline development; can use Groq as its LLM provider |
| LLM | Groq: openai/gpt-oss-120b primary, qwen/qwen3-32b fallback | Recommended by organisers; fast |
| Frontend | Next.js + TypeScript + Tailwind + Radix/shadcn + Recharts/visx + Framer Motion | See 4.7 |
| Streaming | Server-Sent Events for the memory feed | Simple, one-directional |
| Testing | pytest, hypothesis (simulator properties), Playwright (UI smoke) | Edge cases are 20% of the score |
| Deploy | Frontend on Vercel; backend on Render, Railway or Fly.io; Hindsight Cloud | Free or cheap tiers |

## 6.3 Repository structure

```
underdog/
  README.md                 # includes 'How Hindsight is used' section
  docker-compose.yml        # backend + optional local Hindsight
  Makefile                  # make data, make sim, make seed, make eval, make dev
  .env.example
  backend/
    app/
      main.py               # FastAPI app, routers
      config.py             # settings from env
      models.py             # SQLModel tables
      schemas.py            # Pydantic API + LLM output schemas
      adapters/
        base.py             # MarketplaceAdapter protocol
        simulated.py        # reads data/sim/*
        keepa.py            # stub with same interface
      engine/
        signals.py          # deterministic signal computation
        diagnosis.py        # rules + severity
        scoring.py          # base score, memory adjustment, clamp
        loop.py             # weekly agent loop
      memory/
        service.py          # all Hindsight calls go through here
        formats.py          # retain content templates, tags, doc ids
        bank_setup.py       # bank config, directives, mental models
      llm/
        client.py           # Groq wrapper: retries, fallback, validation
        prompts.py
      eval/harness.py       # memory on / off / oracle runs
      api/                  # routers: week, leads, brands, beliefs, metrics, feed
    tests/
  sim/
    simulator.py
    ground_truth.yaml
  scripts/
    load_real_data.py  select_brands.py  build_sim.py  seed_bank.py  run_eval.py
  data/ (raw gitignored, prepared committed)
  frontend/
    app/ (routes: /, /brands/[id], /outreach, /learned, /learning)
    components/  lib/  styles/tokens.css
  docs/ architecture.png  eval-curve.png  screenshots/
```

## 6.4 Data model (SQLite)

| Table | Key fields |
| --- | --- |
| brand | id, alias, category, n_products, total_ratings, avg_rating, price_min, price_max, archetype_hidden (sim only, never read by agent) |
| product | id, brand_id, parent_asin_hash, title, category_path, price, avg_rating, rating_number |
| snapshot | product_id, week, date, demand_index, bsr, seller_count, buybox_share, buybox_price, in_stock, ad_presence, review_count |
| brand_signal | brand_id, week, signal_name, value (aggregated to brand level) |
| diagnosis | brand_id, week, code, severity, evidence_json |
| lead | id, brand_id, week, base_score, memory_adj, final_score, rank, angle, reason, evidence_memory_ids, mode (on/off/oracle) |
| pitch | id, lead_id, sent_week, angle, draft_text, approved (bool) |
| outcome | id, pitch_id, week, type (no_reply, reply, meeting, proposal, signed, declined, not_now), reason_text, revisit_after |
| belief_snapshot | week, beliefs_json (structured output from reflect), diff_json |
| memory_event | ts, op (retain, recall, reflect, mental_model), summary, latency_ms, payload_ref (for the memory feed) |
| sim_clock | current_week, season_id, seed |

## 6.5 Hindsight design

### Bank

One bank per agency: `underdog-lanternfish`. A seed bank `underdog-seed-w8` is pre-built with weeks 1 to 8 so the demo can be reset instantly by cloning it.

```
from hindsight_client import Hindsight

hs = Hindsight(base_url=settings.HINDSIGHT_URL,   # https://api.hindsight.vectorize.io
               api_key=settings.HINDSIGHT_API_KEY, timeout=60.0)

hs.create_bank(
    bank_id="underdog-lanternfish",
    name="Underdog: Lanternfish Growth",
    mission=("I am the prospecting agent for an Amazon growth agency. I find brands "
             "with fixable marketplace problems and learn which brands and pitch "
             "angles lead to replies, meetings and signed clients."),
    disposition={"skepticism": 4, "literalism": 4, "empathy": 2},
)

hs.update_bank_config(
    "underdog-lanternfish",
    retain_mission=("Keep brand problems, their numbers and dates; every pitch, its "
                    "angle and my lead score; every outcome and the stated reason; "
                    "agency decisions. Ignore email pleasantries."),
    observations_mission=("Form durable beliefs about which brand segments, diagnoses, "
                          "categories and pitch angles lead to replies and meetings, "
                          "with counts. Track when a belief changes. Track my scoring errors."),
    reflect_mission=("You are a careful sales strategist. Ground every recommendation "
                     "in recorded outcomes and cite counts. Prefer evidence over intuition."),
)
```

_Method names and parameters follow the Hindsight Python client docs (v0.10). Check the current docs when implementing; wrap every call in MemoryService so any change is made in one place._

### Directives (hard rules for reflect)

- Never recommend contacting a brand through Amazon messaging.
- Never suggest sending an email without human approval.
- Always cite the outcomes or data behind a recommendation, with counts.
- Never name a past client in outreach; describe them generically (for example 'two kitchenware brands').
- Treat 'do not contact' as permanent.

### What gets retained, and how

| Memory | When | context | tags | document_id |
| --- | --- | --- | --- | --- |
| Brand state change | When a signal crosses a threshold, or every 4th week | marketplace snapshot | brand:<slug>, cat:<cat>, dx:<code>, kind:snapshot | snap:<brand>:w<NN> |
| Diagnosis | New or changed diagnosis | diagnosis | brand, cat, dx, kind:diagnosis | dx:<brand>:w<NN> |
| Pitch (agent's own action) | When a draft is approved | outreach I sent | brand, cat, dx, angle:<angle>, kind:pitch | pitch:<id> |
| Outcome | When logged or simulated | outreach outcome | brand, cat, dx, angle, outcome:<type>, kind:outcome | outcome:<id> |
| Agency decision | When the user sets a rule | agency decision | kind:decision | decision:<id> |

Every retain passes a real `timestamp` for the simulated date, so temporal questions work. `document_id` makes re-runs idempotent. Batches use `retain_batch(..., retain_async=True)` with an `operation_id` for safe retries.

```
items.append({
  "content": ("Week 6 (2026-08-10): Copperleaf Kitchen (Home & Kitchen, 14 products). "
              "Sellers on its top listing rose from 2 to 9 in 30 days. The brand held the "
              "Buy Box 58% of the time, down from 95%. Diagnosis: reseller invasion, "
              "severity 0.78."),
  "context": "marketplace snapshot",
  "timestamp": "2026-08-10T09:00:00Z",
  "document_id": "snap:copperleaf-kitchen:w06",
  "tags": ["brand:copperleaf-kitchen", "cat:home-kitchen",
           "dx:reseller-invasion", "kind:snapshot"],
  "observation_scopes": [["brand:copperleaf-kitchen"], ["dx:reseller-invasion"]],
  "metadata": {"week": "6", "severity": "0.78"},
})

# The agent's own action (experience)
"I pitched Copperleaf Kitchen on 2026-08-11 with the brand-protection angle, citing "
"Buy Box loss. My lead score was 0.71, rank 2 of 12."

# Outcome
"Copperleaf Kitchen replied on 2026-08-14 and booked a call. No objection raised."
"Hearthline replied on 2026-08-12: not now, stretched until after Q4. Revisit in January."
```

### Observation scopes

Use custom `observation_scopes` so beliefs form at the right levels without an explosion of passes. Per pitch or outcome, pass at most four scopes: `[dx]`, `[angle]`, `[dx, angle]`, `[cat]`, and add `[brand]` for brand-level history. Do not scope by week or kind tags (they are for filtering, not beliefs).

### Mental models (living pages shown in 'What I've learned')

| id | Name | source_query |
| --- | --- | --- |
| real-icp | Our real ICP | Based on outreach outcomes, which kinds of brands (category, size, diagnosis, signals) reply and book meetings, and which do not? Give counts. |
| angles-that-work | Pitch angles that work | For each diagnosis, which pitch angle gets replies and meetings and which fails? Give counts and one example each. |
| avoid | What to stop doing | Which segments, categories or behaviours should we stop pursuing, and what is the evidence? |
| revisit | Revisit list | Which brands said not now, when and why, and has their problem worsened since? |
| my-mistakes | Where my scores were wrong | Where were my lead scores or angle choices wrong, and what should change? |

```
hs.create_mental_model(
    bank_id=BANK, id="angles-that-work", name="Pitch angles that work",
    source_query="For each diagnosis, which pitch angle gets replies and meetings ...",
    trigger={"mode": "delta", "refresh_after_consolidation": True,
             "min_refresh_interval_seconds": 120},
)
```

Use `get_mental_model_history` to power the 'Changed: was X in week 4' line on belief cards.

### Recall and reflect usage by feature

| Feature | Call | Key parameters |
| --- | --- | --- |
| Lead drawer: 'What memory says' | recall | query about the brand and its diagnosis; tags=[brand:<slug>] with tags_match any (brand facts plus global); types world, experience, observation; budget mid; include_source_facts for evidence chips |
| Similar brands | recall | query 'outcomes for <dx> brands in <cat>'; tags [dx:<code>]; types observation, experience |
| Weekly prioritisation | reflect | candidate table in the query, including the simulated date; response_schema = PrioritisationResult; include_facts=True; budget mid |
| Belief extraction | reflect | response_schema = BeliefSet; budget high; run once per week after consolidation |
| Revisits | recall | query 'brands that said not now'; temporal_window over the past quarter; then compare to current signals in code |
| Memory feed | all | MemoryService logs each call to memory_event and streams it via SSE |

> **Simulated clock caution**
> Hindsight's recency and 'now' use real server time unless told otherwise. For recall, pass `query_timestamp` set to the simulated date. For reflect, which has no such parameter, state the simulated date in the query ('Today is 2026-08-17, week 7').

### Prioritisation schema (reflect structured output)

```
class LeadAdjustment(BaseModel):
    brand_id: str
    score_adjustment: float = Field(ge=-0.6, le=0.6)   # multiplicative
    recommended_angle: Literal["brand_protection", "inventory_planning",
        "listing_and_reviews", "map_enforcement", "advertising", "growth_partnership"]
    reason: str = Field(max_length=240)
    skip: bool = False
    revisit: bool = False

class PrioritisationResult(BaseModel):
    adjustments: list[LeadAdjustment]
    beliefs_used: list[str]

resp = hs.reflect(bank_id=BANK, query=prompt, budget="mid",
                  response_schema=PrioritisationResult.model_json_schema(),
                  include_facts=True)
result = PrioritisationResult.model_validate(resp.structured_output)
evidence = resp.based_on.memories   # shown as memory chips
```

### Belief schema

```
class Belief(BaseModel):
    id: str                      # stable slug, e.g. 'angle-reseller-invasion'
    group: Literal["who_converts", "which_angle", "avoid", "my_mistakes"]
    statement: str
    confidence: float = Field(ge=0, le=1)
    evidence_count: int

class BeliefSet(BaseModel):
    beliefs: list[Belief]
```

The backend diffs this week's BeliefSet against last week's by belief id (new, strengthened, weakened, reversed) and stores the diff, which drives the belief-card animation.

### Memory off baseline

Identical pipeline with MemoryService replaced by a no-op: final score equals base score, angle chosen by a fixed diagnosis-to-angle rule, drafts written from signals only. Same seed, same data.

## 6.6 Core algorithms

### Signals (brand level, per week)

- `review_velocity` = verified reviews in last 4 weeks; `velocity_growth` = last 13 weeks vs previous 13.
- `seller_delta_30d` = seller count now minus 30 days ago on the brand's top product.
- `buybox_share_30d` = share of days the brand held the Buy Box; plus previous 30 days.
- `oos_episodes_60d`, `price_change_90d`, `ad_presence`, `rating_gap` = rating minus category median.

### Scoring

```
base = 0.45*severity + 0.25*norm(velocity_growth) + 0.15*size_fit + 0.15*recency_of_change
final = clamp(base * (1 + memory_adj), 0, 1)       # memory_adj from reflect
if revisit and problem_worsened: final = max(final, 0.7)
if skip: move to Skipping tray with reason
Shortlist = top 12 by final score, max 5 per category, never a 'do not contact' brand
```

### Weekly loop (pseudo-code)

```
def run_week(week, mode):
    snaps = adapter.snapshots(week)
    signals = compute_signals(snaps)
    dxs = diagnose(signals)
    memory.retain_material_changes(week, signals, dxs)          # skip if mode == off
    candidates = top_n_by_base(dxs, n=40)
    adj = memory.prioritise(week, candidates) if mode == 'on' else {}
    leads = rank(candidates, adj)
    for lead in leads[:12]:
        lead.draft = llm.draft_email(lead, memory.context_for(lead))
        pitch = approve(lead)                                     # auto in simulation
        memory.retain_pitch(week, pitch)
    for outcome in adapter.outcomes_arriving(week):
        memory.retain_outcome(outcome)
    memory.wait_for_consolidation(timeout=90)                    # poll operations
    beliefs = memory.extract_beliefs(week); store_diff(beliefs)
```

## 6.7 API endpoints

| Method and path | Purpose |
| --- | --- |
| GET /api/health | Liveness plus Hindsight and Groq reachability |
| GET /api/week | Current simulated week and season |
| POST /api/week/advance | Run the loop for the next week (live demo button) |
| POST /api/demo/reset?to_week=8 | Clone the seed bank and reset app state |
| GET /api/shortlist?week=&mode=on\|off | Ranked leads with reasons and evidence |
| GET /api/leads/{id} | Lead detail with signals, diagnosis, memory context |
| POST /api/leads/{id}/draft | Generate or regenerate a draft (optional angle override) |
| POST /api/leads/{id}/approve | Approve draft, create pitch, retain it |
| POST /api/pitches/{id}/outcome | Log outcome with reason or revisit date, retain it |
| GET /api/brands/{id} | Brand dossier with full timeline |
| GET /api/beliefs?week= | Belief set and diff; mental model contents |
| GET /api/metrics/learning | Learning curves for on, off and oracle |
| GET /api/memory/feed (SSE) | Stream of memory events |

## 6.8 LLM layer (Groq) and function-calling robustness

The organisers specifically warn about function-calling errors, so this layer is a scoring opportunity.

1. All LLM outputs are requested as JSON matching a Pydantic schema (JSON mode or tool call).
2. Validate with Pydantic. On failure, retry once with a repair prompt that includes the validation error.
3. On a second failure or HTTP 429/5xx, switch to the fallback model (qwen/qwen3-32b), then to a deterministic template.
4. Timeouts: 20 s per call; exponential backoff with jitter on rate limits.
5. Temperature 0.3 for drafts, 0 for classification. Cache by input hash so reruns cost nothing.
6. Post-checks on drafts: under 120 words, no em dashes, mentions at least one brand data point, no past client names, includes an opt-out line.

```
def call_llm(schema, messages):
    for model in [PRIMARY, FALLBACK]:
        for attempt in range(2):
            try:
                raw = groq.chat(model=model, messages=messages, json=True, timeout=20)
                return schema.model_validate_json(raw)
            except ValidationError as e:
                messages = messages + [repair_message(e)]
            except (RateLimit, ServerError, Timeout):
                sleep(backoff(attempt))
    return schema.fallback_template()      # never break the demo
```

## 6.9 Edge cases and error handling

| Case | Handling |
| --- | --- |
| Reflect returns 500 (a retrieval tool failed) | Retry once; then use last week's cached adjustments and show 'Memory is catching up' banner |
| structured_output missing or structured_output_error present | Retry once; fall back to base scores; log to memory feed |
| Consolidation not finished when week ends | Poll operations up to 90 s; show 'Learning from N new outcomes'; beliefs update when done |
| Brand with missing weeks or no price | Signals tolerate gaps (forward fill up to 2 weeks, else mark unknown); diagnosis requires minimum data |
| Brand in two categories | Primary category from most products; tags include both |
| Conflicting outcomes (reply then decline) | Latest outcome wins for status; both retained with timestamps |
| Duplicate retain on rerun | Stable document_id makes it an upsert |
| 'Do not contact' brand appears again | Hard filter in code before scoring, plus a directive |
| Groq rate limited mid-demo | Cached drafts; template fallback |
| Hindsight unreachable | Memory-off mode automatically with a clear banner; nothing crashes |
| Prompt injection in reply text (e.g. 'ignore your rules') | Reply text retained as quoted data with context 'outreach outcome'; directives apply; Memory Defense enabled for prompt_injection |

## 6.10 Performance, cost and demo reliability

- Retain only material changes: roughly 180 brands, about 600 to 900 memories per season, not 180 times 52.
- Pre-seed weeks 1 to 8 once with `scripts/seed_bank.py`, then clone to reset (`aclone_bank`), which copies without re-running the LLM.
- Enable async retain; consider Hindsight's provider batch API only for the offline seed run.
- Precompute and cache all memory-off and oracle runs; only memory-on week 9 runs live.
- Frontend reads from the backend cache per week so the replay scrubber is instant.
- Budget check: watch Hindsight Cloud credit usage after the seed run; the $50 promo should cover development if retains are batched and selective.

## 6.11 Configuration and security

```
# .env.example
HINDSIGHT_URL=https://api.hindsight.vectorize.io
HINDSIGHT_API_KEY=
HINDSIGHT_BANK=underdog-lanternfish
HINDSIGHT_SEED_BANK=underdog-seed-w8
GROQ_API_KEY=
LLM_PRIMARY=openai/gpt-oss-120b
LLM_FALLBACK=qwen/qwen3-32b
SIM_SEED=42
DEMO_MODE=true          # serve cached responses where available
KEEPA_API_KEY=          # optional, unused by default
```

- Secrets only in environment variables; never committed. Add a pre-commit secret scan.
- Enable Hindsight Memory Defense on the bank with redaction for sensitive data and blocking for prompt injection.
- No real personal data: contacts are fictional; brands are anonymised.
- CORS limited to the frontend origin; simple shared-secret header for the demo API.

## 6.12 Testing strategy

| Level | What | Examples |
| --- | --- | --- |
| Unit | Signals, diagnosis rules, scoring | Reseller rule fires at exactly +3 sellers and 75% share; severity monotonic |
| Property | Simulator | Buy Box share always 0 to 1; price never negative; seeded runs identical |
| Contract | LLM and reflect schemas | Recorded fixtures validate; malformed output triggers repair then fallback |
| Integration | MemoryService against local Hindsight Docker | Retain then recall returns the fact; idempotent document_id |
| Evaluation | Harness on a small seed in CI | Memory on beats memory off by a margin across 3 seeds |
| UI smoke | Playwright | Shortlist renders; scrubber changes week; memory toggle splits view |
| Demo rehearsal | Scripted run of section 9 | Reset, advance one week, belief card animates, within 3 minutes |

## 6.13 Keepa adapter (path to production)

`KeepaAdapter` implements the same `MarketplaceAdapter` protocol: `brands(category)`, `snapshots(week)`, `storefront(seller_id)`. Seller storefront lookups cost 10 tokens and product lookups 1 token each, so a small hero set fits the starter plan. Show the stub and its tests in the README as the route to real data.

# 7. Implementation plan

The plan assumes about six working days. A compressed three-day version follows. Each phase ends with a demoable checkpoint so there is always something to show.

## 7.1 Roles (solo or team of up to four)

| Role | Owns | If solo |
| --- | --- | --- |
| A: Data and simulator | Dataset loading, brand selection, anonymisation, simulator, ground truth, eval harness | Days 1 to 2 |
| B: Backend and memory | FastAPI, signals, diagnoses, scoring, MemoryService, bank setup, LLM layer, loop | Days 2 to 4 |
| C: Frontend | Design tokens, all screens, belief animation, replay and toggle | Days 3 to 5 |
| D: Story and content | Demo script, README, article outline, video, screenshots, social post | Days 5 to 6 |

## 7.2 Day 0: setup (2 to 3 hours)

- Create public GitHub repo `underdog` with the structure in 6.3, MIT licence, `.env.example`, Makefile.
- Sign up for Hindsight Cloud, then add promo code **MEMHACK99** in billing. Create an API key. Join the Hindsight Community Slack.
- Get a Groq API key. Verify both models respond.
- Smoke test: retain, recall, reflect against a scratch bank from a 20-line script.
- Optional: run Hindsight locally with Docker for offline development.
- Install the Hindsight docs skill in your coding agent (`npx skills add https://github.com/vectorize-io/hindsight --skill hindsight-docs`).

## 7.3 Six-day plan

| Day | Goals | Tasks | Done when |
| --- | --- | --- | --- |
| 1 | Real data in | Stream 3 categories; select 180 underdog brands; weekly review velocity; anonymise; write prepared parquet | `make data` produces brands and products parquet; spot check 10 brands look real |
| 2 | Simulator and engine | Archetypes, causal signal generation, outcomes with hidden rules; signals, diagnoses, base scoring; memory-off loop; eval harness skeleton | `make sim && make eval` prints weekly memory-off metrics |
| 3 | Memory layer | MemoryService; bank config, directives, mental models; retain formats; prioritisation and belief reflect with schemas; seed script for weeks 1 to 8; clone reset | Memory-on beats memory-off in eval; beliefs change across weeks |
| 4 | API and LLM | All endpoints; Groq drafts with validation, retries, fallback; SSE memory feed; caching; edge cases in 6.9 | Every endpoint returns real data; failure injection does not crash |
| 5 | Frontend | Tokens and fonts; Shortlist, Lead drawer, Learned (with animation), Learning dashboard, Replay and memory toggle; then Dossier and Outreach | Full demo path works in the browser at 1440 px |
| 6 | Polish, proof, story | Tune noise; screenshots and charts; README with Hindsight section and architecture diagram; rehearse demo 3 times; record video; deploy | Deployed URL works; video uploaded; checklist items ticked |

## 7.4 Compressed three-day plan

| Day | Scope |
| --- | --- |
| 1 | Data prep for 2 categories (Home_and_Kitchen, Health_and_Household); 100 brands; simulator with 4 archetypes; signals and diagnoses; memory-off loop |
| 2 | Memory layer with prioritisation and belief reflect; seed bank; eval harness; API endpoints; Groq drafts with fallback |
| 3 | Frontend: Shortlist, Learned with animation, Learning chart, Replay with toggle; README; video; deploy. Skip Dossier, Outreach page and Keepa stub |

## 7.5 Definition of done (whole project)

- `make dev` runs the full app locally from a fresh clone with only API keys added.
- Memory on beats memory off on the learning chart across multiple seeds, with noise visible.
- At least one belief visibly changes during the live demo, with evidence.
- Every recommendation cites memories; nothing is sent without approval.
- README explains exactly how Hindsight is used, with code links.
- No real brand name appears in UI, video, screenshots or article.

# 8. Judging criteria map

Use this as the rehearsal checklist. For each criterion, the demo must show it and the README must explain it.

| Criterion (weight) | Show in the demo | Put in the README / article | Common trap to avoid |
| --- | --- | --- | --- |
| Innovation (30%) | The flip: 'we read marketplace data to find brands in trouble, then learn who says yes'. The Skipping tray. The agent changing its mind | Why existing lead tools do not learn from outcomes; the flipped storefront insight | Spending the demo on email writing |
| Hindsight memory (25%) | Memory feed showing retain and recall live; belief card changing; memory-off vs memory-on split; revisit brand resurfacing | Section 'How Hindsight is used' mapping each feature to retain, recall, reflect, observations, mental models, directives, clone | Using Hindsight only as a vector store |
| Technical (20%) | Failure handling moment (optional: toggle Groq off and show fallback); eval chart with seeds | Architecture diagram; adapter pattern; schema validation, retries, fallback; tests; eval harness | Unverifiable claims; a demo that crashes |
| User experience (15%) | Clean weekly shortlist; one keyboard flow; the signature animation | Screenshots; design principles; accessibility notes | Cluttered dashboards; jargon |
| Real-world impact (10%) | One line on value: one signed client pays for years of the tool | Pricing idea; Keepa adapter as route to production; who buys it | Vague 'this could help businesses' |

# 9. Demo script (3 minutes)

Pre-demo: reset to week 8 (`POST /api/demo/reset?to_week=8`), light theme, browser zoom 110%, memory feed drawer closed, notifications off.

| Time | Say (roughly) | Show |
| --- | --- | --- |
| 0:00 to 0:20 | "Amazon agencies cold-email the same brands with the same pitch, and never learn which ones say yes. Underdog fixes that." | This week screen, week 8 |
| 0:20 to 0:45 | "Here's a real product's review growth. On top of it, resellers pile onto the listing and the brand loses the Buy Box. The brand needs help and doesn't know it yet." | Lead drawer for top brand: signal chart |
| 0:45 to 1:05 | "Without memory, this is what you get." | Toggle Side by side: memory-off list with generic growth angle and supplement brands at the top |
| 1:05 to 1:40 | "With memory, Underdog has learned from 8 weeks of outcomes. It skips supplements, zero of thirty replied. It picks brand protection for this pattern, six of eleven replied. And this brand said 'after Q4', and its resellers doubled, so it's back." | Memory-on column; Skipping tray; memory chips; Revisit badge |
| 1:40 to 2:20 | "Let's run next week live." Log one surprising outcome. | Advance one week; memory feed shows retains; belief card animates: 'Learned from 3 new outcomes' |
| 2:20 to 2:45 | "And it's measurable. Same data, memory on versus off versus an oracle that knows the hidden rules." | Learning dashboard chart |
| 2:45 to 3:00 | "Hindsight is the brain: every brand timeline, every pitch, every outcome, turned into beliefs that change what it does next week." | What I've learned screen |

## 9.1 Backup plan

- Pre-recorded 3-minute video on the laptop desktop.
- `DEMO_MODE=true` serves cached reflect and draft responses if the network is slow.
- If Hindsight is unreachable, switch to the recorded video rather than demoing memory-off.

## 9.2 Likely judge questions

| Question | Answer |
| --- | --- |
| Didn't you just plant the pattern? | Yes, deliberately, so learning can be measured. The agent never sees the rules. Memory-off with the same data does not find them. Real deployments replace the simulator with live data through the adapter. |
| Why not a simple spreadsheet of reply rates? | Outcomes arrive late, reasons are text ('after Q4', 'in-house'), and the same lesson must transfer across brands and categories. Hindsight consolidates text outcomes into beliefs with evidence and keeps history when beliefs change. |
| Is this spam? | Tiny, targeted volumes; a human approves every email; opt-out included; never uses Amazon messaging; directives enforce it. |
| What's real? | Product catalogue, prices, ratings and review timelines. Marketplace dynamics and outcomes are simulated. Names are anonymised. |

# 10. Content deliverables

> **Rule**
> Never write the word "hackathon" in the article, post or hashtags. Frame Underdog as a real product.

## 10.1 Article (each team member)

- Platform: Medium, Dev.to, Hashnode, Substack or LinkedIn Articles. Public link.
- Length: about 1,300 to 1,500 words (satisfies both ranges in the guide).
- Include markdown links: Hindsight GitHub (https://github.com/vectorize-io/hindsight), Hindsight docs (https://hindsight.vectorize.io/), Vectorize agent memory (https://vectorize.io/what-is-agent-memory).
- Must include: a real code snippet (for example the prioritisation reflect call), a before/after example, an honest lesson or dead end, screenshots, and an architecture diagram.
- Tag Code.in. Then share as a link post on one subreddit: r/llmdevs, r/sideproject, r/aiagents or r/aimemory.
- If each member writes one, pick different angles to avoid duplicates (see titles below).

### Title ideas (no event wording)

- My prospecting agent learned to stop chasing fast-growing brands
- I gave a sales agent Hindsight memory. It started skipping leads.
- How I measured whether an agent actually learns (memory on vs off)
- Numbers in code, memory in Hindsight, words from the LLM
- Why my agent's best leads were brands in trouble
- What broke when I simulated 12 weeks of agent memory

### Suggested structure

1. Hook: the moment the agent refused to pitch supplement brands, with the count.
2. What Underdog does and how it fits together (diagram).
3. The core story: turning late, messy outcomes into beliefs with Hindsight (retain formats, observation scopes, mental models).
4. Code: the reflect call with a response schema and cited evidence.
5. Results: learning chart, memory on vs off, one belief that reversed.
6. Lessons: simulated clocks and query_timestamp, schema validation for tool calls, retaining less but better, and one dead end.

## 10.2 LinkedIn post (each team member)

- Under 800 characters; hook in the first two lines without hashtags or links.
- 3 to 7 concrete takeaways, at least one before/after behaviour change; mention Hindsight positively.
- GitHub repo link in the main post. Article URL as the first comment. Then a comment linking https://github.com/vectorize-io/hindsight.
- 3 to 5 hashtags on the last line only, from: #AIAgents #AI #Hindsight #AgentMemory #AIMemory #LLM.

### Draft to adapt

```
Most AI sales agents forget every reply they get.
Mine learned to stop pitching the brands I was most excited about.

I built Underdog: it reads Amazon marketplace signals, finds brands with a
fixable problem, pitches the fix, and learns from every outcome.

What changed once it had Hindsight agent memory:
Week 1: ranked fast growers first, generic pitch.
Week 8: skipped a whole category (0 of 30 replied), picked the angle that
won 6 of 11 times, and resurfaced a 'not now' brand when its problem got worse.

Lessons: compute numbers in code, let memory hold outcomes, validate every
tool call, and measure memory on vs off with the same data.

Repo: <github link>

#AIAgents #AgentMemory #Hindsight #LLM
```

_Replace every number with your real evaluation results before posting, and say the outcomes are simulated if you quote them._

## 10.3 Team video

- 2 to 5 minutes (aim for 3), 1080p minimum, screen recording with voiceover; talking head plus screen preferred.
- Structure from the guide: intro (30 s), problem without memory (30 s), live demo with retain and recall (2 min), one takeaway (30 s).
- Increase font size, close notifications, use OBS, Loom, QuickTime or Filmora.
- Upload publicly to YouTube with a Nano Banana thumbnail (16:9, include a team member's photo).

### Video title ideas

- I built an AI agent that learns which brands say yes
- Memory on vs memory off: watch this agent get smarter in 12 weeks
- My sales agent refused to pitch these brands. It was right.

# 11. README outline

1. Title, one-line pitch, hero screenshot or GIF of the belief card changing.
2. The problem (3 sentences) and what Underdog does (the weekly loop).
3. Demo video link and live URL.
4. **How Hindsight is used** (the most important section): table mapping each feature to retain, recall, reflect, observations, mental models, directives and bank clone, with links to the code in `backend/app/memory/`.
5. Architecture diagram and the principle 'numbers in code, memory in Hindsight, words from the LLM'.
6. Data: what is real (Amazon Reviews 2023 citation), what is simulated, anonymisation, time re-basing.
7. Results: learning chart, memory on vs off vs oracle across seeds, honest caveats.
8. Quick start: prerequisites, `.env`, `make data`, `make sim`, `make seed`, `make dev`.
9. Robustness: schema validation, retries, fallback model, failure modes table.
10. Path to production: Keepa adapter, Gmail approval flow.
11. Tests and evaluation commands.
12. Credits and licences (dataset citation, Hindsight, Groq).

## 11.1 Dataset citation to include

```
Hou, Y., Li, J., He, Z., Yan, A., Chen, X., and McAuley, J. (2024).
Bridging Language and Items for Retrieval and Recommendation. arXiv:2403.03952.
Dataset: McAuley-Lab/Amazon-Reviews-2023 on Hugging Face.
```

# 12. Final submission checklist

## Accounts and setup

|   | Item |
| --- | --- |
| ☐ | Hindsight Cloud account; MEMHACK99 added in billing after registration |
| ☐ | Groq API key; both models tested |
| ☐ | Joined the Hindsight Community Slack |
| ☐ | Public GitHub repo created with licence |

## Product

|   | Item |
| --- | --- |
| ☐ | Real data loaded for 3 categories; brands anonymised |
| ☐ | Simulator with hidden ground truth; seeded and reproducible |
| ☐ | Signals, diagnoses and scoring computed in code with tests |
| ☐ | Hindsight bank configured: missions, disposition, directives, mental models |
| ☐ | Retain uses timestamps, tags, document IDs and observation scopes |
| ☐ | Prioritisation and belief extraction via reflect with response schemas and cited evidence |
| ☐ | Memory-off baseline and oracle runs |
| ☐ | Groq calls validated, retried, with fallback model and template |
| ☐ | Seed bank and clone-based demo reset |
| ☐ | Screens: Shortlist, Lead drawer, What I've learned (animated), Learning dashboard, Replay with memory toggle |
| ☐ | Memory feed shows retain and recall live |
| ☐ | Every edge case in 6.9 handled without a crash |
| ☐ | Deployed frontend and backend URLs work from a fresh browser |

## Proof and repo

|   | Item |
| --- | --- |
| ☐ | Eval harness results across multiple seeds; chart saved to docs/ |
| ☐ | README with 'How Hindsight is used', architecture diagram, data honesty statement, quick start |
| ☐ | No secrets in the repo; .env.example present |
| ☐ | No real brand names anywhere in the UI, screenshots, video or article |
| ☐ | Dataset citation included |

## Demo

|   | Item |
| --- | --- |
| ☐ | Demo script rehearsed at least three times within 3 minutes |
| ☐ | Reset to week 8 tested |
| ☐ | Backup video on the laptop; DEMO_MODE cache warmed |
| ☐ | Answers ready for the judge questions in 9.2 |

## Content (every team member)

|   | Item |
| --- | --- |
| ☐ | Article published publicly (about 1,300 to 1,500 words), no event wording anywhere |
| ☐ | Article includes the three Hindsight links, a code snippet, before/after, a lesson, screenshots |
| ☐ | Code.in tagged |
| ☐ | Article shared as a link post on one of the listed subreddits |
| ☐ | LinkedIn post under 800 characters, repo link in the post, 3 to 5 allowed hashtags on the last line |
| ☐ | First comment: article URL; second comment: Hindsight GitHub link |

## Team video

|   | Item |
| --- | --- |
| ☐ | 2 to 5 minutes, 1080p, voiceover (talking head plus screen preferred) |
| ☐ | Public on YouTube with Nano Banana thumbnail |
| ☐ | Shows the problem without memory and retain/recall live |

## Final submission

|   | Item |
| --- | --- |
| ☐ | GitHub repo link |
| ☐ | Demo video link |
| ☐ | Live demo slot confirmed |
| ☐ | Article, social post and Reddit links for every member |
| ☐ | Explanation of how Hindsight memory is used |

# Appendix A. Prompt templates

## A.1 Weekly prioritisation (reflect query)

```
Today is {sim_date} (week {week} of the season).
You are prioritising which Amazon brands our agency should contact this week.
Use everything you have learned from past pitches and outcomes.
For each candidate below, return a score adjustment between -0.6 and 0.6,
the pitch angle most likely to get a reply, a one-sentence reason with counts,
and whether to skip it or treat it as a revisit.
Candidates (id | category | products | ratings | diagnosis | severity | key signals):
{candidate_table}
```

## A.2 Email draft (Groq)

```
System: You write short, specific outreach emails for an Amazon growth agency.
Rules: under 120 words; plain language; no em dashes; cite one or two numbers from
the brand's data; never name another client; one clear question; include the line
'Reply stop and I won't email again.' Return JSON {subject, body}.
User: Brand: {alias}. Contact first name: {first_name}. Diagnosis: {dx}.
Evidence: {signals}. Angle: {angle}. What memory says: {memory_context}.
```

## A.3 Reply text generator (simulator, templates first)

```
positive:  'Timing is good actually. Can you do Thursday?'
not_now:   'Not the right time, we are stretched until after {period}.'
declined:  'We manage Amazon in-house, thanks.' | 'We already work with an agency.'
no_reply:  (nothing)
```

# Appendix B. Glossary for judges and readers

| Term | Plain meaning |
| --- | --- |
| ASIN | Amazon's product ID |
| BSR (Best Sellers Rank) | How well a product sells relative to its category; lower is better |
| Buy Box | The main 'Add to cart' offer on a listing; the seller who holds it gets most sales |
| Reseller | A third party selling the same product on the brand's listing |
| FBA | Fulfilled by Amazon: Amazon stores and ships the stock |
| MAP | Minimum advertised price a brand asks resellers to respect |
| PPC | Pay-per-click advertising on Amazon |
| Retain / Recall / Reflect | Hindsight's store / search / reason operations |
| Observation | A belief Hindsight consolidates from many memories, with evidence and history |
| Mental model | A living page Hindsight keeps up to date for a standing question |

# Appendix C. Sources checked for this document

- HackwithHyderabad 3.0 Problem Statement and Hackathon Content Guide (provided documents; internal only, do not quote event names in public content)
- Hindsight documentation v0.10: overview, retain, recall, reflect, memory banks, mental models, Python client (hindsight.vectorize.io)
- Hindsight GitHub repository (github.com/vectorize-io/hindsight)
- Amazon Reviews 2023 dataset card (huggingface.co/datasets/McAuley-Lab/Amazon-Reviews-2023)
- Kaggle dataset pages listed in 5.1
- Keepa API documentation (keepa.com/api-docs) for adapter token costs
