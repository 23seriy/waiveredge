"use client";

import { useState } from "react";
import Link from "next/link";
import { ArrowRight, Check, Crown, Flame, Loader2, Zap } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";
type Plan = "monthly" | "season";

const FREE_FEATURES = ["Weekly top streamers list", "Schedule density grid", "Manual roster input (basic)"];
const PRO_FEATURES = ["Everything in Free", "Personalized roster recommendations", "Yahoo league auto-import", "9-Cat z-score mode", "Live injury alerts (coming soon)", "Unlimited leagues"];

export default function PricingPage() {
  const [plan, setPlan] = useState<Plan>("season");
  const [loading, setLoading] = useState(false);

  async function handleCheckout() {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/billing/checkout`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: 1, plan }),
      });
      if (!res.ok) { const b = await res.json().catch(() => null); alert(b?.detail || "Checkout failed"); return; }
      const { checkout_url } = await res.json();
      if (checkout_url) window.location.href = checkout_url;
    } finally { setLoading(false); }
  }

  return (
    <div className="min-h-screen bg-bg">
      <header className="border-b border-line bg-card/60 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-4 py-3 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2 hover:opacity-80 transition-opacity">
            <div className="h-7 w-7 rounded-lg bg-accent flex items-center justify-center"><Zap size={16} className="text-bg" /></div>
            <span className="text-lg font-bold tracking-tight">WaiverEdge</span>
          </Link>
          <Link href="/streamers" className="flex items-center gap-1 text-sm text-muted hover:text-accent transition-colors"><Flame size={14} /> Streamers</Link>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-4 py-16">
        <div className="text-center mb-12">
          <h1 className="text-3xl font-bold tracking-tight mb-3">Upgrade to Pro</h1>
          <p className="text-sm text-muted max-w-lg mx-auto">
            Pro unlocks personalized recommendations for <em className="text-gray-200 not-italic font-medium">your</em> actual roster.
          </p>
        </div>

        <div className="flex justify-center mb-10">
          <div className="flex rounded-lg bg-surface p-1 gap-1">
            <button onClick={() => setPlan("monthly")} className={`rounded-md px-4 py-1.5 text-sm font-medium transition-colors ${plan === "monthly" ? "bg-accent text-bg" : "text-muted hover:text-gray-200"}`}>Monthly</button>
            <button onClick={() => setPlan("season")} className={`rounded-md px-4 py-1.5 text-sm font-medium transition-colors ${plan === "season" ? "bg-accent text-bg" : "text-muted hover:text-gray-200"}`}>Season Pass <span className="text-xs opacity-70">save 30%</span></button>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="rounded-xl border border-line bg-card p-6">
            <h2 className="text-lg font-bold mb-1">Free</h2>
            <p className="text-3xl font-bold mb-1">$0</p>
            <p className="text-xs text-muted mb-6">Forever</p>
            <ul className="space-y-2.5 mb-8">{FREE_FEATURES.map((f) => <li key={f} className="flex items-start gap-2 text-sm text-muted"><Check size={14} className="text-muted mt-0.5 shrink-0" />{f}</li>)}</ul>
            <Link href="/streamers" className="block text-center rounded-lg border border-line py-2.5 text-sm font-medium text-muted hover:border-accent/40 hover:text-gray-200 transition-colors">Current plan</Link>
          </div>

          <div className="rounded-xl border-2 border-accent bg-card p-6 relative">
            <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-accent text-bg text-xs font-bold px-3 py-0.5 rounded-full flex items-center gap-1"><Crown size={12} /> RECOMMENDED</div>
            <h2 className="text-lg font-bold mb-1 flex items-center gap-2">Pro <Crown size={16} className="text-accent" /></h2>
            <p className="text-3xl font-bold mb-1">{plan === "season" ? "$39" : "$8"}<span className="text-base font-normal text-muted">/{plan === "season" ? "season" : "mo"}</span></p>
            <p className="text-xs text-muted mb-6">{plan === "season" ? "~7 months · saves ~$17" : "Cancel anytime"}</p>
            <ul className="space-y-2.5 mb-8">{PRO_FEATURES.map((f) => <li key={f} className="flex items-start gap-2 text-sm"><Check size={14} className="text-pos mt-0.5 shrink-0" />{f}</li>)}</ul>
            <button onClick={handleCheckout} disabled={loading} className="w-full flex items-center justify-center gap-2 rounded-lg bg-accent py-2.5 text-sm font-semibold text-bg hover:opacity-90 disabled:opacity-40">
              {loading ? <><Loader2 size={16} className="animate-spin" /> Processing…</> : <>Upgrade to Pro <ArrowRight size={14} /></>}
            </button>
          </div>
        </div>

        <p className="text-center text-xs text-muted mt-8">Secure checkout powered by Stripe. Cancel anytime.</p>
      </main>
    </div>
  );
}
