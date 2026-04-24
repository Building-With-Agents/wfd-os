"use client"
import { apiFetch } from "@/lib/fetch"

import { useEffect, useState, useCallback } from "react"
import { Search, MapPin, GraduationCap, Briefcase, Star, Filter, ChevronDown, Compass, ExternalLink } from "lucide-react"
import { CandidateProfileModal } from "@/components/showcase/candidate-profile-modal"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import NewsletterSubscribe from "@/components/newsletter-subscribe"

interface Candidate {
  id: string
  first_name: string
  last_initial: string
  display_name: string
  location: string
  availability: string
  track: string
  profile_completeness: number
  parse_confidence: number
  top_skills: string[]
  total_skills: number
  education: {
    institution: string | null
    degree: string | null
    field_of_study: string | null
    graduation_year: number | null
  }
  top_match: {
    role: string
    gap_score: number | null
  } | null
}

interface FilterOption {
  name: string
  count: number
}

const API_BASE = "/api"

const TRACK_LABELS: Record<string, string> = {
  ojt: "OJT Track",
  direct_placement: "Direct Placement",
  digital_skills: "Digital Skills",
}

const TRACK_COLORS: Record<string, string> = {
  ojt: "bg-violet-100 text-violet-800",
  direct_placement: "bg-teal-100 text-teal-800",
  digital_skills: "bg-amber-100 text-amber-800",
}

function MatchScoreRing({ score }: { score: number }) {
  const radius = 20
  const circumference = 2 * Math.PI * radius
  const offset = circumference - (score / 100) * circumference
  const color = score >= 80 ? "#10b981" : score >= 60 ? "#f59e0b" : "#6366f1"

  return (
    <div className="relative h-14 w-14 flex-shrink-0">
      <svg className="h-14 w-14 -rotate-90 transform">
        <circle cx="28" cy="28" r={radius} stroke="#e2e8f0" strokeWidth="4" fill="none" />
        <circle
          cx="28" cy="28" r={radius}
          stroke={color} strokeWidth="4" fill="none" strokeLinecap="round"
          style={{ strokeDasharray: circumference, strokeDashoffset: offset, transition: "stroke-dashoffset 0.5s" }}
        />
      </svg>
      <span className="absolute inset-0 flex items-center justify-center text-xs font-bold" style={{ color }}>
        {score}%
      </span>
    </div>
  )
}

