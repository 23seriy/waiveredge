"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  ArrowUpDown,
  Calendar,
  Check,
  ChevronDown,
  Crown,
  ExternalLink,
  Flame,
  Loader2,
  RefreshCw,
  TrendingUp,
  Zap,
} from "lucide-react";

type Recommendation = {
  add_player_id: number;
  add_name: string;
  add_position: string;
  add_value: number;
  drop_player_id: number | null;
  drop_name: string | null;
  n_games: number;
  soft_matchups: number;
  marginal: number;
  rationale: string;
  total_z: number | null;
  per_cat_z: Record<string, number> | null;
  helps: string[] | null;
};

type LeagueInfo = {
  id: number;
  platform: string;
  league_id: string;
  team_key: string;
  sport: string;
  roster: { player_id: number; name: string; slot: string; droppable: boolean }[];
};

type RecsPayload = {
  connection_id: number;
  week: { start: string; end: string };
  scoring_mode: string;
  recommendations: Recommendation[];
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";
const CAT_LABELS: Record<string, string> = {
  fg_pct: "FG%", ft_pct: "FT%", fg3m: "3PM", pts: "PTS", reb: "REB",
  ast: "AST", stl: "STL", blk: "BLK", turnover: "TO",
  avg: "AVG", hr: "HR", rbi: "RBI", r: "R", sb: "SB",
  w: "W", sv: "SV", era: "ERA", whip: "WHIP", k: "K",
};
const NINE_CAT = ["fg_pct", "ft_pct", "fg3m", "pts", "reb", "ast", "stl", "blk", "turnover"];
const MLB_5X5 = ["avg", "hr", "rbi", "r", "sb", "w", "sv", "era", "whip", "k"];
function getCatKeys(sport: string) { return sport === "mlb" ? MLB_5X5 : NINE_CAT; }
function getCatLabel(sport: string) { return sport === "mlb" ? "5x5" : "9-Cat"; }

function ZBadge({ cat, z }: { cat: string; z: number }) {
  const label = CAT_LABELS[cat] ?? cat;
  const color = z > 0.3 ? "text-pos" : z < -0.3 ? "text-neg" : "text-muted";
  return (
    <span className={`inline-flex items-center rounded px-1.5 py-0.5 text-xs font-mono ${color} bg-surface`}>
      {label} {z >= 0 ? "+" : ""}{z.toFixed(1)}
    </span>
  );
}

function RecCard({ rec, rank, mode, sport, platform, connectionId, onExecuted }: {
  rec: Recommendation; rank: number; mode: string; sport: string;
  platform: string; connectionId: string; onExecuted: () => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const [executing, setExecuting] = useState(false);
  const [execResult, setExecResult] = useState<{ success: boolean; detail: string; deep_link?: string } | null>(null);

  async function handleExecute() {
    setExecuting(true);
    setExecResult(null);
    try {
      const res = await fetch(`${API_BASE}/api/leagues/${connectionId}/execute`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ add_player_id: rec.add_player_id, drop_player_id: rec.drop_player_id }),
      });
      const data = await res.json();
      if (res.ok) {
        setExecResult(data);
        if (data.success) onExecuted();
      } else {
        const detail = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
        setExecResult({ success: false, detail });
      }
    } catch {
      setExecResult({ success: false, detail: "Network error — try again." });
    } finally {
      setExecuting(false);
    }
  }
  const isCategory = mode === "categories" && rec.per_cat_z;
  const marginalStr = mode === "categories"
    ? `${rec.marginal >= 0 ? "+" : ""}${rec.marginal.toFixed(1)}z`
    : `${rec.marginal >= 0 ? "+" : ""}${rec.marginal.toFixed(1)}`;

  return (
    <div className="group rounded-xl border border-line bg-card p-4 transition-colors hover:border-accent/40">
      <div className="flex gap-4 items-start">
        <div className="flex flex-col items-center shrink-0 w-10">
          <span className="text-xs text-muted font-medium">#{rank}</span>
          <span className={`text-lg font-bold tabular-nums ${rec.marginal >= 0 ? "text-pos" : "text-neg"}`}>{marginalStr}</span>
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-baseline gap-2 flex-wrap">
            <h3 className="text-base font-semibold text-gray-100">{rec.add_name}</h3>
            <span className="text-sm text-muted">{rec.add_position}</span>
            {rec.helps && rec.helps.length > 0 && (
              <span className="text-xs bg-pos/15 text-pos rounded-full px-2 py-0.5 font-medium">helps weak cats</span>
            )}
          </div>
          <div className="flex items-center gap-3 mt-1.5 text-sm text-muted">
            <span className="flex items-center gap-1"><Calendar size={12} /> {rec.n_games} game{rec.n_games !== 1 ? "s" : ""}</span>
            {rec.soft_matchups > 0 && <span className="flex items-center gap-1"><TrendingUp size={12} /> {rec.soft_matchups} soft</span>}
            {rec.drop_name && <span>drop <span className="text-accent font-medium">{rec.drop_name}</span></span>}
          </div>
          {isCategory && rec.per_cat_z && (
            <div className="flex flex-wrap gap-1 mt-2">
              {getCatKeys(sport).filter((c) => c in rec.per_cat_z!).map((cat) => <ZBadge key={cat} cat={cat} z={rec.per_cat_z![cat]} />)}
            </div>
          )}
          <div className="flex items-center gap-3 mt-2">
            <button type="button" onClick={() => setExpanded(!expanded)} className="flex items-center gap-1 text-xs text-muted hover:text-gray-300 transition-colors">
              <ChevronDown size={12} className={`transition-transform ${expanded ? "rotate-180" : ""}`} />
              {expanded ? "Less" : "Details"}
            </button>
            {!execResult?.success && (
              execResult?.deep_link ? (
                <a href={execResult.deep_link} target="_blank" rel="noopener noreferrer"
                   className="flex items-center gap-1 text-xs font-medium text-accent hover:text-accent/80 transition-colors">
                  <ExternalLink size={12} /> Open in ESPN
                </a>
              ) : platform === "espn" ? (
                <button type="button" disabled={executing} onClick={async () => {
                  setExecuting(true);
                  try {
                    const res = await fetch(`${API_BASE}/api/leagues/${connectionId}/execute`, {
                      method: "POST",
                      headers: { "Content-Type": "application/json" },
                      body: JSON.stringify({ add_player_id: rec.add_player_id, drop_player_id: rec.drop_player_id }),
                    });
                    const data = await res.json();
                    if (data.deep_link) window.open(data.deep_link, "_blank");
                    setExecResult(data);
                  } catch {
                    setExecResult({ success: false, detail: "Network error — try again." });
                  } finally {
                    setExecuting(false);
                  }
                }}
                  className="flex items-center gap-1 rounded-md bg-accent/15 border border-accent/30 px-2.5 py-1 text-xs font-medium text-accent hover:bg-accent/25 transition-colors disabled:opacity-40">
                  {executing ? <Loader2 size={12} className="animate-spin" /> : <ExternalLink size={12} />}
                  {executing ? "Opening…" : "Open in ESPN"}
                </button>
              ) : (
                <button type="button" onClick={handleExecute} disabled={executing}
                  className="flex items-center gap-1 rounded-md bg-accent/15 border border-accent/30 px-2.5 py-1 text-xs font-medium text-accent hover:bg-accent/25 transition-colors disabled:opacity-40">
                  {executing ? <Loader2 size={12} className="animate-spin" /> : <Zap size={12} />}
                  {executing ? "Executing…" : "Execute move"}
                </button>
              )
            )}
            {execResult?.success && (
              <span className="flex items-center gap-1 text-xs font-medium text-pos">
                <Check size={12} /> Done!
              </span>
            )}
          </div>
          {execResult && !execResult.success && !execResult.deep_link && (
            <p className="mt-1.5 text-xs text-neg">{execResult.detail}</p>
          )}
          {expanded && <p className="mt-1.5 text-sm text-muted leading-relaxed">{rec.rationale}</p>}
        </div>
      </div>
    </div>
  );
}

