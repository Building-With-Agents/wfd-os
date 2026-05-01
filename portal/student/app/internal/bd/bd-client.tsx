"use client"
import { useEffect, useState, useRef } from "react"
import { apiFetch } from "@/lib/fetch"
import {
  Flame, Clock, Mail, Linkedin, MessageSquare, ArrowRight, Send,
  CheckCircle2, AlertCircle, Loader2, RefreshCw, ChevronRight, User,
  Inbox, ChevronDown, ChevronUp, Edit2, Trash2, X,
} from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"

const API = "/api/consulting"
const ASSISTANT_API = "/api/assistant"

interface Priority {
  id?: number
  company_name?: string
  contact_name?: string
  contact_title?: string
  signal_type?: string
  signal_detail?: string
  priority?: string
  detected_at?: string
  // For new_hot
  company_domain?: string
  confidence?: string
  scoring_rationale?: string
  recommended_buyer?: string
  tier_assigned_at?: string
}

interface Prospect {
  company_name: string
  company_domain: string
  confidence: string
  recommended_buyer: string
  contact_id?: number
  contact_name?: string
  contact_title?: string
  contact_email?: string
  match_confidence?: string
  pipeline_stage?: string
  days_since_scored?: number
  scoring_rationale?: string
}

interface WarmSignal {
  id: number
  company_name: string
  company_domain: string
  contact_name: string
  contact_title: string
  signal_type: string
  signal_detail: string
  priority: string
  detected_at: string
}

interface PipelineCard {
  id: number
  company_name: string
  company_domain: string
  contact_name: string
  contact_title: string
  contact_email: string
  company_tier: string
  pipeline_stage: string
}

interface EmailDraft {
  id: number
  company_name: string
  company_domain: string
  contact_name: string
  contact_title?: string
  contact_email: string
  sender: string
  sender_email: string
  subject_line: string
  touch_1_body: string
  touch_2_body: string
  touch_3_body: string
  sequence_status: string
  created_at: string
}

interface ChatMessage {
  role: "user" | "assistant"
  content: string
}

const STAGES = [
  "Identified", "LinkedIn Sent", "LinkedIn Connected", "Email Sent",
  "Replied", "Conversation", "Proposal", "Client",
]

// Props injected by the server component wrapper (app/internal/bd/page.tsx).
// First paint uses these values — no reliance on client-side useEffect fetches.
// See CLAUDE.md "Standing rule — Portal pages that show live data".
interface BDClientProps {
  initialPriorities?: { signals: Priority[]; new_hot: Priority[] } | null
  initialHotProspects?: Prospect[] | null
  initialWarmSignals?: WarmSignal[] | null
  initialPipeline?: { stages: string[]; pipeline: Record<string, PipelineCard[]> } | null
  initialEmailDrafts?: EmailDraft[] | null
}

