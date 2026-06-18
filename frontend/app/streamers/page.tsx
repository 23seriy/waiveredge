"use client";

// Public "top streamers this week" page — no roster, no auth, free content.
// Designed for SEO (server-side indexable title/description) and Reddit/X sharing.
// CTA funnels to the personalized roster tool at /.

import { useEffect, useState } from "react";
import {
  ArrowRight,
  Calendar,
  ChevronDown,
  ChevronUp,
  Flame,
  Loader2,
  TrendingUp,
  Zap,
} from "lucide-react";
import Link from "next/link";

type Matchup = { opponent: string; mult: number };
type TeamSchedule = {
  team_id: number;
  abbreviation: string;
  games: number;
  matchups: { date: string; opponent: string }[];
};
type Streamer = {
  player_id: number;
  name: string;
  position: string;
  team: string;
  n_games: number;
  soft_matchups: number;
  fppg: number;
  projected_total: number;
  matchups: Matchup[];
};
type StreamersPayload = {
  week: { start: string; end: string };
  schedule_grid: TeamSchedule[];
  streamers: Streamer[];
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

function formatDate(iso: string) {
  const d = new Date(iso + "T12:00:00");
  return d.toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" });
}

function MultBadge({ mult }: { mult: number }) {
  if (mult >= 1.08) return <span className="text-pos text-xs font-medium">soft</span>;
  if (mult <= 0.92) return <span className="text-neg text-xs font-medium">tough</span>;
  return null;
}


function ScheduleGrid({ grid, week }: { grid: TeamSchedule[]; week: { start: string; end: string } }) {
  const [showAll, setShowAll] = useState(false);
  const maxGames = grid[0]?.games ?? 0;
  const busiest = grid.filter((t) => t.games === maxGames);
  const displayed = showAll ? grid : grid.filter((t) => t.games >= maxGames - 1);

  return (
    <section className="mb-10">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-base font-semibold flex items-center gap-2">
          <Calendar size={16} className="text-accent" /> Schedule Density
        </h2>
        <span className="text-xs text-muted">
          {formatDate(week.start)} – {formatDate(week.end)}
        </span>
      </div>
      <p className="text-xs text-muted mb-4">
        Teams with more games = more streaming value. Target players on {maxGames}-game teams.
      </p>

      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2">
        {displayed.map((t) => (
          <div
            key={t.team_id}
            className={`rounded-lg border p-3 text-center transition-colors ${
              t.games === maxGames
                ? "border-accent/50 bg-accent/10"
                : "border-line bg-card"
            }`}
          >
            <div className="text-sm font-bold">{t.abbreviation}</div>
            <div className="flex items-center justify-center gap-0.5 mt-1">
              {Array.from({ length: t.games }).map((_, i) => (
                <div
                  key={i}
                  className={`h-2 w-4 rounded-sm ${
                    t.games === maxGames ? "bg-accent" : "bg-muted/50"
                  }`}
                />
              ))}
            </div>
            <div className="text-xs text-muted mt-1.5">
              {t.games} game{t.games !== 1 ? "s" : ""}
            </div>
            <div className="text-[10px] text-muted mt-0.5">
              {t.matchups.map((m) => m.opponent).join(", ")}
            </div>
          </div>
        ))}
      </div>

      {!showAll && displayed.length < grid.length && (
        <button
          onClick={() => setShowAll(true)}
          className="mt-3 flex items-center gap-1 text-xs text-muted hover:text-accent transition-colors mx-auto"
        >
          <ChevronDown size={12} /> Show all {grid.length} teams
        </button>
      )}
      {showAll && (
        <button
          onClick={() => setShowAll(false)}
          className="mt-3 flex items-center gap-1 text-xs text-muted hover:text-accent transition-colors mx-auto"
        >
          <ChevronUp size={12} /> Show fewer
        </button>
      )}
    </section>
  );
}


function StreamerRow({ s, rank }: { s: Streamer; rank: number }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <div
      className={`rounded-xl border bg-card p-4 transition-colors hover:border-accent/40 ${
        rank <= 3 ? "border-accent/30" : "border-line"
      }`}
    >
      <div className="flex gap-4 items-start">
        {/* Rank + projected */}
        <div className="flex flex-col items-center shrink-0 w-12">
          <span className={`text-xs font-medium ${rank <= 3 ? "text-accent" : "text-muted"}`}>
            #{rank}
          </span>
          <span className="text-lg font-bold tabular-nums text-pos">
            {s.projected_total.toFixed(0)}
          </span>
          <span className="text-[10px] text-muted">fpts</span>
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-baseline gap-2 flex-wrap">
            <h3 className="text-base font-semibold text-gray-100">{s.name}</h3>
            <span className="text-sm text-muted">{s.position}</span>
            <span className="text-xs bg-surface text-muted rounded px-1.5 py-0.5 font-mono">
              {s.team}
            </span>
            {rank <= 3 && (
              <span className="text-xs bg-accent/15 text-accent rounded-full px-2 py-0.5 font-medium flex items-center gap-0.5">
                <Flame size={10} /> top pick
              </span>
            )}
          </div>

          {/* Stats row */}
          <div className="flex items-center gap-3 mt-1.5 text-sm text-muted">
            <span className="flex items-center gap-1">
              <Calendar size={12} /> {s.n_games} game{s.n_games !== 1 ? "s" : ""}
            </span>
            <span className="tabular-nums">{s.fppg.toFixed(1)}/g</span>
            {s.soft_matchups > 0 && (
              <span className="flex items-center gap-1 text-pos">
                <TrendingUp size={12} /> {s.soft_matchups} soft
              </span>
            )}
          </div>

          {/* Matchup chips */}
          <button
            type="button"
            onClick={() => setExpanded(!expanded)}
            className="flex items-center gap-1 mt-2 text-xs text-muted hover:text-gray-300 transition-colors"
          >
            <ChevronDown size={12} className={`transition-transform ${expanded ? "rotate-180" : ""}`} />
            Matchups
          </button>
          {expanded && (
            <div className="flex flex-wrap gap-1.5 mt-1.5">
              {s.matchups.map((m, i) => (
                <span
                  key={i}
                  className="inline-flex items-center gap-1 rounded bg-surface px-2 py-1 text-xs font-mono"
                >
                  vs {m.opponent} <MultBadge mult={m.mult} />
                </span>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}


function SkeletonRow() {
  return (
    <div className="rounded-xl border border-line bg-card p-4 animate-pulse">
      <div className="flex gap-4">
        <div className="w-12 flex flex-col items-center gap-1">
          <div className="h-3 w-6 rounded bg-line" />
          <div className="h-5 w-10 rounded bg-line" />
        </div>
        <div className="flex-1 space-y-2">
          <div className="h-4 w-44 rounded bg-line" />
          <div className="h-3 w-64 rounded bg-line" />
          <div className="h-3 w-28 rounded bg-line" />
        </div>
      </div>
    </div>
  );
}


export default function StreamersPage() {
  const [data, setData] = useState<StreamersPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API_BASE}/api/streamers?top=30`)
      .then(async (res) => {
        if (!res.ok) throw new Error(`API error ${res.status}`);
        return res.json();
      })
      .then((d) => setData(d as StreamersPayload))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="min-h-screen bg-bg">
      {/* Header */}
      <header className="border-b border-line bg-card/60 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-4 py-3 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2 hover:opacity-80 transition-opacity">
            <div className="h-7 w-7 rounded-lg bg-accent flex items-center justify-center">
              <Zap size={16} className="text-bg" />
            </div>
            <span className="text-lg font-bold tracking-tight">WaiverEdge</span>
          </Link>
          <Link
            href="/"
            className="flex items-center gap-1.5 rounded-lg bg-accent px-3 py-1.5 text-sm font-semibold text-bg hover:opacity-90 transition-opacity"
          >
            Your roster <ArrowRight size={14} />
          </Link>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-8">
        {/* Title */}
        <div className="mb-8">
          <h1 className="text-2xl font-bold tracking-tight mb-2 flex items-center gap-2">
            <Flame size={22} className="text-accent" />
            Top Streamers This Week
          </h1>
          <p className="text-sm text-muted leading-relaxed max-w-2xl">
            The best fantasy streaming pickups ranked by projected value.
            Schedule density × matchups × recent form — real sports data, updated weekly.
          </p>
        </div>

        {/* Error */}
        {error && (
          <div className="rounded-lg border border-neg/30 bg-neg/10 px-4 py-3 mb-6">
            <p className="text-sm text-neg">{error}</p>
          </div>
        )}

        {/* Loading */}
        {loading && (
          <div className="space-y-3">
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2 mb-10">
              {[1, 2, 3, 4, 5, 6, 7, 8].map((i) => (
                <div key={i} className="rounded-lg border border-line bg-card p-3 animate-pulse">
                  <div className="h-4 w-10 mx-auto rounded bg-line" />
                  <div className="h-2 w-16 mx-auto rounded bg-line mt-2" />
                </div>
              ))}
            </div>
            {[1, 2, 3, 4, 5].map((i) => <SkeletonRow key={i} />)}
          </div>
        )}

        {/* Content */}
        {data && !loading && (
          <>
            <ScheduleGrid grid={data.schedule_grid} week={data.week} />

            {/* Streamers list */}
            <section>
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-base font-semibold flex items-center gap-2">
                  <TrendingUp size={16} className="text-pos" /> Top Streaming Pickups
                </h2>
                <span className="text-xs text-muted">
                  {data.streamers.length} players · by projected fpts
                </span>
              </div>

              <div className="space-y-3">
                {data.streamers.map((s, i) => (
                  <StreamerRow key={s.player_id} s={s} rank={i + 1} />
                ))}
              </div>
            </section>

            {/* CTA */}
            <div className="mt-12 rounded-xl border border-accent/30 bg-accent/5 p-6 text-center">
              <h3 className="text-lg font-bold mb-2">Want picks for YOUR roster?</h3>
              <p className="text-sm text-muted mb-4 max-w-md mx-auto">
                The streamers above are generic. Paste your roster and the engine ranks who to
                add and who to drop — personalized value-over-replacement.
              </p>
              <Link
                href="/"
                className="inline-flex items-center gap-2 rounded-lg bg-accent px-5 py-2.5 text-sm font-semibold text-bg hover:opacity-90 transition-opacity"
              >
                <Zap size={16} /> Rank adds for my team <ArrowRight size={14} />
              </Link>
            </div>
          </>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-line mt-16 py-6">
        <p className="text-center text-xs text-muted">
          WaiverEdge · Real sports data · No logos or trademarks used
        </p>
      </footer>
    </div>
  );
}