function CandidateCard({ candidate, onViewProfile }: { candidate: Candidate; onViewProfile: (id: string) => void }) {
  const completionPct = Math.round(candidate.profile_completeness * 100)

  return (
    <Card className="overflow-hidden transition-shadow hover:shadow-lg">
      <div className="p-5">
        {/* Header: Name + Score */}
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full bg-primary text-sm font-semibold text-primary-foreground">
                {candidate.first_name[0]}
              </div>
              <div className="min-w-0">
                <h3 className="truncate text-base font-semibold text-foreground">
                  {candidate.display_name}
                </h3>
                <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                  <MapPin className="h-3 w-3 flex-shrink-0" />
                  <span className="truncate">{candidate.location}</span>
                </div>
              </div>
            </div>
          </div>
          <MatchScoreRing score={completionPct} />
        </div>

        {/* Education */}
        {candidate.education.institution && (
          <div className="mt-3 flex items-start gap-2 text-sm text-muted-foreground">
            <GraduationCap className="mt-0.5 h-4 w-4 flex-shrink-0" />
            <div className="min-w-0">
              <span className="font-medium text-foreground">
                {candidate.education.degree}
                {candidate.education.field_of_study ? ` in ${candidate.education.field_of_study}` : ""}
              </span>
              <br />
              <span className="truncate text-xs">{candidate.education.institution}</span>
              {candidate.education.graduation_year && (
                <span className="text-xs"> ({candidate.education.graduation_year})</span>
              )}
            </div>
          </div>
        )}

        {/* Skills */}
        <div className="mt-3">
          <div className="flex flex-wrap gap-1.5">
            {candidate.top_skills.map((skill, i) => (
              <Badge key={`${skill}-${i}`} variant="secondary" className="text-xs">
                {skill}
              </Badge>
            ))}
            {candidate.total_skills > 5 && (
              <Badge variant="outline" className="text-xs text-muted-foreground">
                +{candidate.total_skills - 5} more
              </Badge>
            )}
          </div>
        </div>

        {/* Top Match */}
        {candidate.top_match && (
          <div className="mt-3 rounded-md bg-muted/50 px-3 py-2 text-xs">
            <div className="flex items-center gap-1.5 text-muted-foreground">
              <Briefcase className="h-3 w-3" />
              <span>Best match: <span className="font-medium text-foreground">{candidate.top_match.role}</span></span>
            </div>
          </div>
        )}

        {/* Footer: Track + Availability + Action */}
        <div className="mt-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Badge className={`text-xs ${TRACK_COLORS[candidate.track] || "bg-slate-100 text-slate-800"}`}>
              {TRACK_LABELS[candidate.track] || candidate.track}
            </Badge>
            <span className="flex items-center gap-1 text-xs text-green-600">
              <span className="h-1.5 w-1.5 rounded-full bg-green-500" />
              {candidate.availability}
            </span>
          </div>
          <Button size="sm" variant="outline" className="gap-1 text-xs" onClick={() => onViewProfile(candidate.id)}>
            View Profile
            <ExternalLink className="h-3 w-3" />
          </Button>
        </div>
      </div>
    </Card>
  )
}

interface InitialData { candidates: any[]; total: number; skills: any[]; locations: any[] }

