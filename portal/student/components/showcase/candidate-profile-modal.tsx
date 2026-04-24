"use client"
import { apiFetch } from "@/lib/fetch"

import { useEffect, useState } from "react"
import {
  MapPin, GraduationCap, Briefcase, Mail, ExternalLink,
  Shield, Calendar, Award, X, Compass, Linkedin, Github, Globe,
} from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog"
import { Separator } from "@/components/ui/separator"

const API_BASE = "/api"

const TRACK_LABELS: Record<string, string> = {
  ojt: "OJT Track",
  direct_placement: "Direct Placement",
  digital_skills: "Digital Skills",
}

const TRACK_COLORS: Record<string, string> = {
  ojt: "bg-violet-100 text-violet-800 border-violet-200",
  direct_placement: "bg-teal-100 text-teal-800 border-teal-200",
  digital_skills: "bg-amber-100 text-amber-800 border-amber-200",
}

const SKILL_CATEGORY_COLORS: Record<string, string> = {
  "Programming Languages": "bg-blue-50 text-blue-700 border-blue-200",
  "Cloud & Infrastructure": "bg-purple-50 text-purple-700 border-purple-200",
  "Data & Analytics": "bg-emerald-50 text-emerald-700 border-emerald-200",
  "Tools & Frameworks": "bg-orange-50 text-orange-700 border-orange-200",
  "Other Skills": "bg-slate-50 text-slate-700 border-slate-200",
}

interface CandidateDetail {
  id: string
  first_name: string
  last_initial: string
  display_name: string
  location: string
  availability: string
  track: string
  profile_completeness: number
  parse_confidence: number
  skills_grouped: Record<string, string[]>
  total_skills: number
  education: {
    primary: {
      institution: string | null
      degree: string | null
      field_of_study: string | null
      graduation_year: number | null
    }
    records: any[]
  }
  work_experience: {
    title: string | null
    company_type: string
    duration: string
    is_current: boolean
    start_date: string | null
    end_date: string | null
  }[]
  certifications: string[]
  career_objective: string | null
  best_match: { role: string; gap_score: number | null } | null
  linkedin_url: string | null
  github_url: string | null
  portfolio_url: string | null
  last_updated: string | null
  resume_verified: boolean
  contact: {
    method: string
    email: string
    subject: string
    body: string
  }
}

function MatchScoreRing({ score, size = "lg" }: { score: number; size?: "sm" | "lg" }) {
  const radius = size === "lg" ? 36 : 20
  const svgSize = size === "lg" ? 88 : 56
  const strokeWidth = size === "lg" ? 5 : 4
  const circumference = 2 * Math.PI * radius
  const offset = circumference - (score / 100) * circumference
  const color = score >= 80 ? "#10b981" : score >= 60 ? "#f59e0b" : "#6366f1"
  const fontSize = size === "lg" ? "text-lg" : "text-xs"

  return (
    <div className="relative flex-shrink-0" style={{ width: svgSize, height: svgSize }}>
      <svg className="-rotate-90 transform" width={svgSize} height={svgSize}>
        <circle cx={svgSize / 2} cy={svgSize / 2} r={radius} stroke="#e2e8f0" strokeWidth={strokeWidth} fill="none" />
        <circle
          cx={svgSize / 2} cy={svgSize / 2} r={radius}
          stroke={color} strokeWidth={strokeWidth} fill="none" strokeLinecap="round"
          style={{ strokeDasharray: circumference, strokeDashoffset: offset, transition: "stroke-dashoffset 0.8s ease-out" }}
        />
      </svg>
      <span className={`absolute inset-0 flex items-center justify-center font-bold ${fontSize}`} style={{ color }}>
        {score}%
      </span>
    </div>
  )
}

function ContactCTA({ candidate }: { candidate: CandidateDetail }) {
  const mailtoUrl = `mailto:${candidate.contact.email}?subject=${encodeURIComponent(candidate.contact.subject)}&body=${encodeURIComponent(candidate.contact.body)}`

  return (
    <div className="rounded-lg border border-primary/20 bg-primary/5 p-4">
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="font-semibold text-foreground">
            Hire {candidate.first_name} through CFA
          </p>
          <p className="text-sm text-muted-foreground">
            All contact is facilitated by Computing for All
          </p>
        </div>
        <a href={mailtoUrl}>
          <Button className="gap-2">
            <Mail className="h-4 w-4" />
            Contact CFA
          </Button>
        </a>
      </div>
    </div>
  )
}

