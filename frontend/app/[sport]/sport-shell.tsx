"use client";

import { useEffect, useRef, useState } from "react";
import { useParams, usePathname } from "next/navigation";
import Link from "next/link";
import { ChevronDown, Flame, LayoutDashboard, Link2, LogOut, TrendingUp, Zap } from "lucide-react";
import type { ReactNode } from "react";
import { useAuthUser } from "../components/auth-header";
import { LeagueProvider, useLeagues } from "../components/league-context";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

function UserMenu() {
  const { user, loaded } = useAuthUser();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  if (!loaded) return null;

  if (!user) {
    return (
      <Link
        href="/signin"
        className="rounded-lg bg-accent px-4 py-1.5 text-sm font-semibold text-bg hover:brightness-110 transition-all shadow-sm shadow-accent/20"
      >
        Get Started
      </Link>
    );
  }

  return (
    <div ref={ref} className="relative">
      <button type="button" onClick={() => setOpen(!open)} className="flex items-center gap-2 hover:opacity-80 transition-opacity">
        {user.picture ? (
          <img src={user.picture} alt="" className="h-7 w-7 rounded-full border border-line" referrerPolicy="no-referrer" />
        ) : (
          <div className="h-7 w-7 rounded-full bg-accent/20 flex items-center justify-center text-xs font-bold text-accent">
            {(user.name || user.email)[0].toUpperCase()}
          </div>
        )}
      </button>
      {open && (
        <div className="absolute right-0 top-full mt-2 w-52 rounded-xl border border-line bg-card shadow-2xl shadow-black/40 overflow-hidden z-50 animate-fade-in">
          <div className="px-4 py-3 border-b border-line/50">
            <p className="text-sm font-medium truncate">{user.name || "User"}</p>
            <p className="text-xs text-muted truncate">{user.email}</p>
          </div>
          <button
            type="button"
            onClick={() => {
              localStorage.removeItem("we_token");
              window.location.reload();
            }}
            className="flex items-center gap-2 w-full px-4 py-2.5 text-sm text-muted hover:text-gray-200 hover:bg-surface transition-colors"
          >
            <LogOut size={14} /> Sign out
          </button>
        </div>
      )}
    </div>
  );
}

const SPORT_META: Record<string, { name: string; icon: string; active: boolean }> = {
  mlb: { name: "MLB", icon: "\u26BE", active: true },
  wnba: { name: "WNBA", icon: "\u{1F3C0}", active: true },
  nba: { name: "NBA", icon: "\u{1F3C0}", active: false },
};

const VALID_SPORTS = new Set(["nba", "mlb", "wnba"]);

