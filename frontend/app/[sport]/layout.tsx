"use client";

import { useParams } from "next/navigation";
import Link from "next/link";
import { Flame, Zap } from "lucide-react";
import type { ReactNode } from "react";

const SPORT_META: Record<string, { name: string; icon: string }> = {
  nba: { name: "NBA", icon: "\u{1F3C0}" },
  mlb: { name: "MLB", icon: "\u26BE" },
};

const VALID_SPORTS = new Set(["nba", "mlb"]);

export default function SportLayout({ children }: { children: ReactNode }) {
  const params = useParams();
  const sport = params.sport as string;
  const meta = SPORT_META[sport];

  if (!VALID_SPORTS.has(sport)) {
    return (
      <div className="min-h-screen bg-bg flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold mb-2">Sport not found</h1>
          <p className="text-muted mb-4">Choose a supported sport:</p>
          <Link href="/" className="text-accent hover:underline">← Back to home</Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-bg">
      <header className="border-b border-line bg-card/60 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link href="/" className="flex items-center gap-2 hover:opacity-80 transition-opacity">
              <div className="h-7 w-7 rounded-lg bg-accent flex items-center justify-center">
                <Zap size={16} className="text-bg" />
              </div>
              <span className="text-lg font-bold tracking-tight">WaiverEdge</span>
            </Link>
            <span className="text-xs bg-accent/10 text-accent border border-accent/30 rounded-md px-2 py-1 font-semibold">
              {meta.icon} {meta.name}
            </span>
          </div>
          <nav className="flex items-center gap-4">
            <Link href={`/${sport}/streamers`} className="flex items-center gap-1 text-sm text-muted hover:text-accent transition-colors">
              <Flame size={14} /> Streamers
            </Link>
            <Link href="/pricing" className="text-sm text-muted hover:text-accent transition-colors">
              Pricing
            </Link>
          </nav>
        </div>
      </header>

      {children}

      <footer className="border-t border-line mt-16 py-6">
        <p className="text-center text-xs text-muted">
          WaiverEdge &middot; Real sports data &middot; No logos or trademarks used
        </p>
      </footer>
    </div>
  );
}
