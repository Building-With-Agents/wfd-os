import { ArrowRight, ExternalLink, TrendingUp, Gift, Clock } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"

interface SkillGap {
  skill: string
  resource: string
  provider: string
  duration: string
  link: string
  isFree?: boolean
}

interface GapAnalysisPreviewProps {
  gapScore: number
  previousScore: number
  topMatchJob: string
  skillGaps: SkillGap[]
  totalHoursToClose: string
  targetScore: number
}

export function GapAnalysisPreview({ 
  gapScore, 
  previousScore,
  topMatchJob, 
  skillGaps,
  totalHoursToClose,
  targetScore
}: GapAnalysisPreviewProps) {
  const circumference = 2 * Math.PI * 36
  const strokeDashoffset = circumference - (gapScore / 100) * circumference
  const scoreImprovement = gapScore - previousScore

  return (
    <Card>
      <CardHeader className="pb-4">
        <CardTitle className="text-lg">My Gap Analysis</CardTitle>
      </CardHeader>
      <CardContent className="space-y-5">
        <div className="flex items-center gap-4">
          <div className="relative h-20 w-20 flex-shrink-0">
            <svg className="h-20 w-20 -rotate-90 transform">
              <circle
                cx="40"
                cy="40"
                r="36"
                stroke="currentColor"
                strokeWidth="6"
                fill="none"
                className="text-muted"
              />
              <circle
                cx="40"
                cy="40"
                r="36"
                stroke="currentColor"
                strokeWidth="6"
                fill="none"
                strokeLinecap="round"
                className="text-secondary transition-all duration-1000 ease-out"
                style={{
                  strokeDasharray: circumference,
                  strokeDashoffset: strokeDashoffset,
                }}
              />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <span className="text-lg font-bold text-foreground">{gapScore}%</span>
              <span className="text-[10px] text-muted-foreground">ready</span>
            </div>
          </div>
          <div className="space-y-1">
            <p className="text-sm text-muted-foreground">You are</p>
            <p className="font-semibold text-foreground">
              {gapScore}% ready for your top match
            </p>
            <p className="text-sm text-secondary">{topMatchJob}</p>
          </div>
        </div>

        {/* Progress Over Time */}
        <div className="rounded-lg bg-success/10 border border-success/20 px-4 py-3">
          <div className="flex items-center gap-2">
            <TrendingUp className="h-4 w-4 text-success" />
            <span className="text-sm font-medium text-success">
              Up from {previousScore}% last week (+{scoreImprovement}%)
            </span>
          </div>
          <div className="mt-2 h-2 rounded-full bg-muted overflow-hidden">
            <div 
              className="h-full bg-success transition-all duration-500"
              style={{ width: `${(scoreImprovement / (targetScore - previousScore)) * 100}%` }}
            />
          </div>
        </div>

        {/* Time to Close Gaps */}
        <div className="flex items-center gap-2 rounded-lg bg-accent/30 px-4 py-2">
          <Clock className="h-4 w-4 text-accent-foreground flex-shrink-0" />
          <p className="text-sm text-accent-foreground">
            <span className="font-medium">{totalHoursToClose}</span> of learning to reach {targetScore}% match
          </p>
        </div>

        <div className="space-y-3">
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground flex items-center gap-1">
            <TrendingUp className="h-3 w-3" />
            Top skills to develop
          </p>
          <div className="space-y-2">
            {skillGaps.map((gap, index) => (
              <a
                key={index}
                href={gap.link}
                target="_blank"
                rel="noopener noreferrer"
                className={`group flex items-center justify-between rounded-lg border p-3 transition-all hover:border-primary/50 hover:bg-accent/20 ${
                  gap.isFree 
                    ? "border-success/30 bg-success/5" 
                    : "border-border bg-card"
                }`}
              >
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <p className="font-medium text-foreground group-hover:text-primary truncate">
                      {gap.skill}
                    </p>
                    {gap.isFree && (
                      <Badge variant="secondary" className="bg-success/15 text-success border-success/20 gap-1">
                        <Gift className="h-3 w-3" />
                        Free
                      </Badge>
                    )}
                  </div>
                  <p className="text-sm text-muted-foreground truncate">
                    {gap.provider} &middot; {gap.duration}
                  </p>
                </div>
                <ExternalLink className="h-4 w-4 flex-shrink-0 text-muted-foreground transition-colors group-hover:text-primary" />
              </a>
            ))}
          </div>
        </div>

        <Button variant="outline" className="w-full gap-2">
          View full gap analysis
          <ArrowRight className="h-4 w-4" />
        </Button>
      </CardContent>
    </Card>
  )
}
