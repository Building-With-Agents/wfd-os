"use client"

import { useState, FormEvent } from "react"
import { Compass, ExternalLink } from "lucide-react"

interface UnsubscribeResult {
  success: boolean
  email: string
  found: boolean
}

interface Props {
  initialEmail: string
  initialResult: UnsubscribeResult | null
}

export default function UnsubscribeClient({ initialEmail, initialResult }: Props) {
  const [resubEmail, setResubEmail] = useState("")
  const [resubState, setResubState] = useState<"idle" | "submitting" | "success" | "duplicate" | "error">("idle")
  const [resubMessage, setResubMessage] = useState("")

  async function handleResubscribe(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    if (!resubEmail || !resubEmail.includes("@")) {
      setResubState("error")
      setResubMessage("Please enter a valid email")
      return
    }
    setResubState("submitting")
    try {
      const r = await fetch("/api/marketing/newsletter-subscribe", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: resubEmail, source: "unsubscribe_page_resub" }),
      })
      const data = await r.json().catch(() => ({}))
      if (r.ok && data.success) {
        setResubState("success")
        setResubMessage("You're in — first issue coming soon")
      } else if (r.status === 409 || data.already_subscribed) {
        setResubState("duplicate")
        setResubMessage("Already subscribed — thanks for being with us")
      } else {
        setResubState("error")
        setResubMessage(data.error || "Something went wrong. Please try again.")
      }
    } catch {
      setResubState("error")
      setResubMessage("Network error. Please try again.")
    }
  }

  const resubDone = resubState === "success" || resubState === "duplicate"

  return (
    <div className="min-h-screen bg-background">
      <main className="mx-auto flex min-h-screen max-w-xl flex-col items-center justify-center px-4 py-12 text-center">
        {/* CFA logo */}
        <div className="mb-8 flex items-center gap-2 text-foreground">
          <Compass className="h-8 w-8 text-primary" />
          <span className="text-lg font-semibold">Computing for All</span>
        </div>

        {/* Headline + body */}
        <h1 className="mb-4 text-3xl font-bold text-foreground sm:text-4xl">
          You&apos;ve been unsubscribed
        </h1>
        <p className="mb-8 max-w-md text-base text-muted-foreground">
          You won&apos;t receive any more newsletters from Computing for All. Changed your mind? You
          can resubscribe below.
        </p>

        {initialEmail && initialResult?.success ? (
          <p className="mb-8 text-xs text-muted-foreground">
            Unsubscribed: <span className="font-mono text-foreground">{initialEmail}</span>
          </p>
        ) : null}

        {/* Resubscribe form */}
        <div className="mb-10 w-full max-w-md rounded-lg border border-border bg-card p-6 shadow-sm">
          <h2 className="mb-3 text-sm font-semibold text-foreground">Resubscribe</h2>
          {resubDone ? (
            <p
              className="text-sm font-medium text-primary"
              role="status"
              aria-live="polite"
            >
              {resubMessage}
            </p>
          ) : (
            <form onSubmit={handleResubscribe} className="flex flex-col gap-2 sm:flex-row">
              <label htmlFor="resub-email" className="sr-only">
                Email address
              </label>
              <input
                id="resub-email"
                type="email"
                required
                placeholder="Your work email"
                value={resubEmail}
                onChange={(e) => setResubEmail(e.target.value)}
                disabled={resubState === "submitting"}
                className="flex-1 rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary disabled:opacity-50"
              />
              <button
                type="submit"
                disabled={resubState === "submitting"}
                className="rounded-md bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground transition hover:bg-primary/90 disabled:opacity-60"
              >
                {resubState === "submitting" ? "Subscribing…" : "Subscribe"}
              </button>
            </form>
          )}
          {resubState === "error" && (
            <p className="mt-2 text-xs text-destructive" role="alert">
              {resubMessage}
            </p>
          )}
        </div>

        {/* Link back to main site */}
        <a
          href="https://computingforall.org"
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 text-sm text-primary hover:underline"
        >
          computingforall.org
          <ExternalLink className="h-3 w-3" />
        </a>
      </main>
    </div>
  )
}
