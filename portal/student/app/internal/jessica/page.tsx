"use client"
import { useEffect, useState, useRef } from "react"
import { apiFetch } from "@/lib/fetch"
import {
  TrendingUp, FileText, Plus, Send, MessageSquare, Loader2, RefreshCw,
  AlertTriangle, CheckCircle2, BarChart3, Users,
} from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Input } from "@/components/ui/input"

const API = "/api/consulting"
const ASSISTANT_API = "/api/assistant"

interface ContentPiece {
  id: number
  title: string
  author: string
  vertical: string
  topic_tags: string[]
  status: string
  distributed_at: string | null
  submitted_at: string
  contacts_reached: number
  signals_generated: number
  signal_rate_pct: number
  signals?: number
}

interface Gap {
  topic: string
  company_count: number
  companies: string[]
  tiers: string[]
  has_coverage: boolean
  priority: "high" | "medium" | "covered"
}

interface ChatMessage {
  role: "user" | "assistant"
  content: string
}

const TOPIC_OPTIONS = [
  "ai-adoption", "data-engineering", "talent-pipeline", "agentic-ai",
  "cost-reduction", "workforce-intelligence", "compliance",
  "hiring-trends", "digital-transformation",
]

export default function JessicaMarketingCenter() {
  const [performance, setPerformance] = useState<ContentPiece[]>([])
  const [gaps, setGaps] = useState<Gap[]>([])
  const [calendar, setCalendar] = useState<ContentPiece[]>([])
  const [leads, setLeads] = useState<any>({ this_week: 0, last_week: 0, by_content: [] })
  const [loading, setLoading] = useState(true)
  const [statusFilter, setStatusFilter] = useState("all")
  const [showForm, setShowForm] = useState(false)

  // Form state
  const [formTitle, setFormTitle] = useState("")
  const [formUrl, setFormUrl] = useState("")
  const [formAuthor, setFormAuthor] = useState("ritu")
  const [formVertical, setFormVertical] = useState("general")
  const [formTags, setFormTags] = useState<string[]>([])
  const [formFunnel, setFormFunnel] = useState("awareness")
  const [formFormat, setFormFormat] = useState("long-form")
  const [formDistribute, setFormDistribute] = useState("immediately")
  const [formScheduleDate, setFormScheduleDate] = useState("")
  const [submitting, setSubmitting] = useState(false)

  // Chat state
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [chatInput, setChatInput] = useState("")
  const [chatLoading, setChatLoading] = useState(false)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const chatEndRef = useRef<HTMLDivElement>(null)

  const fetchAll = async () => {
    setLoading(true)
    try {
      const safeJson = async (url: string) => {
        try {
          const r = await apiFetch(url)
          if (!r.ok) {
            console.error(`${url} -> HTTP ${r.status}`)
            return null
          }
          return await r.json()
        } catch (e) {
          console.error(`${url} fetch failed`, e)
          return null
        }
      }

      const [perf, g, cal, l] = await Promise.all([
        safeJson(`${API}/marketing/performance`),
        safeJson(`${API}/marketing/gaps`),
        safeJson(`${API}/marketing/calendar`),
        safeJson(`${API}/marketing/leads-summary`),
      ])

      setPerformance(perf?.content || [])
      setGaps(g?.gaps || [])
      setCalendar(cal?.calendar || [])
      setLeads(l || { this_week: 0, last_week: 0, by_content: [] })
    } catch (e) {
      console.error("Fetch error", e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchAll() }, [])
  useEffect(() => { chatEndRef.current?.scrollIntoView({ behavior: "smooth" }) }, [messages])

  const sendMessage = async (msg: string) => {
    if (!msg.trim()) return
    setMessages(prev => [...prev, { role: "user", content: msg }])
    setChatLoading(true)
    setChatInput("")

    try {
      // Use apiFetch so the ngrok-skip-browser-warning header is applied —
      // this lets remote reviewers (via ngrok tunnel) reach the assistant API
      // without being intercepted by the ngrok free-tier interstitial page.
      const res = await apiFetch(`${ASSISTANT_API}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          agent_type: "marketing",
          message: msg,
          session_id: sessionId,
          user_role: "jessica",
        }),
      })
      const data = await res.json()
      setMessages(prev => [...prev, { role: "assistant", content: data.response || "(no response)" }])
      if (data.session_id) setSessionId(data.session_id)
    } catch (e: any) {
      setMessages(prev => [...prev, { role: "assistant", content: `Error: ${e.message}` }])
    } finally {
      setChatLoading(false)
    }
  }

  const submitContent = async () => {
    if (!formTitle.trim()) return
    setSubmitting(true)
    try {
      const body: any = {
        title: formTitle,
        url: formUrl,
        author: formAuthor,
        vertical: formVertical,
        topic_tags: formTags,
        funnel_stage: formFunnel,
        format: formFormat,
        distribute_immediately: formDistribute === "immediately",
      }
      if (formDistribute === "schedule" && formScheduleDate) {
        body.schedule_datetime = formScheduleDate
      }
      const res = await apiFetch(`${API}/marketing/submit-content`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      })
      const data = await res.json()
      alert(`Content submitted! ID: ${data.id}, status: ${data.status}\nDistribution: ${data.estimated_distribution}`)
      setShowForm(false)
      setFormTitle(""); setFormUrl(""); setFormTags([])
      fetchAll()
    } catch (e: any) {
      alert(`Submit failed: ${e.message}`)
    } finally {
      setSubmitting(false)
    }
  }

  const filteredCalendar = calendar.filter(c => {
    if (statusFilter === "all") return true
    return c.status === statusFilter
  })

  const topPerformer = performance
    .filter(p => p.signal_rate_pct > 0)
    .sort((a, b) => b.signal_rate_pct - a.signal_rate_pct)[0]

  return (
    <div className="min-h-screen bg-slate-100">
      {/* Header */}
      <div className="bg-white border-b border-slate-200 px-6 py-3">
        <div className="flex items-center justify-between">
          <h1 className="text-xl font-bold text-slate-900">Jessica · Marketing Intelligence Center</h1>
          <nav className="flex gap-4 text-sm">
            <a href="/internal" className="text-slate-600 hover:text-slate-900">Internal Home</a>
            <a href="/internal/bd" className="text-slate-600 hover:text-slate-900">BD</a>
            <a href="/internal/marketing" className="text-slate-600 hover:text-slate-900">Marketing Workflow</a>
            <a href="/internal/jessica" className="text-blue-600 font-semibold">Jessica</a>
          </nav>
        </div>
      </div>

      <div className="flex h-[calc(100vh-57px)]">
        {/* LEFT PANEL — 60% */}
        <div className="w-3/5 overflow-y-auto p-6 space-y-6">

          {/* SECTION 1: Content Performance */}
          <Card className="p-5">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold flex items-center gap-2">
                <BarChart3 className="w-5 h-5 text-green-600" />
                Content Performance
              </h2>
              <Button size="sm" variant="ghost" onClick={fetchAll}><RefreshCw className="w-4 h-4" /></Button>
            </div>

            {loading && <div className="text-sm text-slate-500">Loading...</div>}
            {!loading && performance.length === 0 && (
              <div className="text-sm text-slate-500">No content distributed yet.</div>
            )}

            <div className="space-y-2">
              {performance.map(p => (
                <div key={p.id} className="border rounded p-3 hover:bg-slate-50">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="font-medium">{p.title}</div>
                      <div className="text-xs text-slate-500">by {p.author} · {p.vertical}</div>
                      <div className="text-xs text-slate-600 mt-1">
                        {p.contacts_reached} contacts · {p.signals_generated} signals · {p.signal_rate_pct}% rate
                      </div>
                    </div>
                    {topPerformer?.id === p.id && (
                      <Badge className="bg-green-600">Best Performer</Badge>
                    )}
                    {p.contacts_reached > 0 && p.signals_generated === 0 && (
                      <Badge variant="outline" className="text-slate-500">No signals yet</Badge>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </Card>

          {/* SECTION 2: Content Gap Analysis */}
          <Card className="p-5">
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-amber-600" />
              Content Gap Analysis
            </h2>
            {gaps.length === 0 && (
              <div className="text-sm text-slate-500">No content gaps detected.</div>
            )}
            <div className="space-y-2">
              {gaps.map((g, i) => (
                <div key={i} className="border rounded p-3">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex-1">
                      <div className="font-medium text-sm">{g.topic}</div>
                      <div className="text-xs text-slate-600 mt-1">
                        {g.company_count} companies need this · {g.companies.slice(0, 3).join(", ")}
                        {g.companies.length > 3 ? ` +${g.companies.length - 3} more` : ""}
                      </div>
                    </div>
                    <Badge
                      className={
                        g.priority === "high" ? "bg-red-600" :
                        g.priority === "medium" ? "bg-yellow-500" :
                        "bg-green-600"
                      }
                    >
                      {g.priority === "covered" ? "Covered" : g.priority}
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          </Card>

          {/* SECTION 3: Content Calendar */}
          <Card className="p-5">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold flex items-center gap-2">
                <FileText className="w-5 h-5" />
                Content Calendar
              </h2>
              <Button size="sm" onClick={() => setShowForm(!showForm)}>
                <Plus className="w-4 h-4 mr-1" /> New Content
              </Button>
            </div>

            <div className="flex gap-2 mb-3">
              {["all", "pending", "distributed", "completed"].map(s => (
                <button
                  key={s}
                  className={`text-xs px-3 py-1 rounded ${statusFilter === s ? "bg-blue-600 text-white" : "bg-slate-100 text-slate-600"}`}
                  onClick={() => setStatusFilter(s)}
                >
                  {s.charAt(0).toUpperCase() + s.slice(1)}
                </button>
              ))}
            </div>

            {showForm && (
              <div className="border rounded p-3 mb-3 bg-slate-50 space-y-2">
                <Input placeholder="Title *" value={formTitle} onChange={e => setFormTitle(e.target.value)} />
                <Input placeholder="URL" value={formUrl} onChange={e => setFormUrl(e.target.value)} />
                <div className="grid grid-cols-2 gap-2">
                  <select className="border rounded px-2 py-1 text-sm" value={formAuthor} onChange={e => setFormAuthor(e.target.value)}>
                    <option value="ritu">Ritu</option>
                    <option value="jason">Jason</option>
                    <option value="jessica">Jessica</option>
                  </select>
                  <select className="border rounded px-2 py-1 text-sm" value={formVertical} onChange={e => setFormVertical(e.target.value)}>
                    <option value="general">General</option>
                    <option value="workforce">Workforce</option>
                    <option value="healthcare">Healthcare</option>
                    <option value="legal">Legal</option>
                    <option value="professional-services">Professional Services</option>
                  </select>
                  <select className="border rounded px-2 py-1 text-sm" value={formFunnel} onChange={e => setFormFunnel(e.target.value)}>
                    <option value="awareness">Awareness</option>
                    <option value="consideration">Consideration</option>
                    <option value="decision">Decision</option>
                  </select>
                  <select className="border rounded px-2 py-1 text-sm" value={formFormat} onChange={e => setFormFormat(e.target.value)}>
                    <option value="long-form">Long-form</option>
                    <option value="short-form">Short-form</option>
                    <option value="email-snippet">Email snippet</option>
                    <option value="case-study">Case study</option>
                  </select>
                </div>
                <div>
                  <div className="text-xs text-slate-500 mb-1">Topic tags:</div>
                  <div className="flex flex-wrap gap-1">
                    {TOPIC_OPTIONS.map(t => (
                      <button
                        key={t}
                        type="button"
                        className={`text-xs px-2 py-1 rounded ${formTags.includes(t) ? "bg-blue-600 text-white" : "bg-slate-200"}`}
                        onClick={() => setFormTags(formTags.includes(t) ? formTags.filter(x => x !== t) : [...formTags, t])}
                      >
                        {t}
                      </button>
                    ))}
                  </div>
                </div>
                <div className="flex gap-3 items-center text-sm">
                  <label><input type="radio" checked={formDistribute === "immediately"} onChange={() => setFormDistribute("immediately")} /> Distribute now</label>
                  <label><input type="radio" checked={formDistribute === "schedule"} onChange={() => setFormDistribute("schedule")} /> Schedule</label>
                </div>
                {formDistribute === "schedule" && (
                  <Input type="datetime-local" value={formScheduleDate} onChange={e => setFormScheduleDate(e.target.value)} />
                )}
                <div className="flex gap-2">
                  <Button size="sm" onClick={submitContent} disabled={submitting || !formTitle.trim()}>
                    {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : "Submit"}
                  </Button>
                  <Button size="sm" variant="outline" onClick={() => setShowForm(false)}>Cancel</Button>
                </div>
              </div>
            )}

            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left">
                  <th className="py-2 pr-3">Title</th>
                  <th className="py-2 pr-3">Author</th>
                  <th className="py-2 pr-3">Status</th>
                  <th className="py-2 pr-3">Submitted</th>
                  <th className="py-2 pr-3">Signals</th>
                </tr>
              </thead>
              <tbody>
                {filteredCalendar.map(c => (
                  <tr key={c.id} className="border-b">
                    <td className="py-2 pr-3 font-medium">{c.title}</td>
                    <td className="py-2 pr-3 capitalize">{c.author}</td>
                    <td className="py-2 pr-3">
                      <Badge variant="outline">{c.status}</Badge>
                    </td>
                    <td className="py-2 pr-3 text-xs text-slate-500">
                      {c.submitted_at?.slice(0, 10)}
                    </td>
                    <td className="py-2 pr-3">{c.signals || 0}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>

          {/* SECTION 4: Lead Capture */}
          <Card className="p-5">
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Users className="w-5 h-5 text-blue-600" />
              Lead Capture
            </h2>
            <div className="grid grid-cols-3 gap-4 mb-4">
              <div>
                <div className="text-xs text-slate-500">This Week</div>
                <div className="text-2xl font-bold">{leads.this_week}</div>
              </div>
              <div>
                <div className="text-xs text-slate-500">Last Week</div>
                <div className="text-2xl font-bold text-slate-500">{leads.last_week}</div>
              </div>
              <div>
                <div className="text-xs text-slate-500">Change</div>
                <div className={`text-2xl font-bold ${leads.delta_pct >= 0 ? "text-green-600" : "text-red-600"}`}>
                  {leads.delta_pct >= 0 ? "+" : ""}{leads.delta_pct}%
                </div>
              </div>
            </div>
            {leads.by_content && leads.by_content.length > 0 && (
              <div className="space-y-1">
                <div className="text-xs font-semibold uppercase tracking-wide text-slate-600 mb-2">Top by Content</div>
                {leads.by_content.slice(0, 5).map((c: any, i: number) => (
                  <div key={i} className="flex items-center gap-2">
                    <div className="flex-1 text-sm truncate">{c.content_title || "Untitled"}</div>
                    <div className="text-xs font-bold w-8 text-right">{c.leads}</div>
                    <div className="bg-blue-200 h-2 rounded" style={{ width: `${Math.min(c.leads * 20, 200)}px` }} />
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>

        {/* RIGHT PANEL — 40% — Marketing Assistant Chat */}
        <div className="w-2/5 border-l bg-white flex flex-col">
          <div className="border-b px-4 py-3">
            <h2 className="font-semibold flex items-center gap-2">
              <MessageSquare className="w-5 h-5" />
              Marketing Assistant
            </h2>
            <div className="text-xs text-slate-500">Powered by Gemini · Reads from content_submissions, company_scores, marketing_leads</div>
          </div>

          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {messages.length === 0 && (
              <div className="text-sm text-slate-500 space-y-2">
                <div>Ask me anything about your content:</div>
                <div className="space-y-1">
                  <button className="text-left text-blue-600 hover:underline block" onClick={() => sendMessage("What should I write this week?")}>→ What should I write this week?</button>
                  <button className="text-left text-blue-600 hover:underline block" onClick={() => sendMessage("Tell me about the companies that need content about digital transformation")}>→ Companies needing digital transformation content</button>
                  <button className="text-left text-blue-600 hover:underline block" onClick={() => sendMessage("Draft an outline for a piece about nonprofits struggling with digital transformation")}>→ Draft an outline on nonprofit struggles</button>
                </div>
              </div>
            )}
            {messages.map((m, i) => (
              <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
                <div className={`max-w-[85%] px-3 py-2 rounded-lg text-sm whitespace-pre-wrap ${
                  m.role === "user" ? "bg-blue-600 text-white" : "bg-slate-100 text-slate-900"
                }`}>
                  {m.content}
                </div>
              </div>
            ))}
            {chatLoading && (
              <div className="flex items-center gap-2 text-sm text-slate-500">
                <Loader2 className="w-4 h-4 animate-spin" /> Thinking...
              </div>
            )}
            <div ref={chatEndRef} />
          </div>

          <form
            onSubmit={(e) => { e.preventDefault(); sendMessage(chatInput) }}
            className="border-t p-3 flex gap-2"
          >
            <Input
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              placeholder="Ask the Marketing Assistant..."
              disabled={chatLoading}
            />
            <Button type="submit" disabled={chatLoading || !chatInput.trim()}>
              <Send className="w-4 h-4" />
            </Button>
          </form>
        </div>
      </div>
    </div>
  )
}
