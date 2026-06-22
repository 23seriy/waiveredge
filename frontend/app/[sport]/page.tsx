"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import {
  ArrowRight,
  ArrowUpDown,
  Calendar,
  ChevronDown,
  Flame,
  Loader2,
  RotateCcw,
  Search,
  Shield,
  TrendingUp,
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
};

type Payload = {
  week: { start: string; end: string };
  scoring_mode?: ScoringMode;
  recommendations: Recommendation[];
  unresolved?: string[];
  resolved_count?: number;
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "https://localhost:8000";
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


function ModeToggle({ mode, onChange, sport }: { mode: ScoringMode; onChange: (m: ScoringMode) => void; sport: Sport }) {
  if (POINTS_ONLY_SPORTS.has(sport)) return null;
  return (
    <div className="flex rounded-lg bg-surface p-1 gap-1">
      <button
        type="button"
        onClick={() => onChange("points")}
        className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
          mode === "points"
            ? "bg-accent text-bg"
            : "text-muted hover:text-gray-200"
        }`}
      >
        <Zap size={14} /> Points
      </button>
      <button
        type="button"
        onClick={() => onChange("categories")}
        className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
          mode === "categories"
            ? "bg-accent text-bg"
            : "text-muted hover:text-gray-200"
        }`}
      >
        <ArrowUpDown size={14} /> {getCatLabel(sport)}
      </button>
    </div>
  );
}


