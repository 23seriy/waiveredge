"use client";

import Link from "next/link";
import { Zap } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

export default function SignInPage() {
  return (
    <div className="min-h-screen bg-bg flex flex-col">
      <header className="border-b border-line/50 bg-bg/80 backdrop-blur-md sticky top-0 z-20">
        <div className="mx-auto px-6 md:px-12 lg:px-20 py-3 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2 hover:opacity-80 transition-opacity">
            <div className="h-8 w-8 rounded-lg bg-accent flex items-center justify-center shadow-lg shadow-accent/20">
              <Zap size={18} className="text-bg" />
            </div>
            <span className="text-lg font-bold tracking-tight">WaiverEdge</span>
          </Link>
        </div>
      </header>

      <main className="flex-1 flex items-center justify-center px-6">
        <div className="w-full max-w-sm text-center animate-fade-in">
          <div className="inline-flex items-center justify-center h-14 w-14 rounded-2xl bg-accent/10 border border-accent/20 mb-6">
            <Zap size={28} className="text-accent" />
          </div>

          <h1 className="text-2xl font-extrabold tracking-tight mb-2">
            Sign in to WaiverEdge
          </h1>
          <p className="text-sm text-muted mb-8">
            Get personalized waiver recommendations for your fantasy leagues.
          </p>

          <a
            href={`${API_BASE}/api/auth/google`}
            className="flex items-center justify-center gap-3 w-full rounded-lg border border-line bg-card px-4 py-3 text-sm font-medium hover:border-accent/40 hover:bg-surface transition-all"
          >
            <svg viewBox="0 0 24 24" width="20" height="20" className="shrink-0">
              <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" />
              <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
              <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18A10.96 10.96 0 0 0 1 12c0 1.77.42 3.45 1.18 4.93l3.66-2.84z" />
              <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
            </svg>
            Continue with Google
          </a>

          <p className="text-xs text-muted/60 mt-6">
            By continuing, you agree to our terms of service.
          </p>

          <Link href="/" className="inline-flex items-center gap-1 text-sm text-muted hover:text-accent transition-colors mt-6">
            ← Back to home
          </Link>
        </div>
      </main>
    </div>
  );
}
