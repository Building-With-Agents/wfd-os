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
        source: "/auth/:path*",
        destination: "http://localhost:8003/auth/:path*",
      },
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
      // Finance cockpit API (agents/finance/cockpit_api.py on :8013).
      // Its routes are at the service root (/cockpit/status, /cockpit/hero,
      // etc.) — the rewrite strips the /api/finance prefix.
      //   /api/finance/cockpit/hero  (portal)
      //   -> http://localhost:8013/cockpit/hero  (service)
      {
        source: "/api/finance/:path*",
        destination: "http://localhost:8013/:path*",
      },
      // Recruiting API (agents/job_board/api.py on :8012). Routes at
      // service root (/jobs, /students, /applications, /stats/workday).
      // Directory name uses underscore for Python importability — the
      // user-facing language stays "Recruiting" (URL prefix + sidebar
      // nav both use that term).
      //   /api/recruiting/jobs  (portal)
      //   -> http://localhost:8012/jobs  (service)
      {
        source: "/api/recruiting/:path*",
        destination: "http://localhost:8012/:path*",
      },
      {
        source: "/api/apollo/:path*",
        destination: "http://localhost:8010/api/apollo/:path*",
      },
      {
        source: "/api/showcase/:path*",
        destination: "http://localhost:8002/api/showcase/:path*",
      },
      // Student Portal API (agents/portal/student_api.py on :8001). Serves
      // the /student?id=<uuid> dashboard — profile, matches, gap, journey,
      // showcase. Routes already sit under /api/student/* at the service,
      // so this is a pass-through (no prefix strip).
      {
        source: "/api/student/:path*",
        destination: "http://localhost:8001/api/student/:path*",
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
      // Gary's magic-link auth routes (mounted on student_api.py on :8001):
      //   POST /auth/login, GET /auth/verify, POST /auth/logout, GET /auth/me
      //   PLUS GET /auth/dev-login (env-gated, DEV_AUTH_BYPASS=1 only).
      // Session cookies set by these endpoints are shared across every
      // backend using settings.auth.secret_key (laborpulse, showcase,
      // consulting_api, cockpit_api) — sign in once, all services honor
      // the same cookie.
      {
        source: "/auth/:path*",
        destination: "http://localhost:8001/auth/:path*",
      },
      // LaborPulse Q&A API (agents/laborpulse/api.py on :8015). The
      // default port in its docstring is 8012 but we moved it to 8015
      // to avoid colliding with the Recruiting/job_board service
      // already on 8012. Service routes live under /api/laborpulse/*
      // at the root, so this is a pass-through rewrite (no prefix
      // strip). Runs in mock mode when JIE_BASE_URL is unset —
      // returns canned Borderplex answers after ~10s.
      {
        source: "/api/laborpulse/:path*",
        destination: "http://localhost:8015/api/laborpulse/:path*",
      },
      // Platform-wide stats (student count, showcase-eligible count, etc.)
      // served by student_api.py on :8001 — NOT :8005 (which was a stale
      // placeholder). /coalition + /for-employers consume this to render
      // the hero stats bar dynamically with hardcoded fallback.
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
        destination: "http://localhost:8001/api/stats",
      },
      {
        source: "/api/:path*",
        destination: "http://localhost:8011/api/:path*",
      },
    ]
  },
}

export default nextConfig
