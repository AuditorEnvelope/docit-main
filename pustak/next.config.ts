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
  async rewrites() {
    return [
      {
        source: '/:path*',
        has: [
          {
            type: 'host',
            value: '(?<org>[^.]+)\\.docbook\\.site',
          },
          {
            type: 'missing',
            key: 'path',
            value: '^(_next|api)(/.*)?$',
          },
        ],
        destination: '/docs/:org/:path*',
      },
    ];
  },
};

export default nextConfig;