export default function LeaguePage() {
  const params = useParams();
  const connectionId = params.id as string;
  const sport = params.sport as string;
  const [league, setLeague] = useState<LeagueInfo | null>(null);
  const [recs, setRecs] = useState<RecsPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [unresolved, setUnresolved] = useState<string[]>([]);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [lr, rr] = await Promise.all([
        fetch(`${API_BASE}/api/leagues/${connectionId}`),
        fetch(`${API_BASE}/api/leagues/${connectionId}/recs`),
      ]);
      if (!lr.ok) throw new Error(`League fetch failed (${lr.status})`);
      setLeague((await lr.json()) as LeagueInfo);
      if (rr.status === 402) {
        setError("__paywall__");
      } else if (rr.ok) {
        setRecs((await rr.json()) as RecsPayload);
      } else {
        const rb = await rr.json().catch(() => null);
        const detail = rb?.detail;
        const recsMsg = typeof detail === "string" ? detail : detail ? JSON.stringify(detail) : `Recs failed (${rr.status})`;
        setError(recsMsg);
      }
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : typeof e === "string" ? e : "Failed to load";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [connectionId]);

  useEffect(() => { loadData(); }, [loadData]);

  async function syncRoster() {
    setSyncing(true);
    setUnresolved([]);
    try {
      const res = await fetch(`${API_BASE}/api/leagues/${connectionId}/sync`, { method: "POST" });
      if (res.status === 402) {
        setError("__paywall__");
        return;
      }
      if (!res.ok) {
        const b = await res.json().catch(() => null);
        const detail = b?.detail;
        const msg = typeof detail === "string" ? detail : detail ? JSON.stringify(detail) : `Sync failed (${res.status})`;
        throw new Error(msg);
      }
      const syncResult = await res.json();
      if (syncResult.unresolved && syncResult.unresolved.length > 0) {
        setUnresolved(syncResult.unresolved);
      }
      await loadData();
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : typeof e === "string" ? e : "Sync failed";
      setError(msg);
    } finally {
      setSyncing(false);
    }
  }

  const mode = recs?.scoring_mode ?? "points";
  const leagueSport = league?.sport ?? sport;

  return (
    <main className="max-w-3xl mx-auto px-4 py-8">
      {loading && <div className="flex items-center justify-center py-20"><Loader2 size={24} className="animate-spin text-accent" /><span className="ml-2 text-muted">Loading…</span></div>}
      {error === "__paywall__" && (
        <div className="rounded-xl border-2 border-accent bg-accent/5 p-6 text-center mb-6">
          <Crown size={28} className="text-accent mx-auto mb-2" />
          <h3 className="text-lg font-bold mb-1">Upgrade to Pro</h3>
          <p className="text-sm text-muted mb-4">Personalized league recommendations require WaiverEdge Pro.</p>
          <Link href="/pricing" className="inline-flex items-center gap-2 rounded-lg bg-accent px-5 py-2.5 text-sm font-semibold text-bg hover:opacity-90">
            <Crown size={14} /> View pricing
          </Link>
        </div>
      )}
      {error && error !== "__paywall__" && <div className="rounded-lg border border-neg/30 bg-neg/10 px-4 py-3 mb-6"><p className="text-sm text-neg">{error}</p></div>}

      {league && !loading && (
        <>
          <div className="flex items-center justify-between mb-6">
            <div>
              <h1 className="text-xl font-bold tracking-tight">Your League</h1>
              <p className="text-xs text-muted mt-0.5">{league.platform.toUpperCase()} · {league.league_id}{league.roster.length > 0 && ` · ${league.roster.length} players`}</p>
            </div>
            <button onClick={syncRoster} disabled={syncing} className="flex items-center gap-1.5 rounded-lg bg-surface border border-line px-3 py-1.5 text-sm text-muted hover:text-accent hover:border-accent/40 transition-colors disabled:opacity-40">
              <RefreshCw size={14} className={syncing ? "animate-spin" : ""} /> {syncing ? "Syncing…" : "Sync roster"}
            </button>
          </div>

          {league.roster.length === 0 && (
            <div className="rounded-xl border border-accent/30 bg-accent/5 p-6 text-center mb-8">
              <p className="text-sm text-muted mb-3">No roster synced yet.</p>
              <button onClick={syncRoster} disabled={syncing} className="inline-flex items-center gap-2 rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-bg hover:opacity-90 disabled:opacity-40">
                <RefreshCw size={14} className={syncing ? "animate-spin" : ""} /> Sync from {league.platform === "espn" ? "ESPN" : "Yahoo"}
              </button>
            </div>
          )}

          {unresolved.length > 0 && (
            <div className="rounded-lg border border-accent/30 bg-accent/10 px-4 py-3 mb-4">
              <p className="text-sm text-accent">
                Couldn&apos;t match {unresolved.length} player{unresolved.length !== 1 ? "s" : ""}: {unresolved.join(", ")}.
                These players may not be in our data yet (recent callups, minor leaguers).
              </p>
            </div>
          )}

          {league.roster.length > 0 && (
            <div className="mb-8">
              <h2 className="text-base font-semibold mb-3">Your Roster</h2>
              <div className="rounded-xl border border-line bg-card overflow-hidden">
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-px bg-line">
                  {league.roster.map((p) => (
                    <div key={p.player_id} className="bg-card px-3 py-2 flex items-center gap-2">
                      <span className="text-xs bg-surface text-muted rounded px-1.5 py-0.5 font-mono shrink-0">
                        {p.slot || "UTIL"}
                      </span>
                      <span className="text-sm truncate">{p.name}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {recs && recs.recommendations.length > 0 && (
            <>
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h2 className="text-base font-semibold">Waiver Action List</h2>
                  <p className="text-xs text-muted mt-0.5">Week of {recs.week.start} to {recs.week.end}{recs.scoring_mode === "categories" && <> · <span className="text-accent">{getCatLabel(leagueSport)}</span></>}</p>
                </div>
                <span className="text-xs text-muted">{recs.recommendations.length} add{recs.recommendations.length !== 1 ? "s" : ""}</span>
              </div>
              <div className="space-y-3">{recs.recommendations.map((r, i) => <RecCard key={r.add_player_id} rec={r} rank={i + 1} mode={mode} sport={leagueSport} platform={league?.platform ?? ""} connectionId={connectionId} onExecuted={loadData} />)}</div>
            </>
          )}
          {recs && recs.recommendations.length === 0 && league.roster.length > 0 && (
            <p className="text-sm text-muted text-center py-12">No free agents outrank your roster this week.</p>
          )}
        </>
      )}
    </main>
  );
}
