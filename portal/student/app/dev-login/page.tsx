"use client"

// Dev-mode sign-in page. One-click issue of a wfdos_session cookie for
// any allowlisted email, used to get past @llm_gated endpoints
// (LaborPulse /query + /feedback today; BD dashboard, others tomorrow)
// without running the magic-link email flow in local dev.
//
// Backed by GET /auth/dev-login?email=... on student_api.py (:8001),
// which is itself env-gated by DEV_AUTH_BYPASS=1. If that env var isn't
// set, the backend returns 404 and this page shows the error plainly.
//
// Remove or gate this page before any prod deploy. It's intentionally
// at /dev-login (not /internal/dev-login) because the session cookie
// needs to exist BEFORE any /internal/* cockpit surface is useful —
// there's no chicken-and-egg where you'd need to already be signed in
// to reach the sign-in page.

import { useCallback, useEffect, useState } from "react"
import { useRouter, useSearchParams } from "next/navigation"
import { Suspense } from "react"
import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { AlertTriangle, CheckCircle2, LogOut, User } from "lucide-react"

// Mirror the WFDOS_AUTH_*_ALLOWLIST env vars. The backend is the source
// of truth — unallowlisted emails submitted here would 403 from
// /auth/dev-login anyway. This list is just the UX affordance.
interface AllowlistedUser {
  email: string
  label: string
  role: "admin" | "staff" | "workforce-development" | "student"
}

const ALLOWLISTED: AllowlistedUser[] = [
  { email: "ritu@computingforall.org", label: "Ritu Bahl (Executive Director)", role: "admin" },
  { email: "gary.larson@computingforall.org", label: "Gary Larson (Technical Lead)", role: "admin" },
  { email: "jason@computingforall.org", label: "Jason (BD)", role: "staff" },
  { email: "jessica@computingforall.org", label: "Jessica (Marketing)", role: "staff" },
  { email: "krista@computingforall.org", label: "Krista", role: "staff" },
  { email: "bethany@computingforall.org", label: "Bethany", role: "staff" },
  { email: "leslie@computingforall.org", label: "Leslie", role: "staff" },
  { email: "alma@borderplex.workforce", label: "Alma (WSB — workforce-dev director)", role: "workforce-development" },
]

interface MeResponse {
  email: string
  role: string
  tenant_id: string | null
}

function DevLoginContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const nextUrl = searchParams.get("next") || "/"

  const [selectedEmail, setSelectedEmail] = useState<string>(ALLOWLISTED[0].email)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [current, setCurrent] = useState<MeResponse | null>(null)
  const [checkedMe, setCheckedMe] = useState(false)

  // On mount, fetch /auth/me so we can show "currently signed in as X"
  useEffect(() => {
    let cancelled = false
    fetch("/auth/me", { credentials: "include" })
      .then(async (r) => {
        if (cancelled) return
        if (r.ok) {
          const body = (await r.json()) as MeResponse
          setCurrent(body)
        } else {
          setCurrent(null)
        }
      })
      .catch(() => {
        if (!cancelled) setCurrent(null)
      })
      .finally(() => {
        if (!cancelled) setCheckedMe(true)
      })
    return () => { cancelled = true }
  }, [])

  const signIn = useCallback(async () => {
    setSubmitting(true)
    setError(null)
    try {
      const r = await fetch(
        `/auth/dev-login?email=${encodeURIComponent(selectedEmail)}`,
        { credentials: "include" },
      )
      if (!r.ok) {
        const body = await r.json().catch(() => ({}))
        const msg =
          (body as { error?: { message?: string }; detail?: string })?.error
            ?.message ||
          (body as { detail?: string })?.detail ||
          `HTTP ${r.status}`
        throw new Error(msg)
      }
      // Cookie is set; bounce to where the user was trying to go.
      router.push(nextUrl)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
      setSubmitting(false)
    }
  }, [selectedEmail, nextUrl, router])

  const signOut = useCallback(async () => {
    try {
      await fetch("/auth/logout", { method: "POST", credentials: "include" })
    } catch {
      // even if logout fails server-side, clear local view
    }
    setCurrent(null)
  }, [])

  const grouped = groupByRole(ALLOWLISTED)

  return (
    <main className="mx-auto max-w-xl px-4 py-10">
      <div className="mb-4 flex items-center gap-2 rounded-md border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-900">
        <AlertTriangle className="h-4 w-4 flex-shrink-0" />
        <span>
          <strong>Dev-mode sign-in.</strong> Skips the magic-link email flow —
          only active while <code>DEV_AUTH_BYPASS=1</code>. Disable before any
          production deploy.
        </span>
      </div>

      <Card className="p-6">
        <h1 className="text-xl font-semibold tracking-tight">Sign in (dev)</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Pick a user and hit Sign in. A session cookie is issued; all gated
          services (LaborPulse, BD dashboard, anything behind{" "}
          <code>@llm_gated</code>) accept it.
        </p>

        {/* Currently signed in */}
        {checkedMe && current ? (
          <div className="mt-5 flex items-center justify-between rounded-md border bg-muted/30 px-3 py-2 text-sm">
            <div className="flex items-center gap-2">
              <User className="h-4 w-4 text-muted-foreground" />
              <span>
                Signed in as <strong>{current.email}</strong>
                <span className="ml-2 rounded bg-muted px-1.5 py-0.5 text-xs text-muted-foreground">
                  {current.role}
                </span>
              </span>
            </div>
            <Button variant="outline" size="sm" onClick={signOut} className="gap-1">
              <LogOut className="h-3 w-3" />
              Sign out
            </Button>
          </div>
        ) : null}

        <label className="mt-6 block text-sm font-medium text-foreground">
          User
        </label>
        <select
          className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
          value={selectedEmail}
          onChange={(e) => setSelectedEmail(e.target.value)}
          disabled={submitting}
        >
          {(Object.keys(grouped) as Array<keyof typeof grouped>).map((role) => (
            <optgroup key={role} label={formatRoleLabel(role)}>
              {grouped[role].map((u) => (
                <option key={u.email} value={u.email}>
                  {u.label} — {u.email}
                </option>
              ))}
            </optgroup>
          ))}
        </select>

        {error ? (
          <div className="mt-4 rounded-md border border-destructive/40 bg-destructive/5 p-3 text-sm text-destructive">
            {error}
          </div>
        ) : null}

        <Button
          className="mt-6 w-full"
          onClick={signIn}
          disabled={submitting}
        >
          {submitting ? (
            <span className="flex items-center gap-2">Signing in…</span>
          ) : (
            <span className="flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4" />
              Sign in as {summaryOf(selectedEmail)}
            </span>
          )}
        </Button>

        <p className="mt-4 text-xs text-muted-foreground">
          On success you'll redirect to{" "}
          <code className="text-foreground">{nextUrl}</code>. Append{" "}
          <code className="text-foreground">?next=/some/path</code> to come
          back to a specific page after sign-in.
        </p>
      </Card>
    </main>
  )
}

function groupByRole(users: AllowlistedUser[]) {
  const out: Record<AllowlistedUser["role"], AllowlistedUser[]> = {
    admin: [],
    staff: [],
    "workforce-development": [],
    student: [],
  }
  for (const u of users) out[u.role].push(u)
  return out
}

function formatRoleLabel(role: AllowlistedUser["role"]): string {
  const map: Record<AllowlistedUser["role"], string> = {
    admin: "Admin",
    staff: "CFA Staff",
    "workforce-development": "Workforce Development (external)",
    student: "Student",
  }
  return map[role] ?? role
}

function summaryOf(email: string): string {
  const u = ALLOWLISTED.find((x) => x.email === email)
  return u?.label ?? email
}

export default function DevLoginPage() {
  return (
    <Suspense fallback={<div className="p-10 text-sm text-muted-foreground">Loading…</div>}>
      <DevLoginContent />
    </Suspense>
  )
}
