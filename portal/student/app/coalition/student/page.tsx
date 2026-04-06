"use client"

import { useEffect, useState } from "react"
import { useSearchParams } from "next/navigation"
import { Suspense } from "react"
import { Header } from "@/components/dashboard/header"
import { CongratulationsBanner } from "@/components/dashboard/congratulations-banner"
import { JobMatchesSection } from "@/components/dashboard/job-matches-section"
import { JourneyPipeline } from "@/components/dashboard/journey-pipeline"
import { GapAnalysisPreview } from "@/components/dashboard/gap-analysis-preview"
import { ShowcaseStatus } from "@/components/dashboard/showcase-status"
import { AICareerNavigator } from "@/components/dashboard/ai-career-navigator"
import {
  fetchProfile,
  fetchMatches,
  fetchGapAnalysis,
  fetchJourney,
  fetchShowcase,
  type StudentProfile,
  type JobMatch,
  type GapAnalysis,
  type Journey,
  type Showcase,
} from "@/lib/api"

function DashboardContent() {
  const searchParams = useSearchParams()
  const studentId = searchParams.get("id")

  const [profile, setProfile] = useState<StudentProfile | null>(null)
  const [matches, setMatches] = useState<JobMatch[]>([])
  const [gap, setGap] = useState<GapAnalysis | null>(null)
  const [journey, setJourney] = useState<Journey | null>(null)
  const [showcase, setShowcase] = useState<Showcase | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!studentId) {
      setError("No student ID provided. Use ?id=<student-uuid> in the URL.")
      setLoading(false)
      return
    }

    async function loadData() {
      try {
        const [profileData, matchesData, gapData, journeyData, showcaseData] =
          await Promise.all([
            fetchProfile(studentId!),
            fetchMatches(studentId!),
            fetchGapAnalysis(studentId!),
            fetchJourney(studentId!),
            fetchShowcase(studentId!),
          ])
        setProfile(profileData)
        setMatches(matchesData.matches)
        setGap(gapData)
        setJourney(journeyData)
        setShowcase(showcaseData)
      } catch (err: any) {
        setError(
          `Failed to load dashboard: ${err.message}. Is the API running on localhost:8001?`
        )
      } finally {
        setLoading(false)
      }
    }
    loadData()
  }, [studentId])

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <div className="text-center">
          <div className="mx-auto mb-4 h-12 w-12 animate-spin rounded-full border-4 border-primary border-t-transparent" />
          <p className="text-muted-foreground">Loading your dashboard...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <div className="mx-auto max-w-md rounded-lg border bg-card p-8 text-center shadow-md">
          <h2 className="mb-2 text-lg font-semibold text-destructive">
            Connection Error
          </h2>
          <p className="text-sm text-muted-foreground">{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="mt-4 rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground hover:bg-primary/90"
          >
            Try again
          </button>
        </div>
      </div>
    )
  }

  if (!profile) return null

  // Derive first name for welcome message
  const firstName = profile.full_name.split(" ")[0]

  // Build gap analysis props from API data
  const skillGaps = (gap?.skill_gaps || []).map((sg) => ({
    skill: sg.skill,
    resource: sg.resource.title,
    provider: sg.resource.provider,
    duration: `${sg.resource.duration_hours}hrs`,
    link: sg.resource.url,
    isFree: sg.resource.is_free,
  }))

  // Build showcase items from API data
  const showcaseItems = (showcase?.checklist || []).map((item) => ({
    id: item.id,
    label: item.label,
    completed: item.completed,
    actionLink: item.action_link || undefined,
    actionLabel: item.action_label || undefined,
  }))

  // Build congratulations message
  const showCongrats = profile.resume_parsed
  const congratsAchievement = showCongrats
    ? "Your resume has been parsed successfully!"
    : undefined
  const congratsImprovement = showCongrats
    ? `Profile completeness: ${Math.round(profile.profile_completeness_score * 100)}%`
    : undefined

  // Top match info for gap analysis
  const topMatchJob = matches.length > 0
    ? `${matches[0].title}${matches[0].company ? ` at ${matches[0].company}` : ""}`
    : "No matches yet"

  return (
    <div className="min-h-screen bg-background">
      <Header
        studentName={firstName}
        profileCompletion={Math.round(profile.profile_completeness_score * 100)}
      />

      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <div className="space-y-8">
          {/* Congratulations Banner */}
          {showCongrats && congratsAchievement && (
            <CongratulationsBanner
              achievement={congratsAchievement}
              improvement={congratsImprovement}
            />
          )}

          {/* Job Matches Hero Section */}
          <JobMatchesSection matches={matches} />

          {/* Two Column Layout for smaller sections */}
          <div className="grid gap-8 lg:grid-cols-2">
            {/* Left Column */}
            <div className="space-y-8">
              {journey && (
                <JourneyPipeline
                  stages={journey.stages}
                  currentStage={journey.current_stage}
                  trackName={
                    journey.track === "ojt"
                      ? "OJT Track"
                      : "Direct Placement Track"
                  }
                  nextStep={journey.next_step}
                  studentName={profile.full_name}
                  cohort={journey.cohort || "Cohort 2025"}
                  estimatedTimeToNext={`~${journey.estimated_weeks_to_next} weeks to next stage`}
                />
              )}
              {showcase && (
                <ShowcaseStatus
                  isActive={showcase.showcase_active}
                  items={showcaseItems}
                  employerViews={showcase.employer_views}
                />
              )}
            </div>

            {/* Right Column */}
            <div>
              {gap && gap.has_analysis && (
                <GapAnalysisPreview
                  gapScore={gap.gap_score}
                  previousScore={Math.max(0, gap.gap_score - 8)}
                  topMatchJob={topMatchJob}
                  skillGaps={skillGaps}
                  totalHoursToClose={`~${gap.hours_to_close} hours`}
                  targetScore={90}
                />
              )}
              {gap && !gap.has_analysis && (
                <div className="rounded-lg border bg-card p-6 text-center">
                  <p className="text-muted-foreground">
                    Complete your profile to generate a gap analysis
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>
      </main>

      {/* AI Career Navigator */}
      <AICareerNavigator
        studentName={firstName}
        studentId={studentId || ""}
        newMatchCount={matches.length}
      />
    </div>
  )
}

export default function StudentDashboard() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center">
          <div className="h-12 w-12 animate-spin rounded-full border-4 border-primary border-t-transparent" />
        </div>
      }
    >
      <DashboardContent />
    </Suspense>
  )
}
