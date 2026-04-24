import type { Metadata } from 'next'
import { Geist, Geist_Mono } from 'next/font/google'
import { Analytics } from '@vercel/analytics/next'
import ChatWidget from '@/components/ChatWidget'
import './globals.css'

const _geist = Geist({ subsets: ["latin"] });
const _geistMono = Geist_Mono({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: 'Waifinder - Student Portal',
  description: 'Connect to your career journey with AI-powered job matching and skill development',
  generator: 'v0.app',
  icons: {
    icon: [
      {
        url: '/icon-light-32x32.png',
        media: '(prefers-color-scheme: light)',
      },
      {
        url: '/icon-dark-32x32.png',
        media: '(prefers-color-scheme: dark)',
      },
      {
        url: '/icon.svg',
        type: 'image/svg+xml',
      },
    ],
    apple: '/apple-icon.png',
  },
}

// NOTE on ngrok + dev mode:
//
// Next.js 16.2 Turbopack's dev runtime calls `new window.WebSocket(.../_next/webpack-hmr)`
// synchronously inside `hydrate()` at app-index.tsx:361. When the app is
// served through an ngrok tunnel (or any reverse proxy where WebSockets fail
// or are unstable), the failure interrupts React hydration at a point that
// leaves client components rendered but WITHOUT event handlers attached —
// every button is visually present but completely inert.
//
// We spent a long session (2026-04-09, Ritu + Claude) trying to work around
// this by stubbing `window.WebSocket` with a no-op (v1: readyState=CLOSED
// forever — blocked waiting for onopen; v2: fake-open that fired onopen on
// next tick — `[HMR] connected` appeared but buttons still dead; v3: stub
// disabled — real WebSocket fails and hydration breaks exactly as before).
// None of the variants unblocked hydration, because the issue is not just
// the open event — Turbopack's chunk-loading pipeline has additional
// invariants tied to the WebSocket that the stubs couldn't satisfy.
//
// THE ACTUAL FIX: run a PRODUCTION BUILD when serving to remote users.
//   cd portal/student
//   npm run build
//   npm run start
// Production mode has no HMR, no dev WebSocket, and no createWebSocket call
// in hydrate(). Works over ngrok / any tunnel cleanly. Dev mode stays fine
// on localhost for local editing.
//
// If a future Next.js version regresses this on localhost OR you discover
// a dev-mode workaround that actually works, the git history for this file
// has the full stub implementation that was tried and removed.

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en">
      <body className="font-sans antialiased">
        {children}
        <ChatWidget />
        <Analytics />
      </body>
    </html>
  )
}
