import type { Metadata } from 'next'
import { Geist, Geist_Mono, Figtree, DM_Mono, Instrument_Serif } from 'next/font/google'
import { Analytics } from '@vercel/analytics/next'
import ChatWidget from '@/components/ChatWidget'
import './globals.css'

const _geist = Geist({ subsets: ["latin"] });
const _geistMono = Geist_Mono({ subsets: ["latin"] });

// Finance cockpit fonts — exposed as CSS custom properties consumed by
// the .cockpit-surface scope in globals.css. Loaded once at the root so
// every cockpit-style agent surface shares the same font subset.
const cockpitSans = Figtree({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-cockpit-sans",
});
const cockpitMono = DM_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-cockpit-mono",
});
const cockpitDisplay = Instrument_Serif({
  subsets: ["latin"],
  weight: ["400"],
  variable: "--font-cockpit-display",
});
const cockpitFontVars = `${cockpitSans.variable} ${cockpitMono.variable} ${cockpitDisplay.variable}`;

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

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en" className={cockpitFontVars}>
      <body className="font-sans antialiased">
        {children}
        <ChatWidget />
        <Analytics />
      </body>
    </html>
  )
}
