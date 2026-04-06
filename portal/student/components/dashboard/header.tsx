import { Compass, ArrowRight, User, Settings, LogOut, ChevronDown } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"

interface HeaderProps {
  studentName: string
  profileCompletion: number
}

export function Header({ studentName, profileCompletion }: HeaderProps) {
  const circumference = 2 * Math.PI * 22
  const strokeDashoffset = circumference - (profileCompletion / 100) * circumference
  const initials = studentName.split(" ").map((n) => n[0]).join("").toUpperCase()

  return (
    <header className="border-b border-border bg-card">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-4 sm:px-6 lg:px-8">
        {/* Logo and Branding */}
        <div className="flex items-center gap-3">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary shadow-lg shadow-primary/25">
            <Compass className="h-7 w-7 text-primary-foreground" />
          </div>
          <div>
            <span className="text-2xl font-bold text-foreground tracking-tight">Waifinder</span>
            <p className="text-xs text-muted-foreground">Your AI-powered career navigator</p>
          </div>
        </div>

        <div className="flex items-center gap-4 sm:gap-6">
          {/* Profile Completion Ring - Larger and more prominent */}
          <div className="hidden items-center gap-3 sm:flex">
            <div className="relative h-14 w-14">
              <svg className="h-14 w-14 -rotate-90 transform">
                <circle
                  cx="28"
                  cy="28"
                  r="22"
                  stroke="currentColor"
                  strokeWidth="4"
                  fill="none"
                  className="text-muted"
                />
                <circle
                  cx="28"
                  cy="28"
                  r="22"
                  stroke="currentColor"
                  strokeWidth="4"
                  fill="none"
                  strokeLinecap="round"
                  className="text-primary transition-all duration-1000 ease-out"
                  style={{
                    strokeDasharray: circumference,
                    strokeDashoffset: strokeDashoffset,
                  }}
                />
              </svg>
              <span className="absolute inset-0 flex items-center justify-center text-sm font-bold text-foreground">
                {profileCompletion}%
              </span>
            </div>
            <div className="text-sm">
              <p className="font-medium text-foreground">Profile {profileCompletion}% complete</p>
              <p className="text-xs text-muted-foreground">Finish to unlock all features</p>
            </div>
          </div>

          <Button className="gap-2 hidden sm:flex">
            Complete profile
            <ArrowRight className="h-4 w-4" />
          </Button>

          {/* Avatar with Dropdown */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button className="flex items-center gap-2 rounded-full focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2">
                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary text-primary-foreground font-semibold text-sm">
                  {initials}
                </div>
                <ChevronDown className="h-4 w-4 text-muted-foreground hidden sm:block" />
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-48">
              <DropdownMenuItem className="gap-2">
                <User className="h-4 w-4" />
                My Profile
              </DropdownMenuItem>
              <DropdownMenuItem className="gap-2">
                <Settings className="h-4 w-4" />
                Settings
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem className="gap-2 text-destructive">
                <LogOut className="h-4 w-4" />
                Sign out
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      <div className="mx-auto max-w-7xl px-4 pb-4 sm:px-6 lg:px-8">
        <h1 className="text-2xl font-semibold text-foreground sm:text-3xl">
          Welcome back, {studentName}
        </h1>
        <p className="mt-1 text-muted-foreground">Let&apos;s continue your career journey</p>
      </div>
    </header>
  )
}
