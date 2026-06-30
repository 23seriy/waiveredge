# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this product is

WaiverEdge is a fantasy sports "do this now" waiver action list — currently
supporting **NBA basketball**, **MLB baseball**, and **WNBA basketball**. The scoring core fuses **schedule density × DvP matchup ×
injury role-bump × availability** into a single value-over-replacement number per
candidate, then ranks free agents against *your* roster. The sport registry
(`app/sports.py`) makes adding new sports config-only. The README's "The model"
section is the spec — keep changes explainable and deterministic (no ML in v1).

## Commands

All backend commands assume `cd backend && source .venv/bin/activate`.

```bash
# Backend setup
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Run the API (materializes real NBA fixtures lazily on first request)
uvicorn app.main:app --reload                  # http://localhost:8000

# Refresh the real-data fixtures (writes backend/sample_data_nba/*.json)
python scripts/dump_real_fixtures.py

# CLI prototype that prints the ranked action list against real data
python scripts/prototype_scoring.py

# Live check of the core thesis ("schedule beats talent") against stats.nba.com
python scripts/validate_nba_api.py

# Tests — both forms work
python -m pytest                                # pytest discovery
python tests/test_scoring.py                    # stdlib-only manual runner
python -m pytest tests/test_scoring.py::test_schedule_density_beats_talent   # single test

# Frontend (Next.js 15 app router)
cd ../frontend
npm install
npm run dev                                     # http://localhost:3000
npm run build && npm run lint

# Postgres (only for the future DB-backed per-user endpoint)
docker compose up -d db
```

## Architecture

The codebase has three concentric layers — change them in this order of
preference (inner is most stable):

1. **`backend/app/scoring/`** — the pure-stdlib scoring core. This is the IP.
   - `types.py` — dataclasses (`Player`, `GameLog`, `ScheduledGame`, `Injury`,
     `Projection`, `ValueResult`, `Recommendation`). Other layers consume these.
   - `projections.py` — recency-weighted `fppg` from game logs.
   - `matchups.py` — defense-vs-position multiplier (`DvPTable`), clamped to
     `MULT_FLOOR..MULT_CEIL` (±15%). Our own metric derived from box scores.
   - `engine.py` — `rank_waiver_adds` is the entry point. Formula:
     `weekly_value = Σ fppg × role_mult × matchup_mult × avail_prob` over the
     games in the week, then `marginal = weekly_value(FA) − weekly_value(weakest
     droppable same-position rostered player)`. Recommendations are sorted by
     `marginal`.
   - `scoring_systems.py` — `fantasy_points(line, scoring)` + presets.

2. **`backend/app/data/`** — adapts external feeds into the scoring core's shapes.
   - `nba_fixtures.py` — builds real fixtures from **stats.nba.com via nba_api**.
     Auto-selects a representative mid-season week (densest week in the middle
     third of the latest available season) — no hardcoded dates. Imported lazily.
   - `balldontlie.py` — optional production feed client (paid ALL-STAR tier
     unlocks injuries → activates the dormant `role_mult` / `avail_prob` signals).
   - `espn.py` — ESPN Fantasy API client. **Read** via
     `lm-api-reads.fantasy.espn.com` (roster, free agents, settings).
     **Write** via `lm-api-writes.fantasy.espn.com` (`add_drop_player`,
     `claim_waiver`) using `espn_s2` + `SWID` cookies. Game codes:
     `fba` (NBA), `flb` (MLB), `wfba` (WNBA), `ffl` (NFL), `fhl` (NHL).
   - `yahoo.py` — Yahoo Fantasy API client (OAuth + league data + transactions).
   - `ingest.py` — loads balldontlie into Postgres or refreshes fixture JSON.

3. **`backend/app/`** — service + API.
   - `recommendations.py` — `load_fixtures()` (lazy-materializes
     `sample_data_nba/*.json` / `sample_data_mlb/*.json` / `sample_data_wnba/*.json`), `build_recommendations(fx, sport)`, `manual_recommendations()`
     (accent-folding name resolver via `_normalize_name` — `Jokić` matches
     `Jokic`). Also `build_espn_id_map()` which cross-references ESPN
     player IDs with fixture IDs for transaction execution.
   - `main.py` — FastAPI: `/health`, `/api/recommendations/sample`,
     `POST /api/recommendations/manual {roster, droppable?}`. The per-user
     `/api/recommendations/{connection_id}` is sketched out in a TODO and depends
     on Yahoo OAuth + ingestion.
   - `models.py` / `db.py` — SQLAlchemy 2.0; `migrations/0001_init.sql` is the
     source of truth for the schema today.

Frontend (`frontend/`) is a Next.js 15 app-router UI with Tailwind CSS — sport-
scoped routes (`/[sport]/`), manual-roster form, streamers, league connect, and
pricing pages.

### Data flow

```
stats.nba.com ──(nba_api)──► nba_fixtures.build_real_fixtures
ESPN injuries API ─────────► espn_injuries.fetch_nba_injuries (NBA injuries.json)
statsapi.mlb.com ──────────► mlb_fixtures.build_real_fixtures
ESPN public API ───────────► wnba_fixtures.build_real_fixtures
                                  │
                                  ▼
                     backend/sample_data_{nba,mlb,wnba}/*.json (gitignored)
                                  │
                load_fixtures() ──┴──► build_recommendations ──► rank_waiver_adds ──► API

ESPN write API flow (transactions):
  connect/sync ─► build_espn_id_map() ─► scoring_json["espn_player_keys"] = {our_id: espn_id}
  execute      ─► look up espn_id    ─► ESPNFantasyClient.add_drop_player() ─► lm-api-writes
```

The same `build_recommendations` is used by the CLI prototype and the API; the
future per-user endpoint will swap the data source from `sample_data_nba/*.json` to
Postgres queries but reuse the engine unchanged.

### Invariants to preserve

- **Scoring core stays pure-stdlib.** Don't import fastapi/httpx/nba_api/SQLAlchemy
  inside `app/scoring/*`. The test runner relies on this (`test_scoring.py` can be
  run with no deps installed).
- **Every recommendation must be explainable.** `Recommendation` carries the
  games, soft matchups, role note, availability, and the drop player it's
  measured against; `_rationale` formats them. New signals should appear in the
  rationale, not just the score.
- **DvP multipliers are clamped** (`MULT_FLOOR`/`MULT_CEIL`, currently ±15%).
  Don't remove the clamp — it prevents a small DvP sample from dominating the
  ranking.
- **Injury feeds are per-sport.** NBA has a free live injury feed via ESPN's
  public API (`data/espn_injuries.py`, written into `injuries.json` at fixture
  build), which activates `role_mult` / `avail_prob`. MLB and WNBA still have no
  feed — their `injuries.json` is empty, so those signals stay at 1.0 there. The
  engine supports both paths and the unit tests cover them — don't rip out the
  code that handles empty injuries.
- **Week selection is dynamic.** Don't hardcode season strings or dates;
  `nba_fixtures` auto-selects from `DEFAULT_SEASONS` and the densest mid-season
  week so the app keeps working as seasons roll over.

## Legal / data hygiene

Raw stats are not NBA IP (NBA v. Motorola, Feist) — fine to use. **No team logos
or marks** anywhere; plain-text team names only. Don't host game video. No
gambling features.

# CLAUDE.md

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.
