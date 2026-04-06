"use client"

import { useState } from "react"
import { MessageCircle, X, Send, Sparkles } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { sendChatMessage } from "@/lib/api"

const suggestedQuestions = [
  "Show me my best opportunity",
  "What should I learn next?",
  "How do I improve my match score?",
]

interface AICareerNavigatorProps {
  studentName?: string
  studentId?: string
  newMatchCount?: number
}

export function AICareerNavigator({
  studentName = "there",
  studentId = "",
  newMatchCount = 0,
}: AICareerNavigatorProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [userMessages, setUserMessages] = useState<
    { role: "user" | "assistant"; content: string }[]
  >([])
  const [input, setInput] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const hasNewInsight = newMatchCount > 0

  const welcomeMessage = {
    role: "assistant" as const,
    content:
      newMatchCount > 0
        ? `Hi ${studentName}! I found ${newMatchCount} matches for you. Want to see your best opportunity?`
        : `Hi ${studentName}! Complete your profile to see job matches and career recommendations.`,
  }

  const messages = [welcomeMessage, ...userMessages]

  const handleSendMessage = async (message: string) => {
    if (!message.trim() || isLoading) return

    setUserMessages((prev) => [...prev, { role: "user", content: message }])
    setInput("")
    setIsLoading(true)

    try {
      const data = await sendChatMessage(studentId, message)
      setUserMessages((prev) => [
        ...prev,
        { role: "assistant", content: data.response },
      ])
    } catch {
      setUserMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content:
            "Sorry, I couldn't connect to the server. Please try again.",
        },
      ])
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <>
      {!isOpen && (
        <button
          onClick={() => setIsOpen(true)}
          className="fixed bottom-6 right-6 z-50 flex items-center gap-3 rounded-full bg-primary px-4 py-3 text-primary-foreground shadow-lg transition-all hover:scale-105 hover:shadow-xl animate-pulse"
        >
          <div className="relative">
            <MessageCircle className="h-6 w-6" />
            {hasNewInsight && (
              <span className="absolute -right-1 -top-1 flex h-4 w-4 items-center justify-center rounded-full bg-secondary text-[9px] font-bold text-secondary-foreground">
                {newMatchCount}
              </span>
            )}
          </div>
          <span className="hidden font-medium sm:inline">
            Ask your Career Navigator
          </span>
        </button>
      )}

      {isOpen && (
        <div className="fixed bottom-6 right-6 z-50 flex w-[90vw] max-w-md flex-col overflow-hidden rounded-2xl border border-border bg-card shadow-2xl sm:w-96">
          <div className="flex items-center justify-between border-b border-border bg-primary p-4 text-primary-foreground">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary-foreground/20">
                <Sparkles className="h-5 w-5" />
              </div>
              <div>
                <h3 className="font-semibold">Career Navigator</h3>
                <p className="text-xs text-primary-foreground/80">
                  AI-powered guidance
                </p>
              </div>
            </div>
            <button
              onClick={() => setIsOpen(false)}
              className="rounded-full p-1 transition-colors hover:bg-primary-foreground/20"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          <div className="flex max-h-80 flex-1 flex-col gap-3 overflow-y-auto p-4">
            {messages.map((message, index) => (
              <div
                key={index}
                className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
              >
                <div
                  className={`max-w-[85%] rounded-2xl px-4 py-2 text-sm ${
                    message.role === "user"
                      ? "bg-primary text-primary-foreground"
                      : "bg-muted text-foreground"
                  }`}
                >
                  {message.content}
                </div>
              </div>
            ))}
            {isLoading && (
              <div className="flex justify-start">
                <div className="rounded-2xl bg-muted px-4 py-2 text-sm text-muted-foreground">
                  Thinking...
                </div>
              </div>
            )}
          </div>

          <div className="flex flex-wrap gap-2 border-t border-border px-4 py-3">
            {suggestedQuestions.map((question, index) => (
              <button
                key={index}
                onClick={() => handleSendMessage(question)}
                disabled={isLoading}
                className="rounded-full border border-border bg-card px-3 py-1.5 text-xs text-foreground transition-colors hover:border-primary hover:bg-primary/5 disabled:opacity-50"
              >
                {question}
              </button>
            ))}
          </div>

          <div className="flex gap-2 border-t border-border p-4">
            <Input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSendMessage(input)}
              placeholder="Ask me anything..."
              className="flex-1"
              disabled={isLoading}
            />
            <Button
              size="icon"
              onClick={() => handleSendMessage(input)}
              disabled={isLoading || !input.trim()}
            >
              <Send className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}
    </>
  )
}
