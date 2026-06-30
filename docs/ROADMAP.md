# WaiverEdge — Roadmap

> Sequenced to merge the **business repositioning** (be the injury-reaction tool;
> gate on a *taste* of personalization; make the share the growth loop; narrow to
> **NBA on Yahoo** first) with the **engineering priorities** from the code review.
> Phases are ordered by leverage: fix what's unsafe → ship the wedge → prove demand →
> harden → earn model credibility → expand.

**Guiding principle:** the only un-retired risk is *distribution + conversion*, not
tech. Every phase past 0 should move one of: time-to-first-aha, conversion, or share
rate. Don't expand surface area (sports/platforms) until the NBA/Yahoo loop is loved.

### Progress snapshot
- **Phase 0 — ✅ Done.** PRs #59 (ESPN collision), #60 (CORS), #61 (app_secret guard),
  #62 (CI), plus #66 (render.yaml CORS follow-up). 0.4 (key rotation) is a manual op.
- **Phase 1 — 🟡 In progress.** The in-app injury-alert loop is live: per-league recs
  already existed; NBA injury feed (#63), auto-scan (#65), hourly injury refresh (#67),
  and Resend email delivery (#69) are merged. **Remaining:** taste paywall (1d, feature-flagged,
  disabled by default — flip `TASTE_PAYWALL_ENABLED=true` to activate).

---

## Phase 0 — Stop the bleeding (security & correctness)
**Goal:** nothing unsafe or embarrassing ships to a real user. ~1 day.
**Do this regardless of strategy.**

| # | Task | File | Done when |
|---|------|------|-----------|
| 0.1 | Fix ESPN account collision — key user on `league_id + team_id` (+sport), not `league_id` alone | `backend/app/api/espn.py:124` | Two users on the same public ESPN league get distinct accounts (test) |
| 0.2 | Lock CORS to actual frontend domain(s); drop the `*.vercel.app` wildcard | `backend/app/main.py:88` | Regex removed or scoped to your deploy URLs |
| 0.3 | Fail-fast if `app_secret` is still the default outside dev | `backend/app/config.py:39` | Server refuses to boot in prod with `change-me-in-production` |
| 0.4 | Rotate the local API keys (no git exposure, but cheap insurance) | local `.env` | balldontlie/Yahoo/Stripe-test keys regenerated |
| 0.5 | Add minimal CI (pytest + `npm run build`/lint on PR) | `.github/workflows/ci.yml` (new) | Green check required to merge; 110 backend tests gated |

**Success criteria:** P0 bugs closed, CI gating merges, no default secrets in prod.

---

## Phase 1 — The wedge: injury-alert loop + personalized taste
**Goal:** ship the actual product — "tell me the one move to make *right now*" — for
**NBA on Yahoo only**. This is the repositioning made real. ~2–3 weeks.

### 1a. Per-user recommendations (the paid value prop) — ✅ already shipped
- Per-league recs already exist via `GET /api/leagues/{id}/recs` (Pro-gated), using the
  connection's roster + league weights. The `/api/recommendations/{connection_id}` stub
  in `main.py` is a redundant TODO and can be removed.

### 1b. Injury-alert producer (the headline feature) — ✅ done (#63, #65, #67)
- NBA injury feed from ESPN's free API → `injuries.json` (#63) — **no paid dependency**.
- Auto-scan in the scheduler creates `InjuryAlert` rows for connected leagues (#65).
- Hourly injury-only refresh keeps alerts timely without a full rebuild (#67).

### 1c. Delivery — ✅ done (#69)
- Resend HTTP integration. Pro users with real emails receive injury alert emails.
  No-ops when `RESEND_API_KEY` is unset.

### 1d. Gate on a *taste* of personalization (conversion lever) — 🟡 implemented, flag off
- Free: connect a league + see **your #1 move**; ranks 2–10 blurred; generic streamers.
- Pro: full ranked list + injury alerts + unlimited leagues.
- Move the paywall off "generic vs nothing" and onto "one taste vs your whole answer."
  Frontend paywall today keys on a fragile `"__paywall__"` string — replace with a typed
  402 contract.

**Success criteria:** a Yahoo NBA user connects, sees their top move free, gets an injury
alert within minutes of a real ruling, and the upgrade path is one click. Time-to-first-aha
< 60s from landing.

---

## Phase 2 — Growth loop + validate willingness-to-pay
**Goal:** make the product spread itself, and *prove* demand before building more. ~1–2 weeks.

| # | Task | Why |
|---|------|-----|
| 2.1 | **Shareable action-list card** — auto-generate a clean "my Week N moves" image with watermark + link | Every group-chat paste is a free ad; beats SEO for cold-start |
| 2.2 | Public SEO streamers page (per-week URLs) | Recurring search intent; the free magnet |
| 2.3 | **Annual-first pricing** — make the **$49 season pass the default**, monthly the pricier per-month option | Kills churn (the seasonality fix); raises ARPU |
| 2.4 | Price a notch higher ($10–12/mo) — a money-league edge is underpriced at $8 | WTP is real; test it |
| 2.5 | WTP pre-order test — "get injury alerts — $X" button capturing intent/emails | Validates the *only* un-retired risk before more eng |

**Success criteria:** measurable share rate per active user; a real conversion number
(even small) from the pre-order/taste flow to replace the assumed 4%.

---

## Phase 3 — Harden for paying customers
**Goal:** the app degrades gracefully and doesn't lie when an upstream fails. ~1–2 weeks.
**Trigger this once Phase 1 has real users — not before.**

- **Defensive external calls:** ESPN/Yahoo/stats adapters swallow exceptions and return
  `[]` (looks like "no free agents"). Surface errors; add backoff + a simple circuit
  breaker. Bound background fixture builds so they can't show "building…" forever.
  (`backend/app/data/*`, `recommendations.py`)
- **Validate at boundaries:** injury status → enum (`engine.py`); required fixture keys on
  load (`recommendations.py`); a few Zod schemas for API payloads on the frontend.
- **Frontend resilience:** typed API responses, one shared fetch hook (retry/error/loading
  is duplicated across pages), skeletons on the league page, a handful of Playwright tests
  for the connect→recs→upgrade path.
- **De-risk schema drift:** centralize the scattered ESPN/Yahoo/MLB stat-ID maps; dedup the
  three near-identical fixture builders (~500 lines).

**Success criteria:** an upstream outage produces a clear user-facing state, never a silent
empty list; connect→recs→upgrade is covered by an automated test.

---

## Phase 4 — Model credibility & expansion
**Goal:** make the rankings defensible, then widen the funnel. Ongoing.

- **Backtest the magic numbers** (`RECENCY_DECAY=0.85`, `ROLE_BUMP=1.15`, availability
  ladder, `MIN_SAMPLE`): project vs. actual on historical weeks. Turns "plausible" into
  "defensible" — and the backtest itself is marketing.
- **Confidence signal:** even a coarse `low_confidence` flag in the rationale stops
  thin-data recs (3-game rookies) from ranking like stable veterans.
- **Multi-week horizon:** engine is hardcoded to a 1-week window; parameterize it — playoff
  weeks are the highest-leverage fantasy moment.
- **Then expand surface area** (only now): ESPN as a first-class path, MLB, multi-league
  dashboard. The sport registry already makes this config-shaped.

**Success criteria:** a published backtest; rankings carry confidence; window length is a
parameter; expansion reuses the engine unchanged.

---

## What we are deliberately NOT doing yet
- Multi-sport / multi-platform GTM — infra stays, but focus is **NBA on Yahoo** until loved.
- Paid acquisition — organic + the share loop until LTV is proven.
- DFS affiliate / API tier — revenue stacking is real but additive; it comes after the
  subscription floor exists.
- Charging on top of the ESPN cookie hack — Yahoo official API is what we stake money on.

## Sequencing at a glance
```
Phase 0  (days)      safety + CI            ── must, regardless
Phase 1  (2–3 wk)    injury loop + taste    ── the product / first dollars
Phase 2  (1–2 wk)    share loop + WTP test  ── distribution / proof
Phase 3  (1–2 wk)    harden                 ── once real users arrive
Phase 4  (ongoing)   credibility + expand   ── widen the funnel
```
First dollars are realistically **Phase 0 + Phase 1**: one league-import + one injury
alert + one paywall away.
