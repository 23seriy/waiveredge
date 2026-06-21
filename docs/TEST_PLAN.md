# WaiverEdge — Manual Test Plan

Living document. Check items off as you verify them; add new rows as features land.

## Prerequisites

```bash
# Backend
cd backend && source .venv/bin/activate
uvicorn app.main:app --reload          # http://localhost:8000

# Frontend
cd frontend && npm run dev             # http://localhost:3000

# Unit tests (87 currently)
python -m pytest tests/ -v
```

---

## 1. Backend API (curl / Swagger UI at http://localhost:8000/docs)

### 1.1 Health
| # | Test | How | Expected | Status |
|---|------|-----|----------|--------|
| 1 | Health endpoint | `GET /health` | `{"status":"ok","service":"waiveredge","has_api_key":...}` | |

### 1.2 Streamers (public, no auth)
| # | Test | How | Expected | Status |
|---|------|-----|----------|--------|
| 2 | Default top 30 | `GET /api/streamers` | `week`, `schedule_grid` (all 30 teams), `streamers` (≤30) | |
| 3 | Custom top N | `GET /api/streamers?top=5` | ≤5 streamers returned | |
| 4 | Clamp at 50 | `GET /api/streamers?top=999` | ≤50 streamers | |
| 5 | Sorted desc | Check `projected_total` is descending | | |
| 6 | Schedule grid sorted | Teams sorted by games desc | | |
| 7 | Streamer shape | Each has `player_id`, `name`, `position`, `team`, `n_games`, `fppg`, `projected_total`, `matchups` | | |

### 1.3 Manual Recommendations — Points Mode
| # | Test | How | Expected | Status |
|---|------|-----|----------|--------|
| 8 | Basic roster | `POST /api/recommendations/manual` with `{"roster":["Nikola Jokic","Luka Doncic","Trae Young"]}` | 200, `scoring_mode:"points"`, recs with `total_z:null` | |
| 9 | Accent folding | `"Nikola Jokić"` vs `"Nikola Jokic"` | Both resolve (same `resolved_count`) | |
| 10 | Unresolved names | Include `"FakePlayer123"` | `unresolved: ["FakePlayer123"]` | |
| 11 | All names fake | `{"roster":["Fake1","Fake2"]}` | 400 with detail message | |
| 12 | Empty roster | `{"roster":[]}` | 422 (Pydantic min_length) | |
| 13 | Default mode | Omit `scoring_mode` | Defaults to `"points"` | |

### 1.4 Manual Recommendations — Categories Mode
| # | Test | How | Expected | Status |
|---|------|-----|----------|--------|
| 14 | 9-cat request | Add `"scoring_mode":"categories"` + standard 9 cats | 200, `scoring_mode:"categories"`, recs have `total_z`, `per_cat_z`, `helps` | |
| 15 | Invalid mode | `"scoring_mode":"invalid"` | 422 | |
| 16 | Partial categories | Send only `["pts","ast","stl"]` | Only those 3 in `per_cat_z` | |

### 1.5 Sample Recommendations
| # | Test | How | Expected | Status |
|---|------|-----|----------|--------|
| 17 | Points mode | `GET /api/recommendations/sample` | 200, recs present, `scoring_mode:"points"` | |
| 18 | Categories mode | `GET /api/recommendations/sample?mode=categories` | 200, recs with `total_z` | |

### 1.6 Yahoo OAuth (requires Yahoo credentials configured)
| # | Test | How | Expected | Status |
|---|------|-----|----------|--------|
| 19 | No config → 503 | Clear `YAHOO_CLIENT_ID`, hit `GET /api/auth/yahoo` | 503 "not configured" | |
| 20 | Redirect | With config, hit `GET /api/auth/yahoo` | 302 redirect to Yahoo consent URL | |
| 21 | Callback flow | Complete Yahoo OAuth in browser | Redirects to `/league/{id}` with connection created | |

### 1.7 League Endpoints (requires Postgres + synced connection)
| # | Test | How | Expected | Status |
|---|------|-----|----------|--------|
| 22 | Get league | `GET /api/leagues/{id}` | Connection info + roster | |
| 23 | 404 | `GET /api/leagues/99999` | 404 | |
| 24 | Sync roster | `POST /api/leagues/{id}/sync` | Synced count + unresolved | |
| 25 | Get recs | `GET /api/leagues/{id}/recs` | Personalized recommendations | |

### 1.8 Billing (requires Stripe test keys)
| # | Test | How | Expected | Status |
|---|------|-----|----------|--------|
| 26 | No config → 503 | Clear `STRIPE_SECRET_KEY`, hit checkout | 503 | |
| 27 | Checkout session | `POST /api/billing/checkout {"user_id":1,"plan":"monthly"}` | `checkout_url` returned | |
| 28 | Billing status | `GET /api/billing/status/1` | `tier`, `has_subscription` | |

---

## 2. Frontend UI (http://localhost:3000)

### 2.1 Home Page (`/`)
| # | Test | How | Expected | Status |
|---|------|-----|----------|--------|
| 29 | Page loads | Navigate to `/` | Sport picker cards (MLB live, NBA offseason), Pricing nav | |
| 30 | Sport nav | Click MLB card | Navigates to `/mlb` | |
| 31 | Footer links | Check footer | Pricing + MLB Streamers links present | |

