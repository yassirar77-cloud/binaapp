const path = require('path')

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: false,

  webpack: (config) => {
    config.resolve.alias['@'] = path.resolve(__dirname, 'src')
    return config
  },

  typescript: {
    ignoreBuildErrors: true
  },

  eslint: {
    ignoreDuringBuilds: true
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
}

module.exports = nextConfig