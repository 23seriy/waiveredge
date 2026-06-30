# WaiverEdge — Deployment Guide

## Option A: Railway (backend) + Vercel (frontend)

### Backend (Railway)

1. Create a new project at https://railway.app
2. Add a **Postgres** plugin (free tier available)
3. Connect your GitHub repo, set root directory to `backend/`
4. Add environment variables:
   ```
   DATABASE_URL=<railway provides this>
   CORS_ORIGINS=https://your-frontend.vercel.app
   YAHOO_CLIENT_ID=...
   YAHOO_CLIENT_SECRET=...
   YAHOO_REDIRECT_URI=https://your-api.railway.app/api/auth/yahoo/callback
   OPENAI_API_KEY=sk-...          # optional
   STRIPE_SECRET_KEY=sk_live_...  # optional
   ```
5. Railway auto-deploys from `railway.toml`. Health check: `/health`

### Frontend (Vercel)

1. Import the repo at https://vercel.com/import
2. Set root directory to `frontend/`
3. Add environment variable:
   ```
   NEXT_PUBLIC_API_BASE=https://your-api.railway.app
   ```
4. Deploy — Vercel auto-detects Next.js

### Post-deploy

- Update Yahoo app redirect URI to `https://your-api.railway.app/api/auth/yahoo/callback`
- Run migrations: `railway run psql < migrations/0001_init.sql`
- Update CORS_ORIGINS to match your Vercel domain

---

## Option B: Fly.io (backend) + Vercel (frontend)

### Backend (Fly.io)

1. Install flyctl: `brew install flyctl`
2. From `backend/`:
   ```bash
   fly launch --name waiveredge-api --region iad
   fly postgres create --name waiveredge-db
   fly postgres attach waiveredge-db
   ```
3. Set secrets:
   ```bash
   fly secrets set CORS_ORIGINS=https://your-frontend.vercel.app
   fly secrets set YAHOO_CLIENT_ID=...
   fly secrets set YAHOO_CLIENT_SECRET=...
   fly secrets set YAHOO_REDIRECT_URI=https://waiveredge-api.fly.dev/api/auth/yahoo/callback
   fly secrets set OPENAI_API_KEY=sk-...
   ```
4. Deploy: `fly deploy`

### Frontend — same as Option A (Vercel)

---

## Environment Variables Reference

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | Yes (for leagues) | Postgres connection string |
| `ENVIRONMENT` | Recommended | `production` enforces a real `APP_SECRET`; defaults to `development` |
| `APP_SECRET` | Yes in prod | Session-signing secret; the app refuses to boot with the default outside `development` |
| `CORS_ORIGINS` | Yes | Allowed frontend origins (comma-separated, no trailing slash) |
| `CORS_ORIGIN_REGEX` | Optional | Regex for extra allowed origins (e.g. Vercel preview URLs); empty by default |
| `FRONTEND_URL` | Yes (OAuth/billing) | Frontend base URL for post-login and Stripe redirects |
| `YAHOO_CLIENT_ID` | For Yahoo OAuth | Yahoo app client ID |
| `YAHOO_CLIENT_SECRET` | For Yahoo OAuth | Yahoo app client secret |
| `YAHOO_REDIRECT_URI` | For Yahoo OAuth | Must match Yahoo app settings |
| `GOOGLE_CLIENT_ID` | For Google login | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | For Google login | Google OAuth client secret |
| `GOOGLE_REDIRECT_URI` | For Google login | Must match the Google app's authorized redirect URI |
| `OPENAI_API_KEY` | Optional | Enables AI rationale generation |
| `STRIPE_SECRET_KEY` | Optional | Enables Pro billing |
| `STRIPE_WEBHOOK_SECRET` | Optional | Stripe webhook verification |
| `STRIPE_PRO_MONTHLY_PRICE_ID` | Optional | Stripe price ID for $8/mo |
| `STRIPE_PRO_SEASON_PRICE_ID` | Optional | Stripe price ID for $39/season |
| `BALLDONTLIE_API_KEY` | Optional | Stabilized stats feed (ALL-STAR tier). NBA injuries are already free via ESPN — no key needed for them. |

## Notes

- The backend serves NBA fixtures from `stats.nba.com` and MLB from `statsapi.mlb.com` — both free, no keys needed
- First request to a sport materializes fixtures (~7 min for MLB, ~3 min for NBA). Subsequent requests are instant (24h cache)
- Railway/Fly persistent storage is not needed — fixtures are rebuilt automatically
