"use client";

import { useParams, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { ArrowLeft, ArrowRight, ExternalLink, Loader2 } from "lucide-react";
import Link from "next/link";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "https://localhost:8000";

const SPORT_META: Record<string, { name: string; icon: string; full: string }> = {
  nba: { name: "NBA", icon: "\u{1F3C0}", full: "NBA Basketball" },
  mlb: { name: "MLB", icon: "\u26BE", full: "MLB Baseball" },
  wnba: { name: "WNBA", icon: "\u{1F3C0}", full: "WNBA Basketball" },
};

// Sports where Yahoo Fantasy is not available
const ESPN_ONLY_SPORTS = new Set(["wnba"]);

type ESPNTeam = { id: number; name: string; abbrev?: string; top_players?: string[] };

function ESPNConnectForm({ sport }: { sport: string }) {
  const [leagueId, setLeagueId] = useState("");
  const [espnS2, setEspnS2] = useState("");
  const [swid, setSwid] = useState("");
  const [teams, setTeams] = useState<ESPNTeam[]>([]);
  const [selectedTeam, setSelectedTeam] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadingTeams, setLoadingTeams] = useState(false);
  const [result, setResult] = useState<string | null>(null);

  async function fetchTeams() {
    if (!leagueId.trim()) return;
    setLoadingTeams(true);
    setResult(null);
    setTeams([]);
    setSelectedTeam(null);
    try {
      const res = await fetch(`${API_BASE}/api/espn/teams?league_id=${leagueId}&season=2026&sport=${sport}`);
      if (!res.ok) { const b = await res.json().catch(() => null); setResult(b?.detail || "Failed to load teams"); return; }
      const data = (await res.json()) as ESPNTeam[];
      setTeams(data);
      if (data.length === 0) setResult("No teams found in this league.");
    } catch { setResult("Could not reach the API."); }
    finally { setLoadingTeams(false); }
  }

  async function handleConnect() {
    if (!leagueId.trim() || selectedTeam === null) return;
    setLoading(true);
    setResult(null);
    try {
      const res = await fetch(`${API_BASE}/api/espn/connect`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          league_id: parseInt(leagueId),
          season: 2026,
          sport,
          team_id: selectedTeam,
          espn_s2: espnS2,
          swid,
        }),
      });
      if (!res.ok) { const b = await res.json().catch(() => null); setResult(b?.detail || `Failed (${res.status})`); return; }
      const data = await res.json();
      window.location.href = `/${sport}/league/${data.connection_id}`;
    } catch { setResult("Could not reach the API."); }
    finally { setLoading(false); }
  }

  return (
    <div className="space-y-3">
      <div>
        <label className="text-xs text-muted block mb-1">League ID</label>
        <input
          type="text"
          value={leagueId}
          onChange={(e) => { setLeagueId(e.target.value); setTeams([]); setSelectedTeam(null); }}
          placeholder="e.g. 2052775362"
          className="w-full bg-surface border border-line rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-accent"
        />
      </div>

      {teams.length === 0 && (
        <button
          onClick={fetchTeams}
          disabled={loadingTeams || !leagueId.trim()}
          className="w-full flex items-center justify-center gap-2 rounded-lg bg-surface border border-line px-4 py-2 text-sm font-medium text-gray-200 hover:border-accent/40 transition-colors disabled:opacity-40"
        >
          {loadingTeams ? <><Loader2 size={14} className="animate-spin" /> Finding teams…</> : "Find teams in this league"}
        </button>
      )}

      {teams.length > 0 && (
        <div>
          <label className="text-xs text-muted block mb-1">Select your team</label>
          <div className="grid grid-cols-2 gap-2">
            {teams.map((t) => (
              <button
                key={t.id}
                onClick={() => setSelectedTeam(t.id)}
                className={`text-left rounded-lg border px-3 py-2.5 transition-colors ${
                  selectedTeam === t.id
                    ? "border-accent bg-accent/10 text-gray-100"
                    : "border-line bg-surface text-muted hover:border-accent/40"
                }`}
              >
                <span className="text-sm font-medium block">{t.name}</span>
                {t.top_players && t.top_players.length > 0 && (
                  <span className="text-[10px] text-muted block mt-0.5">
                    {t.top_players.join(", ")}
                  </span>
                )}
              </button>
            ))}
          </div>
        </div>
      )}

      <details className="text-xs text-muted">
        <summary className="cursor-pointer hover:text-accent">Private league? Add cookies (optional)</summary>
        <div className="mt-2 space-y-2">
          <input type="text" value={espnS2} onChange={(e) => setEspnS2(e.target.value)} placeholder="espn_s2 cookie value"
            className="w-full bg-surface border border-line rounded-lg px-3 py-1.5 text-sm text-gray-200 focus:outline-none focus:border-accent" />
          <input type="text" value={swid} onChange={(e) => setSwid(e.target.value)} placeholder="SWID cookie value"
            className="w-full bg-surface border border-line rounded-lg px-3 py-1.5 text-sm text-gray-200 focus:outline-none focus:border-accent" />
          <p className="text-[10px] text-muted">Find these in your browser DevTools → Application → Cookies → espn.com</p>
        </div>
      </details>

      {result && <p className="text-sm text-neg">{result}</p>}

      {selectedTeam !== null && (
        <button
          onClick={handleConnect}
          disabled={loading}
          className="w-full flex items-center justify-center gap-2 rounded-lg bg-red-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-red-500 transition-colors disabled:opacity-40"
        >
          {loading ? <><Loader2 size={14} className="animate-spin" /> Connecting…</> : "Connect ESPN League"}
        </button>
      )}
    </div>
  );
}


