"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import {
  ArrowDown,
  ArrowUpDown,
  Calendar,
  ChevronDown,
  Link2,
  Loader2,
  Plus,
  RotateCcw,
  Search,
  Sparkles,
  TrendingUp,
  Users,
  Zap,
} from "lucide-react";
import Link from "next/link";

type Sport = "nba" | "mlb" | "wnba";
type ScoringMode = "points" | "categories";

type Recommendation = {
  add_player_id: number;
  add_name: string;
  add_position: string;
  add_value: number;
  drop_name: string | null;
  drop_value: number;
  n_games: number;
  soft_matchups: number;
  marginal: number;
  rationale: string;
  total_z: number | null;
  per_cat_z: Record<string, number> | null;
  helps: string[] | null;
  add_fppg?: number;
  drop_fppg?: number;
};

type Payload = {
  week: { start: string; end: string };
  scoring_mode?: ScoringMode;
  recommendations: Recommendation[];
  unresolved?: string[];
  resolved_count?: number;
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";
const STORAGE_KEY = "waiveredge.roster.v1";
const MODE_KEY = "waiveredge.mode.v1";

const SPORT_INFO: Record<Sport, { name: string; sample: string }> = {
  nba: {
    name: "NBA",
    sample: "Nikola Jokic\nLuka Doncic\nAnthony Edwards\nJaren Jackson Jr.\nTyrese Haliburton\nBam Adebayo\nJalen Brunson\nTrae Young\nDomantas Sabonis\nScottie Barnes",
  },
  mlb: {
    name: "MLB",
    sample: "Aaron Judge\nShohei Ohtani\nMookie Betts\nFreddie Freeman\nCorbin Carroll\nJulio Rodriguez\nBobby Witt Jr.\nCorey Seager\nRonald Acuna Jr.\nMatt Olson",
  },
  wnba: {
    name: "WNBA",
    sample: "A'ja Wilson\nBreanna Stewart\nNapheesa Collier\nCaitlin Clark\nAlyssa Thomas\nKelsey Plum\nJewell Loyd\nSabrina Ionescu\nDearica Hamby\nKahleah Copper",
  },
};

const ESPN_ONLY_SPORTS = new Set<Sport>(["wnba"]);
const POINTS_ONLY_SPORTS = new Set<Sport>(["wnba"]);

const CAT_LABELS: Record<string, string> = {
  fg_pct: "FG%", ft_pct: "FT%", fg3m: "3PM", pts: "PTS", reb: "REB",
  ast: "AST", stl: "STL", blk: "BLK", turnover: "TO",
  avg: "AVG", hr: "HR", rbi: "RBI", r: "R", sb: "SB",
  w: "W", sv: "SV", era: "ERA", whip: "WHIP", k: "K",
};

const NINE_CAT = ["fg_pct", "ft_pct", "fg3m", "pts", "reb", "ast", "stl", "blk", "turnover"];
const MLB_5X5 = ["avg", "hr", "rbi", "r", "sb", "w", "sv", "era", "whip", "k"];

function getCatKeys(sport: Sport) { return sport === "mlb" ? MLB_5X5 : NINE_CAT; }
function getCatLabel(sport: Sport) { return sport === "mlb" ? "5x5" : "9-Cat"; }

function formatDate(iso: string) {
  const d = new Date(iso + "T12:00:00");
  return d.toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" });
}

function playerHeadshotUrl(playerId: number, sport: string): string {
  if (sport === "mlb") {
    return `https://img.mlbstatic.com/mlb-photos/image/upload/d_people:generic:headshot:67:current.png/w_80,q_auto:best/v1/people/${playerId}/headshot/67/current`;
  }
  const espnSport = sport === "wnba" ? "wnba" : "nba";
  return `https://a.espncdn.com/combiner/i?img=/i/headshots/${espnSport}/players/full/${playerId}.png&h=80&w=80`;
}

function PlayerHeadshot({ playerId, sport, size = 40, name }: { playerId: number; sport: string; size?: number; name: string }) {
  const [err, setErr] = useState(false);
  const initials = name.split(" ").map((w) => w[0]).join("").slice(0, 2).toUpperCase();

  if (err) {
    return (
      <div
        className="rounded-full bg-gradient-to-br from-accent/30 to-accent/10 flex items-center justify-center text-xs font-bold text-accent shrink-0"
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


function ModeToggle({ mode, onChange, sport }: { mode: ScoringMode; onChange: (m: ScoringMode) => void; sport: Sport }) {
  if (POINTS_ONLY_SPORTS.has(sport)) return null;
  return (
    <div className="flex rounded-lg bg-surface/80 p-0.5 gap-0.5">
      <button
        type="button"
        onClick={() => onChange("points")}
        className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-all ${
          mode === "points"
            ? "bg-accent text-bg shadow-sm shadow-accent/20"
            : "text-muted hover:text-gray-200"
        }`}
      >
        <Zap size={13} /> Points
      </button>
      <button
        type="button"
        onClick={() => onChange("categories")}
        className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-all ${
          mode === "categories"
            ? "bg-accent text-bg shadow-sm shadow-accent/20"
            : "text-muted hover:text-gray-200"
        }`}
      >
        <ArrowUpDown size={13} /> {getCatLabel(sport)}
      </button>
    </div>
  );
}


function ZBadge({ cat, z }: { cat: string; z: number }) {
  const label = CAT_LABELS[cat] ?? cat;
  const color = z > 0.3 ? "text-pos bg-pos/10" : z < -0.3 ? "text-neg bg-neg/10" : "text-muted bg-surface";
  return (
    <span className={`inline-flex items-center rounded-md px-1.5 py-0.5 text-[11px] font-mono font-medium ${color}`}>
      {label} {z >= 0 ? "+" : ""}{z.toFixed(1)}
    </span>
  );
}


function AIInsightButton({ rec }: { rec: Recommendation }) {
  const [insight, setInsight] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [visible, setVisible] = useState(false);

  async function fetchInsight() {
    if (insight) { setVisible(!visible); return; }
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/recommendations/explain`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(rec),
      });
      if (res.ok) {
        const d = await res.json();
        setInsight(d.llm_rationale || d.engine_rationale || "No insight available.");
      } else {
        setInsight("AI insights require an OpenAI API key.");
      }
      setVisible(true);
    } catch { setInsight("Could not generate insight."); setVisible(true); }
    finally { setLoading(false); }
  }

  return (
    <>
      <button
        type="button"
        onClick={fetchInsight}
        disabled={loading}
        className="flex items-center gap-1 text-[11px] font-medium text-accent/70 hover:text-accent transition-colors disabled:opacity-50"
      >
        {loading ? <Loader2 size={10} className="animate-spin" /> : <Sparkles size={10} />}
        {insight && visible ? "Hide" : "AI Insight"}
      </button>
      {visible && insight && (
        <p className="mt-2 text-sm text-gray-300 leading-relaxed bg-gradient-to-r from-accent/5 to-transparent border border-accent/15 rounded-lg px-3 py-2.5">
          {insight}
        </p>
      )}
    </>
  );
}


function RecCard({ rec, rank, mode, sport }: { rec: Recommendation; rank: number; mode: ScoringMode; sport: Sport }) {
  const [expanded, setExpanded] = useState(false);
  const isCategory = mode === "categories" && rec.per_cat_z;
  const marginalStr = mode === "categories"
    ? `${rec.marginal >= 0 ? "+" : ""}${rec.marginal.toFixed(1)}z`
    : `${rec.marginal >= 0 ? "+" : ""}${rec.marginal.toFixed(1)}`;
  const isTop3 = rank <= 3;

  return (
    <div className={`group relative rounded-xl border bg-card/80 backdrop-blur-sm p-4 transition-all hover:shadow-lg hover:shadow-accent/5 ${
      isTop3 ? "border-accent/30 hover:border-accent/50" : "border-line/60 hover:border-line"
    }`}>
      {isTop3 && (
        <div className="absolute -top-px left-4 right-4 h-[2px] bg-gradient-to-r from-transparent via-accent/60 to-transparent rounded-full" />
      )}

      <div className="flex gap-3.5 items-start">
        {/* Rank + headshot */}
        <div className="flex flex-col items-center shrink-0 gap-1.5">
          <span className={`text-[10px] font-bold uppercase tracking-wider ${isTop3 ? "text-accent" : "text-muted/60"}`}>
            #{rank}
          </span>
          <PlayerHeadshot playerId={rec.add_player_id} sport={sport} size={44} name={rec.add_name} />
        </div>

        {/* Main content */}
        <div className="flex-1 min-w-0">
          {/* Player name + position */}
          <div className="flex items-center gap-2 flex-wrap">
            <h3 className="text-[15px] font-semibold text-gray-100 leading-tight">
              {rec.add_name}
            </h3>
            <span className="text-xs text-muted/80 bg-surface/80 rounded px-1.5 py-0.5 font-medium">
              {rec.add_position}
            </span>
            {rec.helps && rec.helps.length > 0 && (
              <span className="text-[10px] bg-pos/15 text-pos rounded-full px-2 py-0.5 font-semibold uppercase tracking-wide">
                helps weak cats
              </span>
            )}
          </div>

          {/* Value + stats row */}
          <div className="flex items-center gap-4 mt-2">
            <div className={`flex items-center gap-1 rounded-lg px-2.5 py-1 text-sm font-bold tabular-nums ${
              rec.marginal >= 0 ? "bg-pos/10 text-pos" : "bg-neg/10 text-neg"
            }`}>
              {rec.marginal >= 0 ? <TrendingUp size={12} /> : <ArrowDown size={12} />}
              {marginalStr}
            </div>
            <div className="flex items-center gap-3 text-xs text-muted">
              <span className="flex items-center gap-1">
                <Calendar size={11} /> {rec.n_games} game{rec.n_games !== 1 ? "s" : ""}
              </span>
              {rec.soft_matchups > 0 && (
                <span className="flex items-center gap-1 text-pos/80">
                  <TrendingUp size={11} /> {rec.soft_matchups} soft
                </span>
              )}
              {rec.add_fppg ? (
                <span className="tabular-nums">{rec.add_fppg.toFixed(1)} fppg</span>
              ) : null}
            </div>
          </div>

          {/* Drop recommendation */}
          {rec.drop_name && (
            <div className="flex items-center gap-2 mt-2 text-xs">
              <span className="text-muted/60">drop</span>
              <span className="inline-flex items-center gap-1 text-neg/80 bg-neg/5 border border-neg/10 rounded-md px-2 py-0.5 font-medium">
                <ArrowDown size={10} />
                {rec.drop_name}
                {rec.drop_fppg ? <span className="text-muted/50 ml-0.5">({rec.drop_fppg.toFixed(1)})</span> : null}
              </span>
            </div>
          )}

          {/* Category z-scores */}
          {isCategory && rec.per_cat_z && (
            <div className="flex flex-wrap gap-1 mt-2.5">
              {getCatKeys(sport).filter((c) => c in rec.per_cat_z!).map((cat) => (
                <ZBadge key={cat} cat={cat} z={rec.per_cat_z![cat]} />
              ))}
            </div>
          )}

          {/* Details + AI */}
          <div className="flex items-center gap-3 mt-2.5">
            <button
              type="button"
              onClick={() => setExpanded(!expanded)}
              className="flex items-center gap-1 text-[11px] font-medium text-muted hover:text-gray-300 transition-colors"
            >
              <ChevronDown size={11} className={`transition-transform ${expanded ? "rotate-180" : ""}`} />
              {expanded ? "Less" : "Why?"}
            </button>
            <AIInsightButton rec={rec} />
          </div>
          {expanded && (
            <p className="mt-2 text-[13px] text-muted leading-relaxed">{rec.rationale}</p>
          )}
        </div>
      </div>
    </div>
  );
}


function SkeletonCard() {
  return (
    <div className="rounded-xl border border-line/50 bg-card/60 p-4 animate-pulse">
      <div className="flex gap-3.5">
        <div className="flex flex-col items-center gap-1.5 shrink-0">
          <div className="h-3 w-5 rounded bg-line/50" />
          <div className="h-11 w-11 rounded-full bg-line/50" />
        </div>
        <div className="flex-1 space-y-2.5">
          <div className="h-4 w-36 rounded bg-line/50" />
          <div className="flex gap-3">
            <div className="h-7 w-16 rounded-lg bg-line/50" />
            <div className="h-4 w-24 rounded bg-line/50 self-center" />
          </div>
          <div className="h-3 w-48 rounded bg-line/50" />
        </div>
      </div>
    </div>
  );
}


function FixtureStatus({ sport }: { sport: Sport }) {
  const [status, setStatus] = useState<{ has_data: boolean; building: boolean; progress: string } | null>(null);

  useEffect(() => {
    let active = true;
    const poll = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/fixtures/status?sport=${sport}`);
        if (res.ok && active) {
          const d = await res.json();
          setStatus(d);
          if (d.building && !d.has_data) {
            setTimeout(poll, 5000);
          }
        }
      } catch { /* ignore */ }
    };
    poll();
    return () => { active = false; };
  }, [sport]);

  if (!status || status.has_data) return null;
  if (!status.building) return null;

  return (
    <div className="rounded-xl border border-accent/30 bg-gradient-to-r from-accent/5 to-transparent p-6 text-center mb-6">
      <Loader2 size={24} className="animate-spin text-accent mx-auto mb-2" />
      <h3 className="text-sm font-semibold mb-1">
        Preparing {SPORT_INFO[sport as Sport]?.name ?? sport.toUpperCase()} data...
      </h3>
      <p className="text-xs text-muted">
        {status.progress || "Fetching players and game stats. This only happens once and takes a few minutes."}
      </p>
    </div>
  );
}


