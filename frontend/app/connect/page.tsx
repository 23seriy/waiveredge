"use client";

import { useSearchParams } from "next/navigation";
import { Suspense } from "react";
import { ArrowRight, ExternalLink, Flame, Zap } from "lucide-react";
import Link from "next/link";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

function ConnectContent() {
  const params = useSearchParams();
  const error = params.get("error");

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
            Link your Yahoo Fantasy Basketball league and get personalized
            waiver recommendations for <em className="text-gray-200 not-italic font-medium">your</em> actual roster.
          </p>
        </div>

        {error && (
          <div className="rounded-lg border border-neg/30 bg-neg/10 px-4 py-3 mb-6 text-center">
            <p className="text-sm text-neg">
              {error === "no_leagues" ? "No active NBA leagues found on your Yahoo account." : `Error: ${error}`}
            </p>
          </div>
        )}

        <div className="rounded-xl border border-line bg-card p-8 text-center">
          <div className="flex justify-center mb-6">
            <div className="h-16 w-16 rounded-2xl bg-purple-600/20 flex items-center justify-center">
              <span className="text-3xl">Y!</span>
            </div>
          </div>
          <h2 className="text-lg font-semibold mb-2">Yahoo Fantasy Basketball</h2>
          <p className="text-sm text-muted mb-6 max-w-sm mx-auto">
            We&apos;ll import your roster and league scoring settings. Read-only — we never modify your team.
          </p>
          <a
            href={`${API_BASE}/api/auth/yahoo`}
            className="inline-flex items-center gap-2 rounded-lg bg-purple-600 px-6 py-3 text-sm font-semibold text-white hover:bg-purple-500 transition-colors"
          >
            Connect with Yahoo <ExternalLink size={14} />
          </a>

          <div className="mt-8 pt-6 border-t border-line">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-left">
              <div className="rounded-lg bg-surface p-3">
                <p className="text-sm font-medium mb-1">Auto-import roster</p>
                <p className="text-xs text-muted">Your actual players, positions, and slots.</p>
              </div>
              <div className="rounded-lg bg-surface p-3">
                <p className="text-sm font-medium mb-1">League scoring</p>
                <p className="text-xs text-muted">Points or 9-cat — detected automatically.</p>
              </div>
              <div className="rounded-lg bg-surface p-3">
                <p className="text-sm font-medium mb-1">Ranked pickups</p>
                <p className="text-xs text-muted">Value-over-replacement for YOUR team.</p>
              </div>
            </div>
          </div>
        </div>

        <div className="mt-8 text-center">
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
