import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Enable strict TypeScript and ESLint for production
  eslint: {
    ignoreDuringBuilds: false, // Enable ESLint checks
  },
  typescript: {
    ignoreBuildErrors: false, // Enable TypeScript checks
  },
  // Enable React strict mode
  reactStrictMode: true,
  // Optimize images
  images: {
    domains: ['avatars.githubusercontent.com', 'github.com'],
  },
};

export default nextConfig;
