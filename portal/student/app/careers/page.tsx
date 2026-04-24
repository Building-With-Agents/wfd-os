"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import {
  Compass, ArrowLeft, Upload, FileText, User, Mail, ArrowRight,
  Search, Sparkles, CheckCircle2, AlertCircle, Loader2,
  Target, TrendingUp, XCircle, BookOpen,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"

// Matches the shape returned by /api/student/quick-gap-analysis
interface QuickAnalysisResult {
  job_title: string | null
  match_score: number
  verdict: string
  matched_skills: string[]
  missing_skills: string[]
  partial_matches: string[]
  narrative: string
  growth_tips: string[]
}

const SKILL_OPTIONS = [
  "Python", "JavaScript", "Java", "SQL", "HTML/CSS", "React",
  "AWS", "Azure", "Docker", "Linux", "Git", "Node.js",
  "Data Analysis", "Machine Learning", "Cybersecurity",
  "Network Administration", "Help Desk", "Project Management",
  "Agile/Scrum", "Tableau", "Power BI", "Excel",
]

const ROLE_OPTIONS = [
  "Software Developer", "Data Analyst", "Cloud Engineer",
  "IT Support", "Cybersecurity Analyst", "Web Developer",
  "DevOps Engineer", "Database Administrator", "UX Designer",
  "Network Engineer", "QA Engineer", "Business Analyst",
]

interface IntakeResult {
  student_id: string
  email: string
  full_name: string
  action: "created" | "existing"
  skills_matched: number
}