export default function SportDashboard() {
  const params = useParams();
  const sport = (params.sport as Sport) || "nba";

  const [rosterText, setRosterText] = useState("");
  const [mode, setMode] = useState<ScoringMode>("points");
  const [data, setData] = useState<Payload | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const saved = typeof window !== "undefined" ? localStorage.getItem(`${STORAGE_KEY}.${sport}`) : null;
    setRosterText(saved && saved.trim() ? saved : (SPORT_INFO[sport]?.sample ?? ""));
    const savedMode = typeof window !== "undefined" ? localStorage.getItem(MODE_KEY) : null;
    if (POINTS_ONLY_SPORTS.has(sport)) {
      setMode("points");
    } else if (savedMode === "points" || savedMode === "categories") {
      setMode(savedMode);
    }
    setData(null);
  }, [sport]);

  function handleModeChange(m: ScoringMode) {
    setMode(m);
    localStorage.setItem(MODE_KEY, m);
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    const roster = rosterText.split("\n").map((s) => s.trim()).filter(Boolean);

    const body: Record<string, unknown> = { roster, scoring_mode: mode, sport };
    if (mode === "categories") body.categories = getCatKeys(sport);
    localStorage.setItem(`${STORAGE_KEY}.${sport}`, rosterText);

    for (let attempt = 0; attempt < 2; attempt++) {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 30000);
      try {
        const res = await fetch(`${API_BASE}/api/recommendations/manual`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
          signal: controller.signal,
        });
        clearTimeout(timeout);

        if (res.status === 501) {
          setError(`${SPORT_INFO[sport]?.name ?? sport.toUpperCase()} data is still being prepared. Please try again in a few minutes.`);
          setData(null);
          break;
        }
        if (!res.ok) {
          const respBody = await res.json().catch(() => null);
          const detail = respBody?.detail;
          setError(typeof detail === "string" ? detail : detail?.message || `Request failed (${res.status})`);
          setData(null);
          break;
        }
        setData((await res.json()) as Payload);
        break;
      } catch (err) {
        clearTimeout(timeout);
        const isAbort = err instanceof DOMException && err.name === "AbortError";
        if (attempt === 1 || !isAbort) {
          setError(isAbort
            ? "Request timed out. The server may be building data — try again in a minute."
            : "Could not reach the server. Check that the backend is running.");
          setData(null);
        }
      }
    }
    setLoading(false);
  }

  function loadSample() {
    setRosterText(SPORT_INFO[sport]?.sample ?? "");
  }

  const rosterCount = rosterText.split("\n").filter((l) => l.trim()).length;

  return (
    <main className="mx-auto px-4 md:px-8 lg:px-16 max-w-5xl">
      {/* Hero */}
      <section className="pt-8 pb-4 md:pt-12 md:pb-6 text-center animate-fade-in">
        <div className="inline-flex items-center gap-2 rounded-full bg-accent/10 border border-accent/20 px-4 py-1.5 mb-4">
          <Zap size={14} className="text-accent" />
          <span className="text-xs font-semibold text-accent">
            {ESPN_ONLY_SPORTS.has(sport) ? "ESPN" : "Yahoo & ESPN"} · {POINTS_ONLY_SPORTS.has(sport) ? "H2H Points" : `${getCatLabel(sport)} & Points`}
          </span>
        </div>
        <h1 className="text-2xl md:text-4xl font-extrabold tracking-tight mb-3">
          {SPORT_INFO[sport]?.name ?? sport.toUpperCase()} Waiver Wire
        </h1>
        <p className="text-sm text-muted max-w-md mx-auto leading-relaxed">
          Paste your roster to get personalized add/drop recommendations,
          or{" "}
          <Link href={`/${sport}/connect`} className="text-accent hover:underline font-medium inline-flex items-center gap-0.5">
            <Link2 size={12} /> connect your league
          </Link>
          .
        </p>
      </section>

      {/* Fixture status check */}
      <FixtureStatus sport={sport} />

      {/* Two-column layout: input + results */}
      <section className="mt-2 grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: Roster input */}
        <div className="lg:col-span-4 lg:sticky lg:top-20 lg:self-start">
          <div className="rounded-xl border border-line/60 bg-card/80 backdrop-blur-sm overflow-hidden">
            <div className="flex items-center justify-between px-4 py-2.5 border-b border-line/40 bg-surface/30">
              <div className="flex items-center gap-2">
                <Users size={13} className="text-accent" />
                <span className="text-xs font-semibold uppercase tracking-wider text-muted">
                  Your Roster
                </span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-[10px] text-muted/60 tabular-nums">{rosterCount} players</span>
                <button
                  type="button"
                  onClick={loadSample}
                  className="flex items-center gap-1 text-[11px] text-muted hover:text-accent transition-colors"
                >
                  <RotateCcw size={10} /> Sample
                </button>
              </div>
            </div>

            <form onSubmit={submit}>
              <textarea
                rows={8}
                value={rosterText}
                onChange={(e) => setRosterText(e.target.value)}
                placeholder="One player name per line&#10;&#10;Aaron Judge&#10;Shohei Ohtani&#10;Mookie Betts&#10;..."
                className="w-full bg-transparent px-4 py-3 text-[13px] font-mono text-gray-200 placeholder:text-muted/30 resize-y focus:outline-none min-h-[200px]"
              />

              <div className="px-4 pb-4 space-y-3">
                <ModeToggle mode={mode} onChange={handleModeChange} sport={sport} />

                <button
                  type="submit"
                  disabled={loading || !rosterText.trim()}
                  className="w-full flex items-center justify-center gap-2 rounded-lg bg-accent py-2.5 text-sm font-semibold text-bg transition-all hover:brightness-110 hover:shadow-lg hover:shadow-accent/25 disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:shadow-none disabled:hover:brightness-100"
                >
                  {loading ? (
                    <>
                      <Loader2 size={15} className="animate-spin" /> Analyzing…
                    </>
                  ) : (
                    <>
                      <Search size={15} /> Rank waiver adds
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>

        {/* Right: Results */}
        <div className="lg:col-span-8">
          {/* Error */}
          {error && (
            <div className="rounded-xl border border-neg/30 bg-neg/5 px-4 py-4 mb-5 animate-fade-in">
              <p className="text-sm text-neg">{error}</p>
            </div>
          )}

          {/* Loading skeleton */}
          {loading && !data && (
            <div className="space-y-3 animate-fade-in">
              {[1, 2, 3, 4, 5].map((i) => <SkeletonCard key={i} />)}
            </div>
          )}

          {/* Empty state before results */}
          {!data && !loading && !error && (
            <div className="flex flex-col items-center justify-center py-20 text-center animate-fade-in">
              <div className="h-16 w-16 rounded-2xl bg-surface/80 flex items-center justify-center mb-4">
                <Search size={28} className="text-muted/40" />
              </div>
              <h3 className="text-sm font-semibold text-muted mb-1">No results yet</h3>
              <p className="text-xs text-muted/60 max-w-xs">
                Paste your roster on the left and hit &ldquo;Rank waiver adds&rdquo; to see personalized recommendations.
              </p>
            </div>
          )}

          {/* Results */}
          {data && !loading && (
            <div className="animate-fade-in">
              {/* Results header */}
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h2 className="text-lg font-bold flex items-center gap-2">
                    <Plus size={16} className="text-accent" />
                    Waiver Action List
                  </h2>
                  <p className="text-xs text-muted mt-0.5 flex items-center gap-1.5">
                    <Calendar size={10} />
                    {formatDate(data.week.start)} – {formatDate(data.week.end)}
                    {typeof data.resolved_count === "number" && (
                      <> · {data.resolved_count} matched</>
                    )}
                    {data.scoring_mode === "categories" && (
                      <> · <span className="text-accent font-medium">{getCatLabel(sport)} z-score</span></>
                    )}
                  </p>
                </div>
                <span className="text-xs text-muted bg-surface/80 px-2.5 py-1 rounded-md font-medium tabular-nums">
                  {data.recommendations.length} add{data.recommendations.length !== 1 ? "s" : ""}
                </span>
              </div>

              {/* Unresolved names */}
              {data.unresolved && data.unresolved.length > 0 && (
                <div className="rounded-xl border border-accent/30 bg-accent/5 px-4 py-3 mb-4">
                  <p className="text-sm text-accent">
                    Couldn&apos;t match: <span className="font-medium">{data.unresolved.join(", ")}</span>. Fix spelling or remove the line.
                  </p>
                </div>
              )}

              {/* Empty results */}
              {data.recommendations.length === 0 ? (
                <div className="text-center py-20 rounded-xl border border-line/50 bg-card/50">
                  <span className="text-4xl block mb-3">🎉</span>
                  <p className="text-sm font-semibold mb-1">Your roster is stacked</p>
                  <p className="text-xs text-muted">No free agents outrank your current players this week.</p>
                </div>
              ) : (
                <div className="space-y-2.5">
                  {data.recommendations.map((r, i) => (
                    <RecCard key={r.add_player_id} rec={r} rank={i + 1} mode={mode} sport={sport} />
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </section>
    </main>
  );
}
