import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Disable ESLint during builds (warnings won't block production)
  eslint: {
    ignoreDuringBuilds: true,
  },
  typescript: {
    // Keep TypeScript checks but don't block on errors
    ignoreBuildErrors: false,
  },
  // Enable React strict mode
  reactStrictMode: true,
  // Optimize images
  images: {
    domains: ['avatars.githubusercontent.com', 'github.com'],
  },
};

export default nextConfig;
