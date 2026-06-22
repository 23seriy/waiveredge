import type { Metadata } from "next";
import type { ReactNode } from "react";
import SportShell from "./sport-shell";

const SPORT_SEO: Record<string, { title: string; description: string }> = {
  nba: {
    title: "NBA Waiver Wire Rankings — WaiverEdge",
    description: "Find the best NBA fantasy basketball waiver wire pickups ranked for your roster. H2H Points and 9-Cat leagues supported. Powered by schedule density, matchups, and recent form.",
  },
  mlb: {
    title: "MLB Waiver Wire Rankings — WaiverEdge",
    description: "Find the best MLB fantasy baseball waiver wire pickups ranked for your roster. H2H Points and 5x5 leagues supported. Powered by schedule density, matchups, and recent form.",
  },
  wnba: {
    title: "WNBA Waiver Wire Rankings — WaiverEdge",
    description: "Find the best WNBA fantasy basketball waiver wire pickups ranked for your roster. H2H Points leagues supported. ESPN only. Powered by schedule density, matchups, and recent form.",
  },
};

export async function generateMetadata({ params }: { params: Promise<{ sport: string }> }): Promise<Metadata> {
  const { sport } = await params;
  const seo = SPORT_SEO[sport] || {
    title: `${sport.toUpperCase()} Waiver Wire — WaiverEdge`,
    description: "Fantasy sports waiver wire rankings powered by schedule density, matchups, and recent form.",
  };

  return {
    title: seo.title,
    description: seo.description,
    openGraph: {
      title: seo.title,
      description: seo.description,
      siteName: "WaiverEdge",
      type: "website",
    },
    twitter: {
      card: "summary_large_image",
      title: seo.title,
      description: seo.description,
    },
  };
}

export default function SportLayout({ children }: { children: ReactNode }) {
  return <SportShell>{children}</SportShell>;
}
