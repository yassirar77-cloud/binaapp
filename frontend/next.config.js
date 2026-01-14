const path = require('path')

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: false,

  // Turbopack config (Next.js 16+)
  turbopack: {
    root: path.resolve(__dirname),
  },

  webpack: (config) => {
    config.resolve.alias['@'] = path.resolve(__dirname, 'src')
    return config
  },

  typescript: {
    ignoreBuildErrors: true
  },

  // Proxy API through Vercel to fix mobile CORS issues
  async rewrites() {
    return [
      {
        source: '/backend/:path*',
        destination: 'https://binaapp-backend.onrender.com/:path*',
      },
    ];
  },

  // Headers for PWA manifests and service workers
  async headers() {
    return [
      {
        source: '/manifest.json',
        headers: [
          { key: 'Content-Type', value: 'application/manifest+json' },
        ],
      },
      {
        source: '/rider-manifest.json',
        headers: [
          { key: 'Content-Type', value: 'application/manifest+json' },
        ],
      },
      {
        source: '/sw.js',
        headers: [
          { key: 'Content-Type', value: 'application/javascript' },
          { key: 'Service-Worker-Allowed', value: '/' },
        ],
      },
      {
        source: '/sw-rider.js',
        headers: [
          { key: 'Content-Type', value: 'application/javascript' },
          { key: 'Service-Worker-Allowed', value: '/rider' },
        ],
      },
    ];
  },
}

module.exports = nextConfig