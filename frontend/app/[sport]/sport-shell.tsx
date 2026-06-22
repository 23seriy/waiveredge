"use client";

import { useParams, usePathname } from "next/navigation";
import Link from "next/link";
import { Flame, LayoutDashboard, Zap } from "lucide-react";
import type { ReactNode } from "react";

const SPORT_META: Record<string, { name: string; icon: string }> = {
  nba: { name: "NBA", icon: "\u{1F3C0}" },
  mlb: { name: "MLB", icon: "\u26BE" },
  wnba: { name: "WNBA", icon: "\u{1F3C0}" },
};

const VALID_SPORTS = new Set(["nba", "mlb", "wnba"]);

export default function SportShell({ children }: { children: ReactNode }) {
  const params = useParams();
  const pathname = usePathname();
  const sport = params.sport as string;
  const meta = SPORT_META[sport];
  const onStreamers = pathname.endsWith("/streamers");
  const onConnect = pathname.endsWith("/connect");
  const onDashboard = pathname === `/${sport}`;

  if (!VALID_SPORTS.has(sport)) {
    return (
      <div className="min-h-screen bg-bg flex items-center justify-center">
        <div className="text-center animate-fade-in">
          <span className="text-4xl block mb-4">🏟️</span>
          <h1 className="text-2xl font-bold mb-2">Sport not found</h1>
          <p className="text-muted mb-6">That sport isn&apos;t available yet.</p>
          <Link href="/" className="inline-flex items-center gap-1 text-sm text-accent hover:underline">
            ← Back to home
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-bg flex flex-col">
      <header className="border-b border-line/50 bg-bg/80 backdrop-blur-md sticky top-0 z-20">
        <div className="max-w-5xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link href="/" className="flex items-center gap-2 hover:opacity-80 transition-opacity">
              <div className="h-8 w-8 rounded-lg bg-accent flex items-center justify-center shadow-lg shadow-accent/20">
                <Zap size={18} className="text-bg" />
              </div>
              <span className="text-lg font-bold tracking-tight hidden sm:inline">WaiverEdge</span>
            </Link>
            <span className="text-xs bg-accent/10 text-accent border border-accent/30 rounded-full px-2.5 py-1 font-semibold">
              {meta.icon} {meta.name}
            </span>
          </div>
          <nav className="flex items-center gap-1">
            {onStreamers || onConnect ? (
              <Link href={`/${sport}`} className={`flex items-center gap-1.5 text-sm px-3 py-1.5 rounded-lg transition-colors ${onDashboard ? "text-accent bg-accent/10" : "text-muted hover:text-gray-200 hover:bg-surface"}`}>
                <LayoutDashboard size={14} /> Dashboard
              </Link>
            ) : (
              <Link href={`/${sport}`} className={`flex items-center gap-1.5 text-sm px-3 py-1.5 rounded-lg transition-colors ${onDashboard ? "text-accent bg-accent/10" : "text-muted hover:text-gray-200 hover:bg-surface"}`}>
                <LayoutDashboard size={14} /> <span className="hidden sm:inline">Dashboard</span>
              </Link>
            )}
            {!onStreamers && (
              <Link href={`/${sport}/streamers`} className="flex items-center gap-1.5 text-sm px-3 py-1.5 rounded-lg text-muted hover:text-gray-200 hover:bg-surface transition-colors">
                <Flame size={14} /> <span className="hidden sm:inline">Streamers</span>
              </Link>
            )}
            {onStreamers && (
              <span className="flex items-center gap-1.5 text-sm px-3 py-1.5 rounded-lg text-accent bg-accent/10">
                <Flame size={14} /> Streamers
              </span>
            )}
            <Link href="/pricing" className="text-sm px-3 py-1.5 rounded-lg text-muted hover:text-gray-200 hover:bg-surface transition-colors">
              Pricing
            </Link>
          </nav>
        </div>
      </header>

      <div className="flex-1">{children}</div>

      <footer className="border-t border-line/50 bg-card/30 mt-16">
        <div className="max-w-4xl mx-auto px-4 py-6">
          <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
            <Link href="/" className="flex items-center gap-2 text-muted hover:text-gray-300 transition-colors">
              <div className="h-5 w-5 rounded bg-accent/70 flex items-center justify-center">
                <Zap size={10} className="text-bg" />
              </div>
              <span className="text-xs font-medium">WaiverEdge</span>
            </Link>
            <div className="flex items-center gap-4 text-xs text-muted">
              <Link href="/" className="hover:text-accent transition-colors">Home</Link>
              <Link href={`/${sport}/streamers`} className="hover:text-accent transition-colors">Streamers</Link>
              <Link href="/pricing" className="hover:text-accent transition-colors">Pricing</Link>
            </div>
          </div>
          <p className="text-center text-[11px] text-muted/50 mt-4">
            &copy; {new Date().getFullYear()} WaiverEdge
          </p>
        </div>
      </footer>
    </div>
  );
}
