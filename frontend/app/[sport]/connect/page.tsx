"use client";

import { useParams, useRouter, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useState } from "react";
import { ArrowRight, ChevronDown, ExternalLink, Link2, Loader2, Plus, RotateCcw, Search, Trash2, Trophy, Users } from "lucide-react";
import Link from "next/link";
import { useLeagues } from "../../components/league-context";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";
const AUTH_BASE = process.env.NEXT_PUBLIC_AUTH_BASE || API_BASE;
const STORAGE_KEY = "waiveredge.roster.v1";
const LEAGUES_KEY = "waiveredge.leagues.v1";

type SavedLeague = {
  id: number;
  platform: string;
  league_id: string;
  team_key: string | null;
  sport: string;
  roster_count: number;
  created_at: string | null;
};

function getSavedLeagueIds(sport: string): number[] {
  try {
    const raw = localStorage.getItem(`${LEAGUES_KEY}.${sport}`);
    return raw ? JSON.parse(raw) : [];
  } catch { return []; }
}

function saveLeagueId(sport: string, id: number) {
  const ids = getSavedLeagueIds(sport);
  if (!ids.includes(id)) {
    localStorage.setItem(`${LEAGUES_KEY}.${sport}`, JSON.stringify([...ids, id]));
  }
}

function removeLeagueId(sport: string, id: number) {
  const ids = getSavedLeagueIds(sport).filter((x) => x !== id);
  localStorage.setItem(`${LEAGUES_KEY}.${sport}`, JSON.stringify(ids));
}

const SPORT_META: Record<string, { name: string; icon: string; full: string; sample: string }> = {
  nba: { name: "NBA", icon: "\u{1F3C0}", full: "NBA Basketball", sample: "Nikola Jokic\nLuka Doncic\nAnthony Edwards\nJaren Jackson Jr.\nTyrese Haliburton\nBam Adebayo\nJalen Brunson\nTrae Young\nDomantas Sabonis\nScottie Barnes" },
  mlb: { name: "MLB", icon: "\u26BE", full: "MLB Baseball", sample: "Aaron Judge\nShohei Ohtani\nMookie Betts\nFreddie Freeman\nCorbin Carroll\nJulio Rodriguez\nBobby Witt Jr.\nCorey Seager\nRonald Acuna Jr.\nMatt Olson" },
  wnba: { name: "WNBA", icon: "\u{1F3C0}", full: "WNBA Basketball", sample: "A'ja Wilson\nBreanna Stewart\nNapheesa Collier\nCaitlin Clark\nAlyssa Thomas\nKelsey Plum\nJewell Loyd\nSabrina Ionescu\nDearica Hamby\nKahleah Copper" },
};

// Sports where Yahoo Fantasy is not available
const ESPN_ONLY_SPORTS = new Set(["wnba"]);

type ESPNTeam = { id: number; name: string; abbrev?: string; top_players?: string[] };

function ESPNConnectForm({ sport, onConnected }: { sport: string; onConnected: () => void }) {
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
    } catch (err) { setResult("Could not reach the API. The server may be waking up — please try again in 30 seconds."); }
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
      saveLeagueId(sport, data.connection_id);
      onConnected();
      setLeagueId("");
      setTeams([]);
      setSelectedTeam(null);
      setResult(null);
    } catch (err) { setResult(`Could not reach the API. The server may be waking up — please try again in 30 seconds.`); }
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
          className="w-full flex items-center justify-center gap-2 rounded-lg bg-accent px-4 py-2.5 text-sm font-semibold text-bg hover:brightness-110 transition-colors disabled:opacity-40"
        >
          {loading ? <><Loader2 size={14} className="animate-spin" /> Connecting…</> : "Connect ESPN League"}
        </button>
      )}
    </div>
  );
}


