"use client";

// Manual roster input → POST /api/recommendations/manual. This is the bridge to
// "for YOUR roster" recommendations before Yahoo OAuth lands; the request/response
// shape is intentionally the same the OAuth-backed endpoint will use.

import { useEffect, useState } from "react";

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
};

type Payload = {
  week: { start: string; end: string };
  recommendations: Recommendation[];
  unresolved?: string[];
  resolved_count?: number;
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";
const STORAGE_KEY = "waiveredge.roster.v1";

// Seeded with a real NBA roster so the page works end-to-end on first load.
// (Accents are folded server-side, so plain ASCII like "Nikola Jokic" resolves.)
const SAMPLE_ROSTER = [
  "Nikola Jokic",
  "Luka Doncic",
  "Anthony Edwards",
  "Jaren Jackson Jr.",
  "Tyrese Haliburton",
  "Bam Adebayo",
  "Jalen Brunson",
  "Trae Young",
  "Domantas Sabonis",
  "Scottie Barnes",
].join("\n");

export default function Home() {
  const [rosterText, setRosterText] = useState("");
  const [data, setData] = useState<Payload | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const saved = typeof window !== "undefined" ? localStorage.getItem(STORAGE_KEY) : null;
    setRosterText(saved && saved.trim() ? saved : SAMPLE_ROSTER);
  }, []);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    const roster = rosterText.split("\n").map((s) => s.trim()).filter(Boolean);
    try {
      localStorage.setItem(STORAGE_KEY, rosterText);
      const res = await fetch(`${API_BASE}/api/recommendations/manual`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ roster }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        const detail = body?.detail;
        const msg = typeof detail === "string"
          ? detail
          : detail?.message || `Request failed (${res.status})`;
        setError(msg);
        setData(null);
      } else {
        setData((await res.json()) as Payload);
      }
    } catch {
      setError(`Could not reach the API at ${API_BASE}. Start the backend: uvicorn app.main:app --reload`);
      setData(null);
    } finally {
      setLoading(false);
    }
  }

  function loadSample() {
    setRosterText(SAMPLE_ROSTER);
  }

  return (
    <main>
      <h1>WaiverEdge</h1>
      <p className="sub">
        Paste your fantasy roster (one player per line) — the engine ranks the best
        waiver adds for <em>your</em> team this week.
      </p>

      <form onSubmit={submit} className="form">
        <textarea
          className="roster"
          rows={10}
          value={rosterText}
          onChange={(e) => setRosterText(e.target.value)}
          placeholder="One player name per line"
        />
        <div className="actions">
          <button type="submit" disabled={loading || !rosterText.trim()}>
            {loading ? "Ranking…" : "Rank waiver adds"}
          </button>
          <button type="button" className="secondary" onClick={loadSample}>
            Load sample roster
          </button>
        </div>
      </form>

      {error && <p className="err">{error}</p>}

      {data && (
        <>
          <p className="sub">
            Waiver action list — week of {data.week.start} to {data.week.end}
            {typeof data.resolved_count === "number" && ` · ${data.resolved_count} roster players matched`}
          </p>

          {data.unresolved && data.unresolved.length > 0 && (
            <p className="warn">
              Couldn't match: {data.unresolved.join(", ")}. They're ignored — fix
              spelling or remove the line.
            </p>
          )}

          {data.recommendations.length === 0 && (
            <p className="sub">No free agents outrank your roster this week.</p>
          )}

          {data.recommendations.map((r, i) => (
            <div className="rec" key={r.add_player_id}>
              <div className="marginal">{r.marginal >= 0 ? "+" : ""}{r.marginal.toFixed(1)}</div>
              <div>
                <h3>
                  {i + 1}. {r.add_name} <span style={{ color: "var(--muted)" }}>({r.add_position})</span>
                </h3>
                <p>{r.rationale}</p>
                {r.drop_name && (
                  <p>
                    Drop <span className="drop">{r.drop_name}</span> · {r.n_games} games ·{" "}
                    {r.soft_matchups} soft matchup{r.soft_matchups === 1 ? "" : "s"}
                  </p>
                )}
              </div>
            </div>
          ))}
        </>
      )}
    </main>
  );
}
