# WaiverEdge

**The fantasy sports move-finder.** Fuses *schedule density × positional matchups
× live injuries × your actual open roster slots* into a single ranked **"do this now"**
waiver action list — the cross-referencing serious managers currently do by hand across
3+ tools. Currently supports **NBA basketball**, **MLB baseball**, and **WNBA basketball**.

> The wedge: incumbents each own a slice (Hashtag Basketball = schedule, Basketball
> Monster = projections, FantasyPros = start/sit). Nobody fuses all of it against *your*
> roster. That fusion is the product; a fast, reliable injury feed is the moat.

📈 **How this earns money:** see [docs/BUSINESS.md](docs/BUSINESS.md) — the idea, the
monetization model, unit economics, and realistic revenue scenarios.

---

## Quickstart — real NBA data

The app **always serves real NBA data**, pulled from **stats.nba.com** (the official
source balldontlie wraps) via `nba_api`. The scoring core itself is pure-stdlib Python.

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python scripts/dump_real_fixtures.py    # fetch real players/box scores/schedule
python scripts/prototype_scoring.py     # ranked waiver action list (real players)
python tests/test_scoring.py            # unit tests (stdlib runner)
```

`dump_real_fixtures.py` works from a residential IP — datacenter IPs are what
stats.nba.com blocks, which is why a *deployed* product pays for a stabilized feed
instead. The API also materializes this data automatically on first request, so you can
skip the dump step and just start the server.

Sample output (real players; the week is auto-selected — see below):

```
WAIVEREDGE — weekly waiver action list  (2026-01-01 -> 2026-01-07)
Schedule density (games this week, busiest 8):
    SAC  #### 4
    BOS  #### 4
Top 10 free-agent adds (value over replacement for the default roster):
  1. [+120.7]  Kawhi Leonard (SF/PF) — 4 games this week, 1 vs soft matchup. Projected 257.0 fpts ...
```

**Which week?** Fantasy basketball is a regular-season product (Oct–Apr); in the
offseason no NBA teams play, so there's nothing to project. MLB runs Apr–Oct. The app therefore
**auto-selects a representative mid-season week** — the densest week in the middle third
of the latest available season (which sidesteps the October ramp-up, the All-Star break,
and end-of-season resting). No hardcoded dates: when 2026-27 tips off, it tracks that
season automatically.

**The thesis, on real data:** the league's top scorer falls out of the weekly top-10 on
a 3-game week while 5-game role players leap up — schedule + matchup decide it, not raw
talent. `scripts/validate_nba_api.py` runs that exact check live and prints it.

### Serve it through the API

```bash
uvicorn app.main:app --reload
```

- `GET /api/recommendations/sample` — ranks a real default roster.
- `POST /api/recommendations/manual` — ranks a roster you paste (`{"roster": ["Nikola Jokic", ...]}`);
  accents are folded, so `Nikola Jokic` matches `Nikola Jokić`.

---

## The model (deterministic, explainable — no ML in v1)

For each candidate player over the scoring window:

```
weekly_value = Σ over games this week:  fppg × role_mult × matchup_mult × avail_prob
```

then ranked by **value over replacement for your roster**:

```
marginal = weekly_value(candidate) − weekly_value(weakest droppable rostered player
           who shares a position)
