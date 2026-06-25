"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  AlertTriangle,
  ArrowLeft,
  Bell,
  Check,
  Loader2,
  RefreshCw,
  TrendingUp,
} from "lucide-react";

type Alert = {
  id: number;
  sport: string;
  injured_player_name: string;
  injury_status: string;
  injury_note: string | null;
  pickup_player_name: string | null;
  pickup_marginal: number | null;
  pickup_rationale: string | null;
  is_read: boolean;
  created_at: string | null;
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

export default function AlertsPage() {
  const params = useParams();
  const sport = params.sport as string;
  const connectionId = params.id as string;
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadAlerts = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/alerts/${connectionId}`);
      if (res.ok) setAlerts((await res.json()) as Alert[]);
    } catch {
      setError("Failed to load alerts");
    } finally {
      setLoading(false);
    }
  }, [connectionId]);

  useEffect(() => { loadAlerts(); }, [loadAlerts]);

  async function scanNow() {
    setScanning(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/api/alerts/scan/${connectionId}`, { method: "POST" });
      if (!res.ok) { const b = await res.json().catch(() => null); throw new Error(b?.detail || "Scan failed"); }
      const result = await res.json();
      if (result.new_alerts > 0) await loadAlerts();
      else setError(`Scan complete — no new injury alerts found.`);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Scan failed");
    } finally {
      setScanning(false);
    }
  }

  async function markRead(alertId: number) {
    await fetch(`${API_BASE}/api/alerts/${alertId}/read`, { method: "POST" });
    setAlerts((prev) => prev.map((a) => a.id === alertId ? { ...a, is_read: true } : a));
  }

  const unread = alerts.filter((a) => !a.is_read).length;

  return (
    <main className="mx-auto px-6 md:px-12 lg:px-20 py-8">
      <div className="flex items-center gap-3 mb-6">
        <Link
          href={`/${sport}/league/${connectionId}`}
          className="inline-flex items-center gap-1 text-xs text-muted hover:text-accent transition-colors"
        >
          <ArrowLeft size={12} /> Back to League
        </Link>
      </div>

      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold tracking-tight flex items-center gap-2">
            <Bell size={20} className="text-accent" /> Injury Alerts
          </h1>
          <p className="text-xs text-muted mt-0.5">
            {unread > 0 ? `${unread} unread alert${unread !== 1 ? "s" : ""}` : "No unread alerts"}
          </p>
        </div>
        <button
          onClick={scanNow}
          disabled={scanning}
          className="flex items-center gap-1.5 rounded-lg bg-accent px-3 py-1.5 text-sm font-semibold text-bg hover:opacity-90 disabled:opacity-40"
        >
          <RefreshCw size={14} className={scanning ? "animate-spin" : ""} />
          {scanning ? "Scanning…" : "Scan for injuries"}
        </button>
      </div>

      {error && (
        <div className="rounded-lg border border-accent/30 bg-accent/10 px-4 py-3 mb-6">
          <p className="text-sm text-accent">{error}</p>
        </div>
      )}

      {loading && (
        <div className="flex items-center justify-center py-20">
          <Loader2 size={24} className="animate-spin text-accent" />
        </div>
      )}

      {!loading && alerts.length === 0 && (
        <div className="rounded-xl border border-line bg-card p-8 text-center">
          <Bell size={32} className="text-muted mx-auto mb-3" />
          <h2 className="text-lg font-semibold mb-2">No Injury Alerts Yet</h2>
          <p className="text-sm text-muted max-w-sm mx-auto mb-4">
            Click &ldquo;Scan for injuries&rdquo; to check for new injury-driven pickup opportunities in your league.
          </p>
        </div>
      )}

      {!loading && alerts.length > 0 && (
        <div className="space-y-3">
          {alerts.map((a) => (
            <div
              key={a.id}
              className={`rounded-xl border p-4 transition-colors ${
                a.is_read ? "border-line bg-card/60 opacity-60" : "border-neg/40 bg-card"
              }`}
            >
              <div className="flex gap-3 items-start">
                <div className="shrink-0 mt-0.5">
                  <AlertTriangle size={18} className={a.is_read ? "text-muted" : "text-neg"} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-baseline gap-2 flex-wrap">
                    <span className="text-sm font-semibold text-neg">{a.injured_player_name}</span>
                    <span className="text-xs bg-neg/15 text-neg rounded px-1.5 py-0.5 font-medium uppercase">
                      {a.injury_status}
                    </span>
                  </div>
                  {a.injury_note && <p className="text-xs text-muted mt-0.5">{a.injury_note}</p>}

                  {a.pickup_player_name && (
                    <div className="mt-2 rounded-lg bg-surface p-2.5">
                      <div className="flex items-center gap-2">
                        <TrendingUp size={14} className="text-pos" />
                        <span className="text-sm font-medium">Pick up {a.pickup_player_name}</span>
                        {a.pickup_marginal && (
                          <span className="text-xs text-pos font-mono">+{a.pickup_marginal.toFixed(1)}</span>
                        )}
                      </div>
                      {a.pickup_rationale && (
                        <p className="text-xs text-muted mt-1">{a.pickup_rationale}</p>
                      )}
                    </div>
                  )}

                  <div className="flex items-center gap-3 mt-2">
                    {a.created_at && (
                      <span className="text-[10px] text-muted">
                        {new Date(a.created_at).toLocaleString()}
                      </span>
                    )}
                    {!a.is_read && (
                      <button
                        onClick={() => markRead(a.id)}
                        className="flex items-center gap-1 text-[10px] text-muted hover:text-accent transition-colors"
                      >
                        <Check size={10} /> Mark read
                      </button>
                    )}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </main>
  );
}
