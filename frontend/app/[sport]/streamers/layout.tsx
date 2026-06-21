import type { Metadata } from "next";
import type { ReactNode } from "react";

const SPORT_STREAMERS_SEO: Record<string, { title: string; description: string }> = {
  nba: {
    title: "NBA Streamers This Week — WaiverEdge",
    description:
      "Top NBA fantasy basketball streaming pickups ranked by projected value. Schedule density, matchup quality, and recent form — updated weekly.",
  },
  mlb: {
    title: "MLB Streamers This Week — WaiverEdge",
    description:
      "Top MLB fantasy baseball streaming pickups ranked by projected value. Schedule density, matchup quality, and recent form — updated weekly.",
  },
};

export async function generateMetadata({
  params,
}: {
  params: Promise<{ sport: string }>;
}): Promise<Metadata> {
  const { sport } = await params;
  const seo = SPORT_STREAMERS_SEO[sport] || {
    title: `${sport.toUpperCase()} Streamers — WaiverEdge`,
    description: "Top fantasy streaming pickups ranked by projected value this week.",
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
  };
}

export default function StreamersLayout({ children }: { children: ReactNode }) {
  return children;
}
