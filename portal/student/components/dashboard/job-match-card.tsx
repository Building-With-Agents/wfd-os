import { MapPin, DollarSign, Clock } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardFooter, CardHeader } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"

interface JobMatch {
  id: string
  title: string
  company: string
  companyInitials: string
  companyColor: string
  location: string
  matchScore: number
  matchingSkills: string[]
  missingSkills: string[]
  salaryRange: string
  postedDaysAgo: number
  isNew?: boolean
}

interface JobMatchCardProps {
  job: JobMatch
}

export function JobMatchCard({ job }: JobMatchCardProps) {
  const getScoreColor = (score: number) => {
    if (score >= 80) return "text-success"
    if (score >= 60) return "text-warning"
    return "text-destructive"
  }

  const getScoreBgColor = (score: number) => {
    if (score >= 80) return "bg-success/10"
    if (score >= 60) return "bg-warning/10"
    return "bg-destructive/10"
  }

  const circumference = 2 * Math.PI * 36
  const strokeDashoffset = circumference - (job.matchScore / 100) * circumference

  return (
    <Card className="flex h-full flex-col transition-all hover:shadow-lg hover:-translate-y-1">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-start gap-3 min-w-0 flex-1">
            {/* Company Logo Placeholder */}
            <div 
              className="flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-lg text-sm font-bold text-white"
              style={{ backgroundColor: job.companyColor }}
            >
              {job.companyInitials}
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <h3 className="truncate text-lg font-semibold text-foreground">{job.title}</h3>
                {job.isNew && (
                  <Badge className="bg-secondary text-secondary-foreground flex-shrink-0">
                    New
                  </Badge>
                )}
              </div>
              <p className="text-sm text-muted-foreground">{job.company}</p>
            </div>
          </div>
          {/* Match Score Ring - Larger */}
          <div className={`relative h-20 w-20 flex-shrink-0 rounded-full ${getScoreBgColor(job.matchScore)}`}>
            <svg className="h-20 w-20 -rotate-90 transform">
              <circle
                cx="40"
                cy="40"
                r="36"
                stroke="currentColor"
                strokeWidth="5"
                fill="none"
                className="text-muted"
              />
              <circle
                cx="40"
                cy="40"
                r="36"
                stroke="currentColor"
                strokeWidth="5"
                fill="none"
                strokeLinecap="round"
                className={`${getScoreColor(job.matchScore)} transition-all duration-1000 ease-out`}
                style={{
                  strokeDasharray: circumference,
                  strokeDashoffset: strokeDashoffset,
                }}
              />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <span className={`text-lg font-bold ${getScoreColor(job.matchScore)}`}>
                {job.matchScore}%
              </span>
              <span className="text-[10px] text-muted-foreground">match</span>
            </div>
          </div>
        </div>
      </CardHeader>

      <CardContent className="flex-1 space-y-4">
        <div className="flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
          <div className="flex items-center gap-1">
            <MapPin className="h-4 w-4" />
            <span>{job.location}</span>
          </div>
          <div className="flex items-center gap-1">
            <DollarSign className="h-4 w-4" />
            <span>{job.salaryRange}</span>
          </div>
          <div className="flex items-center gap-1">
            <Clock className="h-4 w-4" />
            <span>Posted {job.postedDaysAgo} {job.postedDaysAgo === 1 ? "day" : "days"} ago</span>
          </div>
        </div>

        <div className="space-y-2">
          <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Skills that match</p>
          <div className="flex flex-wrap gap-2">
            {job.matchingSkills.map((skill) => (
              <Badge key={skill} variant="secondary" className="bg-success/15 text-success border-success/20">
                {skill}
              </Badge>
            ))}
          </div>
        </div>

        <div className="space-y-2">
          <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Skills to develop</p>
          <div className="flex flex-wrap gap-2">
            {job.missingSkills.map((skill) => (
              <Badge key={skill} variant="secondary" className="bg-warning/15 text-warning border-warning/20">
                {skill}
              </Badge>
            ))}
          </div>
        </div>
      </CardContent>

      <CardFooter className="flex gap-2 pt-4">
        <Button className="flex-1">Apply Now</Button>
        <Button variant="outline" className="flex-1">Gap Analysis</Button>
      </CardFooter>
    </Card>
  )
}