export default function BDCommandCenter(props: BDClientProps) {
  const [priorities, setPriorities] = useState<{ signals: Priority[], new_hot: Priority[] }>(
    props.initialPriorities || { signals: [], new_hot: [] }
  )
  const [hotProspects, setHotProspects] = useState<Prospect[]>(props.initialHotProspects || [])
  const [warmSignals, setWarmSignals] = useState<WarmSignal[]>(props.initialWarmSignals || [])
  const [pipeline, setPipeline] = useState<{ stages: string[], pipeline: Record<string, PipelineCard[]> }>(
    props.initialPipeline || { stages: STAGES, pipeline: {} }
  )
  const [emailDrafts, setEmailDrafts] = useState<EmailDraft[]>(props.initialEmailDrafts || [])
  const [expandedDraft, setExpandedDraft] = useState<number | null>(null)
  const [editingDraft, setEditingDraft] = useState<number | null>(null)
  const [editSubject, setEditSubject] = useState("")
  const [editBody, setEditBody] = useState("")
  const [draftActionLoading, setDraftActionLoading] = useState<number | null>(null)
  // Start loading=false when SSR provided any data; only show loading spinner
  // if we actually need to fetch client-side (fallback path)
  const [loading, setLoading] = useState(!props.initialHotProspects)

  // Chat state
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [chatInput, setChatInput] = useState("")
  const [chatLoading, setChatLoading] = useState(false)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const chatEndRef = useRef<HTMLDivElement>(null)

  // Suggestion pills shown in the chat panel. Starts with a curated default
  // set so Jason can click instead of typing; updated dynamically by the
  // assistant's extract_suggestions() override after each response.
  //
  // IMPORTANT: Every pill phrase must be SPECIFIC and unambiguous. Phrases
  // like "Show me the top Hot prospect's messaging" caused Gemini to pick
  // COMC (which has no draft) instead of a Hot prospect that actually has
  // a draft — context poisoning followed. Always reference a specific
  // company or a specific tool action.
  const DEFAULT_PILLS = [
    "What should I work on today?",
    "Show me all 5 email drafts waiting for approval",
    "Categorize my prospects by consulting fit",
    "Which are real consulting fits vs content targets?",
    "Tell me about Mountain West Conference",
    "Show me the Food & Friends email draft",
    "Generate a LinkedIn note for Harbor Path",
    "Where are my prospects in the pipeline?",
  ]
  const [suggestionPills, setSuggestionPills] = useState<string[]>(DEFAULT_PILLS)

  // Drag state
  const [dragCard, setDragCard] = useState<PipelineCard | null>(null)

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

      const [p, hp, ws, pl, ed] = await Promise.all([
        safeJson(`${API}/bd/priorities`),
        safeJson(`${API}/bd/hot-prospects`),
        safeJson(`${API}/bd/warm-signals`),
        safeJson(`${API}/bd/pipeline`),
        safeJson(`${API}/bd/email-drafts`),
      ])

      setPriorities({
        signals: p?.signals || [],
        new_hot: p?.new_hot || [],
      })
      setHotProspects(hp?.prospects || [])
      setWarmSignals(ws?.signals || [])
      setPipeline({
        stages: pl?.stages || STAGES,
        pipeline: pl?.pipeline || {},
      })
      setEmailDrafts(ed?.drafts || [])
    } catch (e) {
      console.error("Fetch error", e)
    } finally {
      setLoading(false)
    }
  }

  // SSR-first data loading: if server provided initialHotProspects we already
  // have data and skip the first fetchAll. Still refresh every 60s for live
  // updates while Jason has the tab open.
  useEffect(() => {
    if (!props.initialHotProspects) {
      // Fallback path — server-side fetch didn't run for some reason
      fetchAll()
    }
    const interval = setInterval(fetchAll, 60000)
    return () => clearInterval(interval)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  const startNewConversation = () => {
    setMessages([])
    setSessionId(null)
    setChatInput("")
    setSuggestionPills(DEFAULT_PILLS)
  }

  // Internal helper that actually sends a message. Takes an explicit session
  // id so callers can force a fresh session (for pill clicks) or continue the
  // existing session (for typed follow-ups). See sendMessage / sendPill below
  // for the two public wrappers.
  const sendMessageWithSession = async (msg: string, sessionOverride: string | null) => {
    if (!msg.trim()) return

    // If starting a fresh session, clear prior messages so the user sees a
    // clean chat panel. Prior Gemini contexts were poisoning responses —
    // once the assistant said "no draft for COMC" it got stuck referencing
    // COMC across every subsequent question.
    if (sessionOverride === null) {
      setMessages([{ role: "user", content: msg }])
      setSessionId(null)
    } else {
      setMessages(prev => [...prev, { role: "user", content: msg }])
    }
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
          agent_type: "bd",
          message: msg,
          session_id: sessionOverride,
          user_role: "jason",
        }),
      })

      // If we got a non-JSON response (e.g. ngrok interstitial HTML), surface
      // that clearly instead of silently choking on res.json().
      const contentType = res.headers.get("content-type") || ""
      if (!contentType.includes("application/json")) {
        const body = await res.text()
        console.error("[BD chat] non-JSON response", body.slice(0, 200))
        setMessages(prev => [...prev, {
          role: "assistant",
          content: `Error: assistant returned non-JSON (${res.status}). First 200 chars: ${body.slice(0, 200)}`,
        }])
        return
      }

      const data = await res.json()
      setMessages(prev => [...prev, { role: "assistant", content: data.response || "(no response)" }])
      if (data.session_id) setSessionId(data.session_id)
      // Update suggestion pills from the agent's extract_suggestions override.
      // Fall back to defaults if the agent didn't return any.
      if (Array.isArray(data.suggestions) && data.suggestions.length > 0) {
        setSuggestionPills(data.suggestions)
      } else {
        setSuggestionPills(DEFAULT_PILLS)
      }
    } catch (e: any) {
      console.error("[BD chat] fetch threw", e)
      setMessages(prev => [...prev, { role: "assistant", content: `Error: ${e.message}` }])
    } finally {
      setChatLoading(false)
    }
  }

  // Continue the existing conversation (used when Jason types a follow-up).
  const sendMessage = (msg: string) => sendMessageWithSession(msg, sessionId)

  // Start a fresh conversation (used when Jason clicks a suggestion pill or
  // a "Tell me more" button). This prevents Gemini context poisoning where
  // an earlier confused answer affects all subsequent responses.
  const sendPill = (msg: string) => sendMessageWithSession(msg, null)

  const loadProspectIntoChat = (companyName: string) => {
    sendPill(`Tell me about ${companyName}`)
  }

  const loadSignalIntoChat = (signal: WarmSignal) => {
    sendPill(`I have a warm signal from ${signal.contact_name} at ${signal.company_name} — they ${signal.signal_type}. What should I do next?`)
  }

  const updatePipelineStage = async (contactId: number, newStage: string) => {
    try {
      await apiFetch(`${API}/bd/pipeline/${contactId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ stage: newStage }),
      })
      fetchAll()
    } catch (e) {
      console.error("Stage update failed", e)
    }
  }

  const startEditDraft = (draft: EmailDraft) => {
    setEditingDraft(draft.id)
    setEditSubject(draft.subject_line)
    setEditBody(draft.touch_1_body)
  }

  const cancelEditDraft = () => {
    setEditingDraft(null)
    setEditSubject("")
    setEditBody("")
  }

  const saveEditDraft = async (draftId: number) => {
    setDraftActionLoading(draftId)
    try {
      await apiFetch(`${API}/bd/email-drafts/${draftId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          subject_line: editSubject,
          touch_1_body: editBody,
        }),
      })
      setEditingDraft(null)
      fetchAll()
    } catch (e: any) {
      alert(`Save failed: ${e.message}`)
    } finally {
      setDraftActionLoading(null)
    }
  }

  const approveDraft = async (draftId: number, companyName: string) => {
    if (!confirm(`Send Touch 1 email to ${companyName}? This will send a real email.`)) return
    setDraftActionLoading(draftId)
    try {
      const res = await apiFetch(`${API}/bd/email-drafts/${draftId}/approve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ approved_by: "ritu" }),
      })
      const data = await res.json()
      if (data.success) {
        alert(`Sent to ${data.sent_to}!\n${data.next_touch}`)
        fetchAll()
      } else {
        alert(`Send failed: ${JSON.stringify(data)}`)
      }
    } catch (e: any) {
      alert(`Approve failed: ${e.message}`)
    } finally {
      setDraftActionLoading(null)
    }
  }

  const rejectDraft = async (draftId: number, companyName: string) => {
    if (!confirm(`Reject and delete draft for ${companyName}?`)) return
    setDraftActionLoading(draftId)
    try {
      await apiFetch(`${API}/bd/email-drafts/${draftId}`, { method: "DELETE" })
      fetchAll()
    } catch (e: any) {
      alert(`Reject failed: ${e.message}`)
    } finally {
      setDraftActionLoading(null)
    }
  }

  const markActioned = async (signalId: number) => {
    try {
      await apiFetch(`${API}/bd/signals/${signalId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ actioned: true }),
      })
      fetchAll()
    } catch (e) {
      console.error("Mark actioned failed", e)
    }
  }

  const handleDragStart = (card: PipelineCard) => setDragCard(card)
  const handleDragOver = (e: React.DragEvent) => e.preventDefault()
  const handleDrop = (stage: string) => {
    if (dragCard && dragCard.pipeline_stage !== stage) {
      updatePipelineStage(dragCard.id, stage)
    }
    setDragCard(null)
  }

  return (
    <div className="min-h-screen bg-slate-100">
      {/* Header with internal nav */}
      <div className="bg-white border-b border-slate-200 px-6 py-3">
        <div className="flex items-center justify-between">
          <h1 className="text-xl font-bold text-slate-900">BD Command Center</h1>
          <nav className="flex gap-4 text-sm">
            <a href="/internal" className="text-slate-600 hover:text-slate-900">Internal Home</a>
            <a href="/internal/bd" className="text-blue-600 font-semibold">BD</a>
            <a href="/internal/marketing" className="text-slate-600 hover:text-slate-900">Marketing Workflow</a>
            <a href="/internal/jessica" className="text-slate-600 hover:text-slate-900">Jessica</a>
          </nav>
        </div>
      </div>

      <div className="flex h-[calc(100vh-57px)]">
        {/* LEFT PANEL — 60% */}
        <div className="w-3/5 overflow-y-auto p-6 space-y-6">

          {/* SECTION 1: Today's Priorities */}
          <Card className="p-5">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold flex items-center gap-2">
                <Flame className="w-5 h-5 text-orange-500" />
                Today's Priorities
              </h2>
              <Button size="sm" variant="ghost" onClick={fetchAll}>
                <RefreshCw className="w-4 h-4" />
              </Button>
            </div>

            {loading && <div className="text-sm text-slate-500">Loading...</div>}

            {!loading && (priorities.signals?.length || 0) === 0 && (priorities.new_hot?.length || 0) === 0 && (
              <div className="text-sm text-slate-500">No urgent items right now.</div>
            )}

            {(priorities.signals || []).map((s, i) => (
              <div key={`sig-${i}`} className="border-l-4 border-orange-500 bg-orange-50 p-3 rounded mb-2">
                <div className="font-medium">{s.company_name}</div>
                <div className="text-sm text-slate-600">{s.contact_name} ({s.contact_title})</div>
                <div className="text-xs text-slate-500 mt-1">{s.signal_detail}</div>
                <Button size="sm" className="mt-2" onClick={() => sendMessage(`Help me respond to the warm signal from ${s.company_name}`)}>
                  Ask Assistant
                </Button>
              </div>
            ))}

            {(priorities.new_hot || []).map((h, i) => (
              <div key={`hot-${i}`} className="border-l-4 border-red-500 bg-red-50 p-3 rounded mb-2">
                <div className="flex items-center gap-2">
                  <Badge variant="destructive">New Hot</Badge>
                  <span className="font-medium">{h.company_name}</span>
                </div>
                <div className="text-xs text-slate-600 mt-1">{h.scoring_rationale?.slice(0, 150)}...</div>
                <Button size="sm" className="mt-2" onClick={() => loadProspectIntoChat(h.company_name!)}>
                  Tell me more
                </Button>
              </div>
            ))}
          </Card>

          {/* SECTION 1.5: Email Drafts Awaiting Approval */}
          <Card className="p-5">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold flex items-center gap-2">
                <Inbox className="w-5 h-5 text-blue-600" />
                Email Drafts Awaiting Approval ({emailDrafts.length})
              </h2>
            </div>

            {emailDrafts.length === 0 && (
              <div className="text-sm text-slate-500">No drafts pending review.</div>
            )}

            <div className="space-y-2">
              {emailDrafts.map(d => (
                <div key={d.id} className="border rounded bg-blue-50/30">
                  {/* Header row */}
                  <div
                    className="p-3 cursor-pointer hover:bg-blue-50"
                    onClick={() => setExpandedDraft(expandedDraft === d.id ? null : d.id)}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          {expandedDraft === d.id ? (
                            <ChevronUp className="w-4 h-4 text-slate-400 flex-shrink-0" />
                          ) : (
                            <ChevronDown className="w-4 h-4 text-slate-400 flex-shrink-0" />
                          )}
                          <span className="font-medium truncate">{d.subject_line}</span>
                        </div>
                        <div className="text-xs text-slate-600 ml-6 mt-1">
                          To: <span className="font-medium">{d.contact_name}</span> ({d.contact_email}) · {d.company_name} · from {d.sender}
                        </div>
                      </div>
                      <Badge variant="outline" className="text-amber-700 border-amber-400">
                        pending review
                      </Badge>
                    </div>
                  </div>

                  {/* Expanded body */}
                  {expandedDraft === d.id && (
                    <div className="border-t p-3 bg-white">
                      {editingDraft === d.id ? (
                        <div className="space-y-2">
                          <div>
                            <label className="text-xs font-semibold text-slate-600">Subject</label>
                            <Input
                              value={editSubject}
                              onChange={(e) => setEditSubject(e.target.value)}
                              className="mt-1"
                            />
                          </div>
                          <div>
                            <label className="text-xs font-semibold text-slate-600">Body</label>
                            <Textarea
                              value={editBody}
                              onChange={(e) => setEditBody(e.target.value)}
                              rows={10}
                              className="mt-1 font-mono text-sm"
                            />
                          </div>
                          <div className="flex gap-2">
                            <Button
                              size="sm"
                              onClick={() => saveEditDraft(d.id)}
                              disabled={draftActionLoading === d.id}
                            >
                              {draftActionLoading === d.id ? <Loader2 className="w-4 h-4 animate-spin" /> : "Save changes"}
                            </Button>
                            <Button size="sm" variant="outline" onClick={cancelEditDraft}>
                              Cancel
                            </Button>
                          </div>
                        </div>
                      ) : (
                        <>
                          <div className="text-sm whitespace-pre-wrap text-slate-800 mb-3 p-3 bg-slate-50 rounded">
                            {d.touch_1_body}
                          </div>
                          {d.touch_2_body && (
                            <details className="mb-2">
                              <summary className="text-xs font-semibold text-slate-600 cursor-pointer hover:text-slate-900">
                                Touch 2 (auto-sends in 5 days if no reply) ▾
                              </summary>
                              <div className="text-xs whitespace-pre-wrap text-slate-700 mt-2 p-3 bg-slate-50 rounded">
                                {d.touch_2_body}
                              </div>
                            </details>
                          )}
                          {d.touch_3_body && (
                            <details className="mb-3">
                              <summary className="text-xs font-semibold text-slate-600 cursor-pointer hover:text-slate-900">
                                Touch 3 (auto-sends in 10 days if no reply) ▾
                              </summary>
                              <div className="text-xs whitespace-pre-wrap text-slate-700 mt-2 p-3 bg-slate-50 rounded">
                                {d.touch_3_body}
                              </div>
                            </details>
                          )}
                          <div className="flex gap-2 pt-2 border-t">
                            <Button
                              size="sm"
                              className="bg-green-600 hover:bg-green-700"
                              onClick={() => approveDraft(d.id, d.company_name)}
                              disabled={draftActionLoading === d.id}
                            >
                              {draftActionLoading === d.id ? (
                                <Loader2 className="w-4 h-4 animate-spin mr-1" />
                              ) : (
                                <Send className="w-4 h-4 mr-1" />
                              )}
                              Approve & Send
                            </Button>
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => startEditDraft(d)}
                              disabled={draftActionLoading === d.id}
                            >
                              <Edit2 className="w-4 h-4 mr-1" /> Edit
                            </Button>
                            <Button
                              size="sm"
                              variant="outline"
                              className="text-red-600 hover:bg-red-50"
                              onClick={() => rejectDraft(d.id, d.company_name)}
                              disabled={draftActionLoading === d.id}
                            >
                              <Trash2 className="w-4 h-4 mr-1" /> Reject
                            </Button>
                          </div>
                        </>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </Card>

          {/* SECTION 2: Hot Prospects Table */}
          <Card className="p-5">
            <h2 className="text-lg font-semibold mb-4">Hot Prospects ({hotProspects.length})</h2>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left">
                    <th className="py-2 pr-3">Company</th>
                    <th className="py-2 pr-3">Confidence</th>
                    <th className="py-2 pr-3">Recommended Buyer</th>
                    <th className="py-2 pr-3">Email Status</th>
                    <th className="py-2 pr-3">Days</th>
                  </tr>
                </thead>
                <tbody>
                  {hotProspects.map(p => (
                    <tr
                      key={p.company_domain}
                      className="border-b hover:bg-blue-50 cursor-pointer"
                      onClick={() => loadProspectIntoChat(p.company_name)}
                    >
                      <td className="py-2 pr-3 font-medium">{p.company_name}</td>
                      <td className="py-2 pr-3">
                        <Badge variant={p.confidence === "High" ? "default" : "secondary"}>{p.confidence}</Badge>
                      </td>
                      <td className="py-2 pr-3 text-xs text-slate-600">{p.recommended_buyer?.slice(0, 60)}</td>
                      <td className="py-2 pr-3">
                        {p.contact_email ? (
                          <Badge variant="outline" className="text-green-700">
                            <Mail className="w-3 h-3 mr-1" /> {p.match_confidence}
                          </Badge>
                        ) : (
                          <Badge variant="outline" className="text-slate-500">No email</Badge>
                        )}
                      </td>
                      <td className="py-2 pr-3 text-xs">{p.days_since_scored}d</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>

          {/* SECTION 3: Warm Signals Queue */}
          <Card className="p-5">
            <h2 className="text-lg font-semibold mb-4">
              Warm Signals Queue ({warmSignals.length})
            </h2>
            {warmSignals.length === 0 && (
              <div className="text-sm text-slate-500">No unacted warm signals.</div>
            )}
            <div className="space-y-2">
              {warmSignals.map(s => (
                <div key={s.id} className="border rounded p-3 bg-yellow-50">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="font-medium">{s.contact_name}, {s.contact_title}</div>
                      <div className="text-sm text-slate-600">{s.company_name}</div>
                      <Badge variant="outline" className="mt-1">{s.signal_type}</Badge>
                    </div>
                    <div className="flex gap-2">
                      <Button size="sm" variant="outline" onClick={() => markActioned(s.id)}>
                        <CheckCircle2 className="w-4 h-4 mr-1" /> Mark Actioned
                      </Button>
                      <Button size="sm" onClick={() => loadSignalIntoChat(s)}>
                        Ask Assistant
                      </Button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </Card>

          {/* SECTION 4: Pipeline Tracker */}
          <Card className="p-5">
            <h2 className="text-lg font-semibold mb-4">Pipeline Tracker</h2>
            <div className="overflow-x-auto">
              <div className="flex gap-3 min-w-max pb-2">
                {pipeline.stages?.map(stage => (
                  <div
                    key={stage}
                    className="w-48 flex-shrink-0 bg-slate-50 rounded p-2"
                    onDragOver={handleDragOver}
                    onDrop={() => handleDrop(stage)}
                  >
                    <div className="text-xs font-semibold uppercase tracking-wide text-slate-600 mb-2">
                      {stage} ({pipeline.pipeline?.[stage]?.length || 0})
                    </div>
                    <div className="space-y-2">
                      {pipeline.pipeline?.[stage]?.map(card => (
                        <div
                          key={card.id}
                          draggable
                          onDragStart={() => handleDragStart(card)}
                          className="bg-white border rounded p-2 cursor-move hover:shadow"
                        >
                          <div className="text-xs font-semibold">{card.company_name}</div>
                          <div className="text-xs text-slate-500">{card.contact_name}</div>
                          <Badge variant="outline" className="mt-1 text-xs">{card.company_tier}</Badge>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </Card>
        </div>

        {/* RIGHT PANEL — 40% — BD Assistant Chat */}
        <div className="w-2/5 border-l bg-white flex flex-col">
          <div className="border-b px-4 py-3 flex items-start justify-between gap-2">
            <div>
              <h2 className="font-semibold flex items-center gap-2">
                <MessageSquare className="w-5 h-5" />
                BD Assistant
              </h2>
              <div className="text-xs text-slate-500">Powered by Gemini · Reads from company_scores, warm_signals, hot_warm_contacts</div>
            </div>
            {messages.length > 0 && (
              <button
                type="button"
                onClick={startNewConversation}
                className="flex-shrink-0 rounded border border-slate-200 px-2 py-1 text-xs text-slate-600 hover:bg-slate-50"
                title="Start a fresh conversation — prior context is cleared"
              >
                + New
              </button>
            )}
          </div>

          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {messages.length === 0 && (
              <div className="text-sm text-slate-500">
                Ask me anything about your prospects, or tap one of the suggestions below.
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

          {/* Suggestion pills — static defaults on load, dynamic follow-ups
              after each assistant response via extract_suggestions().
              Clicking a pill ALWAYS starts a fresh conversation (sendPill)
              so Gemini never carries confused context forward from an
              earlier response. */}
          {suggestionPills.length > 0 && !chatLoading && (
            <div className="border-t bg-slate-50/50 p-3">
              <div className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-slate-500">
                Try one of these (starts a fresh conversation)
              </div>
              <div className="flex flex-wrap gap-1.5">
                {suggestionPills.map((pill, i) => (
                  <button
                    key={`${pill}-${i}`}
                    type="button"
                    onClick={() => sendPill(pill)}
                    disabled={chatLoading}
                    className="rounded-full border border-blue-200 bg-white px-3 py-1 text-xs text-blue-700 hover:border-blue-400 hover:bg-blue-50 disabled:opacity-50"
                  >
                    {pill}
                  </button>
                ))}
              </div>
            </div>
          )}

          <form
            onSubmit={(e) => { e.preventDefault(); sendMessage(chatInput) }}
            className="border-t p-3 flex gap-2"
          >
            <Input
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              placeholder="Ask the BD Assistant..."
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