function ManualRosterForm({ sport, sample }: { sport: string; sample: string }) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [rosterText, setRosterText] = useState("");

  function loadSample() {
    setRosterText(sample);
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = rosterText.trim();
    if (!trimmed) return;
    localStorage.setItem(`${STORAGE_KEY}.${sport}`, trimmed);
    router.push(`/${sport}?source=manual`);
  }

  const rosterCount = rosterText.split("\n").filter((l) => l.trim()).length;

  return (
    <div className="rounded-xl border border-line/60 bg-card/60 overflow-hidden mb-8">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-6 py-4 text-left hover:bg-surface/30 transition-colors"
      >
        <div className="flex items-center gap-3">
          <Users size={18} className="text-muted" />
          <div>
            <p className="text-sm font-semibold">Paste your roster manually</p>
            <p className="text-xs text-muted">Don&apos;t use Yahoo or ESPN? Enter player names directly.</p>
          </div>
        </div>
        <ChevronDown size={16} className={`text-muted transition-transform ${open ? "rotate-180" : ""}`} />
      </button>

      {open && (
        <form onSubmit={handleSubmit} className="border-t border-line/40 px-6 py-5 animate-fade-in">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-muted tabular-nums">{rosterCount} player{rosterCount !== 1 ? "s" : ""}</span>
            <button
              type="button"
              onClick={loadSample}
              className="flex items-center gap-1 text-[11px] text-muted hover:text-accent transition-colors"
            >
              <RotateCcw size={10} /> Load sample
            </button>
          </div>
          <textarea
            rows={6}
            value={rosterText}
            onChange={(e) => setRosterText(e.target.value)}
            placeholder={"One player name per line\n\n" + sample.split("\n").slice(0, 3).join("\n") + "\n..."}
            className="w-full bg-surface/50 border border-line/50 rounded-lg px-4 py-3 text-[13px] font-mono text-gray-200 placeholder:text-muted/30 resize-y focus:outline-none focus:border-accent/40 min-h-[140px]"
          />
          <button
            type="submit"
            disabled={!rosterText.trim()}
            className="mt-3 w-full flex items-center justify-center gap-2 rounded-lg bg-accent py-2.5 text-sm font-semibold text-bg transition-all hover:brightness-110 hover:shadow-lg hover:shadow-accent/25 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <Search size={15} /> Rank waiver adds
          </button>
        </form>
      )}
    </div>
  );
}


function ConnectedLeagues({ sport, leagues, onRemove }: { sport: string; leagues: SavedLeague[]; onRemove: (id: number) => void }) {
  if (leagues.length === 0) return null;
  return (
    <div className="rounded-xl border border-accent/30 bg-accent/5 p-5 mb-8 animate-fade-in">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Trophy size={16} className="text-accent" />
          <h2 className="text-sm font-semibold">Your Connected Leagues</h2>
        </div>
        <span className="text-xs text-muted">{leagues.length} league{leagues.length !== 1 ? "s" : ""}</span>
      </div>
      <div className="space-y-2">
        {leagues.map((l) => (
          <div key={l.id} className="flex items-center justify-between rounded-lg border border-line bg-card px-4 py-3">
            <Link href={`/${sport}/league/${l.id}`} className="flex items-center gap-3 min-w-0 flex-1 hover:opacity-80 transition-opacity">
              <span className="text-xs font-bold uppercase text-muted bg-surface rounded px-1.5 py-0.5">{l.platform}</span>
              <div className="min-w-0">
                <span className="text-sm font-medium block truncate">{l.league_id}</span>
                <span className="text-xs text-muted">{l.roster_count} player{l.roster_count !== 1 ? "s" : ""} synced</span>
              </div>
            </Link>
            <div className="flex items-center gap-2 shrink-0 ml-3">
              <Link
                href={`/${sport}/league/${l.id}`}
                className="flex items-center gap-1 rounded-md bg-accent/15 border border-accent/30 px-2.5 py-1 text-xs font-medium text-accent hover:bg-accent/25 transition-colors"
              >
                <ArrowRight size={12} /> View
              </Link>
              <button
                type="button"
                onClick={(e) => { e.preventDefault(); onRemove(l.id); }}
                className="p-1 rounded text-muted hover:text-neg transition-colors"
                title="Remove from this list"
              >
                <Trash2 size={13} />
              </button>
            </div>
          </div>
        ))}
      </div>
      <p className="text-[11px] text-muted mt-3 text-center">Connect another league below</p>
    </div>
  );
}


