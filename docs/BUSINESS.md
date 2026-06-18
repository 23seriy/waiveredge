# WaiverEdge — Product & Business Plan

> **Purpose of this project: make money.** This document explains the idea and,
> in detail, how it earns — the model, the pricing, the unit economics, realistic
> revenue scenarios, and the path to first dollars. Numbers marked *(illustrative)*
> are planning assumptions to validate, not promises.

---

## TL;DR

- **What:** a fantasy sports "move-finder" SaaS — starting with **NBA basketball**
  and expanding to **MLB baseball**. It tells a manager exactly which
  waiver/streaming move to make *right now* for *their* roster, by fusing schedule
  density × matchups × injuries — the cross-referencing serious players do by hand
  across 3+ tools today.
- **Why it earns:** fantasy managers are a **proven paying audience** with weekly,
  high-engagement need during lengthy seasons (NBA Oct–Apr, MLB Apr–Oct — nearly
  year-round coverage). Competing tools already charge $5–15/mo, which validates
  willingness-to-pay.
- **How it earns:** primarily a **freemium subscription** ($8/mo or a discounted
  season pass), with the free tier as a cheap acquisition funnel. Secondary stacked
  revenue: DFS affiliate referrals, a data/API tier for creators, and off-season
  products to fight seasonality.
- **Why it can be profitable solo:** costs are tiny (~$150–300/mo fixed, near-zero
  per user) → **~90% gross margin**. Acquisition is organic-heavy (Reddit + SEO),
  keeping CAC low against a multi-season LTV.

---

## Part 1 — The Idea

### The problem
Winning season-long fantasy sports (basketball, baseball, and beyond) is driven
by three things that change daily:

1. **Schedule density** — a player on a team with 4 games this week out-produces an
   equal player whose team plays 2. "Streaming" players for extra games is the single
   biggest weekly lever in head-to-head leagues.
2. **Matchups** — players score more against weak defenses (defense-vs-position).
3. **Injuries / role changes** — when a starter sits, his backup's minutes and value
   spike *immediately*; the first manager to grab him wins.

Serious managers currently juggle **3+ separate tools** to cross-reference these
(Hashtag Basketball for schedules, Basketball Monster for projections, FantasyPros for
start/sit) — and still have to mentally combine them against *their own* open roster
spots. Nobody fuses all of it into a single answer.

### The product
WaiverEdge connects to a manager's league, then outputs a **ranked "do this now"
action list**:

> *"Add Tyler Herro (drop Jaren Jackson Jr.): 5 games this week, 2 soft matchups —
> +92 projected points for your roster."*

