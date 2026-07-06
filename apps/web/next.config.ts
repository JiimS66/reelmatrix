import type { NextConfig } from "next";

const API_ORIGIN = (
  process.env.BACKEND_ORIGIN || "http://121.43.99.199:8000"
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