### 2.2 Sport Dashboard (`/[sport]`)
| # | Test | How | Expected | Status |
|---|------|-----|----------|--------|
| 32 | Page loads | Navigate to `/mlb` | Header with sport badge, mode toggle, roster textarea | |
| 33 | Sample roster pre-filled | Check textarea | 10 MLB player names | |
| 34 | Mode toggle | Click Points ↔ 5x5 | Toggle highlights | |
| 35 | Submit points mode | Click "Rank waiver adds" in Points | Loading spinner → recommendation cards appear | |
| 36 | Submit 5x5 mode | Switch to 5x5, submit | Cards show z-score badges (green/red/gray), `helps weak cats` chips | |
| 37 | Expand rationale | Click "Details" on a card | Full rationale text expands | |
| 38 | Unresolved warning | Add a fake name to roster, submit | Orange warning bar listing the unresolved name | |
| 39 | Error state | Stop backend, submit | Red error box with connection message | |
| 40 | Persist roster | Type custom roster, reload page | Restored from localStorage | |
| 41 | Persist mode | Switch to 5x5, reload | Mode restored | |

### 2.3 Streamers Page (`/[sport]/streamers`)
| # | Test | How | Expected | Status |
|---|------|-----|----------|--------|
| 42 | Page loads | Navigate to `/mlb/streamers` | Title, schedule grid, top streamers list | |
| 43 | Schedule grid | Check team cards | Teams with most games highlighted in accent, game-count bars visible | |
| 44 | Show all teams | Click "Show all teams" | Expands to all teams | |
| 45 | Streamer cards | Check top 3 | "top pick" flame badge, rank #, projected fpts | |
| 46 | Matchup expand | Click "Matchups" on a card | Opponent chips with soft/tough badges | |
| 47 | CTA banner | Scroll to bottom | "Want picks for YOUR roster?" with link back to sport dashboard | |
| 48 | Header nav | Click WaiverEdge logo | Navigates to `/` | |

### 2.4 Connect Page (`/[sport]/connect`)
| # | Test | How | Expected | Status |
|---|------|-----|----------|--------|
| 49 | Page loads | Navigate to `/mlb/connect` | Yahoo + ESPN connect cards with feature grid | |
| 50 | Yahoo button | Click "Connect with Yahoo" | Redirects to Yahoo OAuth (or API error if not configured) | |
| 51 | ESPN flow | Enter league ID, fetch teams, select, connect | Redirects to `/mlb/league/{id}` | |
| 52 | Error param | Navigate to `/mlb/connect?error=no_leagues` | Error banner shown | |
| 53 | Manual fallback | Click "Paste your roster manually" | Navigates to `/mlb` | |

### 2.5 Pricing Page (`/pricing`)
| # | Test | How | Expected | Status |
|---|------|-----|----------|--------|
| 54 | Page loads | Navigate to `/pricing` | Free vs Pro cards, plan toggle, ← Back link | |
| 55 | Plan toggle | Click Monthly ↔ Season Pass | Price updates ($8/mo vs $39/season), savings text changes | |
| 56 | Pro features | Check Pro card | 6 features listed with green checks | |
| 57 | Checkout button | Click "Upgrade to Pro" | Calls billing API (503 if Stripe not configured — expected for dev) | |
| 58 | SEO metadata | View page source | `<title>Pricing — WaiverEdge Pro</title>` present | |

### 2.6 League Page (`/[sport]/league/[id]`) — requires active connection
| # | Test | How | Expected | Status |
|---|------|-----|----------|--------|
| 59 | Page loads | Navigate to `/mlb/league/1` | League info header, sync button | |
| 60 | Sync roster | Click "Sync roster" | Spinner → roster populated | |
| 61 | Unresolved shown | After sync with missing players | Orange banner listing unmatched names | |
| 62 | Recommendations | After sync | Personalized rec cards appear | |
| 63 | Scoring detection | If Yahoo league is H2H-cats/roto | Category badge in header, z-score cards | |

### 2.7 Responsive / Cross-cutting
| # | Test | How | Expected | Status |
|---|------|-----|----------|--------|
| 64 | Mobile layout | Resize to 375px width | Cards stack, text readable, no overflow | |
| 65 | Nav links | Click all header links | Each navigates correctly, sport-scoped | |
| 66 | Dark mode consistent | Visual scan all pages | bg-bg dark background, no white flashes | |
| 67 | Invalid sport | Navigate to `/fake` | "Sport not found" with back link | |

---

## 3. Unit Tests (automated)

```bash
cd backend && python -m pytest tests/ -v
```

| Suite | Count | Covers |
|---|---|---|
| `test_api.py` | 14 | All HTTP endpoints via TestClient |
| `test_categories.py` | 5 | 9-cat z-score engine |
| `test_matchups.py` | 9 | DvP table, clamping, shrinkage, positions |
| `test_name_resolution.py` | 13 | Accent folding, punctuation, deduplication |
| `test_projections.py` | 11 | Recency weighting, edge cases, MLB weights |
| `test_recommendations.py` | 7 | Service layer (build_recs, top_streamers) |
| `test_scoring.py` | 10 | Core engine integration |
| `test_scoring_systems.py` | 12 | LeagueScoring, sport config, fantasy_points |
| **Total** | **87** | |

---

## Change Log

| Date | Change |
|---|---|
| 2026-06-17 | Initial plan — 60 manual checks + 46 automated tests |
| 2026-06-21 | Updated for sport-scoped routes, 87 automated tests, unresolved player display |
