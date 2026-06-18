import type { ReactNode } from "react";
import "./globals.css";

export const metadata = {
  title: "WaiverEdge",
  description: "Your fantasy sports move-finder — NBA basketball and MLB baseball",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
