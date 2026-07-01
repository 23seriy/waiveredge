# Shareable OG Image Card — Design Spec

**Date:** 2026-06-30  
**Phase:** 2.1 (Growth loop)  
**Goal:** Every paste of a league recs URL in a group chat auto-renders a "your Week N moves" card — zero friction, zero user action required.

---

## What we're building

A Next.js `opengraph-image.tsx` route co-located with the league page at:

```
frontend/app/[sport]/league/[id]/opengraph-image.tsx
```

Next.js App Router automatically serves this as the OG image whenever the parent URL is unfurled by Slack, iMessage, Twitter/X, Discord, etc.

---

## Data flow

1. When a URL is unfurled, the client (Slack/etc.) sends a GET to the page
2. Next.js detects `opengraph-image.tsx` and renders it server-side via `ImageResponse`
3. The route fetches `GET {API_BASE}/api/leagues/{id}/recs` with no auth cookies — `connection_id` is the identifier
4. Top recommendations are injected into the image layout

---

## Image spec

- **Size:** 1200×630 px (standard OG)
- **Layout:**
  - Top-left: "WaiverEdge" wordmark
  - Title: "Your Week {start}–{end} Moves"
  - Body: up to 3 recommendation rows — `+{marginal} · {add_name} ({add_position})` — with drop name if present
  - Paywalled rows: show `#2 · Unlock on Pro` instead of player names
  - Bottom-right: `waiveredge.app` watermark
- **Palette:** dark background (`#0d0d0f`), accent green (`#22c55e`), muted gray text — matches app theme
- **Font:** system sans-serif (no external font fetching; avoids latency and edge-runtime font issues)

---

## Fallback

If the backend fetch fails, returns 0 recs, or errors: render a generic card — "WaiverEdge · NBA Waiver Wire · waiveredge.app" — no error shown to the crawler.

---

## What's not in scope

- No "copy image" or download button (that's approach B, deferred)
- No per-player headshots or team logos (legal constraint in CLAUDE.md)
- No auth — the OG route is public; connection_id in the URL is the only identifier

---

## Files changed

| File | Action |
|------|--------|
| `frontend/app/[sport]/league/[id]/opengraph-image.tsx` | New — the OG image route |

No backend changes. No new dependencies.

---

## Success criteria

- Pasting `https://waiveredge.app/nba/league/123` in Slack/Discord/iMessage unfurls a card showing real player names and marginal values
- Fallback card renders when backend is unreachable
- Build passes (`npm run build`)
