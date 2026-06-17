# WaiverEdge — Manual Test Plan

Living document. Check items off as you verify them; add new rows as features land.

## Prerequisites

```bash
# Backend
cd backend && source .venv/bin/activate
uvicorn app.main:app --reload          # http://localhost:8000

# Frontend
cd frontend && npm run dev             # http://localhost:3000

# Unit tests (46 currently)
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
| 29 | Page loads | Navigate to `/` | Header with WaiverEdge logo, mode toggle, Streamers/Connect/Pro links | |
| 30 | Sample roster pre-filled | Check textarea | 10 NBA player names | |
| 31 | Mode toggle | Click Points ↔ 9-Cat | Toggle highlights, hero text updates | |
| 32 | Submit points mode | Click "Rank waiver adds" in Points | Loading spinner → recommendation cards appear | |
| 33 | Submit 9-cat mode | Switch to 9-Cat, submit | Cards show z-score badges (green/red/gray), `helps weak cats` chips | |
| 34 | Expand rationale | Click "Details" on a card | Full rationale text expands | |
| 35 | Unresolved warning | Add a fake name to roster, submit | Orange warning bar listing the unresolved name | |
| 36 | Error state | Stop backend, submit | Red error box with connection message | |
| 37 | Persist roster | Type custom roster, reload page | Restored from localStorage | |
| 38 | Persist mode | Switch to 9-Cat, reload | Mode restored | |

### 2.2 Streamers Page (`/streamers`)
| # | Test | How | Expected | Status |
|---|------|-----|----------|--------|
| 39 | Page loads | Navigate to `/streamers` | Title, schedule grid, top streamers list | |
| 40 | Schedule grid | Check team cards | Teams with most games highlighted in accent, game-count bars visible | |
| 41 | Show all teams | Click "Show all 30 teams" | Expands to all teams | |
| 42 | Streamer cards | Check top 3 | "top pick" flame badge, rank #, projected fpts | |
| 43 | Matchup expand | Click "Matchups" on a card | Opponent chips with soft/tough badges | |
| 44 | CTA banner | Scroll to bottom | "Want picks for YOUR roster?" with link to `/` | |
| 45 | Header nav | Click WaiverEdge logo | Navigates to `/` | |

### 2.3 Connect Page (`/connect`)
| # | Test | How | Expected | Status |
|---|------|-----|----------|--------|
| 46 | Page loads | Navigate to `/connect` | Yahoo connect card with feature grid | |
| 47 | Connect button | Click "Connect with Yahoo" | Redirects to Yahoo OAuth (or API error if not configured) | |
| 48 | Error param | Navigate to `/connect?error=no_leagues` | Error banner shown | |
| 49 | Manual fallback | Click "Paste your roster manually" | Navigates to `/` | |

### 2.4 Pricing Page (`/pricing`)
| # | Test | How | Expected | Status |
|---|------|-----|----------|--------|
| 50 | Page loads | Navigate to `/pricing` | Free vs Pro cards, plan toggle | |
| 51 | Plan toggle | Click Monthly ↔ Season Pass | Price updates ($8/mo vs $39/season), savings text changes | |
| 52 | Pro features | Check Pro card | 6 features listed with green checks | |
| 53 | Checkout button | Click "Upgrade to Pro" | Calls billing API (503 if Stripe not configured — expected for dev) | |

### 2.5 League Page (`/league/[id]`) — requires active Yahoo connection
| # | Test | How | Expected | Status |
|---|------|-----|----------|--------|
| 54 | Page loads | Navigate to `/league/1` | League info header, sync button | |
| 55 | Sync roster | Click "Sync roster" | Spinner → roster populated | |
| 56 | Recommendations | After sync | Personalized rec cards appear | |
| 57 | 9-cat detection | If Yahoo league is H2H-cats | 9-Cat badge in header, z-score cards | |

### 2.6 Responsive / Cross-cutting
| # | Test | How | Expected | Status |
|---|------|-----|----------|--------|
| 58 | Mobile layout | Resize to 375px width | Cards stack, text readable, no overflow | |
| 59 | Nav links | Click all header links | Each navigates correctly | |
| 60 | Dark mode consistent | Visual scan all pages | bg-bg dark background, no white flashes | |

---

## 3. Unit Tests (automated)

```bash
cd backend && python -m pytest tests/ -v
```

| Suite | Count | Covers |
|---|---|---|
| `test_api.py` | 14 | All HTTP endpoints via TestClient |
| `test_categories.py` | 5 | 9-cat z-score engine |
| `test_recommendations.py` | 7 | Service layer (build_recs, top_streamers) |
| `test_scoring.py` | 10 | Core engine, DvP, name resolution |
| `test_scoring_systems.py` | 10 | LeagueScoring, config, fantasy_points |
| **Total** | **46** | |

---

## Change Log

| Date | Change |
|---|---|
| 2026-06-17 | Initial plan — 60 manual checks + 46 automated tests |
