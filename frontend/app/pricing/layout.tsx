import type { Metadata } from "next";
import type { ReactNode } from "react";

export const metadata: Metadata = {
  title: "Pricing — WaiverEdge Pro",
  description:
    "Upgrade to WaiverEdge Pro for personalized fantasy waiver wire recommendations. Yahoo & ESPN auto-import, 9-Cat and 5x5 z-score modes, unlimited leagues.",
  openGraph: {
    title: "Pricing — WaiverEdge Pro",
    description:
      "Personalized fantasy waiver wire picks for your roster. Points, 9-Cat, and 5x5 leagues.",
    siteName: "WaiverEdge",
    type: "website",
  },
};

export default function PricingLayout({ children }: { children: ReactNode }) {
  return children;
}
