"use client"

import { useState } from "react"
import {
  Compass, ArrowLeft, Upload, FileText, User, Mail, ArrowRight,
  Search, Sparkles, CheckCircle2, AlertCircle,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import NewsletterSubscribe from "@/components/newsletter-subscribe"

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

export default function CareersPage() {
  const [showIntakeForm, setShowIntakeForm] = useState(false)
  const [lookupEmail, setLookupEmail] = useState("")
  const [selectedSkills, setSelectedSkills] = useState<string[]>([])
  const [selectedRoles, setSelectedRoles] = useState<string[]>([])
  const [intakeName, setIntakeName] = useState("")
  const [intakeEmail, setIntakeEmail] = useState("")
  const [submitted, setSubmitted] = useState(false)
  const [isDragOver, setIsDragOver] = useState(false)
  const [uploadMessage, setUploadMessage] = useState<string | null>(null)

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

  const handleFileDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(false)
    setUploadMessage("Processing your resume... This feature requires Anthropic API credits. Add $25 at console.anthropic.com to activate.")
  }

  const handleFileSelect = () => {
    setUploadMessage("Processing your resume... This feature requires Anthropic API credits. Add $25 at console.anthropic.com to activate.")
  }

  const handleIntakeSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setSubmitted(true)
  }

  const handleLookup = () => {
    if (!lookupEmail) return
    setUploadMessage(`Looking up ${lookupEmail}... This feature requires the student lookup API to be connected. Check back soon.`)
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
                    <p className="text-sm font-medium text-amber-800">Resume processing paused</p>
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
          <Card className="p-6">
            <div className="flex items-center gap-2 mb-4">
              <User className="h-5 w-5 text-primary" />
              <h2 className="text-lg font-semibold text-foreground">Tell us about yourself</h2>
            </div>

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

              <Button type="submit" className="w-full gap-2">
                Show me my matches <Sparkles className="h-4 w-4" />
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
            <AlertCircle className="mx-auto mb-4 h-10 w-10 text-amber-500" />
            <h2 className="text-xl font-bold text-foreground">Profile created!</h2>
            <p className="mt-2 text-muted-foreground">
              Your job matching and gap analysis requires Anthropic API credits to process.
            </p>
            <p className="mt-1 text-sm text-muted-foreground">
              Add $25 at console.anthropic.com to activate real-time matching.
            </p>
            <div className="mt-6 space-y-2 text-left mx-auto max-w-sm">
              {["Profile saved to CFA pipeline", "Skills recorded for matching",
                "Job match engine queued (pending credits)", "Gap analysis queued (pending credits)"].map((step, i) => (
                <div key={i} className="flex items-center gap-2 text-sm text-muted-foreground">
                  <CheckCircle2 className={`h-4 w-4 ${i < 2 ? "text-green-500" : "text-amber-400"}`} /> {step}
                </div>
              ))}
            </div>
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
              onKeyDown={e => e.key === "Enter" && handleLookup()}
            />
            <Button variant="outline" onClick={handleLookup} className="gap-1 flex-shrink-0">
              <Search className="h-4 w-4" /> Find my profile
            </Button>
          </div>
          {uploadMessage && lookupEmail && (
            <p className="mt-2 text-xs text-amber-600">{uploadMessage}</p>
          )}
        </div>
      </main>

      <footer className="border-t border-border bg-card py-4 mt-8">
        <NewsletterSubscribe />
        <div className="mx-auto max-w-4xl px-4 text-center text-xs text-muted-foreground">
          &copy; 2026 Computing for All | computingforall.org
        </div>
      </footer>
    </div>
  )
}
