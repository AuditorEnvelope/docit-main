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
  async headers() {
    return [
      {
        source: '/render-docs/:path*',
        headers: [
          {
            key: 'Cache-Control',
            value: 'no-store, must-revalidate',
          },
          {
            key: 'Pragma',
            value: 'no-cache',
          },
        ],
      },
    ];
  },
  async rewrites() {
    const hostRule = {
      type: 'host' as const,
      value: '(?<org>[^.]+)\\.docbook\\.site',
    };

    return [
      {
        source: '/',
        has: [hostRule],
        destination: '/docs/:org',
      },
      {
        source: '/:path((?!_next|api).*)',
        has: [hostRule],
        destination: '/docs/:org/:path',
      },
    ];
  },
};

export default nextConfig;
