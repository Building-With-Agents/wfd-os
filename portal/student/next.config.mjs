/** @type {import('next').NextConfig} */
const nextConfig = {
  typescript: {
    ignoreBuildErrors: true,
  },
  images: {
    unoptimized: true,
  },
  async rewrites() {
    return [
      {
        source: "/auth/:path*",
        destination: "http://localhost:8003/auth/:path*",
      },
      {
        source: "/api/college/:path*",
        destination: "http://localhost:8004/api/college/:path*",
      },
      {
        source: "/api/consulting/:path*",
        destination: "http://localhost:8006/api/consulting/:path*",
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
      {
        source: "/api/laborpulse/:path*",
        destination: "http://localhost:8012/api/laborpulse/:path*",
      },
      {
        source: "/api/student/:path*",
        destination: "http://localhost:8001/api/student/:path*",
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
