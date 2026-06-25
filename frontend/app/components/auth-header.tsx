"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { LogOut, Zap } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";
const TOKEN_KEY = "we_token";

type AuthUser = { id: number; email: string; name: string | null; picture: string | null; tier: string };

export function getAuthHeaders(): Record<string, string> {
  const token = typeof window !== "undefined" ? localStorage.getItem(TOKEN_KEY) : null;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export function useAuthUser() {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem(TOKEN_KEY);
    if (!token) {
      setLoaded(true);
      return;
    }
    fetch(`${API_BASE}/api/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => r.json())
      .then((d) => {
        if (d.user) {
          setUser(d.user);
        } else {
          localStorage.removeItem(TOKEN_KEY);
        }
        setLoaded(true);
      })
      .catch(() => {
        localStorage.removeItem(TOKEN_KEY);
        setLoaded(true);
      });
  }, []);

  return { user, loaded };
}

function UserMenu({ user }: { user: AuthUser }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

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
              localStorage.removeItem(TOKEN_KEY);
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

export default function AuthHeader() {
  const { user, loaded } = useAuthUser();

  return (
    <header className="border-b border-line/50 bg-bg/80 backdrop-blur-md sticky top-0 z-20">
      <div className="mx-auto px-6 md:px-12 lg:px-20 py-3 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-2 hover:opacity-80 transition-opacity">
          <div className="h-8 w-8 rounded-lg bg-accent flex items-center justify-center shadow-lg shadow-accent/20">
            <Zap size={18} className="text-bg" />
          </div>
          <span className="text-lg font-bold tracking-tight">WaiverEdge</span>
        </Link>
        <nav className="flex items-center gap-5">
          <Link href="/pricing" className="text-sm text-muted hover:text-accent transition-colors">
            Pricing
          </Link>
          {loaded && (
            user ? (
              <UserMenu user={user} />
            ) : (
              <Link
                href="/signin"
                className="rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-bg hover:brightness-110 transition-all shadow-sm shadow-accent/20"
              >
                Get Started
              </Link>
            )
          )}
        </nav>
      </div>
    </header>
  );
}
