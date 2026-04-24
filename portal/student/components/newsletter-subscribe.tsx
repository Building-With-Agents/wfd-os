"use client"

import { useState, FormEvent } from "react"
import { Mail } from "lucide-react"

/**
 * NewsletterSubscribe — shared footer subscribe form.
 *
 * Posts to /api/marketing/newsletter-subscribe which is proxied by
 * next.config.mjs to http://localhost:8008/api/marketing/newsletter-subscribe
 * (agents/marketing/api.py).
 */
export default function NewsletterSubscribe() {
  const [email, setEmail] = useState("")
  const [state, setState] = useState<"idle" | "submitting" | "success" | "duplicate" | "error">("idle")
  const [message, setMessage] = useState("")

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    if (!email || !email.includes("@")) {
      setState("error")
      setMessage("Please enter a valid email")
      return
    }
    setState("submitting")
    try {
      const r = await fetch("/api/marketing/newsletter-subscribe", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, source: "website_footer" }),
      })
      const data = await r.json().catch(() => ({}))
      if (r.ok && data.success) {
        setState("success")
        setMessage("You're in — first issue coming soon")
      } else if (r.status === 409 || data.already_subscribed) {
        setState("duplicate")
        setMessage("Already subscribed — thanks for being with us")
      } else {
        setState("error")
        setMessage(data.error || "Something went wrong. Please try again.")
      }
    } catch {
      setState("error")
      setMessage("Network error. Please try again.")
    }
  }

  const done = state === "success" || state === "duplicate"

  return (
    <div className="mx-auto max-w-2xl px-4 pb-8 text-center">
      <div className="mb-2 flex items-center justify-center gap-2">
        <Mail className="h-4 w-4 text-primary" />
        <h3 className="text-base font-semibold text-foreground">Stay ahead of the curve</h3>
      </div>
      <p className="mb-4 text-sm text-muted-foreground">
        Practical AI insights for Washington State businesses. No jargon. Monthly.
      </p>

      {done ? (
        <p className="text-sm font-medium text-primary" role="status" aria-live="polite">
          {message}
        </p>
      ) : (
        <form onSubmit={handleSubmit} className="mx-auto flex max-w-md flex-col gap-2 sm:flex-row">
          <label htmlFor="newsletter-email" className="sr-only">
            Email address
          </label>
          <input
            id="newsletter-email"
            type="email"
            required
            placeholder="Your work email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            disabled={state === "submitting"}
            suppressHydrationWarning
            className="flex-1 rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={state === "submitting"}
            suppressHydrationWarning
            className="rounded-md bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground transition hover:bg-primary/90 disabled:opacity-60"
          >
            {state === "submitting" ? "Subscribing…" : "Subscribe"}
          </button>
        </form>
      )}

      {state === "error" && (
        <p className="mt-2 text-xs text-destructive" role="alert">
          {message}
        </p>
      )}
    </div>
  )
}