It does the fusion (schedule × matchup × injury × **your** open slots → value over
replacement) so the user doesn't have to. **The engine already exists and is validated
on real NBA data** (see [validation](#proof-its-real)).

### Who it's for
**Serious season-long fantasy sports managers** — starting with basketball (head-to-head
and roto) and expanding to baseball. Competitive leagues (money leagues, long-running
friend leagues, multi-team managers). This is a deliberately *narrow, high-intent*
niche: they have a recurring weekly job, real stakes, and a demonstrated habit of
paying for an edge. Multi-sport coverage (NBA Oct–Apr + MLB Apr–Oct) creates
**near year-round engagement**, reducing seasonality — the biggest risk in a
single-sport tool.

### Why now
- LLMs make per-recommendation **natural-language rationales** and **injury-report
  parsing** cheap — a solo dev can ship the "explain why" layer that used to need an
  editorial team.
- Free NBA data (stats.nba.com / balldontlie) makes the underlying numbers accessible.
- Incumbent fantasy platforms (Sleeper, Yahoo, ESPN) treat basketball as second-class
  with laggy injury feeds — leaving room for a focused tool.

### Proof it's real
The scoring engine is built and validated on **3,346 real NBA box-score rows** from
stats.nba.com. It correctly ranks the league's top scorer (Luka Dončić) *out* of the
weekly top-10 when his team only plays 3 games, while elevating 5-game role players —
exactly the logic managers pay for. See `README.md` and `scripts/validate_nba_api.py`.

---

## Part 2 — Why This Makes Money

The hardest question for any consumer product is "will anyone pay?" For fantasy tools,
that's **already answered** — the market tells us:

| Signal | Evidence |
|---|---|
| Direct competitors charge money | Basketball Monster, Hashtag Basketball Premium, FantasyPros, RotoWire — all paid, $5–15/mo |
| The need is **recurring & weekly** | Managers set lineups and work the waiver wire every few days for ~7 months |
| The stakes are real | Money leagues + pride leagues create genuine willingness-to-pay for an edge |
| A captive community exists | r/fantasybball and similar are large, active, and tool-hungry |
| Low compliance burden | No gambling exposure (vs. the betting lane) → no licensing/geofencing cost |

We're not betting on creating demand — we're **better-packaging demand that already
pays**. The wedge is fusion + a faster injury feed, not inventing a new behavior.

---

## Part 3 — The Monetization Model

The strategy is **revenue stacking**: a recurring subscription floor, plus additive
streams that reuse the same engine and audience.

### 3.1 Primary: Freemium subscription

**Free tier (the acquisition funnel — designed to be shared and to rank in search):**
- Weekly schedule-density grid (games per team)
- Generic "top streamers this week" list
- Basic player projections

**Pro — $8/mo, or $39/season *(illustrative)*** *(season ≈ 7 months, a ~30% discount vs monthly):*
- The personalized **"for YOUR roster"** ranked action list (the core value)
- **Live injury alerts** (push/email) — the killer feature
- Unlimited leagues, advanced/era-adjusted projections, daily "stream tonight"

**Power — $15/mo *(illustrative)*** *(multi-league grinders & the most engaged):*
- Multi-league dashboard, head-to-head category targeting
- DFS slate tools, trade analyzer
- Data/API access (see 3.3)

The gate is deliberate: **free answers "what's happening," paid answers "what should
*I* do."** Personalization + injury alerts are what people pay for.

### 3.2 Secondary: DFS affiliate referrals
Your audience overlaps heavily with DFS pick'em players (PrizePicks, Underdog). A
non-intrusive "try this slate" referral earns **affiliate/CPA per converted user** —
often far more than a month of subscription. You **never take a bet** (you're a
referrer), so this stays light-touch: add responsible-gambling disclaimers and
geo-awareness. This is *optional and additive* — it does not compromise the
compliance-free positioning of the core fantasy product.

### 3.3 Secondary: Data/API for creators & media
The cleaned projections + streamer rankings + injury-parsed feed are valuable to
fantasy **newsletter writers, podcasters, and small media sites**. Sell an API/embed
tier (e.g., $49–199/mo *(illustrative)*). Same engine, near-zero marginal cost, and
these customers also become distribution (they cite you).

### 3.4 Secondary: Sponsorship & off-season products
- **Sponsorship:** fantasy-adjacent brands sponsor the free weekly streamer content.
- **Off-season (anti-seasonality):** a **Draft Kit** (Sept–Oct) and **dynasty/keeper**
  tools convert your in-season audience into off-season revenue and reduce churn.

### 3.5 How the streams reinforce each other
```
 Free tools  ──SEO/Reddit──▶  Audience  ──┬──▶  Pro/Power subscriptions   (recurring floor)
                                          ├──▶  DFS affiliate CPA          (high-value spikes)
                                          ├──▶  API/data tier              (B2B upside)
                                          └──▶  Sponsorship + off-season   (fills the calendar)
```
One engine, one audience, four ways to monetize.

---

## Part 4 — Unit Economics & Revenue Scenarios

### 4.1 Cost structure (why margins are high)
| Item | Monthly *(illustrative)* |
|---|---|
| Data feed (balldontlie ALL-STAR $9.99 → GOAT $39.99 at scale) | $10–40 |
| Hosting + Postgres (Railway/Fly/Neon) | $25–120 |
| Email/push (alerts) | $20–50 |
| Domain, misc SaaS | $10–30 |
| **Fixed total** | **~$65–240/mo** |
| Marginal cost per user | ~$0 |
| Payment processing | ~2.9% + 30¢ per charge |

→ **Gross margin ≈ 90%+.** The business is cheap to run; the constraint is
*acquisition and retention*, not infrastructure.

### 4.2 Key assumptions *(illustrative — validate these)*
- Blended **ARPU ≈ $50 / paying user / season** (≈ $8/mo × 7 months, conservative;
  ignores off-season).
- **Free → paid conversion ≈ 3–5%** of active free users (typical freemium band for a
  high-intent niche tool).
- **Acquisition: organic-heavy** (Reddit, SEO free tools, build-in-public) → low CAC.
- **Retention:** multi-season for engaged users → LTV spans 2+ seasons.

### 4.3 Revenue scenarios (per season)
| Stage | Active free users | Conv. | Paying subs | Subs revenue | + Affiliate/API | **Total / season** |
|---|---|---|---|---|---|---|
| **Year 1 — Seed** | 5,000 | 4% | 200 | $10,000 | ~$1–3K | **~$11–13K** |
| **Year 2 — Growth** | 30,000 | 4% | 1,200 | $60,000 | ~$10K | **~$70K** |
| **Year 3 — Scale** | 100,000 | 5% | 5,000 | $250,000 | ~$50K | **~$300K** |

These are *illustrative* and hinge on execution and marketing, not on the tech (which
is proven). The point: **a solo operator path to $5K → $25K MRR in-season is realistic**
if the audience is acquired well, because the margin and WTP are both favorable.

### 4.4 Sensitivity (Year 2, 30,000 free users)
| Conversion → | 2% | 4% | 6% |
|---|---|---|---|
| Paying subs | 600 | 1,200 | 1,800 |
| Subs revenue/season | $30K | $60K | $90K |

Conversion is the lever that matters most — which is why the **paywall placement**
(personalization + injury alerts) and **onboarding** are the highest-leverage product
work.

---

## Part 5 — Go-To-Market (cheap, founder-led)

The audience is **concentrated and reachable for ~$0**, which is what makes the unit
economics work:

1. **r/fantasybball + fantasy Discords/Twitter** — build in public, post genuinely
   useful weekly analysis, let the free tool spread.
2. **SEO free tools** — a public "best streamers this week" page and per-week pages
   ("fantasy basketball streaming Week 12", "MLB waiver wire Week 8") capture
   recurring search intent across both sports. The free
   schedule grid is the SEO magnet.
3. **Shareability** — every recommendation/action-list card is screenshot-friendly for
   group chats and X.
4. **Creator partnerships** — give fantasy podcasters/newsletters free Power + the API;
   they cite you → distribution.

Launch cadence: ship free tool → grow audience pre-season (Sept–Oct draft season is the
annual acquisition spike) → convert during the season.

---

## Part 6 — Path to First Revenue (milestones)

| Milestone | Unlocks |
|---|---|
| ✅ Scoring engine validated on real data | The product is technically real |
| **Yahoo OAuth league import** | Per-user recommendations = the paid value prop |
| **Stripe + paywall** (free vs Pro) | First subscription dollars |
| **Live injury push/email alerts** | The retention/upgrade driver |
| Public free "streamers this week" page | The SEO/Reddit acquisition engine |
| ESPN import + multi-league | Expands the addressable audience |
| DFS affiliate + API tier | Revenue stacking on the same base |

First dollars are realistically **one league-import + one paywall away**.

---

## Part 7 — Why It Can Win (defensibility)

- **The fusion is the moat** — competitors each own one slice; combining them against
  *your roster* is the differentiated product, and the cleaned data + scoring warehouse
  is tedious for a hobbyist to replicate.
- **Injury speed/reliability** — incumbents have documented lag/errors; being fastest to
  the value-opening pickup is a concrete, defensible edge.
- **Focus** — owning "what should I do with my team *right now*" beats out-featuring
  broad incumbents.

---

## Part 8 — Risks to Revenue & Mitigations

| Risk | Mitigation |
|---|---|
| **Seasonality** (revenue concentrates Oct–Apr) | Season pass pricing; off-season Draft Kit + dynasty tools; annual framing |
| **League-sync fragility** (ESPN moved hosts; platforms can revoke) | Lead with documented **Yahoo API**; always offer **manual roster import** so the product works regardless; cache + degrade gracefully |
| **Low conversion** | Put the paywall on personalization + alerts; invest in onboarding; free tier must deliver a real "aha" |
| **Incumbent adds the feature** | Move fast on injury speed + UX; own the niche relationship before they care |
| **Data-source instability** (free feeds) | Pay for a stable feed (balldontlie ALL-STAR) in production; abstract the data layer (already done) |
| **CAC creeps up** | Stay organic-first (Reddit/SEO); only pay for acquisition once LTV is proven |

---

## Part 9 — Honest Outlook

This is **not** a venture-scale rocket — it's a **high-margin, solo-or-small-team SaaS**
in a proven-paying niche. The realistic prize is a profitable product doing **low-five
to low-six figures per season** with ~90% margins and modest, organic-led acquisition —
achievable because the willingness-to-pay is real, the costs are negligible, and the
hard technical risk (does the engine work?) is **already retired**.

The remaining risk is almost entirely **go-to-market and conversion**, not technology —
which is the right risk to be left holding.
