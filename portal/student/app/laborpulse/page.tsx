import LaborPulseClient from "./LaborPulseClient"

/**
 * LaborPulse — workforce-development director Q&A.
 *
 * Server component: the page shell. The real work happens client-side in
 * LaborPulseClient because SSE reads go through the browser's
 * EventSource / fetch ReadableStream and the progressive render has to
 * re-render on every chunk.
 *
 * Auth: /api/laborpulse/query already enforces the
 * workforce-development / staff / admin role via @llm_gated (#25). If
 * the user isn't authenticated, the client surfaces the 401 envelope as
 * a "please sign in" state. We don't redirect server-side because the
 * same page renders fine for signed-in visitors who haven't asked a
 * question yet — no point eagerly bouncing them.
 */
export default function LaborPulsePage() {
  return (
    <main className="mx-auto max-w-4xl px-4 py-8">
      <header className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight">LaborPulse</h1>
        <p className="text-muted-foreground text-sm">
          Workforce-development Q&amp;A. Ask about demand, wages, sector
          shifts, skills gaps in your region. Answers are grounded in
          live job-posting data.
        </p>
      </header>
      <LaborPulseClient />
    </main>
  )
}
