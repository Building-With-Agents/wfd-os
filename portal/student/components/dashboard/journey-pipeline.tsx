import { Check, Sparkles } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"

interface JourneyStage {
  id: number
  name: string
  completed: boolean
  current: boolean
}

interface JourneyPipelineProps {
  stages: JourneyStage[]
  currentStage: number
  trackName: string
  nextStep: string
  studentName: string
  cohort: string
  estimatedTimeToNext: string
}

export function JourneyPipeline({ 
  stages, 
  currentStage, 
  trackName, 
  nextStep, 
  studentName, 
  cohort, 
  estimatedTimeToNext 
}: JourneyPipelineProps) {
  return (
    <Card>
      <CardHeader className="pb-4">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div>
            <CardTitle className="text-lg">My Journey</CardTitle>
            <p className="text-sm text-muted-foreground mt-1">
              {studentName} &middot; {cohort}
            </p>
          </div>
          <Badge variant="secondary" className="bg-primary/10 text-primary border-primary/20">
            {trackName}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Estimated Time Banner */}
        <div className="flex items-center gap-2 rounded-lg bg-secondary/20 border border-secondary/30 px-4 py-2">
          <Sparkles className="h-4 w-4 text-secondary flex-shrink-0" />
          <p className="text-sm font-medium text-secondary-foreground">
            {estimatedTimeToNext}
          </p>
        </div>

        {/* Desktop Pipeline */}
        <div className="hidden md:block">
          <div className="relative flex items-center justify-between">
            {/* Connection Line */}
            <div className="absolute left-4 right-4 top-1/2 h-1 -translate-y-1/2 bg-muted" />
            <div 
              className="absolute left-4 top-1/2 h-1 -translate-y-1/2 bg-primary transition-all duration-500"
              style={{ width: `${((currentStage - 1) / (stages.length - 1)) * 100}%` }}
            />
            
            {stages.map((stage) => (
              <div key={stage.id} className="relative z-10 flex flex-col items-center">
                <div
                  className={`flex h-10 w-10 items-center justify-center rounded-full border-2 transition-all ${
                    stage.completed
                      ? "border-primary bg-primary text-primary-foreground animate-in zoom-in-50 duration-300"
                      : stage.current
                      ? "border-primary bg-card text-primary ring-4 ring-primary/20"
                      : "border-muted bg-card text-muted-foreground"
                  }`}
                >
                  {stage.completed ? (
                    <Check className="h-5 w-5" />
                  ) : (
                    <span className="text-sm font-medium">{stage.id}</span>
                  )}
                </div>
                <span
                  className={`mt-2 text-xs font-medium ${
                    stage.current ? "text-primary" : stage.completed ? "text-foreground" : "text-muted-foreground"
                  }`}
                >
                  {stage.name}
                </span>
                {stage.completed && (
                  <span className="text-[10px] text-success mt-0.5">Complete</span>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Mobile Pipeline */}
        <div className="md:hidden">
          <div className="space-y-3">
            {stages.map((stage) => (
              <div key={stage.id} className="flex items-center gap-3">
                <div
                  className={`flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full border-2 ${
                    stage.completed
                      ? "border-primary bg-primary text-primary-foreground"
                      : stage.current
                      ? "border-primary bg-card text-primary"
                      : "border-muted bg-card text-muted-foreground"
                  }`}
                >
                  {stage.completed ? (
                    <Check className="h-4 w-4" />
                  ) : (
                    <span className="text-xs font-medium">{stage.id}</span>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  <span
                    className={`text-sm ${
                      stage.current ? "font-semibold text-primary" : stage.completed ? "text-foreground" : "text-muted-foreground"
                    }`}
                  >
                    {stage.name}
                  </span>
                  {stage.completed && (
                    <Check className="h-3 w-3 text-success" />
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Next Step Callout */}
        <div className="rounded-lg bg-accent/30 p-4">
          <p className="text-sm font-medium text-accent-foreground">
            <span className="text-primary">Next step:</span> {nextStep}
          </p>
        </div>
      </CardContent>
    </Card>
  )
}
