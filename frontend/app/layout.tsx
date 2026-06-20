import type { ReactNode } from "react";
import "./globals.css";

export const metadata = {
  title: "WaiverEdge — Fantasy Waiver Wire Rankings",
  description: "Know exactly who to pick up. Fantasy baseball and basketball waiver wire adds ranked for your roster — powered by schedule density, matchups, and recent form.",
  openGraph: {
    title: "WaiverEdge — Fantasy Waiver Wire Rankings",
    description: "Know exactly who to pick up. MLB and NBA waiver wire adds ranked for your roster.",
    siteName: "WaiverEdge",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "WaiverEdge — Fantasy Waiver Wire Rankings",
    description: "Know exactly who to pick up. MLB and NBA waiver wire adds ranked for your roster.",
  },
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
