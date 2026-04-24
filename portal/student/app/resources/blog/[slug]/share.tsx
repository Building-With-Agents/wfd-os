"use client"

import { Share2 } from "lucide-react"

export default function ShareButton() {
  return (
    <div className="flex items-center gap-3">
      <span className="text-sm font-medium text-muted-foreground">Share:</span>
      <button
        className="inline-flex items-center gap-1 rounded-md border px-3 py-1.5 text-xs font-medium hover:bg-muted"
        onClick={() => { if (typeof navigator !== "undefined") navigator.clipboard?.writeText(window.location.href) }}
      >
        <Share2 className="h-3 w-3" /> Copy link
      </button>
    </div>
  )
}
