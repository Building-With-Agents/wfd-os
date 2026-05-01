import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { GraduationCap, Briefcase, Award, FileText } from "lucide-react"
import type { StudentProfile, WorkExperienceEntry } from "@/lib/api"

// Resume Summary card for the Student Portal. Assembled directly from
// parsed resume data (no LLM call). Shows:
//   - Career objective (if the resume had one)
//   - Education: degree/field @ institution with graduation year
//   - Work experience: most recent → earliest (3 shown; "+N more" if taller)
//   - Top 5 skills
//   - Certifications (if any)
// This is the "about this student" card Dinah (case manager) needs when
// she opens Fabian's portal — a quick read of who he is before drilling
// into job matches.

export interface ResumeSummaryProps {
  profile: StudentProfile
}

function formatDate(iso: string | null): string {
  if (!iso) return ""
  const [y, m] = iso.split("-")
  const monthNames = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
  ]
  const monthIdx = Number(m) - 1
  return `${monthNames[monthIdx] ?? ""} ${y}`.trim()
}

function formatRange(entry: WorkExperienceEntry): string {
  const start = formatDate(entry.start_date)
  const end = entry.is_current ? "Present" : formatDate(entry.end_date)
  if (!start && !end) return ""
  if (!end) return start
  return `${start} – ${end}`
}

export function ResumeSummary({ profile }: ResumeSummaryProps) {
  const work = profile.work_experience ?? []
  const shownWork = work.slice(0, 3)
  const extraWork = Math.max(0, work.length - shownWork.length)
  const skills = profile.skills ?? []
  const shownSkills = skills.slice(0, 8)
  const extraSkills = Math.max(0, skills.length - shownSkills.length)
  const certs = profile.certifications ?? []

  return (
    <Card className="p-6">
      <div className="mb-4 flex items-center gap-2">
        <FileText className="h-5 w-5 text-primary" />
        <h2 className="text-lg font-semibold">Resume Summary</h2>
      </div>

      {profile.career_objective ? (
        <p className="mb-6 text-sm leading-relaxed text-muted-foreground">
          {profile.career_objective}
        </p>
      ) : null}

      {/* Education */}
      {profile.institution ? (
        <div className="mb-5">
          <div className="mb-1 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            <GraduationCap className="h-3.5 w-3.5" />
            Education
          </div>
          <div className="text-sm font-medium text-foreground">
            {profile.degree} {profile.field_of_study}
          </div>
          <div className="text-sm text-muted-foreground">
            {profile.institution}
            {profile.graduation_year ? ` · ${profile.graduation_year}` : null}
          </div>
        </div>
      ) : null}

      {/* Work experience */}
      {shownWork.length > 0 ? (
        <div className="mb-5">
          <div className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            <Briefcase className="h-3.5 w-3.5" />
            Experience
          </div>
          <ul className="space-y-3">
            {shownWork.map((w, i) => (
              <li key={i}>
                <div className="text-sm font-medium text-foreground">
                  {w.title ?? "Position"}
                </div>
                <div className="text-sm text-muted-foreground">
                  {w.company ?? ""}
                  {formatRange(w) ? ` · ${formatRange(w)}` : ""}
                </div>
                {w.description ? (
                  <div className="mt-1 line-clamp-2 text-xs text-muted-foreground">
                    {w.description}
                  </div>
                ) : null}
              </li>
            ))}
            {extraWork > 0 ? (
              <li className="text-xs italic text-muted-foreground">
                + {extraWork} more {extraWork === 1 ? "role" : "roles"} on resume
              </li>
            ) : null}
          </ul>
        </div>
      ) : null}

      {/* Top skills */}
      {shownSkills.length > 0 ? (
        <div className="mb-4">
          <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Skills
          </div>
          <div className="flex flex-wrap gap-1.5">
            {shownSkills.map((s) => (
              <Badge key={s} variant="secondary" className="text-xs">
                {s}
              </Badge>
            ))}
            {extraSkills > 0 ? (
              <Badge variant="outline" className="text-xs">
                +{extraSkills} more
              </Badge>
            ) : null}
          </div>
        </div>
      ) : null}

      {/* Certifications */}
      {certs.length > 0 ? (
        <div>
          <div className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            <Award className="h-3.5 w-3.5" />
            Certifications
          </div>
          <ul className="space-y-1">
            {certs.map((c, i) => (
              <li key={i} className="text-sm text-foreground">
                {c}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </Card>
  )
}