```

| Signal | Source | Where |
|---|---|---|
| `fppg` | recency-weighted fantasy avg from game logs | `app/scoring/projections.py` |
| `matchup_mult` | defense-vs-position, derived from box scores (our own metric, clamped ±15%) | `app/scoring/matchups.py` |
| `role_mult` | +15% when a same-position teammate is ruled Out | `app/scoring/engine.py` |
| `avail_prob` | injury status → suit-up probability | `app/scoring/engine.py` |
| games this week | schedule density | `app/scoring/engine.py` |

Everything is traceable — each recommendation shows the games, matchups, and injury
logic that produced it.

> Note: NBA injuries come from ESPN's free public API (`app/data/espn_injuries.py`), so
> `role_mult`/`avail_prob` are live for NBA. MLB/WNBA have no injury feed yet, so those
> signals stay at 1.0 there. The engine supports both paths — covered by the unit tests.

---

## Architecture

```
backend/                  FastAPI + Postgres
  app/
    sports.py             ← sport registry (NBA live, MLB config-only)
    scoring/              ← pure-stdlib scoring core (the IP)
    data/nba_fixtures.py  ← builds REAL fixtures from stats.nba.com (nba_api)
    data/espn_injuries.py ← live NBA injury feed from ESPN's free public API
    data/balldontlie.py   ← optional production feed client (header auth, pagination)
    data/espn.py          ← ESPN Fantasy API client (cookies, read + write)
    data/yahoo.py         ← Yahoo Fantasy API client (OAuth + league data)
    data/ingest.py        ← optional balldontlie → Postgres / fixtures refresh
    api/auth.py           ← Yahoo OAuth endpoints
    api/leagues.py        ← per-user league sync + recs
    api/alerts.py         ← injury alerts (scan + inbox + pickup opportunities)
    api/billing.py        ← Stripe checkout + webhook
    recommendations.py    ← service the API + prototype share (load_fixtures)
    scheduler.py          ← background fixture refresh + injury refresh/scan
    models.py / db.py     ← SQLAlchemy 2.0
    main.py               ← API (sport-aware endpoints)
  migrations/
  sample_data_nba/        ← materialized REAL NBA fixtures (gitignored)
  sample_data_mlb/        ← materialized REAL MLB fixtures (gitignored)
  sample_data_wnba/       ← materialized REAL WNBA fixtures (gitignored)
  scripts/
  tests/                  ← 127 unit tests
frontend/                 Next.js 15 + Tailwind CSS
  app/                    ← /, /[sport]/, /[sport]/streamers, /[sport]/connect, /[sport]/league/[id], /pricing
                            Supported sports: nba, mlb, wnba
docker-compose.yml        Postgres for local dev
```

## Run the full stack

```bash
# 1. Backend (real NBA data needs no API key)
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload      # http://localhost:8000/api/recommendations/sample
                                   # (materializes real fixtures on first request)

# 2. Frontend
cd ../frontend
npm install
npm run dev                        # http://localhost:3000

# Optional: Postgres for the DB-backed, per-user endpoint (post-Yahoo-OAuth)
docker compose up -d db
```

## Production data feed (optional)

The free `nba_api` → stats.nba.com path is perfect for development, but datacenter IPs
get blocked, so a deployed server needs either residential proxies or a stabilized feed.
NBA **injuries are already free** via ESPN's public API (no key needed), so the role-bump /
availability signals are live out of the box. **balldontlie ALL-STAR ($9.99/mo)** remains an
optional drop-in for a stabilized stats feed with a documented SLA.

1. Get a key at <https://app.balldontlie.io> (stats need **ALL-STAR**).
2. Set `BALLDONTLIE_API_KEY` in `backend/.env`.
3. Refresh fixtures from it: `python -m app.data.ingest`, or load Postgres via `ingest_all(db)`.

## Data & legal notes

- Raw stats/scores are **not** NBA IP (*NBA v. Motorola*, *Feist*) — fine to use commercially.
- **No logos / team marks** — plain-text names only.
- Don't host game video. No gambling exposure → no compliance burden.

## Roadmap

- [x] 9-category league scoring (z-score per category)
- [x] Public streamers page (SEO/Reddit acquisition)
- [x] Tailwind CSS UI redesign + Points/9-Cat mode toggle
- [x] Yahoo OAuth league import + per-user recommendations
- [x] Stripe billing + paywall scaffolding (free/Pro tiers)
- [x] Multi-sport architecture (NBA + MLB)
- [x] MLB data pipeline (real data from MLB Stats API)
- [x] ESPN league import (team picker, no cookies for public leagues)
- [x] Live NBA injury feed (ESPN free API) + auto-scanned pickup alerts (scan + inbox)
- [x] LLM-powered AI rationales (OpenAI gpt-4o-mini)
- [x] Fixture caching + background builds (24h cache, progress polling)
- [x] Home page UX redesign (hero, clean header, sport-aware)
- [x] WNBA support (ESPN leagues, ESPN public API for fixtures)
- [x] ESPN programmatic add/drop (write API for all sports, deep-link fallback)
- [x] 127 unit tests (API + engine + projections + matchups + name resolution + scoring systems + WNBA + ESPN transactions + injury feed + alerts + config guard)
- [x] Deploy configs (Dockerfile, Railway, Fly.io, Vercel)
- [x] Deploy MVP to production (Render + Vercel)
- [ ] Nightly DvP recompute job + `team_dvp` cache

