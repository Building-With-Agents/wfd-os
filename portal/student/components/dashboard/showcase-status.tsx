import { Check, Sparkles, Eye, ArrowRight } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"

interface ShowcaseItem {
  id: string
  label: string
  completed: boolean
  actionLink?: string
  actionLabel?: string
}

interface ShowcaseStatusProps {
  isActive: boolean
  items: ShowcaseItem[]
  employerViews?: number
}

export function ShowcaseStatus({ isActive, items, employerViews = 3 }: ShowcaseStatusProps) {
  const completedCount = items.filter((item) => item.completed).length
  const totalCount = items.length
  const canActivate = completedCount === totalCount
  const incompleteItems = items.filter((item) => !item.completed)

  return (
    <Card className={isActive ? "border-success/50 bg-success/5" : ""}>
      <CardHeader className="pb-4">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">My Showcase Status</CardTitle>
          {isActive ? (
            <span className="flex items-center gap-1 rounded-full bg-success/15 px-3 py-1 text-xs font-medium text-success">
              <Sparkles className="h-3 w-3" />
              ACTIVE
            </span>
          ) : (
            <span className="rounded-full bg-muted px-3 py-1 text-xs font-medium text-muted-foreground">
              NOT ACTIVE
            </span>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Urgency Banner for Inactive State */}
        {!isActive && (
          <div className="flex items-center gap-2 rounded-lg bg-secondary/20 border border-secondary/30 px-4 py-3">
            <Eye className="h-4 w-4 text-secondary flex-shrink-0" />
            <p className="text-sm text-secondary-foreground">
              <span className="font-semibold">{employerViews} employers</span> searched for your skills this week
            </p>
          </div>
        )}

        {!isActive && (
          <p className="text-sm text-muted-foreground">
            Complete {totalCount - completedCount} more {totalCount - completedCount === 1 ? "item" : "items"} to activate your showcase and get discovered
          </p>
        )}

        <div className="space-y-2">
          {items.map((item) => (
            <div
              key={item.id}
              className={`flex items-center justify-between rounded-lg p-3 ${
                item.completed ? "bg-success/10" : "bg-muted/50"
              }`}
            >
              <div className="flex items-center gap-3">
                {item.completed ? (
                  <div className="flex h-5 w-5 items-center justify-center rounded-full bg-success text-success-foreground">
                    <Check className="h-3 w-3" />
                  </div>
                ) : (
                  <div className="flex h-5 w-5 items-center justify-center rounded-full border-2 border-warning bg-warning/20">
                    <span className="text-[10px] font-bold text-warning">!</span>
                  </div>
                )}
                <span
                  className={`text-sm ${
                    item.completed ? "text-foreground" : "text-foreground font-medium"
                  }`}
                >
                  {item.label}
                </span>
              </div>
              {/* Actionable link for incomplete items */}
              {!item.completed && item.actionLink && (
                <a
                  href={item.actionLink}
                  className="flex items-center gap-1 text-xs font-medium text-primary hover:underline"
                >
                  {item.actionLabel || "Fix now"}
                  <ArrowRight className="h-3 w-3" />
                </a>
              )}
            </div>
          ))}
        </div>

        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <div>
                <Button
                  className="w-full gap-2"
                  disabled={!canActivate}
                  variant={canActivate ? "default" : "secondary"}
                >
                  <Sparkles className="h-4 w-4" />
                  Activate my showcase
                </Button>
              </div>
            </TooltipTrigger>
            {!canActivate && (
              <TooltipContent className="max-w-xs">
                <p>Complete the following to activate:</p>
                <ul className="mt-1 list-disc pl-4 text-xs">
                  {incompleteItems.map((item) => (
                    <li key={item.id}>{item.label}</li>
                  ))}
                </ul>
              </TooltipContent>
            )}
          </Tooltip>
        </TooltipProvider>

        <p className="text-center text-xs text-muted-foreground">
          Once active, employers can discover and contact you directly
        </p>
      </CardContent>
    </Card>
  )
}
