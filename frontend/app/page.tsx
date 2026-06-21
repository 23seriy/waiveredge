import Link from "next/link";
import { ArrowRight, Flame, Zap } from "lucide-react";

const SPORTS = [
  {
    key: "mlb",
    name: "MLB Baseball",
    icon: "\u26BE",
    description: "Points & 5x5 roto leagues",
    active: true,
    note: "In-season",
  },
  {
    key: "nba",
    name: "NBA Basketball",
    icon: "\u{1F3C0}",
    description: "Points & 9-Cat leagues",
    active: false,
    note: "Offseason \u2014 returns Oct 2026",
  },
];

export default function Home() {
  return (
    <div className="min-h-screen bg-bg">
      <header className="border-b border-line bg-card/60 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="h-7 w-7 rounded-lg bg-accent flex items-center justify-center">
              <Zap size={16} className="text-bg" />
            </div>
            <span className="text-lg font-bold tracking-tight">WaiverEdge</span>
          </div>
          <nav className="flex items-center gap-4">
            <Link href="/pricing" className="text-sm text-muted hover:text-accent transition-colors">
              Pricing
            </Link>
          </nav>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-4">
        <section className="py-16 md:py-24 text-center">
          <h1 className="text-3xl md:text-5xl font-bold tracking-tight mb-4">
            Know exactly who to pick up<br />
            <span className="text-accent">for your roster, this week</span>
          </h1>
          <p className="text-muted text-base md:text-lg max-w-xl mx-auto mb-12 leading-relaxed">
            WaiverEdge fuses schedule density, matchups, and injuries into one ranked
            action list — the waiver move-finder for fantasy managers.
          </p>

          <h2 className="text-sm font-medium text-muted uppercase tracking-wider mb-6">
            Choose your sport
          </h2>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 max-w-lg mx-auto mb-12">
            {SPORTS.map((sport) => (
              <Link
                key={sport.key}
                href={sport.active ? `/${sport.key}` : "#"}
                className={`group rounded-xl border p-6 text-center transition-all ${
                  sport.active
                    ? "border-accent/40 bg-card hover:border-accent hover:shadow-lg hover:shadow-accent/10 cursor-pointer"
                    : "border-line bg-card/60 opacity-60 cursor-not-allowed pointer-events-none"
                }`}
              >
                <span className="text-4xl block mb-3">{sport.icon}</span>
                <h3 className="text-lg font-bold mb-1 flex items-center justify-center gap-2">
                  {sport.name}
                  {sport.active ? (
                    <span className="text-[10px] uppercase tracking-wider font-bold bg-pos/15 text-pos rounded-full px-2 py-0.5">
                      Live
                    </span>
                  ) : (
                    <span className="text-[10px] uppercase tracking-wider font-bold bg-surface text-muted rounded-full px-2 py-0.5">
                      Offseason
                    </span>
                  )}
                </h3>
                <p className="text-sm text-muted mb-3">{sport.description}</p>
                {sport.active && (
                  <span className="inline-flex items-center gap-1 text-sm text-accent font-medium group-hover:gap-2 transition-all">
                    Enter <ArrowRight size={14} />
                  </span>
                )}
                {!sport.active && (
                  <span className="text-xs text-muted">{sport.note}</span>
                )}
              </Link>
            ))}
          </div>

          <div className="rounded-lg bg-surface/50 border border-line p-4 max-w-md mx-auto mb-8">
            <div className="flex flex-col gap-2 text-left">
              <p className="text-sm font-medium">Works with Yahoo &amp; ESPN</p>
              <p className="text-xs text-muted">
                Connect your league for personalized picks, or paste your roster manually.
                Points, 9-Cat, and 5x5 scoring modes.
              </p>
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-line mt-16 py-6">
        <div className="flex items-center justify-center gap-4 text-xs text-muted">
          <span>WaiverEdge</span>
          <span>&middot;</span>
          <Link href="/pricing" className="hover:text-accent transition-colors">Pricing</Link>
          <span>&middot;</span>
          <Link href="/mlb/streamers" className="hover:text-accent transition-colors">MLB Streamers</Link>
          <span>&middot;</span>
          <span>Real sports data</span>
        </div>
      </footer>
    </div>
  );
}
