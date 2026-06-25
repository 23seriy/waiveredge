"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import {
  Calendar,
  ChevronDown,
  ChevronUp,
  Flame,
  Loader2,
  TrendingUp,
} from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

type ScheduleEntry = {
  date: string;
  opponent: string;
  home: boolean;
  matchup_mult: number;
};
type Matchup = { opponent: string; mult: number };
type PlayerRow = {
  player_id: number;
  name: string;
  position: string;
  team: string;
  team_id: number;
  team_name: string;
  n_games: number;
  soft_matchups: number;
  fppg: number;
  projected_total: number;
  games_sampled: number;
  per_game: Record<string, number>;
  schedule: ScheduleEntry[];
  matchups: Matchup[];
};
type Payload = {
  week: { start: string; end: string };
  streamers: PlayerRow[];
  stat_columns: string[];
  stat_labels: Record<string, string>;
};

type Tab = "projections" | "statistics" | "schedule";

// Sport-specific stat column definitions
const STAT_DISPLAY: Record<string, { projections: string[]; statistics: string[] }> = {
  mlb: {
    projections: ["fppg", "n_games", "projected_total"],
    statistics: ["ab", "r", "h", "hr", "rbi", "sb", "bb", "k_hitting", "ip", "k_pitching", "w", "sv", "er"],
  },
  wnba: {
    projections: ["fppg", "n_games", "projected_total"],
    statistics: ["pts", "reb", "ast", "stl", "blk", "fg3m", "turnover", "fgm", "fga", "ftm", "fta"],
  },
  nba: {
    projections: ["fppg", "n_games", "projected_total"],
    statistics: ["pts", "reb", "ast", "stl", "blk", "fg3m", "turnover", "fgm", "fga", "ftm", "fta"],
  },
};

const STAT_LABELS: Record<string, string> = {
  ab: "AB", r: "R", h: "H", hr: "HR", rbi: "RBI", sb: "SB", bb: "BB",
  k_hitting: "K", k_pitching: "K", ip: "IP", w: "W", sv: "SV", er: "ER",
  ha: "HA", bba: "BBA",
  pts: "PTS", reb: "REB", ast: "AST", stl: "STL", blk: "BLK",
  fg3m: "3PM", turnover: "TO", fgm: "FGM", fga: "FGA", ftm: "FTM", fta: "FTA",
  fppg: "FPPG", n_games: "GP", projected_total: "PROJ",
};

function formatDate(iso: string) {
  const d = new Date(iso + "T12:00:00");
  return d.toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" });
}

function formatShortDate(iso: string) {
  const d = new Date(iso + "T12:00:00");
  return d.toLocaleDateString("en-US", { weekday: "short", month: "numeric", day: "numeric" });
}

function MultBadge({ mult }: { mult: number }) {
  if (mult >= 1.08) return <span className="text-pos text-[10px] font-medium ml-0.5">▲</span>;
  if (mult <= 0.92) return <span className="text-neg text-[10px] font-medium ml-0.5">▼</span>;
  return null;
}

function TeamLogo({ teamId, sport, size = 18 }: { teamId: number; sport: string; size?: number }) {
  const [err, setErr] = useState(false);
  if (err) return null;

  const src =
    sport === "mlb"
      ? `https://midfield.mlbstatic.com/v1/team/${teamId}/spots/${size * 2}`
      : `https://a.espncdn.com/combiner/i?img=/i/teamlogos/${sport}/${teamId}.png&h=${size * 2}&w=${size * 2}`;

  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={src}
      alt=""
      width={size}
      height={size}
      className="inline-block"
      onError={() => setErr(true)}
    />
  );
}

function playerHeadshotUrl(playerId: number, sport: string): string {
  if (sport === "mlb") {
    return `https://img.mlbstatic.com/mlb-photos/image/upload/d_people:generic:headshot:67:current.png/w_60,q_auto:best/v1/people/${playerId}/headshot/67/current`;
  }
  const espnSport = sport === "wnba" ? "wnba" : "nba";
  return `https://a.espncdn.com/combiner/i?img=/i/headshots/${espnSport}/players/full/${playerId}.png&h=60&w=60`;
}