export default function TalentShowcase({ initialData }: { initialData?: InitialData }) {
  const [candidates, setCandidates] = useState<Candidate[]>(initialData?.candidates || [])
  const [filterSkills, setFilterSkills] = useState<FilterOption[]>(initialData?.skills || [])
  const [filterLocations, setFilterLocations] = useState<{ label: string; count: number }[]>(initialData?.locations || [])
  const [loading, setLoading] = useState(!initialData)
  const [error, setError] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState("")
  const [selectedSkill, setSelectedSkill] = useState<string>("")
  const [selectedLocation, setSelectedLocation] = useState<string>("")
  const [total, setTotal] = useState(initialData?.total || 0)
  const [selectedCandidateId, setSelectedCandidateId] = useState<string | null>(null)

  const loadCandidates = useCallback(async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams()
      params.set("limit", "50")
      if (selectedSkill && selectedSkill !== "all") params.set("skill", selectedSkill)
      if (selectedLocation && selectedLocation !== "all") params.set("location", selectedLocation)

      const res = await apiFetch(`${API_BASE}/showcase/candidates?${params}`)
      const data = await res.json()
      setCandidates(data.candidates)
      setTotal(data.total)
    } catch (err: any) {
      setError(`Failed to load: ${err.message}`)
    } finally {
      setLoading(false)
    }
  }, [selectedSkill, selectedLocation])

  const loadFilters = useCallback(async () => {
    try {
      const res = await apiFetch(`${API_BASE}/showcase/filters`)
      const data = await res.json()
      setFilterSkills(data.skills)
      setFilterLocations(data.locations)
    } catch {}
  }, [])

  useEffect(() => {
    if (initialData) return
    loadFilters()
    loadCandidates()
  }, [loadFilters, loadCandidates])

  // Client-side search filter
  const filtered = searchQuery
    ? candidates.filter(
        (c) =>
          c.display_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
          c.top_skills.some((s) => s.toLowerCase().includes(searchQuery.toLowerCase())) ||
          (c.education.field_of_study || "").toLowerCase().includes(searchQuery.toLowerCase())
      )
    : candidates

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border bg-card">
        <div className="mx-auto max-w-7xl px-4 py-5 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-primary shadow-lg shadow-primary/25">
                <Compass className="h-6 w-6 text-primary-foreground" />
              </div>
              <div>
                <span className="text-xl font-bold text-foreground tracking-tight">Waifinder</span>
                <span className="ml-2 text-sm text-muted-foreground">Talent Showcase</span>
              </div>
            </div>
            <div className="text-right hidden sm:block">
              <div className="text-sm font-medium text-foreground">Washington Tech Workforce Coalition</div>
              <div className="text-xs text-muted-foreground">Powered by Computing for All</div>
            </div>
          </div>

          <div className="mt-4">
            <h1 className="text-2xl font-semibold text-foreground sm:text-3xl">Discover Tech Talent</h1>
            <p className="mt-1 text-muted-foreground">
              {total} pre-vetted candidates ready for your tech roles
            </p>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
        {/* Search + Filters */}
        <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Search by name, skill, or field of study..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10"
            />
          </div>
          <div className="flex gap-2">
            <Select value={selectedSkill} onValueChange={(v) => setSelectedSkill(v)}>
              <SelectTrigger className="w-[180px]">
                <Filter className="mr-2 h-4 w-4" />
                <SelectValue placeholder="Filter by skill" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All skills</SelectItem>
                {filterSkills.slice(0, 15).map((s) => (
                  <SelectItem key={s.name} value={s.name}>
                    {s.name} ({s.count})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select value={selectedLocation} onValueChange={(v) => setSelectedLocation(v)}>
              <SelectTrigger className="w-[180px]">
                <MapPin className="mr-2 h-4 w-4" />
                <SelectValue placeholder="Filter by location" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All locations</SelectItem>
                {filterLocations.map((l) => (
                  <SelectItem key={l.label} value={l.label}>
                    {l.label} ({l.count})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        {/* Stats bar */}
        <div className="mb-4 flex items-center justify-between text-sm text-muted-foreground">
          <span>Showing {filtered.length} of {total} candidates</span>
          <div className="flex items-center gap-4">
            <span className="flex items-center gap-1">
              <Star className="h-3.5 w-3.5 text-amber-500" />
              Top skills: Python (67), Java (60), SQL (40)
            </span>
          </div>
        </div>

        {/* Error state */}
        {error && (
          <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-6 text-center">
            <p className="text-destructive">{error}</p>
            <Button variant="outline" className="mt-3" onClick={loadCandidates}>
              Retry
            </Button>
          </div>
        )}

        {/* Loading state */}
        {loading && (
          <div className="flex items-center justify-center py-20">
            <div className="text-center">
              <div className="mx-auto mb-4 h-10 w-10 animate-spin rounded-full border-4 border-primary border-t-transparent" />
              <p className="text-muted-foreground">Loading candidates...</p>
            </div>
          </div>
        )}

        {/* Candidate Grid */}
        {!loading && !error && (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {filtered.map((candidate) => (
              <CandidateCard key={candidate.id} candidate={candidate} onViewProfile={setSelectedCandidateId} />
            ))}
          </div>
        )}

        {/* Empty state */}
        {!loading && !error && filtered.length === 0 && (
          <div className="py-20 text-center">
            <p className="text-lg text-muted-foreground">No candidates match your filters</p>
            <Button
              variant="outline"
              className="mt-3"
              onClick={() => {
                setSearchQuery("")
                setSelectedSkill("")
                setSelectedLocation("")
              }}
            >
              Clear filters
            </Button>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-border bg-card py-4">
        <NewsletterSubscribe />
        <div className="mx-auto max-w-7xl px-6 text-center text-xs text-muted-foreground">
          Waifinder Talent Showcase by Computing for All | thewaifinder.com
        </div>
      </footer>

      {/* Profile Modal */}
      <CandidateProfileModal
        candidateId={selectedCandidateId}
        open={!!selectedCandidateId}
        onClose={() => setSelectedCandidateId(null)}
      />
    </div>
  )
}