function ZBadge({ cat, z }: { cat: string; z: number }) {
  const label = CAT_LABELS[cat] ?? cat;
  const color = z > 0.3 ? "text-pos" : z < -0.3 ? "text-neg" : "text-muted";
  return (
    <span className={`inline-flex items-center rounded px-1.5 py-0.5 text-xs font-mono ${color} bg-surface`}>
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
        className="flex items-center gap-1 text-xs text-accent/70 hover:text-accent transition-colors disabled:opacity-50"
      >
        {loading ? <Loader2 size={10} className="animate-spin" /> : <Zap size={10} />}
        {insight && visible ? "Hide AI" : "AI Insight"}
      </button>
      {visible && insight && (
        <p className="mt-1.5 text-sm text-gray-300 leading-relaxed bg-accent/5 border border-accent/20 rounded-lg px-3 py-2">
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

  return (
    <div className="group rounded-xl border border-line bg-card p-4 transition-colors hover:border-accent/40">
      <div className="flex gap-4 items-start">
        <div className="flex flex-col items-center shrink-0 w-10">
          <span className="text-xs text-muted font-medium">#{rank}</span>
          <span className={`text-lg font-bold tabular-nums ${rec.marginal >= 0 ? "text-pos" : "text-neg"}`}>
            {marginalStr}
          </span>
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-baseline gap-2 flex-wrap">
            <h3 className="text-base font-semibold text-gray-100">
              {rec.add_name}
            </h3>
            <span className="text-sm text-muted">{rec.add_position}</span>
            {rec.helps && rec.helps.length > 0 && (
              <span className="text-xs bg-pos/15 text-pos rounded-full px-2 py-0.5 font-medium">
                helps weak cats
              </span>
            )}
          </div>

          <div className="flex items-center gap-3 mt-1.5 text-sm text-muted">
            <span className="flex items-center gap-1">
              <Calendar size={12} /> {rec.n_games} game{rec.n_games !== 1 ? "s" : ""}
            </span>
            {rec.soft_matchups > 0 && (
              <span className="flex items-center gap-1">
                <TrendingUp size={12} /> {rec.soft_matchups} soft
              </span>
            )}
            {rec.drop_name && (
              <span>
                drop <span className="text-accent font-medium">{rec.drop_name}</span>
              </span>
            )}
          </div>

          {isCategory && rec.per_cat_z && (
            <div className="flex flex-wrap gap-1 mt-2">
              {getCatKeys(sport).filter((c) => c in rec.per_cat_z!).map((cat) => (
                <ZBadge key={cat} cat={cat} z={rec.per_cat_z![cat]} />
              ))}
            </div>
          )}

          <div className="flex items-center gap-3 mt-2">
            <button
              type="button"
              onClick={() => setExpanded(!expanded)}
              className="flex items-center gap-1 text-xs text-muted hover:text-gray-300 transition-colors"
            >
              <ChevronDown size={12} className={`transition-transform ${expanded ? "rotate-180" : ""}`} />
              {expanded ? "Less" : "Details"}
            </button>
            <AIInsightButton rec={rec} />
          </div>
          {expanded && (
            <p className="mt-1.5 text-sm text-muted leading-relaxed">{rec.rationale}</p>
          )}
        </div>
      </div>
    </div>
  );
}


function SkeletonCard() {
  return (
    <div className="rounded-xl border border-line bg-card p-4 animate-pulse">
      <div className="flex gap-4">
        <div className="w-10 flex flex-col items-center gap-1">
          <div className="h-3 w-6 rounded bg-line" />
          <div className="h-5 w-10 rounded bg-line" />
        </div>
        <div className="flex-1 space-y-2">
          <div className="h-4 w-40 rounded bg-line" />
          <div className="h-3 w-60 rounded bg-line" />
          <div className="h-3 w-32 rounded bg-line" />
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
    <div className="rounded-xl border border-accent/30 bg-accent/5 p-6 text-center mb-6">
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

  return (
    <main className="max-w-4xl mx-auto px-4">
      {/* Hero section */}
      <section className="py-12 md:py-16 text-center">
        <h1 className="text-3xl md:text-4xl font-bold tracking-tight mb-4">
          {SPORT_INFO[sport]?.name ?? sport.toUpperCase()} Waiver Wire<br />
          <span className="text-accent">ranked for your roster</span>
        </h1>
        <p className="text-muted text-base max-w-xl mx-auto mb-8 leading-relaxed">
          Paste your roster below or{" "}
          <Link href={`/${sport}/connect`} className="text-accent hover:underline">connect your league</Link>{" "}
          for personalized waiver adds — powered by schedule density, matchups, and recent form.
        </p>

        <div className="flex flex-col sm:flex-row items-center justify-center gap-3 mb-6">
          <Link
            href={`/${sport}/connect`}
            className="flex items-center gap-2 rounded-lg bg-accent px-6 py-3 text-sm font-semibold text-bg hover:opacity-90 transition-opacity"
          >
            Connect your league <ArrowRight size={16} />
          </Link>
          <Link
            href={`/${sport}/streamers`}
            className="flex items-center gap-2 rounded-lg border border-line px-6 py-3 text-sm font-medium text-muted hover:text-gray-200 hover:border-accent/40 transition-colors"
          >
            <Flame size={14} /> Free weekly streamers
          </Link>
        </div>

        <p className="text-xs text-muted">
          Works with {ESPN_ONLY_SPORTS.has(sport) ? "ESPN" : "Yahoo & ESPN"} &middot; {POINTS_ONLY_SPORTS.has(sport) ? "Points" : `${getCatLabel(sport)} & Points`} leagues
        </p>
      </section>

      {/* Mode control */}
      <div className="flex flex-wrap items-center justify-center gap-3 mb-8">
        <ModeToggle mode={mode} onChange={handleModeChange} sport={sport} />
      </div>

      {/* Fixture status check */}
      <FixtureStatus sport={sport} />

      {/* Manual roster section */}
      <section className="max-w-3xl mx-auto">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-base font-semibold">Quick Roster Check</h2>
          <p className="text-xs text-muted">or <Link href={`/${sport}/connect`} className="text-accent hover:underline">connect your league</Link> for full features</p>
        </div>

        <form onSubmit={submit} className="mb-8">
          <div className="rounded-xl border border-line bg-card overflow-hidden">
            <div className="flex items-center justify-between px-4 py-2.5 border-b border-line bg-surface/50">
              <span className="text-xs text-muted font-medium uppercase tracking-wider">
                Your Roster
              </span>
              <button
                type="button"
                onClick={loadSample}
                className="flex items-center gap-1 text-xs text-muted hover:text-accent transition-colors"
              >
                <RotateCcw size={11} /> Load sample
              </button>
            </div>
            <textarea
              rows={8}
              value={rosterText}
              onChange={(e) => setRosterText(e.target.value)}
              placeholder="One player name per line&#10;&#10;Nikola Jokic&#10;Luka Doncic&#10;..."
              className="w-full bg-transparent px-4 py-3 text-sm font-mono text-gray-200 placeholder:text-muted/50 resize-y focus:outline-none"
            />
          </div>

          <button
            type="submit"
            disabled={loading || !rosterText.trim()}
            className="mt-3 w-full flex items-center justify-center gap-2 rounded-lg bg-accent py-2.5 text-sm font-semibold text-bg transition-opacity hover:opacity-90 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {loading ? (
              <>
                <Loader2 size={16} className="animate-spin" /> Analyzing…
              </>
            ) : (
              <>
                <Search size={16} /> Rank waiver adds
              </>
            )}
          </button>
        </form>

        {/* Error */}
        {error && (
          <div className="rounded-lg border border-neg/30 bg-neg/10 px-4 py-3 mb-6">
            <p className="text-sm text-neg">{error}</p>
          </div>
        )}

        {/* Loading skeleton */}
        {loading && !data && (
          <div className="space-y-3">
            {[1, 2, 3, 4, 5].map((i) => <SkeletonCard key={i} />)}
          </div>
        )}

        {/* Results */}
        {data && !loading && (
          <>
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-base font-semibold">
                  Waiver Action List
                </h2>
                <p className="text-xs text-muted mt-0.5">
                  Week of {data.week.start} to {data.week.end}
                  {typeof data.resolved_count === "number" && (
                    <> &middot; {data.resolved_count} roster players matched</>
                  )}
                  {data.scoring_mode === "categories" && (
                    <> &middot; <span className="text-accent">{getCatLabel(sport)} z-score mode</span></>
                  )}
                </p>
              </div>
              <span className="text-xs text-muted">
                {data.recommendations.length} add{data.recommendations.length !== 1 ? "s" : ""}
              </span>
            </div>

            {data.unresolved && data.unresolved.length > 0 && (
              <div className="rounded-lg border border-accent/30 bg-accent/10 px-4 py-3 mb-4">
                <p className="text-sm text-accent">
                  Couldn&apos;t match: {data.unresolved.join(", ")}. Fix spelling or remove the line.
                </p>
              </div>
            )}

            {data.recommendations.length === 0 ? (
              <p className="text-sm text-muted text-center py-12">
                No free agents outrank your roster this week.
              </p>
            ) : (
              <div className="space-y-3">
                {data.recommendations.map((r, i) => (
                  <RecCard key={r.add_player_id} rec={r} rank={i + 1} mode={mode} sport={sport} />
                ))}
              </div>
            )}
          </>
        )}
      </section>

      {/* Value props */}
      <section className="max-w-3xl mx-auto mt-8 mb-4">
        <div className="rounded-lg bg-surface/50 border border-line p-4">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-left">
            <div>
              <p className="text-sm font-medium flex items-center gap-1.5 mb-1">
                <Calendar size={14} className="text-accent" /> Schedule density
              </p>
              <p className="text-xs text-muted">More games = more streaming value. We rank who plays most.</p>
            </div>
            <div>
              <p className="text-sm font-medium flex items-center gap-1.5 mb-1">
                <TrendingUp size={14} className="text-pos" /> Matchup quality
              </p>
              <p className="text-xs text-muted">Soft opponents boost projections. We factor opponent strength.</p>
            </div>
            <div>
              <p className="text-sm font-medium flex items-center gap-1.5 mb-1">
                <Shield size={14} className="text-accent" /> Read-only access
              </p>
              <p className="text-xs text-muted">We never modify your team. Connect with confidence.</p>
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}
