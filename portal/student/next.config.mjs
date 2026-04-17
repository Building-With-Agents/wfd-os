/** @type {import('next').NextConfig} */
const nextConfig = {
  // Pin Turbopack's workspace root to this directory. Without this, Turbopack
  // infers a higher ancestor (wfd-os/portal or wfd-os/) because lib/content.ts
  // reads ../../content, which causes CSS resolution to look for `tailwindcss`
  // in the wrong node_modules and fails compilation.
  turbopack: {
    root: import.meta.dirname,
  },
  typescript: {
    ignoreBuildErrors: true,
  },
  images: {
    unoptimized: true,
  },
  async rewrites() {
    return [
      {
        source: "/api/college/:path*",
        destination: "http://localhost:8004/api/college/:path*",
      },
      {
        source: "/api/consulting/:path*",
        destination: "http://localhost:8003/api/consulting/:path*",
      },
      {
        source: "/api/wji/:path*",
        destination: "http://localhost:8007/api/wji/:path*",
      },
      {
        source: "/api/assistant/:path*",
        destination: "http://localhost:8009/api/assistant/:path*",
      },
      {
        source: "/api/marketing/:path*",
        destination: "http://localhost:8008/api/marketing/:path*",
      },
      {
        source: "/api/apollo/:path*",
        destination: "http://localhost:8010/api/apollo/:path*",
      },
      {
        source: "/api/showcase/:path*",
        destination: "http://localhost:8002/api/showcase/:path*",
      },
      // grant-compliance FastAPI runs on :8000. Its routes are at the
      // root of that service (/qb/status, /grants, /transactions, etc.)
      // — not under an /api prefix — so the rewrite strips our /api/grant-compliance
      // prefix entirely. Example: /api/grant-compliance/qb/status (portal)
      // → http://localhost:8000/qb/status (scaffold).
      {
        source: "/api/grant-compliance/:path*",
        destination: "http://localhost:8000/:path*",
      },
      {
        source: "/api/stats",
        destination: "http://localhost:8005/api/stats",
      },
      {
        source: "/api/:path*",
        destination: "http://localhost:8011/api/:path*",
      },
    ]
  },
}

export default nextConfig