function PlayerHeadshot({ playerId, sport, size = 28, name }: { playerId: number; sport: string; size?: number; name: string }) {
  const [err, setErr] = useState(false);
  const initials = name.split(" ").map((w) => w[0]).join("").slice(0, 2).toUpperCase();

  if (err) {
    return (
      <div
        className="rounded-full bg-gradient-to-br from-accent/30 to-accent/10 flex items-center justify-center text-[10px] font-bold text-accent shrink-0"
        style={{ width: size, height: size }}
      >
        {initials}
      </div>
    );
  }

  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={playerHeadshotUrl(playerId, sport)}
      alt={name}
      width={size}
      height={size}
      className="rounded-full object-cover bg-surface shrink-0"
      onError={() => setErr(true)}
    />
  );
}


function ProjectionsTable({ players, sport }: { players: PlayerRow[]; sport: string }) {
  const statKeys = STAT_DISPLAY[sport]?.statistics ?? [];

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-line/50 text-muted text-xs">
            <th className="text-left py-2.5 px-2 font-medium w-8">#</th>
            <th className="text-left py-2.5 px-2 font-medium min-w-[220px]">PLAYER</th>
            <th className="text-center py-2.5 px-2 font-medium">GP</th>
            <th className="text-center py-2.5 px-2 font-medium">FPPG</th>
            <th className="text-center py-2.5 px-2 font-medium bg-accent/5 rounded">PROJ</th>
            {statKeys.map((key) => (
              <th key={key} className="text-center py-2.5 px-2 font-medium">
                {STAT_LABELS[key] || key.toUpperCase()}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {players.map((p, i) => (
            <tr
              key={p.player_id}
              className="border-b border-line/30 hover:bg-surface/50 transition-colors"
            >
              <td className="py-2.5 px-2 text-muted text-xs tabular-nums">{i + 1}</td>
              <td className="py-2.5 px-2">
                <div className="flex items-center gap-2">
                  <PlayerHeadshot playerId={p.player_id} sport={sport} size={28} name={p.name} />
                  <div>
                    <span className="font-medium text-gray-100">{p.name}</span>
                    <div className="flex items-center gap-1 mt-0.5">
                      <TeamLogo teamId={p.team_id} sport={sport} size={12} />
                      <span className="text-muted text-[11px]">
                        {p.team} · {p.position}
                      </span>
                    </div>
                  </div>
                </div>
              </td>
              <td className="py-2.5 px-2 text-center tabular-nums">
                <span className="flex items-center justify-center gap-0.5">
                  <Calendar size={10} className="text-muted" />
                  {p.n_games}
                </span>
              </td>
              <td className="py-2.5 px-2 text-center tabular-nums font-medium">
                {p.fppg.toFixed(1)}
              </td>
              <td className="py-2.5 px-2 text-center tabular-nums font-bold text-pos bg-accent/5">
                {p.projected_total.toFixed(1)}
              </td>
              {statKeys.map((key) => {
                const val = p.per_game[key];
                return (
                  <td key={key} className="py-2.5 px-2 text-center tabular-nums text-muted">
                    {val !== undefined ? val.toFixed(1) : "—"}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}


function StatisticsTable({ players, sport }: { players: PlayerRow[]; sport: string }) {
  const statKeys = STAT_DISPLAY[sport]?.statistics ?? [];

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-line/50 text-muted text-xs">
            <th className="text-left py-2.5 px-2 font-medium w-8">#</th>
            <th className="text-left py-2.5 px-2 font-medium min-w-[220px]">PLAYER</th>
            <th className="text-center py-2.5 px-2 font-medium">GP*</th>
            {statKeys.map((key) => (
              <th key={key} className="text-center py-2.5 px-2 font-medium">
                {STAT_LABELS[key] || key.toUpperCase()}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {players.map((p, i) => (
            <tr
              key={p.player_id}
              className="border-b border-line/30 hover:bg-surface/50 transition-colors"
            >
              <td className="py-2.5 px-2 text-muted text-xs tabular-nums">{i + 1}</td>
              <td className="py-2.5 px-2">
                <div className="flex items-center gap-2">
                  <PlayerHeadshot playerId={p.player_id} sport={sport} size={28} name={p.name} />
                  <div>
                    <span className="font-medium text-gray-100">{p.name}</span>
                    <div className="flex items-center gap-1 mt-0.5">
                      <TeamLogo teamId={p.team_id} sport={sport} size={12} />
                      <span className="text-muted text-[11px]">
                        {p.team} · {p.position}
                      </span>
                    </div>
                  </div>
                </div>
              </td>
              <td className="py-2.5 px-2 text-center tabular-nums text-muted">
                {p.games_sampled}
              </td>
              {statKeys.map((key) => {
                const val = p.per_game[key];
                return (
                  <td key={key} className="py-2.5 px-2 text-center tabular-nums">
                    {val !== undefined ? val.toFixed(1) : "—"}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr>
            <td colSpan={statKeys.length + 3} className="py-2 px-2 text-[10px] text-muted">
              * GP = games sampled for projections (last 30 days, recency-weighted)
            </td>
          </tr>
        </tfoot>
      </table>
    </div>
  );
}


function ScheduleTable({ players, sport, week }: { players: PlayerRow[]; sport: string; week: { start: string; end: string } }) {
  // Collect all unique dates across all players
  const allDates = [
    ...new Set(players.flatMap((p) => p.schedule.map((s) => s.date)).filter(Boolean)),
  ].sort();

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-line/50 text-muted text-xs">
            <th className="text-left py-2.5 px-2 font-medium w-8">#</th>
            <th className="text-left py-2.5 px-2 font-medium min-w-[220px]">PLAYER</th>
            <th className="text-center py-2.5 px-2 font-medium">GP</th>
            {allDates.map((d) => (
              <th key={d} className="text-center py-2.5 px-1.5 font-medium min-w-[65px]">
                {formatShortDate(d)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {players.map((p, i) => {
            const scheduleByDate: Record<string, ScheduleEntry> = {};
            p.schedule.forEach((s) => { scheduleByDate[s.date] = s; });

            return (
              <tr
                key={p.player_id}
                className="border-b border-line/30 hover:bg-surface/50 transition-colors"
              >
                <td className="py-2.5 px-2 text-muted text-xs tabular-nums">{i + 1}</td>
                <td className="py-2.5 px-2">
                  <div className="flex items-center gap-2">
                    <PlayerHeadshot playerId={p.player_id} sport={sport} size={28} name={p.name} />
                    <div>
                      <span className="font-medium text-gray-100">{p.name}</span>
                      <div className="flex items-center gap-1 mt-0.5">
                        <TeamLogo teamId={p.team_id} sport={sport} size={12} />
                        <span className="text-muted text-[11px]">
                          {p.team} · {p.position}
                        </span>
                      </div>
                    </div>
                  </div>
                </td>
                <td className="py-2.5 px-2 text-center tabular-nums font-medium">{p.n_games}</td>
                {allDates.map((d) => {
                  const entry = scheduleByDate[d];
                  if (!entry) {
                    return (
                      <td key={d} className="py-2.5 px-1.5 text-center text-muted/30">
                        —
                      </td>
                    );
                  }
                  return (
                    <td key={d} className="py-2.5 px-1.5 text-center">
                      <span className="inline-flex items-center gap-0.5 text-xs tabular-nums">
                        <span className="text-muted/60 text-[10px]">{entry.home ? "vs" : "@"}</span>
                        <span className="font-medium">{entry.opponent}</span>
                        <MultBadge mult={entry.matchup_mult} />
                      </span>
                    </td>
                  );
                })}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}


function SkeletonTable() {
  return (
    <div className="space-y-2 animate-pulse">
      <div className="h-8 bg-line/50 rounded w-full" />
      {Array.from({ length: 10 }).map((_, i) => (
        <div key={i} className="h-10 bg-line/30 rounded w-full" />
      ))}
    </div>
  );
}


export default function TopAvailablePage() {
  const params = useParams();
  const sport = params.sport as string;
  const [data, setData] = useState<Payload | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>("projections");
  const [showCount, setShowCount] = useState(30);

  useEffect(() => {
    setLoading(true);
    setError(null);
    setData(null);
    fetch(`${API_BASE}/api/streamers?top=50&sport=${sport}`)
      .then(async (res) => {
        if (!res.ok) throw new Error(`API error ${res.status}`);
        return res.json();
      })
      .then((d) => setData(d as Payload))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [sport]);

  const tabs: { key: Tab; label: string }[] = [
    { key: "projections", label: "Projections" },
    { key: "statistics", label: "Statistics" },
    { key: "schedule", label: "Schedule" },
  ];

  const displayed = data ? data.streamers.slice(0, showCount) : [];
  const hasMore = data ? data.streamers.length > showCount : false;

  return (
    <main className="mx-auto px-4 md:px-8 lg:px-16 py-8">
      {/* Header */}
      <div className="mb-6 animate-fade-in">
        <h1 className="text-2xl md:text-3xl font-extrabold tracking-tight mb-2 flex items-center gap-2.5">
          <div className="h-9 w-9 rounded-lg bg-accent/10 flex items-center justify-center">
            <TrendingUp size={20} className="text-accent" />
          </div>
          Top Available
        </h1>
        <p className="text-sm text-muted leading-relaxed max-w-2xl">
          Best free agents ranked by projected fantasy value for the rest of the week.
          Stats are recency-weighted averages from the last 30 days.
        </p>
        {data && (
          <p className="text-xs text-muted/70 mt-1">
            {formatDate(data.week.start)} – {formatDate(data.week.end)} · {data.streamers.length} players
          </p>
        )}
      </div>

      {/* Tab bar */}
      <div className="flex items-center gap-1 mb-5 bg-surface/50 rounded-lg p-1 w-fit">
        {tabs.map((t) => (
          <button
            key={t.key}
            type="button"
            onClick={() => setTab(t.key)}
            className={`px-4 py-1.5 rounded-md text-sm font-medium transition-all ${
              tab === t.key
                ? "bg-accent text-bg shadow-sm"
                : "text-muted hover:text-gray-200"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Error */}
      {error && (
        <div className="rounded-lg border border-neg/30 bg-neg/10 px-4 py-3 mb-6">
          <p className="text-sm text-neg">{error}</p>
        </div>
      )}

      {/* Loading */}
      {loading && <SkeletonTable />}

      {/* Content */}
      {data && !loading && (
        <div className="animate-fade-in rounded-xl border border-line bg-card overflow-hidden">
          {tab === "projections" && (
            <ProjectionsTable players={displayed} sport={sport} />
          )}
          {tab === "statistics" && (
            <StatisticsTable players={displayed} sport={sport} />
          )}
          {tab === "schedule" && (
            <ScheduleTable players={displayed} sport={sport} week={data.week} />
          )}

          {/* Show more / less */}
          <div className="flex items-center justify-center gap-3 py-3 border-t border-line/30">
            {hasMore && (
              <button
                type="button"
                onClick={() => setShowCount((prev) => prev + 20)}
                className="flex items-center gap-1 text-xs text-muted hover:text-accent transition-colors"
              >
                <ChevronDown size={12} /> Show more
              </button>
            )}
            {showCount > 30 && (
              <button
                type="button"
                onClick={() => setShowCount(30)}
                className="flex items-center gap-1 text-xs text-muted hover:text-accent transition-colors"
              >
                <ChevronUp size={12} /> Show less
              </button>
            )}
          </div>
        </div>
      )}
    </main>
  );
}
