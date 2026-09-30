/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,

  // Only import the icons/components actually used instead of whole barrels —
  // trims first-load JS on every page that uses lucide-react or recharts.
  experimental: {
    optimizePackageImports: ['lucide-react', 'recharts'],
  },

  typescript: {
    ignoreBuildErrors: true
  },

  // Short legal URLs. TikTok's app review (and most third-party developer
  // portals) ask for https://<domain>/terms and https://<domain>/privacy.
  // The documents live at the bilingual routes below; the English page is
  // the landing one for reviewers and carries a toggle to the BM version.
  // Redirects run before middleware, so these resolve on binaapp.my and
  // www.binaapp.my alike (Vercel serves both domains from this project).
  async redirects() {
    return [
      { source: '/terms', destination: '/terms-of-service', permanent: true },
      { source: '/privacy', destination: '/privacy-policy', permanent: true },
      { source: '/terma', destination: '/terma-perkhidmatan', permanent: true },
      { source: '/privasi', destination: '/polisi-privasi', permanent: true },
    ];
  },

  // Proxy API through Vercel to fix mobile CORS issues
  async rewrites() {
    return [
      {
        source: '/backend/:path*',
        destination: 'https://binaapp-backend.onrender.com/:path*',
      },
      // TikTok photo posts are PULL_FROM_URL only, from a URL prefix verified
      // in the TikTok developer portal. Staged photos are served from our own
      // domain at /api/tiktok/media/<key> and proxied to the backend here
      // (a rewrite, not a route handler, so Vercel's 4.5 MB function body
      // limit does not apply). Verify the prefix
      // https://www.binaapp.my/api/tiktok/media/ in the TikTok portal.
      {
        source: '/api/tiktok/media/:key',
        destination: 'https://binaapp-backend.onrender.com/api/v1/social/tiktok/media/:key',
      },
      // Malay language route alias
      {
        source: '/daftar',
        destination: '/register',
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
          { key: 'Cache-Control', value: 'public, max-age=0, must-revalidate' },
        ],
      },
      {
        source: '/rider/manifest.json',
        headers: [
          { key: 'Content-Type', value: 'application/manifest+json' },
          { key: 'Cache-Control', value: 'public, max-age=0, must-revalidate' },
        ],
      },
      {
        source: '/sw.js',
        headers: [
          { key: 'Content-Type', value: 'application/javascript' },
          { key: 'Cache-Control', value: 'no-cache, no-store, must-revalidate' },
          { key: 'Service-Worker-Allowed', value: '/' },
        ],
      },
      {
        source: '/rider/sw.js',
        headers: [
          { key: 'Content-Type', value: 'application/javascript' },
          { key: 'Cache-Control', value: 'no-cache, no-store, must-revalidate' },
          { key: 'Service-Worker-Allowed', value: '/rider' },
        ],
      },
    ];
  },
}

module.exports = nextConfig
