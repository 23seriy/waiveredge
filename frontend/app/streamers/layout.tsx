import type { ReactNode } from "react";

export const metadata = {
  title: "Top Fantasy Streamers This Week | WaiverEdge",
  description:
    "Best fantasy sports streaming pickups ranked by projected value. " +
    "NBA basketball and MLB baseball — schedule density × matchups × recent form.",
  openGraph: {
    title: "Top Streamers This Week — WaiverEdge",
    description: "Best fantasy streaming pickups ranked by projected value this week.",
  },
};

export default function StreamersLayout({ children }: { children: ReactNode }) {
  return <>{children}</>;
}
