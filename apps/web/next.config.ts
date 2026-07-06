import type { NextConfig } from "next";

// Rewrite target for /api/* when the app is served behind a proxying host
// (the Vercel mirror). Dev must NEVER silently fall back to the production
// box — that fallback made a fresh checkout behave like the stale deployment.
// Local dev defaults to the local API; production builds default to the demo
// box, and Vercel can override with BACKEND_ORIGIN.
const API_ORIGIN = (
  process.env.BACKEND_ORIGIN ||
  (process.env.NODE_ENV === "development"
    ? "http://localhost:8000"
    : "http://121.43.99.199:8000")
).replace(/\/$/, "");

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${API_ORIGIN}/api/:path*`,
      },
      {
        source: "/health",
        destination: `${API_ORIGIN}/health`,
      },
    ];
  },
};

export default nextConfig;