function ConnectContent() {
  const params = useParams();
  const searchParams = useSearchParams();
  const sport = params.sport as string;
  const meta = SPORT_META[sport] || { name: sport.toUpperCase(), icon: "🏅", full: sport.toUpperCase() };
  const error = searchParams.get("error");

  return (
    <main className="max-w-xl mx-auto px-4 py-8">
      <Link
        href={`/${sport}`}
        className="inline-flex items-center gap-1 text-xs text-muted hover:text-accent transition-colors mb-6"
      >
        <ArrowLeft size={12} /> Back to {meta.name} Dashboard
      </Link>

      <div className="text-center mb-10">
        <h1 className="text-2xl font-bold tracking-tight mb-3">
          Connect Your {meta.name} League
        </h1>
        <p className="text-sm text-muted leading-relaxed max-w-md mx-auto">
          Link your fantasy league and get personalized waiver recommendations
          for <em className="text-gray-200 not-italic font-medium">your</em> actual roster.
        </p>
      </div>

      {error && (
        <div className="rounded-lg border border-neg/30 bg-neg/10 px-4 py-3 mb-6 text-center">
          <p className="text-sm text-neg">
            {error === "no_leagues"
              ? `No active ${meta.name} leagues found on your Yahoo account.`
              : `Error: ${error}`}
          </p>
        </div>
      )}

      {/* Yahoo — hidden for ESPN-only sports */}
      {!ESPN_ONLY_SPORTS.has(sport) && <div className="rounded-xl border border-line bg-card p-6 mb-4">
        <div className="flex items-center gap-3 mb-4">
          <span className="text-2xl">{meta.icon}</span>
          <div>
            <h3 className="text-base font-semibold">Yahoo Fantasy</h3>
            <p className="text-xs text-muted">One-click OAuth connection</p>
          </div>
        </div>
        <a
          href={`${API_BASE}/api/auth/yahoo?sport=${sport}`}
          className="w-full inline-flex items-center justify-center gap-2 rounded-lg bg-purple-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-purple-500 transition-colors"
        >
          Connect with Yahoo <ExternalLink size={14} />
        </a>
      </div>}

      {/* ESPN */}
      <div className="rounded-xl border border-line bg-card p-6 mb-8">
        <div className="flex items-center gap-3 mb-4">
          <span className="text-2xl font-bold text-red-500">ESPN</span>
          <div>
            <h3 className="text-base font-semibold">ESPN Fantasy</h3>
            <p className="text-xs text-muted">Paste your league ID to connect</p>
          </div>
        </div>
        <ESPNConnectForm sport={sport} />
      </div>

      <div className="rounded-lg bg-surface/50 border border-line p-4 mb-8">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-left">
          <div>
            <p className="text-sm font-medium mb-1">Auto-import roster</p>
            <p className="text-xs text-muted">Your actual players, positions, and slots.</p>
          </div>
          <div>
            <p className="text-sm font-medium mb-1">League scoring</p>
            <p className="text-xs text-muted">Points or categories — detected automatically.</p>
          </div>
          <div>
            <p className="text-sm font-medium mb-1">Read-only access</p>
            <p className="text-xs text-muted">We never modify your team.</p>
          </div>
        </div>
      </div>

      <div className="text-center">
        <p className="text-xs text-muted mb-2">Don&apos;t use Yahoo or ESPN?</p>
        <Link href={`/${sport}`} className="inline-flex items-center gap-1 text-sm text-accent hover:underline">
          Paste your roster manually <ArrowRight size={14} />
        </Link>
      </div>
    </main>
  );
}

export default function ConnectPage() {
  return <Suspense><ConnectContent /></Suspense>;
}
