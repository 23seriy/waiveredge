"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Eye, EyeOff, Loader2, Zap } from "lucide-react";
import { useAuthUser } from "../components/auth-header";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

export default function SignInPage() {
  const { user, loaded } = useAuthUser();
  const router = useRouter();
  const [mode, setMode] = useState<"login" | "signup">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (loaded && user) {
      router.replace("/");
    }
  }, [loaded, user, router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const endpoint = mode === "signup" ? "/api/auth/signup" : "/api/auth/login";
      const body: Record<string, string> = { email, password };
      if (mode === "signup" && name.trim()) body.name = name.trim();
      const res = await fetch(`${API_BASE}${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => null);
        setError(data?.detail || `Sign ${mode === "signup" ? "up" : "in"} failed.`);
        return;
      }
      const data = await res.json();
      if (data.token) {
        localStorage.setItem("waiveredge.token", data.token);
        router.replace("/");
      }
    } catch {
      setError("Could not reach the server. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  if (!loaded || user) {
    return (
      <div className="min-h-screen bg-bg flex items-center justify-center">
        <Loader2 size={24} className="animate-spin text-accent" />
      </div>
    );
  }

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
        <div className="w-full max-w-sm animate-fade-in">
          <div className="text-center mb-8">
            <div className="inline-flex items-center justify-center h-14 w-14 rounded-2xl bg-accent/10 border border-accent/20 mb-6">
              <Zap size={28} className="text-accent" />
            </div>

            <h1 className="text-2xl font-extrabold tracking-tight mb-2">
              {mode === "signup" ? "Create your account" : "Sign in to WaiverEdge"}
            </h1>
            <p className="text-sm text-muted">
              {mode === "signup" ? (
                <>Already have an account?{" "}
                  <button type="button" onClick={() => { setMode("login"); setError(null); }} className="text-accent hover:underline font-medium">Sign In</button>
                </>
              ) : (
                <>Don&apos;t have an account?{" "}
                  <button type="button" onClick={() => { setMode("signup"); setError(null); }} className="text-accent hover:underline font-medium">Sign Up</button>
                </>
              )}
            </p>
          </div>

          {/* Google OAuth */}
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

          {/* OR divider */}
          <div className="flex items-center gap-3 my-6">
            <div className="flex-1 h-px bg-line" />
            <span className="text-xs text-muted font-medium uppercase tracking-wider">or</span>
            <div className="flex-1 h-px bg-line" />
          </div>

          {/* Email/Password form */}
          <form onSubmit={handleSubmit} className="space-y-3">
            {mode === "signup" && (
              <input
                type="text"
                placeholder="Name (optional)"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full rounded-lg border border-line bg-card px-4 py-3 text-sm placeholder:text-muted/50 focus:outline-none focus:border-accent/60 transition-colors"
              />
            )}
            <input
              type="email"
              placeholder="Email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="w-full rounded-lg border border-line bg-card px-4 py-3 text-sm placeholder:text-muted/50 focus:outline-none focus:border-accent/60 transition-colors"
            />
            <div className="relative">
              <input
                type={showPassword ? "text" : "password"}
                placeholder="Password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={8}
                className="w-full rounded-lg border border-line bg-card px-4 py-3 pr-10 text-sm placeholder:text-muted/50 focus:outline-none focus:border-accent/60 transition-colors"
              />
              <button
                type="button"
                onClick={() => setShowPassword((v) => !v)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted/50 hover:text-muted transition-colors"
                tabIndex={-1}
              >
                {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>

            {error && (
              <p className="text-sm text-neg">{error}</p>
            )}

            <button
              type="submit"
              disabled={submitting}
              className="w-full rounded-lg bg-accent px-4 py-3 text-sm font-semibold text-bg hover:brightness-110 hover:shadow-lg hover:shadow-accent/25 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {submitting && <Loader2 size={16} className="animate-spin" />}
              {mode === "signup" ? "Create Account" : "Sign In"}
            </button>
          </form>

          {/* Terms and Privacy */}
          <p className="text-xs text-muted/60 mt-6 text-center leading-relaxed">
            By clicking {mode === "signup" ? "Create Account" : "Sign In"}, you agree to our{" "}
            <Link href="/terms" className="text-accent hover:underline">Terms of Use</Link> and{" "}
            <Link href="/privacy" className="text-accent hover:underline">Privacy Policy</Link>.
          </p>

          <div className="text-center mt-6">
            <Link href="/" className="inline-flex items-center gap-1 text-sm text-muted hover:text-accent transition-colors">
              ← Back to home
            </Link>
          </div>
        </div>
      </main>
    </div>
  );
}