function ConnectContent() {
  const params = useParams();
  const searchParams = useSearchParams();
  const sport = params.sport as string;
  const meta = SPORT_META[sport] || { name: sport.toUpperCase(), icon: "🏅", full: sport.toUpperCase(), sample: "" };
  const error = searchParams.get("error");
  const [savedLeagues, setSavedLeagues] = useState<SavedLeague[]>([]);
  const { refreshLeagues: refreshCtxLeagues } = useLeagues();

  const refreshLeagues = useCallback(() => {
    const ids = getSavedLeagueIds(sport);
    if (ids.length === 0) { setSavedLeagues([]); return; }
    fetch(`${API_BASE}/api/leagues?ids=${ids.join(",")}`)
      .then((r) => r.ok ? r.json() : [])
      .then((data) => { setSavedLeagues(data); refreshCtxLeagues(); })
      .catch(() => setSavedLeagues([]));
  }, [sport, refreshCtxLeagues]);

  useEffect(() => { refreshLeagues(); }, [refreshLeagues]);

  function handleRemove(id: number) {
    removeLeagueId(sport, id);
    setSavedLeagues((prev) => prev.filter((l) => l.id !== id));
    refreshCtxLeagues();
  }

  return (
    <main className="mx-auto px-6 md:px-12 lg:px-20 py-8">
      <div className="text-center mb-10 animate-fade-in">
        <div className="inline-flex items-center justify-center h-12 w-12 rounded-xl bg-accent/10 mb-4">
          <span className="text-2xl">{meta.icon}</span>
        </div>
        <h1 className="text-2xl font-extrabold tracking-tight mb-3">
          Connect Your {meta.name} League{savedLeagues.length > 0 ? "s" : ""}
        </h1>
        <p className="text-sm text-muted leading-relaxed max-w-md mx-auto">
          Link your fantasy league{savedLeagues.length > 0 ? "s" : ""} and get personalized waiver recommendations
          for <em className="text-gray-200 not-italic font-medium">your</em> actual roster.
        </p>
      </div>

      <ConnectedLeagues sport={sport} leagues={savedLeagues} onRemove={handleRemove} />

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
          href={`${AUTH_BASE}/api/auth/yahoo?sport=${sport}`}
          className="w-full inline-flex items-center justify-center gap-2 rounded-lg bg-purple-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-purple-500 transition-colors"
        >
          {savedLeagues.some((l) => l.platform === "yahoo") ? "Connect another Yahoo league" : "Connect with Yahoo"} <ExternalLink size={14} />
        </a>
      </div>}

      {/* ESPN */}
      <div className="rounded-xl border border-line bg-card p-6 mb-8">
        <div className="flex items-center gap-3 mb-4">
          <span className="text-2xl font-bold text-red-500">ESPN</span>
          <div>
            <h3 className="text-base font-semibold">ESPN Fantasy</h3>
            <p className="text-xs text-muted">{savedLeagues.some((l) => l.platform === "espn") ? "Add another ESPN league" : "Paste your league ID to connect"}</p>
          </div>
        </div>
        <ESPNConnectForm sport={sport} onConnected={refreshLeagues} />
      </div>

      <div className="rounded-xl bg-surface/30 border border-line/50 p-5 mb-8">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-left">
          <div className="flex gap-3">
            <span className="text-xs font-bold text-accent bg-accent/10 h-5 w-5 rounded flex items-center justify-center shrink-0 mt-0.5">1</span>
            <div>
              <p className="text-sm font-medium mb-0.5">Auto-import roster</p>
              <p className="text-xs text-muted">Your actual players, positions, and slots.</p>
            </div>
          </div>
          <div className="flex gap-3">
            <span className="text-xs font-bold text-accent bg-accent/10 h-5 w-5 rounded flex items-center justify-center shrink-0 mt-0.5">2</span>
            <div>
              <p className="text-sm font-medium mb-0.5">League scoring</p>
              <p className="text-xs text-muted">Points or categories — detected automatically.</p>
            </div>
          </div>
          <div className="flex gap-3">
            <span className="text-xs font-bold text-accent bg-accent/10 h-5 w-5 rounded flex items-center justify-center shrink-0 mt-0.5">3</span>
            <div>
              <p className="text-sm font-medium mb-0.5">Read-only access</p>
              <p className="text-xs text-muted">We never modify your team.</p>
            </div>
          </div>
        </div>
      </div>

      <ManualRosterForm sport={sport} sample={meta.sample} />
    </main>
  );
}

export default function ConnectPage() {
  return <Suspense><ConnectContent /></Suspense>;
}
