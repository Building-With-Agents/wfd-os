import { ArrowRight } from "lucide-react"
import { JobMatchCard } from "./job-match-card"
import type { JobMatch } from "@/lib/api"

const COMPANY_COLORS = ["#6366f1", "#0ea5e9", "#10b981", "#f59e0b", "#ef4444"]

interface JobMatchesSectionProps {
  matches: JobMatch[]
  /** Click a card → open the gap-detail modal keyed by the clicked job's id.
   *  Passed from the student portal page; when undefined the cards render
   *  non-clickable (backward-compatible with the previous display-only UX). */
  onCardClick?: (jobId: string) => void
}

export function JobMatchesSection({ matches, onCardClick }: JobMatchesSectionProps) {
  if (matches.length === 0) {
    return (
      <section className="rounded-lg border bg-card p-8 text-center">
        <h2 className="text-xl font-semibold text-foreground">No job matches yet</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          Complete your profile and add more skills to see job matches
        </p>
      </section>
    )
  }

  return (
    <section className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-semibold text-foreground sm:text-2xl">
            Your top job matches
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Based on your skills, experience, and preferences
          </p>
        </div>
        <a
          href="#"
          className="flex items-center gap-1 text-sm font-medium text-primary transition-colors hover:text-primary/80"
        >
          View all matches
          <ArrowRight className="h-4 w-4" />
        </a>
      </div>

      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
        {matches.map((match, i) => {
          const company = match.company || match.title
          const initials = company
            .split(" ")
            .map((w) => w[0])
            .join("")
            .toUpperCase()
            .slice(0, 2)

          const location = [match.city, match.state].filter(Boolean).join(", ") || "Location TBD"

          const salaryRange =
            match.salary_min && match.salary_max
              ? `$${Math.round(match.salary_min / 1000)}K - $${Math.round(match.salary_max / 1000)}K`
              : match.salary_min
                ? `From $${Math.round(match.salary_min / 1000)}K`
                : null

          const card = (
            <JobMatchCard
              key={match.job_id}
              job={{
                id: match.job_id,
                title: match.title,
                company: company,
                companyInitials: initials,
                companyColor: COMPANY_COLORS[i % COMPANY_COLORS.length],
                location: location,
                matchScore: Math.round(match.match_score),
                matchingSkills: match.matched_skills,
                missingSkills: match.missing_skills,
                salaryRange: salaryRange || "Salary not listed",
                postedDaysAgo: 0,
                isNew: i === 0,
              }}
            />
          )
          if (!onCardClick) return card
          return (
            <button
              key={match.job_id}
              type="button"
              onClick={() => onCardClick(match.job_id)}
              className="text-left transition-transform focus:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2"
              aria-label={`Open detail for ${match.title}`}
            >
              {card}
            </button>
          )
        })}
      </div>
    </section>
  )
}
