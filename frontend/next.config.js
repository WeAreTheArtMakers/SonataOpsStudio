/** @type {import('next').NextConfig} */
const backendInternalUrl = process.env.BACKEND_INTERNAL_URL || 'http://localhost:8000';

const nextConfig = {
  output: 'standalone',
  experimental: {
    typedRoutes: false
  },
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${backendInternalUrl}/:path*`
      }
    ];
  }
};

module.exports = nextConfig;
