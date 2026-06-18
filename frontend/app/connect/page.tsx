"use client";

import { useSearchParams } from "next/navigation";
import { Suspense } from "react";
import { ArrowRight, ExternalLink, Flame, Zap } from "lucide-react";
import Link from "next/link";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "https://localhost:8000";

type Sport = {
  key: string;
  name: string;
  icon: string;
  active: boolean;
  note: string;
};

const SPORTS: Sport[] = [
  { key: "nba", name: "NBA Basketball", icon: "\u{1F3C0}", active: false, note: "Offseason \u2014 returns Oct 2026" },
  { key: "mlb", name: "MLB Baseball",  icon: "\u26BE",     active: true,  note: "In-season" },
];

function SportCard({ sport }: { sport: Sport }) {
  return (
    <div className={`rounded-xl border p-6 transition-colors ${
      sport.active ? "border-accent/40 bg-card" : "border-line bg-card/60 opacity-60"
    }`}>
      <div className="flex items-center gap-3 mb-3">
        <span className="text-3xl">{sport.icon}</span>
        <div>
          <h3 className="text-base font-semibold flex items-center gap-2">
            {sport.name}
            {sport.active ? (
              <span className="text-[10px] uppercase tracking-wider font-bold bg-pos/15 text-pos rounded-full px-2 py-0.5">Active</span>
            ) : (
              <span className="text-[10px] uppercase tracking-wider font-bold bg-surface text-muted rounded-full px-2 py-0.5">Offseason</span>
            )}
          </h3>
          <p className="text-xs text-muted">{sport.note}</p>
        </div>
      </div>

      {sport.active ? (
        <a
          href={`${API_BASE}/api/auth/yahoo?sport=${sport.key}`}
          className="w-full inline-flex items-center justify-center gap-2 rounded-lg bg-purple-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-purple-500 transition-colors"
        >
          Connect with Yahoo <ExternalLink size={14} />
        </a>
      ) : (
        <button
          disabled
          className="w-full inline-flex items-center justify-center gap-2 rounded-lg bg-surface border border-line px-4 py-2.5 text-sm font-medium text-muted cursor-not-allowed"
        >
          Available when season starts
        </button>
      )}
    </div>
  );
}

function ConnectContent() {
  const params = useSearchParams();
  const error = params.get("error");
  const sport = params.get("sport");

  return (
    <div className="min-h-screen bg-bg">
      <header className="border-b border-line bg-card/60 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-3xl mx-auto px-4 py-3 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2 hover:opacity-80 transition-opacity">
            <div className="h-7 w-7 rounded-lg bg-accent flex items-center justify-center">
              <Zap size={16} className="text-bg" />
            </div>
            <span className="text-lg font-bold tracking-tight">WaiverEdge</span>
          </Link>
          <Link href="/streamers" className="flex items-center gap-1 text-sm text-muted hover:text-accent transition-colors">
            <Flame size={14} /> Streamers
          </Link>
        </div>
      </header>

      <main className="max-w-xl mx-auto px-4 py-16">
        <div className="text-center mb-10">
          <h1 className="text-2xl font-bold tracking-tight mb-3">Connect Your Yahoo League</h1>
          <p className="text-sm text-muted leading-relaxed max-w-md mx-auto">
            Link your Yahoo Fantasy league and get personalized waiver recommendations
            for <em className="text-gray-200 not-italic font-medium">your</em> actual roster.
          </p>
        </div>

        {error && (
          <div className="rounded-lg border border-neg/30 bg-neg/10 px-4 py-3 mb-6 text-center">
            <p className="text-sm text-neg">
              {error === "no_leagues"
                ? `No active ${(sport || "").toUpperCase() || "fantasy"} leagues found on your Yahoo account.`
                : `Error: ${error}`}
            </p>
          </div>
        )}

        <div className="space-y-4 mb-8">
          {SPORTS.map((s) => <SportCard key={s.key} sport={s} />)}
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
          <p className="text-xs text-muted mb-2">Don&apos;t have Yahoo?</p>
          <Link href="/" className="inline-flex items-center gap-1 text-sm text-accent hover:underline">
            Paste your roster manually <ArrowRight size={14} />
          </Link>
        </div>
      </main>
    </div>
  );
}

export default function ConnectPage() {
  return <Suspense><ConnectContent /></Suspense>;
}
