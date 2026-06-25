import Link from "next/link";
import { ArrowRight, ChartNoAxesCombined, Link2, ListChecks, Shield, Zap } from "lucide-react";

const SPORTS = [
  {
    key: "mlb",
    name: "MLB Baseball",
    icon: "\u26BE",
    description: "H2H Points & 5×5 category leagues",
    platforms: "Yahoo & ESPN",
    features: ["Points", "5×5 Cats", "Streamers"],
    active: true,
  },
  {
    key: "wnba",
    name: "WNBA Basketball",
    icon: "\u{1F3C0}",
    description: "H2H Points leagues on ESPN",
    platforms: "ESPN",
    features: ["Points", "Streamers"],
    active: true,
  },
  {
    key: "nba",
    name: "NBA Basketball",
    icon: "\u{1F3C0}",
    description: "H2H Points & 9-Cat leagues",
    platforms: "Yahoo & ESPN",
    features: ["Points", "9-Cat", "Streamers"],
    active: false,
    note: "Returns Oct 2026",
  },
];

const STEPS = [
  {
    num: 1,
    icon: ListChecks,
    title: "Pick your sport",
    text: "Choose MLB, WNBA, or NBA. You can switch anytime from the header.",
  },
  {
    num: 2,
    icon: Link2,
    title: "Paste roster or sync your league",
    text: "Drop in player names or connect Yahoo / ESPN for automatic roster import.",
  },
  {
    num: 3,
    icon: ChartNoAxesCombined,
    title: "Get ranked recommendations",
    text: "We crunch schedule density, matchups, and recent form — then rank who to add and who to drop.",
  },
];

