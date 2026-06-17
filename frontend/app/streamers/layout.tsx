import type { ReactNode } from "react";

export const metadata = {
  title: "Top Fantasy Basketball Streamers This Week | WaiverEdge",
  description:
    "Best fantasy basketball streaming pickups ranked by projected value. " +
    "Schedule density × matchups × recent form — real NBA data, updated weekly.",
  openGraph: {
    title: "Top Streamers This Week — WaiverEdge",
    description: "Best NBA streaming pickups ranked by projected value this week.",
  },
};

export default function StreamersLayout({ children }: { children: ReactNode }) {
  return <>{children}</>;
}
