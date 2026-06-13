import type { ReactNode } from "react";
import "./globals.css";

export const metadata = {
  title: "WaiverEdge",
  description: "Your fantasy basketball move-finder",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