export default function Home() {
  return (
    <div className="min-h-screen bg-bg">
      <header className="border-b border-line/50 bg-bg/80 backdrop-blur-md sticky top-0 z-20">
        <div className="mx-auto px-6 md:px-12 lg:px-20 py-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="h-8 w-8 rounded-lg bg-accent flex items-center justify-center shadow-lg shadow-accent/20">
              <Zap size={18} className="text-bg" />
            </div>
            <span className="text-lg font-bold tracking-tight">WaiverEdge</span>
          </div>
          <nav className="flex items-center gap-5">
            <Link href="/pricing" className="text-sm text-muted hover:text-accent transition-colors">
              Pricing
            </Link>
            <Link
              href="/signin"
              className="rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-bg hover:brightness-110 transition-all shadow-sm shadow-accent/20"
            >
              Get Started
            </Link>
          </nav>
        </div>
      </header>

      <main>
        {/* Hero + Sport Picker — one unified section */}
        <section className="relative overflow-hidden">
          <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_rgba(240,136,62,0.08)_0%,_transparent_60%)] pointer-events-none" />
          <div className="mx-auto px-6 md:px-12 lg:px-20 pt-16 pb-6 md:pt-24 md:pb-8 text-center relative">
            <div className="inline-flex items-center gap-2 rounded-full border border-accent/30 bg-accent/5 px-4 py-1.5 text-xs font-medium text-accent mb-6 animate-fade-in">
              <span className="relative flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full rounded-full bg-pos opacity-75 animate-ping" />
                <span className="relative inline-flex h-2 w-2 rounded-full bg-pos" />
              </span>
              MLB &amp; WNBA in-season now
            </div>

            <h1 className="text-4xl md:text-5xl lg:text-6xl font-extrabold tracking-tight mb-4 text-balance animate-fade-in" style={{ animationDelay: "0.1s" }}>
              Know exactly who to pick up{" "}
              <span className="text-accent">for your roster</span>
            </h1>
            <p className="text-muted text-base md:text-lg max-w-xl mx-auto mb-3 leading-relaxed animate-fade-in" style={{ animationDelay: "0.2s" }}>
              WaiverEdge fuses schedule density, matchups, and recent form into one
              ranked action list — the waiver move-finder for fantasy managers.
            </p>
            <p className="text-xs text-muted/70 mb-2 animate-fade-in" style={{ animationDelay: "0.25s" }}>
              No sign-up required &middot; Works with Yahoo &amp; ESPN
            </p>
          </div>
        </section>

        {/* Sport picker — directly below hero with no gap */}
        <section className="mx-auto px-6 md:px-12 lg:px-20 pb-16">
          <h2 className="text-sm font-semibold text-muted uppercase tracking-widest text-center mb-6 animate-fade-in" style={{ animationDelay: "0.3s" }}>
            Pick your sport to get started
          </h2>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5 max-w-4xl mx-auto">
            {SPORTS.map((sport, i) => (
              <Link
                key={sport.key}
                href={sport.active ? `/${sport.key}` : "#"}
                className={`group relative rounded-2xl border p-8 text-center transition-all duration-200 animate-slide-up ${
                  sport.active
                    ? "border-line bg-card hover:border-accent/60 hover:shadow-2xl hover:shadow-accent/10 hover:-translate-y-1 cursor-pointer"
                    : "border-line/40 bg-card/30 opacity-40 cursor-not-allowed pointer-events-none"
                }`}
                style={{ animationDelay: `${0.3 + 0.1 * i}s` }}
              >
                <span className="text-5xl block mb-4 group-hover:scale-110 transition-transform duration-200">{sport.icon}</span>
                <div className="flex items-center justify-center gap-2 mb-2">
                  <h3 className="text-lg font-bold">{sport.name}</h3>
                  {sport.active ? (
                    <span className="text-[10px] uppercase tracking-wider font-bold bg-pos/15 text-pos rounded-full px-2 py-0.5">
                      Live
                    </span>
                  ) : (
                    <span className="text-[10px] uppercase tracking-wider font-bold bg-surface text-muted rounded-full px-2 py-0.5">
                      Off
                    </span>
                  )}
                </div>
                <p className="text-sm text-muted mb-3">{sport.description}</p>
                <div className="flex flex-wrap justify-center gap-1.5 mb-4">
                  {sport.features.map((f) => (
                    <span key={f} className="text-[11px] font-medium bg-surface text-muted rounded-md px-2 py-0.5 border border-line/50">
                      {f}
                    </span>
                  ))}
                </div>
                <p className="text-[11px] text-muted/60 mb-4">{sport.platforms}</p>
                {sport.active ? (
                  <span className="inline-flex items-center justify-center gap-2 w-full rounded-lg bg-accent/10 border border-accent/30 px-4 py-2.5 text-sm font-semibold text-accent group-hover:bg-accent group-hover:text-bg transition-all">
                    Enter {sport.name.split(" ")[0]} <ArrowRight size={14} />
                  </span>
                ) : (
                  <span className="inline-flex items-center justify-center w-full rounded-lg bg-surface/50 px-4 py-2.5 text-sm text-muted">
                    {sport.note}
                  </span>
                )}
              </Link>
            ))}
          </div>
        </section>

        {/* Getting started steps */}
        <section className="border-t border-line/50 bg-surface/30">
          <div className="mx-auto px-6 md:px-12 lg:px-20 py-16">
            <h2 className="text-xl font-bold text-center mb-2">Getting Started</h2>
            <p className="text-sm text-muted text-center mb-10 max-w-md mx-auto">
              Three steps to smarter waiver moves. No account required.
            </p>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-4xl mx-auto">
              {STEPS.map((step) => (
                <div key={step.num} className="relative text-center">
                  <div className="inline-flex items-center justify-center h-14 w-14 rounded-2xl bg-accent/10 border border-accent/20 mb-5">
                    <step.icon size={24} className="text-accent" />
                  </div>
                  <div className="absolute -top-2 left-1/2 -translate-x-1/2 -translate-y-1/2 h-7 w-7 rounded-full bg-accent text-bg text-xs font-bold flex items-center justify-center shadow-lg shadow-accent/30">
                    {step.num}
                  </div>
                  <h3 className="text-sm font-semibold mb-2">{step.title}</h3>
                  <p className="text-xs text-muted leading-relaxed">{step.text}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Trust bar */}
        <section className="border-t border-line/50">
          <div className="mx-auto px-6 md:px-12 lg:px-20 py-10 text-center">
            <div className="inline-flex flex-wrap items-center justify-center gap-x-6 gap-y-3 text-sm text-muted">
              <span className="flex items-center gap-1.5"><Shield size={14} className="text-accent" /> Read-only access</span>
              <span className="text-line hidden sm:inline">|</span>
              <span className="flex items-center gap-1.5">H2H Points, 9-Cat &amp; 5x5</span>
              <span className="text-line hidden sm:inline">|</span>
              <span className="flex items-center gap-1.5">Yahoo &amp; ESPN supported</span>
              <span className="text-line hidden sm:inline">|</span>
              <span className="flex items-center gap-1.5">Updated weekly</span>
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-line/50 bg-card/40">
        <div className="mx-auto px-6 md:px-12 lg:px-20 py-8">
          <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <div className="h-6 w-6 rounded bg-accent/80 flex items-center justify-center">
                <Zap size={12} className="text-bg" />
              </div>
              <span className="text-sm font-semibold">WaiverEdge</span>
            </div>
            <div className="flex flex-wrap items-center justify-center gap-x-5 gap-y-2 text-xs text-muted">
              <Link href="/mlb" className="hover:text-accent transition-colors">MLB</Link>
              <Link href="/wnba" className="hover:text-accent transition-colors">WNBA</Link>
              <Link href="/pricing" className="hover:text-accent transition-colors">Pricing</Link>
            </div>
          </div>
          <p className="text-center text-[11px] text-muted/60 mt-6">
            &copy; {new Date().getFullYear()} WaiverEdge
          </p>
        </div>
      </footer>
    </div>
  );
}
