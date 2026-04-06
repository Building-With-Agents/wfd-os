"use client"

import { useState } from "react"
import { X, PartyPopper, TrendingUp } from "lucide-react"

interface CongratulationsBannerProps {
  achievement: string
  improvement?: string
}

export function CongratulationsBanner({ achievement, improvement }: CongratulationsBannerProps) {
  const [isDismissed, setIsDismissed] = useState(false)

  if (isDismissed) return null

  return (
    <div className="relative overflow-hidden rounded-xl bg-gradient-to-r from-primary/15 via-secondary/15 to-accent/15 border border-primary/20 p-4">
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/20">
            <PartyPopper className="h-5 w-5 text-primary" />
          </div>
          <div>
            <p className="font-semibold text-foreground">
              Congratulations! {achievement}
            </p>
            {improvement && (
              <p className="text-sm text-muted-foreground flex items-center gap-1">
                <TrendingUp className="h-3 w-3 text-success" />
                {improvement}
              </p>
            )}
          </div>
        </div>
        <button
          onClick={() => setIsDismissed(true)}
          className="flex-shrink-0 rounded-full p-1 text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
        >
          <X className="h-4 w-4" />
        </button>
      </div>
      {/* Decorative elements */}
      <div className="absolute -right-4 -top-4 h-24 w-24 rounded-full bg-primary/10 blur-2xl" />
      <div className="absolute -bottom-4 -left-4 h-16 w-16 rounded-full bg-secondary/10 blur-xl" />
    </div>
  )
}