export default function CareersPage() {
  const router = useRouter()
  const [showIntakeForm, setShowIntakeForm] = useState(false)
  const [lookupEmail, setLookupEmail] = useState("")
  const [selectedSkills, setSelectedSkills] = useState<string[]>([])
  const [selectedRoles, setSelectedRoles] = useState<string[]>([])
  const [intakeName, setIntakeName] = useState("")
  const [intakeEmail, setIntakeEmail] = useState("")
  const [submitted, setSubmitted] = useState<IntakeResult | null>(null)
  const [isDragOver, setIsDragOver] = useState(false)
  const [uploadMessage, setUploadMessage] = useState<string | null>(null)
  const [uploadedFileName, setUploadedFileName] = useState<string | null>(null)
  const [intakeError, setIntakeError] = useState<string | null>(null)
  const [intakeLoading, setIntakeLoading] = useState(false)
  const [lookupError, setLookupError] = useState<string | null>(null)
  const [lookupLoading, setLookupLoading] = useState(false)

  // Quick gap-analysis state (the "try it before you sign up" flow).
  // analysisResult carries forward to intake — if set when the user
  // clicks Save, it's included in the POST body so the backend
  // persists a gap_analyses row against the new student.
  const [jdText, setJdText] = useState("")
  const [resumeText, setResumeText] = useState("")
  const [analyzing, setAnalyzing] = useState(false)
  const [analysisError, setAnalysisError] = useState<string | null>(null)
  const [analysisResult, setAnalysisResult] = useState<QuickAnalysisResult | null>(null)

  const toggleSkill = (skill: string) => {
    setSelectedSkills(prev =>
      prev.includes(skill) ? prev.filter(s => s !== skill) : [...prev, skill]
    )
  }

  const toggleRole = (role: string) => {
    setSelectedRoles(prev =>
      prev.includes(role) ? prev.filter(r => r !== role) : [...prev, role]
    )
  }

  // Resume upload: we accept the file name + gently explain that resume
  // parsing for CFA intake is done manually today. Points them at the
  // structured form so they're not stuck. (The Phase A cohort-1 parser
  // runs for WSB via a separate ingestion flow, not through this form.)
  const handleFileDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(false)
    const file = e.dataTransfer.files?.[0]
    if (file) setUploadedFileName(file.name)
    setUploadMessage(
      "Thanks — we've noted your resume. Resume parsing for new intakes is manual today; please also fill out the quick form below so we can match you immediately."
    )
    setShowIntakeForm(true)
  }

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) setUploadedFileName(file.name)
    setUploadMessage(
      "Thanks — we've noted your resume. Resume parsing for new intakes is manual today; please also fill out the quick form below so we can match you immediately."
    )
    setShowIntakeForm(true)
  }

  const handleAnalyze = async () => {
    setAnalysisError(null)
    setAnalyzing(true)
    setAnalysisResult(null)
    try {
      const res = await fetch("/api/student/quick-gap-analysis", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          resume_text: resumeText,
          job_description: jdText,
        }),
      })
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        const msg =
          (body as { error?: { message?: string } })?.error?.message ||
          (body as { detail?: string })?.detail ||
          `HTTP ${res.status}`
        throw new Error(msg)
      }
      const data = (await res.json()) as QuickAnalysisResult
      setAnalysisResult(data)
    } catch (err) {
      setAnalysisError(err instanceof Error ? err.message : String(err))
    } finally {
      setAnalyzing(false)
    }
  }

  // Option B behavior: carry the analysis into the intake form. Pre-
  // select any matched/partial skills that exist in SKILL_OPTIONS so
  // the form is partway filled when the user lands there; the actual
  // analysis JSON rides along on submit and gets persisted as a
  // gap_analyses row by the backend.
  const handleSaveAnalysisAndSignup = () => {
    if (!analysisResult) return
    const preSelected = new Set<string>()
    for (const s of [...analysisResult.matched_skills, ...analysisResult.partial_matches]) {
      // Exact match first, then substring fallback (e.g., "Python 3" -> "Python")
      const exact = SKILL_OPTIONS.find((opt) => opt.toLowerCase() === s.toLowerCase())
      if (exact) {
        preSelected.add(exact)
        continue
      }
      for (const opt of SKILL_OPTIONS) {
        if (s.toLowerCase().includes(opt.toLowerCase())) {
          preSelected.add(opt)
          break
        }
      }
    }
    // Union with what the user might have already picked (usually none)
    setSelectedSkills((prev) => Array.from(new Set([...prev, ...preSelected])))
    setShowIntakeForm(true)
    // Scroll the form into view after it mounts
    setTimeout(() => {
      const el = document.getElementById("intake-form-section")
      if (el) el.scrollIntoView({ behavior: "smooth", block: "start" })
    }, 50)
  }

  const handleAnalyzeAnother = () => {
    setAnalysisResult(null)
    setAnalysisError(null)
  }

  const handleIntakeSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIntakeError(null)
    setIntakeLoading(true)
    try {
      const res = await fetch("/api/student/intake", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: intakeName,
          email: intakeEmail,
          skills: selectedSkills,
          target_roles: selectedRoles,
          // Carry the quick analysis (if any) so the backend persists it
          // as a gap_analyses row — it shows up on the student's portal.
          quick_analysis: analysisResult || undefined,
        }),
      })
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        const msg =
          (body as { error?: { message?: string } })?.error?.message ||
          (body as { detail?: string })?.detail ||
          `HTTP ${res.status}`
        throw new Error(msg)
      }
      const data = (await res.json()) as IntakeResult
      setSubmitted(data)
    } catch (err) {
      setIntakeError(err instanceof Error ? err.message : String(err))
    } finally {
      setIntakeLoading(false)
    }
  }

  const handleLookup = async () => {
    if (!lookupEmail) return
    setLookupError(null)
    setLookupLoading(true)
    try {
      const res = await fetch(
        `/api/student/lookup?email=${encodeURIComponent(lookupEmail)}`
      )
      if (res.status === 404) {
        setLookupError(
          "We couldn't find a profile for that email. Use the form above to get started."
        )
        return
      }
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`)
      }
      const data = (await res.json()) as { student_id: string; full_name: string }
      router.push(`/student?id=${data.student_id}`)
    } catch (err) {
      setLookupError(err instanceof Error ? err.message : String(err))
    } finally {
      setLookupLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border bg-card">
        <div className="mx-auto flex max-w-4xl items-center justify-between px-4 py-3 sm:px-6">
          <a href="/" className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground">
            <ArrowLeft className="h-4 w-4" /> Computing for All
          </a>
          <div className="flex items-center gap-2">
            <Compass className="h-5 w-5 text-primary" />
            <span className="font-semibold text-foreground">Career Accelerator</span>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-3xl px-4 py-12 sm:px-6">
        {/* Hero */}
        <div className="mb-10 text-center">
          <Badge className="mb-4 bg-purple-100 text-purple-700 border-purple-200">
            WA Tech Career Accelerator
          </Badge>
          <h1 className="text-3xl font-bold text-foreground sm:text-4xl">
            Find your next tech job
          </h1>
          <p className="mt-3 text-lg text-muted-foreground">
            Upload your resume and see your job matches in 60 seconds.
            Free. No commitment.
          </p>
        </div>

        {/* QUICK GAP CHECK — the "VALUE BEFORE ASK" hook.
            Visible until the user has submitted an intake. Lets a
            prospective student paste a real job they found + a short
            summary of their skills, and get an honest match score +
            specific gaps + growth tips — with NO signup required. If
            they like what they see, the "Save this analysis" button
            carries the result into the intake form so the analysis
            is persisted on their portal after sign-up. */}
        {!submitted && (
          <Card className="mb-6 border-primary/30 bg-primary/5 p-6">
            <div className="mb-3 flex items-center gap-2">
              <Target className="h-5 w-5 text-primary" />
              <h2 className="text-lg font-semibold text-foreground">
                Try it — see your fit in 30 seconds
              </h2>
            </div>
            <p className="mb-4 text-sm text-muted-foreground">
              Paste a job you found (LinkedIn, Indeed, company career page — anywhere)
              and a quick summary of your skills. We'll tell you how you match, what's
              missing, and what to work on. No signup needed.
            </p>

            {!analysisResult && (
              <div className="space-y-4">
                <div>
                  <label className="mb-1.5 block text-sm font-medium text-foreground">
                    Job description
                  </label>
                  <Textarea
                    value={jdText}
                    onChange={(e) => setJdText(e.target.value)}
                    placeholder={
                      "Paste the full job description here — responsibilities, required skills, nice-to-haves…"
                    }
                    rows={6}
                    className="text-sm"
                    disabled={analyzing}
                  />
                  <p className="mt-1 text-xs text-muted-foreground">
                    {jdText.length.toLocaleString()} / 10,000 characters
                  </p>
                </div>

                <div>
                  <label className="mb-1.5 block text-sm font-medium text-foreground">
                    Your resume or skills summary
                  </label>
                  <Textarea
                    value={resumeText}
                    onChange={(e) => setResumeText(e.target.value)}
                    placeholder={
                      "Paste your resume, or just jot down your skills and most recent experience — a paragraph is plenty."
                    }
                    rows={5}
                    className="text-sm"
                    disabled={analyzing}
                  />
                  <p className="mt-1 text-xs text-muted-foreground">
                    {resumeText.length.toLocaleString()} / 10,000 characters
                  </p>
                </div>

                {analysisError && (
                  <div className="flex items-start gap-3 rounded-md border border-destructive/40 bg-destructive/5 p-3 text-sm text-destructive">
                    <AlertCircle className="mt-0.5 h-4 w-4 flex-shrink-0" />
                    <span>{analysisError}</span>
                  </div>
                )}

                <Button
                  onClick={handleAnalyze}
                  disabled={analyzing || jdText.length < 50 || resumeText.length < 50}
                  className="w-full gap-2"
                >
                  {analyzing ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Analyzing…
                    </>
                  ) : (
                    <>
                      <Sparkles className="h-4 w-4" />
                      Analyze my match
                    </>
                  )}
                </Button>
                {(jdText.length > 0 && jdText.length < 50) ||
                (resumeText.length > 0 && resumeText.length < 50) ? (
                  <p className="text-center text-xs text-muted-foreground">
                    Need at least 50 characters in each field.
                  </p>
                ) : null}
              </div>
            )}

            {analysisResult && (
              <div className="space-y-4">
                {/* Score + verdict header */}
                <div className="flex items-center justify-between rounded-lg border bg-background p-4">
                  <div>
                    <div className="text-xs uppercase tracking-wide text-muted-foreground">
                      Your match
                    </div>
                    <div className="mt-1 text-sm font-medium text-foreground">
                      {analysisResult.job_title ?? "This role"}
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-3xl font-bold text-foreground">
                      {analysisResult.match_score}%
                    </div>
                    <Badge
                      variant="secondary"
                      className={
                        analysisResult.match_score >= 70
                          ? "bg-green-100 text-green-900"
                          : analysisResult.match_score >= 50
                            ? "bg-blue-100 text-blue-900"
                            : analysisResult.match_score >= 30
                              ? "bg-amber-100 text-amber-900"
                              : "bg-red-100 text-red-900"
                      }
                    >
                      {analysisResult.verdict}
                    </Badge>
                  </div>
                </div>

                {/* Narrative */}
                {analysisResult.narrative && (
                  <div className="rounded-lg bg-background p-4 text-sm leading-relaxed text-foreground">
                    {analysisResult.narrative}
                  </div>
                )}

                {/* Matched */}
                {analysisResult.matched_skills.length > 0 && (
                  <div>
                    <div className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-green-700">
                      <CheckCircle2 className="h-3.5 w-3.5" />
                      Skills you have ({analysisResult.matched_skills.length})
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                      {analysisResult.matched_skills.map((s) => (
                        <Badge key={s} className="bg-green-100 text-green-900 hover:bg-green-100">
                          {s}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}

                {/* Partial matches */}
                {analysisResult.partial_matches.length > 0 && (
                  <div>
                    <div className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-blue-700">
                      <TrendingUp className="h-3.5 w-3.5" />
                      Adjacent / transferable ({analysisResult.partial_matches.length})
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                      {analysisResult.partial_matches.map((s) => (
                        <Badge key={s} variant="secondary" className="bg-blue-100 text-blue-900 hover:bg-blue-100">
                          {s}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}

                {/* Gaps */}
                {analysisResult.missing_skills.length > 0 && (
                  <div>
                    <div className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-amber-800">
                      <XCircle className="h-3.5 w-3.5" />
                      Gaps to close ({analysisResult.missing_skills.length})
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                      {analysisResult.missing_skills.map((s) => (
                        <Badge key={s} variant="outline" className="border-amber-300 bg-amber-50 text-amber-900">
                          {s}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}

                {/* Growth tips */}
                {analysisResult.growth_tips.length > 0 && (
                  <div>
                    <div className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-foreground">
                      <BookOpen className="h-3.5 w-3.5" />
                      What to work on
                    </div>
                    <ul className="space-y-1 rounded-lg border bg-background p-3">
                      {analysisResult.growth_tips.map((tip, i) => (
                        <li key={i} className="flex items-start gap-2 text-sm text-foreground">
                          <span className="mt-1 inline-block h-1.5 w-1.5 flex-shrink-0 rounded-full bg-primary" />
                          <span>{tip}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Actions */}
                <div className="flex flex-col gap-2 sm:flex-row">
                  <Button onClick={handleSaveAnalysisAndSignup} className="flex-1 gap-2">
                    <User className="h-4 w-4" />
                    Save this analysis &mdash; create profile
                  </Button>
                  <Button variant="outline" onClick={handleAnalyzeAnother}>
                    Try another job
                  </Button>
                </div>

                <p className="text-center text-xs text-muted-foreground">
                  Creating a profile saves this analysis to your dashboard and surfaces
                  more matches from CFA's job pipeline automatically.
                </p>
              </div>
            )}
          </Card>
        )}

        {!showIntakeForm && !submitted && (
          <div className="space-y-6">
            {/* Path 1: Resume Upload */}
            <Card className="p-6">
              <div className="flex items-center gap-2 mb-4">
                <Upload className="h-5 w-5 text-primary" />
                <h2 className="text-lg font-semibold text-foreground">Upload your resume</h2>
              </div>

              <div
                onDragOver={(e) => { e.preventDefault(); setIsDragOver(true) }}
                onDragLeave={() => setIsDragOver(false)}
                onDrop={handleFileDrop}
                className={`flex flex-col items-center justify-center rounded-xl border-2 border-dashed p-10 transition-colors ${
                  isDragOver ? "border-primary bg-primary/5" : "border-muted-foreground/25 bg-muted/20"
                }`}
              >
                <FileText className="mb-3 h-10 w-10 text-muted-foreground/50" />
                <p className="text-sm font-medium text-foreground">
                  Drag and drop your resume here
                </p>
                <p className="mt-1 text-xs text-muted-foreground">PDF or Word document</p>
                <label>
                  <input type="file" accept=".pdf,.docx,.doc" className="hidden" onChange={handleFileSelect} />
                  <Button variant="outline" size="sm" className="mt-4 gap-1 cursor-pointer" asChild>
                    <span><Upload className="h-3.5 w-3.5" /> Or click to browse</span>
                  </Button>
                </label>
              </div>

              {uploadMessage && (
                <div className="mt-4 flex items-start gap-3 rounded-lg border border-amber-200 bg-amber-50 p-4">
                  <AlertCircle className="mt-0.5 h-5 w-5 flex-shrink-0 text-amber-500" />
                  <div>
                    <p className="text-sm font-medium text-amber-800">
                      {uploadedFileName ? `Received: ${uploadedFileName}` : "Heads up"}
                    </p>
                    <p className="text-sm text-amber-700">{uploadMessage}</p>
                  </div>
                </div>
              )}
            </Card>

            {/* Path 2: No resume */}
            <div className="text-center">
              <button
                onClick={() => setShowIntakeForm(true)}
                className="text-sm font-medium text-primary hover:underline"
              >
                No resume? Answer a few questions instead &rarr;
              </button>
            </div>
          </div>
        )}

        {/* Intake Form (no resume path) */}
        {showIntakeForm && !submitted && (
          <Card id="intake-form-section" className="p-6">
            <div className="flex items-center gap-2 mb-4">
              <User className="h-5 w-5 text-primary" />
              <h2 className="text-lg font-semibold text-foreground">Tell us about yourself</h2>
            </div>
            {analysisResult && (
              <div className="mb-4 flex items-start gap-2 rounded-md border border-primary/30 bg-primary/5 p-3 text-sm">
                <CheckCircle2 className="mt-0.5 h-4 w-4 flex-shrink-0 text-primary" />
                <span className="text-foreground">
                  We pre-selected <strong>{selectedSkills.length}</strong>{" "}
                  {selectedSkills.length === 1 ? "skill" : "skills"} from your gap
                  analysis. Your analysis will be saved to your dashboard when you
                  submit.
                </span>
              </div>
            )}

            <form onSubmit={handleIntakeSubmit} className="space-y-5">
              <div className="grid gap-3 sm:grid-cols-2">
                <div>
                  <label className="mb-1 block text-sm text-muted-foreground">Your name *</label>
                  <Input value={intakeName} onChange={e => setIntakeName(e.target.value)} required />
                </div>
                <div>
                  <label className="mb-1 block text-sm text-muted-foreground">Email *</label>
                  <Input type="email" value={intakeEmail} onChange={e => setIntakeEmail(e.target.value)} required />
                </div>
              </div>

              <div>
                <label className="mb-2 block text-sm font-medium text-foreground">What skills do you have?</label>
                <div className="flex flex-wrap gap-2">
                  {SKILL_OPTIONS.map(skill => (
                    <button
                      key={skill}
                      type="button"
                      onClick={() => toggleSkill(skill)}
                      className={`rounded-full border px-3 py-1.5 text-xs transition-colors ${
                        selectedSkills.includes(skill)
                          ? "border-primary bg-primary text-primary-foreground"
                          : "border-border bg-card text-foreground hover:border-primary"
                      }`}
                    >
                      {skill}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="mb-2 block text-sm font-medium text-foreground">What roles interest you?</label>
                <div className="flex flex-wrap gap-2">
                  {ROLE_OPTIONS.map(role => (
                    <button
                      key={role}
                      type="button"
                      onClick={() => toggleRole(role)}
                      className={`rounded-full border px-3 py-1.5 text-xs transition-colors ${
                        selectedRoles.includes(role)
                          ? "border-teal-500 bg-teal-500 text-white"
                          : "border-border bg-card text-foreground hover:border-teal-500"
                      }`}
                    >
                      {role}
                    </button>
                  ))}
                </div>
              </div>

              {intakeError && (
                <div className="flex items-start gap-3 rounded-lg border border-destructive/40 bg-destructive/5 p-3 text-sm text-destructive">
                  <AlertCircle className="mt-0.5 h-4 w-4 flex-shrink-0" />
                  <span>{intakeError}</span>
                </div>
              )}

              <Button type="submit" className="w-full gap-2" disabled={intakeLoading}>
                {intakeLoading ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Creating your profile…
                  </>
                ) : (
                  <>
                    Show me my matches <Sparkles className="h-4 w-4" />
                  </>
                )}
              </Button>

              <button
                type="button"
                onClick={() => setShowIntakeForm(false)}
                className="block w-full text-center text-xs text-muted-foreground hover:text-foreground"
              >
                &larr; Back to resume upload
              </button>
            </form>
          </Card>
        )}

        {/* Success state */}
        {submitted && (
          <Card className="p-8 text-center">
            <CheckCircle2 className="mx-auto mb-4 h-10 w-10 text-green-500" />
            <h2 className="text-xl font-bold text-foreground">
              {submitted.action === "existing"
                ? `Welcome back, ${submitted.full_name.split(" ")[0]}`
                : "Profile created!"}
            </h2>
            <p className="mt-2 text-muted-foreground">
              {submitted.action === "existing"
                ? "We already have a profile for this email — your dashboard is ready."
                : `Your profile is in the CFA pipeline. ${submitted.skills_matched} skill${
                    submitted.skills_matched === 1 ? "" : "s"
                  } matched our taxonomy.`}
            </p>

            <div className="mt-6 space-y-2 text-left mx-auto max-w-sm">
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <CheckCircle2 className="h-4 w-4 text-green-500" /> Profile saved
              </div>
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <CheckCircle2 className="h-4 w-4 text-green-500" /> Skills recorded
              </div>
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <CheckCircle2 className="h-4 w-4 text-green-500" /> Ready to match against open roles
              </div>
            </div>

            <Button
              className="mt-6 w-full gap-2"
              onClick={() => router.push(`/student?id=${submitted.student_id}`)}
            >
              Open my dashboard <ArrowRight className="h-4 w-4" />
            </Button>

            <p className="mt-3 text-xs text-muted-foreground">
              Bookmark it: <code className="text-foreground">/student?id={submitted.student_id.slice(0, 8)}…</code>
            </p>
          </Card>
        )}

        <Separator className="my-8" />

        {/* Existing Student Lookup */}
        <div className="text-center">
          <h3 className="text-sm font-medium text-foreground">Already have an account?</h3>
          <div className="mx-auto mt-3 flex max-w-sm gap-2">
            <Input
              type="email"
              placeholder="Enter your email"
              value={lookupEmail}
              onChange={e => setLookupEmail(e.target.value)}
              onKeyDown={e => e.key === "Enter" && !lookupLoading && handleLookup()}
              disabled={lookupLoading}
            />
            <Button
              variant="outline"
              onClick={handleLookup}
              className="gap-1 flex-shrink-0"
              disabled={lookupLoading || !lookupEmail}
            >
              {lookupLoading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Search className="h-4 w-4" />
              )}
              Find my profile
            </Button>
          </div>
          {lookupError && (
            <p className="mx-auto mt-2 max-w-sm text-xs text-amber-700">{lookupError}</p>
          )}
        </div>
      </main>

      <footer className="border-t border-border bg-card py-4 mt-8">
        <div className="mx-auto max-w-4xl px-4 text-center text-xs text-muted-foreground">
          &copy; 2026 Computing for All | computingforall.org
        </div>
      </footer>
    </div>
  )
}