function SportSwitcher({ currentSport, pathname }: { currentSport: string; pathname: string }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const current = SPORT_META[currentSport];

  // Preserve sub-path when switching sports (e.g. /mlb/streamers → /wnba/streamers)
  const subPath = pathname.replace(`/${currentSport}`, "") || "";

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1.5 text-xs bg-accent/10 text-accent border border-accent/30 rounded-full px-2.5 py-1 font-semibold hover:bg-accent/20 transition-colors"
      >
        {current.icon} {current.name}
        <ChevronDown size={12} className={`transition-transform ${open ? "rotate-180" : ""}`} />
      </button>

      {open && (
        <div className="absolute top-full left-0 mt-1.5 w-44 rounded-xl border border-line bg-card shadow-2xl shadow-black/40 overflow-hidden z-50 animate-fade-in">
          <div className="px-3 py-2 border-b border-line/50">
            <p className="text-[10px] uppercase tracking-wider text-muted font-semibold">Switch sport</p>
          </div>
          {Object.entries(SPORT_META).map(([key, meta]) => (
            <Link
              key={key}
              href={meta.active ? `/${key}${subPath}` : "#"}
              onClick={() => setOpen(false)}
              className={`flex items-center gap-2.5 px-3 py-2.5 text-sm transition-colors ${
                key === currentSport
                  ? "bg-accent/10 text-accent font-semibold"
                  : meta.active
                    ? "text-gray-200 hover:bg-surface"
                    : "text-muted/50 cursor-not-allowed pointer-events-none"
              }`}
            >
              <span className="text-lg">{meta.icon}</span>
              <span className="flex-1">{meta.name}</span>
              {key === currentSport && (
                <span className="text-[10px] bg-accent/20 text-accent rounded-full px-1.5 py-0.5 font-bold">Active</span>
              )}
              {!meta.active && (
                <span className="text-[10px] bg-surface text-muted rounded-full px-1.5 py-0.5">Off</span>
              )}
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

function LeagueIndicator({ sport }: { sport: string }) {
  const { activeLeague } = useLeagues();
  if (!activeLeague) {
    return (
      <Link
        href={`/${sport}/connect`}
        className="flex items-center gap-1.5 text-sm px-3 py-1.5 rounded-lg text-muted hover:text-gray-200 hover:bg-surface transition-colors"
      >
        <Link2 size={14} /> <span className="hidden sm:inline">Connect</span>
      </Link>
    );
  }
  return (
    <Link
      href={`/${sport}/league/${activeLeague.id}`}
      className="flex items-center gap-1.5 text-sm px-3 py-1.5 rounded-lg text-pos/80 hover:text-pos hover:bg-pos/10 transition-colors"
    >
      <Link2 size={14} />
      <span className="hidden sm:inline">{activeLeague.platform.toUpperCase()}</span>
    </Link>
  );
}


export default function SportShell({ children }: { children: ReactNode }) {
  const params = useParams();
  const pathname = usePathname();
  const sport = params.sport as string;
  const onStreamers = pathname.endsWith("/streamers");
  const onTopAvailable = pathname.endsWith("/top-available");
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
    <LeagueProvider sport={sport}>
    <div className="min-h-screen bg-bg flex flex-col">
      <header className="border-b border-line/50 bg-bg/80 backdrop-blur-md sticky top-0 z-20">
        <div className="mx-auto px-6 md:px-12 lg:px-20 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link href="/" className="flex items-center gap-2 hover:opacity-80 transition-opacity">
              <div className="h-8 w-8 rounded-lg bg-accent flex items-center justify-center shadow-lg shadow-accent/20">
                <Zap size={18} className="text-bg" />
              </div>
              <span className="text-lg font-bold tracking-tight hidden sm:inline">WaiverEdge</span>
            </Link>
            <SportSwitcher currentSport={sport} pathname={pathname} />
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
            <Link
              href={`/${sport}/streamers`}
              className={`flex items-center gap-1.5 text-sm px-3 py-1.5 rounded-lg transition-colors ${
                onStreamers ? "text-accent bg-accent/10" : "text-muted hover:text-gray-200 hover:bg-surface"
              }`}
            >
              <Flame size={14} /> <span className="hidden sm:inline">Streamers</span>
            </Link>
            <Link
              href={`/${sport}/top-available`}
              className={`flex items-center gap-1.5 text-sm px-3 py-1.5 rounded-lg transition-colors ${
                onTopAvailable ? "text-accent bg-accent/10" : "text-muted hover:text-gray-200 hover:bg-surface"
              }`}
            >
              <TrendingUp size={14} /> <span className="hidden sm:inline">Top Available</span>
            </Link>
            <LeagueIndicator sport={sport} />
            <Link href="/pricing" className="text-sm px-3 py-1.5 rounded-lg text-muted hover:text-gray-200 hover:bg-surface transition-colors">
              Pricing
            </Link>
            <UserMenu />
          </nav>
        </div>
      </header>

      <div className="flex-1">{children}</div>

      <footer className="border-t border-line/50 bg-card/30 mt-16">
        <div className="mx-auto px-6 md:px-12 lg:px-20 py-6">
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
              <Link href={`/${sport}/top-available`} className="hover:text-accent transition-colors">Top Available</Link>
              <Link href="/pricing" className="hover:text-accent transition-colors">Pricing</Link>
            </div>
          </div>
          <p className="text-center text-[11px] text-muted/50 mt-4">
            &copy; {new Date().getFullYear()} WaiverEdge
          </p>
        </div>
      </footer>
    </div>
    </LeagueProvider>
  );
}
