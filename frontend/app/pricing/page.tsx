"use client";

import { useState } from "react";
import Link from "next/link";
import { ArrowRight, Check, Crown, Loader2, Zap } from "lucide-react";
import { getAuthHeaders, useAuthUser } from "../components/auth-header";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";
type Plan = "monthly" | "season";

const FREE_FEATURES = [
  "Weekly top streamers list",
  "Schedule density grid",
  "Manual roster input (basic)",
];
const PRO_FEATURES = [
  "Everything in Free",
  "Personalized roster recommendations",
  "Yahoo & ESPN league auto-import",
  "H2H Points, 9-Cat & 5x5 scoring modes",
  "Live injury alerts",
  "Unlimited leagues",
];

export default function PricingPage() {
  const { user, loaded } = useAuthUser();
  const [plan, setPlan] = useState<Plan>("season");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleCheckout() {
    setLoading(true);
    setError(null);
    try {
      if (!user) {
        setError("Please sign in before upgrading.");
        return;
      }
      const res = await fetch(`${API_BASE}/api/billing/checkout`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...getAuthHeaders() },
        body: JSON.stringify({ plan }),
      });
      if (!res.ok) {
        const b = await res.json().catch(() => null);
        const detail = b?.detail;
        setError(typeof detail === "string" ? detail : detail?.message || "Checkout failed. Please try again.");
        return;
      }
      const { checkout_url } = await res.json();
      if (checkout_url) window.location.href = checkout_url;
    } catch {
      setError("Could not reach the server.");
    } finally {
      setLoading(false);
    }
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
          <Link href="/" className="text-sm text-muted hover:text-accent transition-colors">
            ← Home
          </Link>
        </div>
      </header>

      <main className="flex-1 mx-auto px-6 md:px-12 lg:px-20 py-16">
        <div className="text-center mb-12 animate-fade-in">
          <div className="inline-flex items-center justify-center h-12 w-12 rounded-xl bg-accent/10 mb-4">
            <Crown size={24} className="text-accent" />
          </div>
          <h1 className="text-3xl font-extrabold tracking-tight mb-3">Upgrade to Pro</h1>
          <p className="text-sm text-muted max-w-lg mx-auto">
            Pro unlocks personalized recommendations for{" "}
            <em className="text-gray-200 not-italic font-medium">your</em> actual roster
            — MLB, WNBA, and NBA.
          </p>
        </div>

        <div className="flex justify-center mb-10">
          <div className="flex rounded-lg bg-surface p-1 gap-1">
            <button
              onClick={() => setPlan("monthly")}
              className={`rounded-md px-4 py-1.5 text-sm font-medium transition-colors ${
                plan === "monthly" ? "bg-accent text-bg" : "text-muted hover:text-gray-200"
              }`}
            >
              Monthly
            </button>
            <button
              onClick={() => setPlan("season")}
              className={`rounded-md px-4 py-1.5 text-sm font-medium transition-colors ${
                plan === "season" ? "bg-accent text-bg" : "text-muted hover:text-gray-200"
              }`}
            >
              Season Pass <span className="text-xs opacity-70">save 30%</span>
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="rounded-xl border border-line bg-card p-6">
            <h2 className="text-lg font-bold mb-1">Free</h2>
            <p className="text-3xl font-bold mb-1">$0</p>
            <p className="text-xs text-muted mb-6">Forever</p>
            <ul className="space-y-2.5 mb-8">
              {FREE_FEATURES.map((f) => (
                <li key={f} className="flex items-start gap-2 text-sm text-muted">
                  <Check size={14} className="text-muted mt-0.5 shrink-0" />
                  {f}
                </li>
              ))}
            </ul>
            <Link
              href="/"
              className="block text-center rounded-lg border border-line py-2.5 text-sm font-medium text-muted hover:border-accent/40 hover:text-gray-200 transition-colors"
            >
              Current plan
            </Link>
          </div>

          <div className="rounded-xl border-2 border-accent bg-card p-6 relative">
            <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-accent text-bg text-xs font-bold px-3 py-0.5 rounded-full flex items-center gap-1">
              <Crown size={12} /> RECOMMENDED
            </div>
            <h2 className="text-lg font-bold mb-1 flex items-center gap-2">
              Pro <Crown size={16} className="text-accent" />
            </h2>
            <p className="text-3xl font-bold mb-1">
              {plan === "season" ? "$39" : "$8"}
              <span className="text-base font-normal text-muted">
                /{plan === "season" ? "season" : "mo"}
              </span>
            </p>
            <p className="text-xs text-muted mb-6">
              {plan === "season" ? "~7 months · saves ~$17" : "Cancel anytime"}
            </p>
            <ul className="space-y-2.5 mb-8">
              {PRO_FEATURES.map((f) => (
                <li key={f} className="flex items-start gap-2 text-sm">
                  <Check size={14} className="text-pos mt-0.5 shrink-0" />
                  {f}
                </li>
              ))}
            </ul>
            <button
              onClick={loaded && !user ? undefined : handleCheckout}
              disabled={loading}
              className="w-full flex items-center justify-center gap-2 rounded-lg bg-accent py-3 text-sm font-semibold text-bg hover:brightness-110 transition-all shadow-lg shadow-accent/20 disabled:opacity-40 disabled:hover:shadow-none disabled:hover:brightness-100"
            >
              {!loaded ? (
                <Loader2 size={16} className="animate-spin" />
              ) : !user ? (
                <Link href="/signin" className="flex items-center gap-2">
                  Sign in to upgrade <ArrowRight size={14} />
                </Link>
              ) : loading ? (
                <>
                  <Loader2 size={16} className="animate-spin" /> Processing…
                </>
              ) : (
                <>
                  Upgrade to Pro <ArrowRight size={14} />
                </>
              )}
            </button>
          </div>
        </div>

        {error && (
          <div className="rounded-xl border border-neg/30 bg-neg/5 px-4 py-4 mt-6 text-center animate-fade-in">
            <p className="text-sm text-neg">{error}</p>
          </div>
        )}

        <p className="text-center text-xs text-muted mt-8">
          Secure checkout powered by Stripe. Cancel anytime.
        </p>

        {/* FAQ */}
        <section className="mt-16 mb-8">
          <h2 className="text-lg font-bold text-center mb-6">Frequently Asked Questions</h2>
          <div className="space-y-4 max-w-lg mx-auto">
            {[
              { q: "What sports are supported?", a: "MLB, WNBA, and NBA — with NFL and NHL on the roadmap." },
              { q: "Can I cancel anytime?", a: "Yes. Cancel from your Stripe billing portal — no questions asked." },
              { q: "Do you modify my roster?", a: "Never. WaiverEdge uses read-only access to analyze your team." },
              { q: "What platforms are supported?", a: "Yahoo and ESPN Fantasy. WNBA is ESPN only." },
            ].map((faq) => (
              <div key={faq.q} className="rounded-xl border border-line bg-card p-4">
                <p className="text-sm font-medium mb-1">{faq.q}</p>
                <p className="text-xs text-muted">{faq.a}</p>
              </div>
            ))}
          </div>
        </section>
      </main>

      <footer className="border-t border-line/50 bg-card/30">
        <div className="mx-auto px-6 md:px-12 lg:px-20 py-6">
          <p className="text-center text-[11px] text-muted/50">
            &copy; {new Date().getFullYear()} WaiverEdge
          </p>
        </div>
      </footer>
    </div>
  );
}
