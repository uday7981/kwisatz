# Underdog — Live Demo Script

**Target duration:** 3:00. One continuous take, no cuts.

---

## Pre-flight (do this ~90 seconds before hitting record)

Warm the caches so everything is instant on camera:

```bash
# Warm shortlist reflects (three attempts per week to land good adjustments)
for w in 43 44 45; do
  for i in 1 2 3; do
    curl -s "http://127.0.0.1:8000/api/shortlist?week=$w&mode=on" > /dev/null
    sleep 2
  done
done

# Warm beliefs for the diff moment
curl -s "http://127.0.0.1:8000/api/beliefs?week=44" > /dev/null
sleep 3
curl -s "http://127.0.0.1:8000/api/beliefs?week=45" > /dev/null

# Warm analytics
curl -s "http://127.0.0.1:8000/api/analytics" > /dev/null
```

### Browser sanity check at http://localhost:3000/

- Sidebar shows: **This week · Beliefs · Analytics**
- Pipeline strip shows numbers like `180 · 57 · 4 · 12` (memory value greater than 0)
- At least 2 or 3 shortlist rows show a green `up memory +XX%` arrow
- No red banners, no "memory unreachable" state
- Full-screen browser, 1440×900 or larger, light theme, cursor visible, all other tabs closed

---

## The script — 3:00 target

### 0:00 to 0:15 · Hook (15 seconds)

**Say (steady, no rush):**

> Amazon growth agencies cold-email the same brands every week and never learn who actually converts. Underdog is a prospecting agent built on Hindsight. It remembers every pitch and outcome and adjusts who it recommends next week.

**Do:** Sit still on `/`. Do not touch the mouse. Let the numbers on screen do the setup.

---

### 0:15 to 0:45 · The pipeline (30 seconds)

**Say (move cursor across the pipeline strip left to right as you name each number):**

> Every Monday it does the same walk. Scans 180 brands from public marketplace data. 57 show a fireable diagnosis: reseller invasion, stockout risk, price erosion. Memory reranks a handful based on 20 weeks of outreach outcomes. And that gives us this week's twelve.

**Do:** End with cursor on the `SHORTLIST 12` cell.

---

### 0:45 to 1:00 · Memory arrows (15 seconds)

**Say:**

> You can see where memory intervened. These arrows next to the scores. This brand got a 30 percent boost. Without memory, it wouldn't be at the top.

**Do:** Move cursor to the highest `up memory +XX%` label. Hover for a beat so viewers see it.

---

### 1:00 to 1:45 · Inside a lead (45 seconds)

**Say:**

> Let's open the top one.

**Do:** Click the top row (the whole row is clickable). Dossier loads.

**Say (as sparklines render):**

> Pet Supplies brand. Buy Box share collapsed to 40 percent. Resellers piled onto their top listing. Real, fixable problem, and they don't know it yet.

**Do:** Cursor briefly touches the Buy Box sparkline.

**Say (pointing at the "What memory says" sidebar):**

> On the right, what memory knows. The actual signals it noticed. Every past pitch we've sent. Let me draft.

**Do:** Press `A`. Wait about 3 seconds.

**Say (as email appears):**

> Grok wrote it grounded in this brand's actual numbers. Angle is brand protection. That's what memory recommends. Approved.

**Do:** Press `A` again. Button changes to "approved". The outcome row appears.

**Say:**

> Say they book a meeting.

**Do:** Press `3`. "logged" appears in green.

---

### 1:45 to 2:30 · Beliefs — the wow moment (45 seconds)

**Say:**

> That outcome just landed in Hindsight. Let me show you what memory now believes.

**Do:** Click **Beliefs** in the sidebar.

**Say (cursor moves through the four sections as you name them):**

> Four groups. Angles that work: brand protection converts reseller-invasion brands. Who converts: pet supplies replies more than health. What to avoid: brands with existing agencies keep declining, so memory stops pitching them. And where the scoring was wrong.

**Do:** Cursor briefly hovers over one card per section.

**Say:**

> Watch what happens when we advance a week.

**Do:** Press `]`. Cards animate. Look for the small colored dots and words in the top-right of a card, like `new` (green) or `stronger` (yellow). The summary line above the sections reads "Since week 44: 2 new · 1 stronger".

**Say (pointing at the summary line and a badge):**

> Since last week: two new beliefs, one got stronger. Memory saw the outcomes that landed, consolidated them into observations, and the belief cards updated. That's the loop. The agent isn't just running rules. It's forming beliefs from what actually happened.

---

### 2:30 to 2:50 · Analytics (20 seconds)

**Say:**

> And across the whole season...

**Do:** Click **Analytics** in the sidebar.

**Say (cursor sweeps across the numbers row):**

> 180 brands watched, 735 diagnoses fired, 144 shortlist slots. Balanced across three problem types and three pitch angles. Home and Kitchen edging out the others by category.

**Do:** Cursor briefly touches the diagnosis stacked bar and the horizontal angle bars.

---

### 2:50 to 3:00 · Close (10 seconds)

**Say:**

> Every outcome flows back into memory. Next Monday's shortlist reflects it. Memory is the product. Thanks.

**Do:** Stop recording.

---

## Keystrokes to memorize

| Key | Where | Effect |
| --- | --- | --- |
| Click a row | `/` | opens the brand dossier |
| A | dossier | 1st press: generates the draft. 2nd press: approves it |
| 3 | after approve | logs "meeting" outcome |
| ] | `/learned` | advance a week; triggers belief diff animation |
| Esc or Backspace | dossier | back to shortlist |

---

## Backup lines if something breaks live

| Symptom | What to say |
| --- | --- |
| MEMORY 0 on pipeline strip | "Memory's still consolidating this week." Then move on to click a lead. |
| Row has no memory arrow | Click a different row. Pick one that has an arrow. |
| Draft takes more than 5 seconds | "Grok warming up." While waiting, hover the memory sidebar. |
| Belief cards empty after `]` | Press `]` again to force refetch, or say "Consolidation catches up" and skip to Analytics. |
| No badges appear on belief cards | Just say "beliefs updated with the fresh outcomes" without pointing at badges. |
| Any endpoint returns 500 | Refresh the page once. Say "one sec." Resume. |

---

## Voice notes

- Rate: about 150 words per minute. Slower than natural conversation.
- Pause about 1 second after each section transition.
- Land the closing line "Memory is the product" clearly. That's the sentence viewers will remember.

## Words to strike from your vocabulary for the take

- "Hackathon", "prototype", "MVP", "demo", "just". These all undercut the product.
- "AI" as a noun. Say "the agent", "memory", or "Hindsight".
- "So basically" and "essentially". Filler.
- Long "uhh" pauses. Better to cut and restart the segment.

---

## Before the real take

1. One silent run-through (no recording, just walk through the actions).
2. One full record as the take.
3. Watch it back. If it lands between 2:50 and 3:10, ship it.

If your first take feels off in the middle, don't try to save it. Restart. Editing kills the pacing.
