import type { NextConfig } from "next";

// When deployed, the browser talks to this site at /api/..., and Next.js
// forwards those requests to the real backend (BACKEND_URL). That keeps the
// login cookie on one domain, so browsers don't block it as a third-party
// cookie. Locally BACKEND_URL is unset and the app calls the backend directly.
const backendUrl = process.env.BACKEND_URL?.replace(/\/+$/, "");

const nextConfig: NextConfig = {
  async rewrites() {
    if (!backendUrl) return [];
    return [{ source: "/api/:path*", destination: `${backendUrl}/:path*` }];
  },
};

export default nextConfig;
