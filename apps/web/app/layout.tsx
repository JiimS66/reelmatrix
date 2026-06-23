import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "ReelMatrix Campaign Studio",
  description: "Turn a marketing brief into an actionable campaign plan.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
