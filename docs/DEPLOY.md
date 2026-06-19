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
| `CORS_ORIGINS` | Yes | Frontend URL (comma-separated) |
| `YAHOO_CLIENT_ID` | For Yahoo OAuth | Yahoo app client ID |
| `YAHOO_CLIENT_SECRET` | For Yahoo OAuth | Yahoo app client secret |
| `YAHOO_REDIRECT_URI` | For Yahoo OAuth | Must match Yahoo app settings |
| `OPENAI_API_KEY` | Optional | Enables AI rationale generation |
| `STRIPE_SECRET_KEY` | Optional | Enables Pro billing |
| `STRIPE_WEBHOOK_SECRET` | Optional | Stripe webhook verification |
| `STRIPE_PRO_MONTHLY_PRICE_ID` | Optional | Stripe price ID for $8/mo |
| `STRIPE_PRO_SEASON_PRICE_ID` | Optional | Stripe price ID for $39/season |
| `BALLDONTLIE_API_KEY` | Optional | NBA injury feed (ALL-STAR tier) |

## Notes

- The backend serves NBA fixtures from `stats.nba.com` and MLB from `statsapi.mlb.com` — both free, no keys needed
- First request to a sport materializes fixtures (~7 min for MLB, ~3 min for NBA). Subsequent requests are instant (24h cache)
- Railway/Fly persistent storage is not needed — fixtures are rebuilt automatically
