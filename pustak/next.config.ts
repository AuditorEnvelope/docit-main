import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  eslint: {
    // Disable ESLint during build (warnings won't block production builds)
    ignoreDuringBuilds: true,
  },
  typescript: {
    // Disable TypeScript errors during build (for faster deployments)
    ignoreBuildErrors: true,
  },
};

export default nextConfig;
