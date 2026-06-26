"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import type { ReactNode } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";
const LEAGUES_KEY = "waiveredge.leagues.v1";
const ACTIVE_KEY = "waiveredge.active-league.v1";

export type ConnectedLeague = {
  id: number;
  platform: string;
  league_id: string;
  team_key: string | null;
  sport: string;
  roster_count: number;
  created_at: string | null;
};

type LeagueContextValue = {
  leagues: ConnectedLeague[];
  activeLeague: ConnectedLeague | null;
  setActiveLeagueId: (id: number) => void;
  refreshLeagues: () => Promise<void>;
  loading: boolean;
};

const LeagueContext = createContext<LeagueContextValue>({
  leagues: [],
  activeLeague: null,
  setActiveLeagueId: () => {},
  refreshLeagues: async () => {},
  loading: false,
});

export function useLeagues() {
  return useContext(LeagueContext);
}

function getSavedLeagueIds(sport: string): number[] {
  try {
    const raw = localStorage.getItem(`${LEAGUES_KEY}.${sport}`);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function getActiveLeagueId(sport: string): number | null {
  try {
    const raw = localStorage.getItem(`${ACTIVE_KEY}.${sport}`);
    return raw ? parseInt(raw, 10) : null;
  } catch {
    return null;
  }
}

export function LeagueProvider({ sport, children }: { sport: string; children: ReactNode }) {
  const [leagues, setLeagues] = useState<ConnectedLeague[]>([]);
  const [activeLeagueId, setActiveId] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);

  const refreshLeagues = useCallback(async () => {
    const ids = getSavedLeagueIds(sport);
    if (ids.length === 0) {
      setLeagues([]);
      setActiveId(null);
      return;
    }
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/leagues?ids=${ids.join(",")}`);
      if (res.ok) {
        const data: ConnectedLeague[] = await res.json();
        setLeagues(data);
        // Restore active league from localStorage, or default to first
        const savedActive = getActiveLeagueId(sport);
        const validActive = data.find((l) => l.id === savedActive);
        if (validActive) {
          setActiveId(validActive.id);
        } else if (data.length > 0) {
          setActiveId(data[0].id);
          localStorage.setItem(`${ACTIVE_KEY}.${sport}`, String(data[0].id));
        }
      }
    } catch {
      /* network error — keep existing state */
    } finally {
      setLoading(false);
    }
  }, [sport]);

  useEffect(() => {
    refreshLeagues();
  }, [refreshLeagues]);

  const setActiveLeagueId = useCallback(
    (id: number) => {
      setActiveId(id);
      localStorage.setItem(`${ACTIVE_KEY}.${sport}`, String(id));
    },
    [sport],
  );

  const activeLeague = leagues.find((l) => l.id === activeLeagueId) ?? null;

  return (
    <LeagueContext.Provider value={{ leagues, activeLeague, setActiveLeagueId, refreshLeagues, loading }}>
      {children}
    </LeagueContext.Provider>
  );
}