interface CandidateProfileModalProps {
  candidateId: string | null
  open: boolean
  onClose: () => void
}

export function CandidateProfileModal({ candidateId, open, onClose }: CandidateProfileModalProps) {
  const [candidate, setCandidate] = useState<CandidateDetail | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!candidateId || !open) return

    setLoading(true)
    setError(null)

    apiFetch(`${API_BASE}/showcase/candidates/${candidateId}`)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        return res.json()
      })
      .then(setCandidate)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [candidateId, open])

  const completionPct = Math.round((candidate?.profile_completeness || 0) * 100)

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-h-[90vh] max-w-2xl overflow-y-auto p-0">
        <DialogTitle className="sr-only">
          {candidate ? `Candidate profile: ${candidate.first_name} ${candidate.last_name}` : "Candidate profile"}
        </DialogTitle>
        {loading && (
          <div className="flex items-center justify-center py-20">
            <div className="h-10 w-10 animate-spin rounded-full border-4 border-primary border-t-transparent" />
          </div>
        )}

        {error && (
          <div className="p-8 text-center">
            <p className="text-destructive">Failed to load profile: {error}</p>
            <Button variant="outline" className="mt-3" onClick={onClose}>Close</Button>
          </div>
        )}

        {candidate && !loading && (
          <>
            {/* Header */}
            <div className="border-b bg-gradient-to-r from-primary/5 to-primary/10 p-6">
              <div className="flex items-start gap-4">
                <div className="flex h-16 w-16 flex-shrink-0 items-center justify-center rounded-full bg-primary text-xl font-bold text-primary-foreground shadow-lg">
                  {candidate.first_name[0]}
                </div>
                <div className="min-w-0 flex-1">
                  <h2 className="text-2xl font-bold text-foreground">{candidate.display_name}</h2>
                  <div className="mt-1 flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
                    <span className="flex items-center gap-1">
                      <MapPin className="h-4 w-4" />
                      {candidate.location}
                    </span>
                    <span className="flex items-center gap-1 text-green-600">
                      <span className="h-2 w-2 rounded-full bg-green-500" />
                      {candidate.availability}
                    </span>
                    <Badge className={TRACK_COLORS[candidate.track] || "bg-slate-100"}>
                      {TRACK_LABELS[candidate.track] || candidate.track}
                    </Badge>
                  </div>
                  {/* Social links */}
                  <div className="mt-2 flex gap-2">
                    {candidate.linkedin_url && (
                      <a href={candidate.linkedin_url} target="_blank" rel="noopener noreferrer" className="text-muted-foreground hover:text-primary">
                        <Linkedin className="h-4 w-4" />
                      </a>
                    )}
                    {candidate.github_url && (
                      <a href={candidate.github_url} target="_blank" rel="noopener noreferrer" className="text-muted-foreground hover:text-primary">
                        <Github className="h-4 w-4" />
                      </a>
                    )}
                    {candidate.portfolio_url && (
                      <a href={candidate.portfolio_url} target="_blank" rel="noopener noreferrer" className="text-muted-foreground hover:text-primary">
                        <Globe className="h-4 w-4" />
                      </a>
                    )}
                  </div>
                </div>
                <MatchScoreRing score={completionPct} size="lg" />
              </div>

              {/* Contact CTA */}
              <div className="mt-4">
                <ContactCTA candidate={candidate} />
              </div>
            </div>

            <div className="space-y-6 p-6">
              {/* Career Objective */}
              {candidate.career_objective && (
                <section>
                  <h3 className="mb-2 text-sm font-semibold uppercase tracking-wider text-muted-foreground">About</h3>
                  <p className="text-sm leading-relaxed text-foreground">{candidate.career_objective}</p>
                </section>
              )}

              {/* Best Match */}
              {candidate.best_match && (
                <div className="flex items-center gap-3 rounded-lg border bg-muted/30 p-3">
                  <Briefcase className="h-5 w-5 text-primary" />
                  <div>
                    <p className="text-sm font-medium text-foreground">Best match: {candidate.best_match.role}</p>
                    {candidate.best_match.gap_score != null && (
                      <p className="text-xs text-muted-foreground">Gap score: {candidate.best_match.gap_score}%</p>
                    )}
                  </div>
                </div>
              )}

              <Separator />

              {/* Skills */}
              <section>
                <h3 className="mb-3 text-sm font-semibold uppercase tracking-wider text-muted-foreground">
                  Verified Skills ({candidate.total_skills})
                </h3>
                <div className="space-y-3">
                  {Object.entries(candidate.skills_grouped).map(([category, skills]) => (
                    <div key={category}>
                      <p className="mb-1.5 text-xs font-medium text-muted-foreground">{category}</p>
                      <div className="flex flex-wrap gap-1.5">
                        {skills.map((skill) => (
                          <Badge
                            key={skill}
                            variant="outline"
                            className={`text-xs ${SKILL_CATEGORY_COLORS[category] || "bg-slate-50 text-slate-700 border-slate-200"}`}
                          >
                            {skill}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </section>

              <Separator />

              {/* Education */}
              <section>
                <h3 className="mb-3 text-sm font-semibold uppercase tracking-wider text-muted-foreground">Education</h3>
                {candidate.education.primary.institution ? (
                  <div className="flex items-start gap-3">
                    <GraduationCap className="mt-0.5 h-5 w-5 text-muted-foreground" />
                    <div>
                      <p className="font-medium text-foreground">
                        {candidate.education.primary.degree}
                        {candidate.education.primary.field_of_study
                          ? ` in ${candidate.education.primary.field_of_study}`
                          : ""}
                      </p>
                      <p className="text-sm text-muted-foreground">
                        {candidate.education.primary.institution}
                        {candidate.education.primary.graduation_year
                          ? ` (${candidate.education.primary.graduation_year})`
                          : ""}
                      </p>
                    </div>
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground italic">Education details being verified</p>
                )}
              </section>

              {/* Certifications */}
              {candidate.certifications.length > 0 && (
                <>
                  <Separator />
                  <section>
                    <h3 className="mb-3 text-sm font-semibold uppercase tracking-wider text-muted-foreground">
                      Certifications
                    </h3>
                    <div className="space-y-2">
                      {candidate.certifications.map((cert, i) => (
                        <div key={i} className="flex items-center gap-2 text-sm">
                          <Award className="h-4 w-4 text-amber-500" />
                          <span className="text-foreground">{cert}</span>
                        </div>
                      ))}
                    </div>
                  </section>
                </>
              )}

              {/* Work Experience */}
              {candidate.work_experience.length > 0 && (
                <>
                  <Separator />
                  <section>
                    <h3 className="mb-3 text-sm font-semibold uppercase tracking-wider text-muted-foreground">
                      Work Experience
                    </h3>
                    <div className="space-y-4">
                      {candidate.work_experience.map((exp, i) => (
                        <div key={i} className="flex items-start gap-3">
                          <div className="mt-1 flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-md bg-muted">
                            <Briefcase className="h-4 w-4 text-muted-foreground" />
                          </div>
                          <div>
                            <p className="font-medium text-foreground">{exp.title || "Role"}</p>
                            <p className="text-sm text-muted-foreground">{exp.company_type}</p>
                            <div className="flex items-center gap-2 text-xs text-muted-foreground">
                              <Calendar className="h-3 w-3" />
                              <span>{exp.duration}</span>
                              {exp.is_current && (
                                <Badge variant="secondary" className="text-xs">Current</Badge>
                              )}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </section>
                </>
              )}

              <Separator />

              {/* Bottom CTA */}
              <ContactCTA candidate={candidate} />

              {/* Footer */}
              <div className="rounded-lg bg-muted/30 p-4 text-center text-xs text-muted-foreground">
                <div className="flex items-center justify-center gap-1.5">
                  <Shield className="h-3.5 w-3.5" />
                  <span>Profile verified by Computing for All</span>
                </div>
                {candidate.last_updated && (
                  <p className="mt-1">
                    Last updated: {new Date(candidate.last_updated).toLocaleDateString()}
                  </p>
                )}
                <p className="mt-1">
                  All contact happens through CFA. {candidate.first_name}&apos;s privacy is protected.
                </p>
              </div>
            </div>
          </>
        )}
      </DialogContent>
    </Dialog>
  )
}
