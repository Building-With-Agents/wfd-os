"use client"
import { apiFetch } from "@/lib/fetch"

import { useState } from "react"
import { Download, Lock, CheckCircle2 } from "lucide-react"

export default function GatedDownload({ slug, title, pdfUrl }: { slug: string; title: string; pdfUrl: string }) {
  const [name, setName] = useState("")
  const [email, setEmail] = useState("")
  const [submitting, setSubmitting] = useState(false)
  const [open, setOpen] = useState(false)

  const handleSubmit = async () => {
    if (!name.trim() || !email.trim()) return
    setSubmitting(true)
    try {
      await apiFetch("/api/marketing/leads", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, email, content_id: slug, content_title: title, content_type: "research" }),
      })
    } catch { /* still open the gate */ }
    setOpen(true)
    setSubmitting(false)
  }

  if (open) {
    return (
      <div className="rounded-xl border-2 border-purple-200 bg-purple-50 p-6 space-y-3 text-center">
        <CheckCircle2 className="mx-auto h-8 w-8 text-green-500" />
        <h3 className="font-bold text-foreground">Your report is ready!</h3>
        <a href={pdfUrl} target="_blank" rel="noopener noreferrer"
          className="inline-flex items-center gap-2 rounded-md bg-purple-600 px-4 py-2 text-sm font-medium text-white hover:bg-purple-700">
          <Download className="h-4 w-4" /> Download PDF
        </a>
        <p className="text-xs text-muted-foreground">Check your email for a copy as well.</p>
      </div>
    )
  }

  return (
    <div className="rounded-xl border-2 border-purple-200 bg-purple-50 p-6 space-y-4">
      <div className="flex items-center gap-2">
        <Lock className="h-5 w-5 text-purple-600" />
        <h3 className="font-bold text-foreground">Download the full report (PDF)</h3>
      </div>
      <p className="text-sm text-muted-foreground">Enter your name and email to access the complete PDF with charts, data tables, and methodology details.</p>
      <div className="grid gap-2 sm:grid-cols-2">
        <input placeholder="Your name" value={name} onChange={(e) => setName(e.target.value)}
          className="rounded-md border bg-white px-3 py-2 text-sm focus:border-purple-400 focus:outline-none focus:ring-1 focus:ring-purple-400" />
        <input type="email" placeholder="Work email" value={email} onChange={(e) => setEmail(e.target.value)}
          className="rounded-md border bg-white px-3 py-2 text-sm focus:border-purple-400 focus:outline-none focus:ring-1 focus:ring-purple-400" />
      </div>
      <button onClick={handleSubmit} disabled={!name.trim() || !email.trim() || submitting}
        className="w-full rounded-md bg-purple-600 px-4 py-2 text-sm font-medium text-white hover:bg-purple-700 disabled:opacity-50 flex items-center justify-center gap-2">
        {submitting ? "Processing..." : <><Download className="h-4 w-4" /> Download PDF</>}
      </button>
      <p className="text-[10px] text-muted-foreground text-center">We respect your privacy. No spam, ever.</p>
    </div>
  )
}
