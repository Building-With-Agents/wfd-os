"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { Compass, GraduationCap, ArrowLeft, ArrowRight, Mail } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card } from "@/components/ui/card"

export default function CollegeLoginPage() {
  const router = useRouter()
  const [token, setToken] = useState("")
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!token.trim()) {
      setError("Please enter your access code")
      return
    }
    router.push(`/college?token=${encodeURIComponent(token.trim())}`)
  }

  return (
    <div className="flex min-h-screen flex-col bg-background">
      {/* Header */}
      <header className="border-b border-border bg-card">
        <div className="mx-auto flex max-w-4xl items-center justify-between px-4 py-3 sm:px-6">
          <a href="/" className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground">
            <ArrowLeft className="h-4 w-4" /> Computing for All
          </a>
          <div className="flex items-center gap-2">
            <Compass className="h-5 w-5 text-primary" />
            <span className="font-semibold text-foreground">College Partner Portal</span>
          </div>
        </div>
      </header>

      {/* Main */}
      <main className="flex flex-1 items-center justify-center px-4 py-16">
        <Card className="w-full max-w-md p-8">
          <div className="mb-6 text-center">
            <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-xl bg-blue-100">
              <GraduationCap className="h-7 w-7 text-blue-600" />
            </div>
            <h1 className="text-2xl font-bold text-foreground">College Partner Access</h1>
            <p className="mt-2 text-sm text-muted-foreground">
              Enter your institution access code to view your career services dashboard
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="mb-1 block text-sm font-medium text-foreground">
                Institution access code
              </label>
              <Input
                value={token}
                onChange={e => { setToken(e.target.value); setError(null) }}
                placeholder="e.g. bc-001"
                className={error ? "border-destructive" : ""}
              />
              {error && <p className="mt-1 text-xs text-destructive">{error}</p>}
            </div>

            <Button type="submit" className="w-full gap-2">
              Access dashboard <ArrowRight className="h-4 w-4" />
            </Button>
          </form>

          <div className="mt-6 rounded-lg bg-muted/50 p-4 text-center">
            <p className="text-xs text-muted-foreground">
              Don&apos;t have an access code? Contact CFA to register your institution.
            </p>
            <a href="mailto:ritu@computingforall.org?subject=College Partner Portal access request">
              <Button variant="link" size="sm" className="mt-1 gap-1 text-xs">
                <Mail className="h-3.5 w-3.5" /> Request access
              </Button>
            </a>
          </div>
        </Card>
      </main>

      <footer className="border-t border-border bg-card py-4">
        <div className="mx-auto max-w-4xl px-4 text-center text-xs text-muted-foreground">
          &copy; 2026 Computing for All | computingforall.org
        </div>
      </footer>
    </div>
  )
}
