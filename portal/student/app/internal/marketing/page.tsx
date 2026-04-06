"use client"

import { useEffect, useState } from "react"
import {
  Compass, FileText, CheckCircle2, Clock, Send, Eye, ExternalLink,
  ArrowLeft, ArrowRight, Tag, RefreshCw, Loader2, AlertCircle,
} from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog"
import { Separator } from "@/components/ui/separator"

const API_BASE = "/api/marketing"

interface Content {
  id: string
  content_type: string
  title: string
  slug: string
  author: string
  audience_tag: string
  status: string
  content_body: string | null
  sharepoint_doc_url: string | null
  published_url: string | null
  approved_by: string | null
  approved_at: string | null
  published_at: string | null
  created_at: string
}

function renderMarkdown(text: string): string {
  // Simple markdown-like rendering for content preview
  return text
    .replace(/## (.+)/g, '<h2 class="text-lg font-bold text-foreground mt-4 mb-2">$1</h2>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\n\n/g, '</p><p class="text-sm text-foreground/80 leading-relaxed mb-3">')
    .replace(/\n/g, '<br/>')
    .replace(/^/, '<p class="text-sm text-foreground/80 leading-relaxed mb-3">')
    + '</p>'
}

const TYPE_BADGE: Record<string, { label: string; color: string }> = {
  blog_post: { label: "Blog", color: "bg-blue-100 text-blue-700" },
  case_study: { label: "Case Study", color: "bg-purple-100 text-purple-700" },
  email_sequence: { label: "Sequence", color: "bg-amber-100 text-amber-700" },
  sales_asset: { label: "Asset", color: "bg-green-100 text-green-700" },
  social_post: { label: "Social", color: "bg-pink-100 text-pink-700" },
}

const STATUS_CONFIG: Record<string, { label: string; color: string; border: string; bg: string }> = {
  draft: { label: "DRAFT", color: "text-slate-600", border: "border-slate-300", bg: "bg-slate-50" },
  in_review: { label: "IN REVIEW", color: "text-amber-700", border: "border-amber-300", bg: "bg-amber-50" },
  approved: { label: "APPROVED", color: "text-blue-700", border: "border-blue-300", bg: "bg-blue-50" },
  published: { label: "PUBLISHED", color: "text-green-700", border: "border-green-300", bg: "bg-green-50" },
  active: { label: "ACTIVE", color: "text-purple-700", border: "border-purple-300", bg: "bg-purple-50" },
  archived: { label: "ARCHIVED", color: "text-slate-500", border: "border-slate-200", bg: "bg-slate-50" },
}

function formatDate(iso: string | null): string {
  if (!iso) return ""
  return new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric" })
}

export default function MarketingDashboard() {
  const [pipeline, setPipeline] = useState<Record<string, Content[]>>({})
  const [stats, setStats] = useState<Record<string, number>>({})
  const [loading, setLoading] = useState(true)
  const [acting, setActing] = useState<string | null>(null)
  const [viewing, setViewing] = useState<Content | null>(null)
  const [viewBody, setViewBody] = useState<string | null>(null)
  const [loadingBody, setLoadingBody] = useState(false)

  const loadData = () => {
    fetch(`${API_BASE}/pipeline`)
      .then((r) => r.json())
      .then((d) => {
        setPipeline(d.pipeline || {})
        setStats(d.stats || {})
      })
      .finally(() => setLoading(false))
  }

  useEffect(() => { loadData() }, [])

  const updateStatus = async (id: string, status: string, approvedBy?: string) => {
    setActing(id)
    try {
      await fetch(`${API_BASE}/content/${id}/status`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status, approved_by: approvedBy }),
      })
      loadData()
    } finally {
      setActing(null)
    }
  }

  const markLoaded = async (id: string) => {
    setActing(id)
    try {
      await fetch(`${API_BASE}/content/${id}/mark-loaded`, { method: "POST" })
      loadData()
    } finally {
      setActing(null)
    }
  }

  const viewContent = async (c: Content) => {
    setViewing(c)
    setLoadingBody(true)
    setViewBody(null)
    try {
      const r = await fetch(`${API_BASE}/content/${c.id}`)
      if (r.ok) {
        const full = await r.json()
        setViewBody(full.content_body || "(no content)")
      }
    } catch {
      setViewBody("(failed to load content)")
    } finally {
      setLoadingBody(false)
    }
  }

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <Loader2 className="h-10 w-10 animate-spin text-primary" />
      </div>
    )
  }

  const columns = ["in_review", "approved", "published", "active"] as const

  return (
    <div className="min-h-screen bg-slate-100">
      <header className="border-b bg-white">
        <div className="mx-auto max-w-[1600px] px-4 py-3 sm:px-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <a href="/internal" className="flex items-center gap-1 text-xs text-muted-foreground hover:text-primary">
                <ArrowLeft className="h-3 w-3" /> Pipeline
              </a>
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary">
                <FileText className="h-5 w-5 text-primary-foreground" />
              </div>
              <div>
                <h1 className="text-lg font-bold text-foreground">Marketing Content</h1>
                <p className="text-xs text-muted-foreground">Content pipeline — draft to published</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Button size="sm" variant="outline" className="gap-1 text-xs" onClick={loadData}>
                <RefreshCw className="h-3.5 w-3.5" /> Refresh
              </Button>
              <a href="/cfa/ai-consulting/blog">
                <Button size="sm" variant="outline" className="gap-1 text-xs">
                  <Eye className="h-3.5 w-3.5" /> View blog
                </Button>
              </a>
            </div>
          </div>

          {/* Stats row */}
          <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4">
            <Card className="border-l-4 border-amber-500 p-3">
              <p className="text-xs text-muted-foreground">In review</p>
              <p className="text-xl font-bold">{stats.in_review || 0}</p>
            </Card>
            <Card className="border-l-4 border-blue-500 p-3">
              <p className="text-xs text-muted-foreground">Approved</p>
              <p className="text-xl font-bold">{stats.approved || 0}</p>
            </Card>
            <Card className="border-l-4 border-green-500 p-3">
              <p className="text-xs text-muted-foreground">Published</p>
              <p className="text-xl font-bold">{stats.published || 0}</p>
            </Card>
            <Card className="border-l-4 border-purple-500 p-3">
              <p className="text-xs text-muted-foreground">Active sequences</p>
              <p className="text-xl font-bold">{stats.active || 0}</p>
            </Card>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-[1600px] px-4 py-4 sm:px-6">
        <div className="flex gap-3 overflow-x-auto pb-2">
          {columns.map((status) => {
            const cfg = STATUS_CONFIG[status]
            const items = pipeline[status] || []
            return (
              <div key={status} className={`rounded-lg border-2 ${cfg.border} ${cfg.bg} p-3 flex-1 min-w-[250px]`}>
                <div className="mb-3 flex items-center justify-between">
                  <h3 className={`text-xs font-bold ${cfg.color}`}>{cfg.label}</h3>
                  <Badge variant="secondary" className={`text-xs ${cfg.color}`}>{items.length}</Badge>
                </div>
                <div className="space-y-2">
                  {items.length === 0 && (
                    <p className="py-6 text-center text-xs italic text-muted-foreground">No content</p>
                  )}
                  {items.map((c) => {
                    const tb = TYPE_BADGE[c.content_type] || { label: c.content_type, color: "bg-slate-100 text-slate-600" }
                    const isActing = acting === c.id
                    return (
                      <Card key={c.id} className="p-3 space-y-2 text-sm">
                        <div className="flex items-start justify-between gap-2">
                          <div className="min-w-0 flex-1">
                            <p className="font-semibold text-foreground text-xs truncate">{c.title}</p>
                            <div className="mt-1 flex items-center gap-1.5">
                              <span className={`rounded px-1.5 py-0.5 text-[9px] font-semibold ${tb.color}`}>{tb.label}</span>
                              <span className="text-[9px] text-muted-foreground">{c.audience_tag?.replace(/_/g, " ")}</span>
                            </div>
                          </div>
                        </div>
                        <p className="text-[10px] text-muted-foreground">{c.author} · {formatDate(c.created_at)}</p>

                        <div className="flex flex-col gap-1">
                          <Button
                            size="sm"
                            variant="outline"
                            className="h-6 text-[10px] gap-1"
                            onClick={() => viewContent(c)}
                          >
                            <Eye className="h-3 w-3" /> View content
                          </Button>
                          {status === "in_review" && (
                            <Button
                              size="sm"
                              className="h-6 text-[10px] gap-1"
                              disabled={isActing}
                              onClick={() => updateStatus(c.id, "approved", "Ritu Bahl")}
                            >
                              {isActing ? <Loader2 className="h-3 w-3 animate-spin" /> : <CheckCircle2 className="h-3 w-3" />}
                              Approve
                            </Button>
                          )}
                          {status === "approved" && c.content_type !== "email_sequence" && (
                            <Button
                              size="sm"
                              className="h-6 text-[10px] gap-1 bg-green-600 hover:bg-green-700"
                              disabled={isActing}
                              onClick={() => updateStatus(c.id, "published")}
                            >
                              {isActing ? <Loader2 className="h-3 w-3 animate-spin" /> : <Send className="h-3 w-3" />}
                              Publish now
                            </Button>
                          )}
                          {status === "approved" && c.content_type === "email_sequence" && (
                            <Button
                              size="sm"
                              className="h-6 text-[10px] gap-1 bg-purple-600 hover:bg-purple-700"
                              disabled={isActing}
                              onClick={() => markLoaded(c.id)}
                            >
                              {isActing ? <Loader2 className="h-3 w-3 animate-spin" /> : <CheckCircle2 className="h-3 w-3" />}
                              Mark loaded in Apollo
                            </Button>
                          )}
                          {c.sharepoint_doc_url && (
                            <a href={c.sharepoint_doc_url} target="_blank" rel="noopener noreferrer">
                              <Button size="sm" variant="ghost" className="w-full h-6 text-[10px] gap-1">
                                <ExternalLink className="h-3 w-3" /> SharePoint
                              </Button>
                            </a>
                          )}
                        </div>
                      </Card>
                    )
                  })}
                </div>
              </div>
            )
          })}
        </div>
      </main>

      {/* Content Preview Modal */}
      <Dialog open={!!viewing} onOpenChange={(o) => { if (!o) { setViewing(null); setViewBody(null) } }}>
        <DialogContent className="max-w-[800px] max-h-[90vh] overflow-y-auto">
          <DialogTitle className="sr-only">Content preview</DialogTitle>
          {viewing && (
            <div className="space-y-4">
              {/* Header */}
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <span className={`rounded px-2 py-0.5 text-[10px] font-semibold ${(TYPE_BADGE[viewing.content_type] || { color: "bg-slate-100 text-slate-600" }).color}`}>
                    {(TYPE_BADGE[viewing.content_type] || { label: viewing.content_type }).label}
                  </span>
                  <span className={`rounded px-2 py-0.5 text-[10px] font-semibold ${(STATUS_CONFIG[viewing.status] || STATUS_CONFIG.draft).color} ${(STATUS_CONFIG[viewing.status] || STATUS_CONFIG.draft).bg}`}>
                    {viewing.status.toUpperCase()}
                  </span>
                  {viewing.audience_tag && (
                    <Badge variant="outline" className="text-[10px]">{viewing.audience_tag.replace(/_/g, " ")}</Badge>
                  )}
                </div>
                <h2 className="text-xl font-bold text-foreground">{viewing.title}</h2>
                <p className="mt-1 text-xs text-muted-foreground">
                  By {viewing.author || "CFA"} &middot; {formatDate(viewing.created_at)}
                  {viewing.approved_by && <> &middot; Approved by {viewing.approved_by}</>}
                  {viewing.published_at && <> &middot; Published {formatDate(viewing.published_at)}</>}
                </p>
              </div>

              <Separator />

              {/* Content body */}
              {loadingBody ? (
                <div className="flex items-center justify-center py-10">
                  <Loader2 className="h-6 w-6 animate-spin text-primary" />
                </div>
              ) : viewBody ? (
                <div
                  className="prose prose-sm max-w-none"
                  dangerouslySetInnerHTML={{ __html: renderMarkdown(viewBody) }}
                />
              ) : (
                <p className="text-sm italic text-muted-foreground">No content body available.</p>
              )}

              <Separator />

              {/* Actions */}
              <div className="flex flex-wrap gap-2">
                {viewing.status === "in_review" && (
                  <Button
                    size="sm"
                    className="gap-1"
                    disabled={acting === viewing.id}
                    onClick={() => {
                      updateStatus(viewing.id, "approved", "Ritu Bahl")
                      setViewing((v) => v ? { ...v, status: "approved", approved_by: "Ritu Bahl" } : null)
                    }}
                  >
                    <CheckCircle2 className="h-3.5 w-3.5" /> Approve
                  </Button>
                )}
                {viewing.status === "approved" && viewing.content_type !== "email_sequence" && (
                  <Button
                    size="sm"
                    className="gap-1 bg-green-600 hover:bg-green-700"
                    disabled={acting === viewing.id}
                    onClick={() => {
                      updateStatus(viewing.id, "published")
                      setViewing((v) => v ? { ...v, status: "published" } : null)
                    }}
                  >
                    <Send className="h-3.5 w-3.5" /> Publish now
                  </Button>
                )}
                {viewing.sharepoint_doc_url && (
                  <a href={viewing.sharepoint_doc_url} target="_blank" rel="noopener noreferrer">
                    <Button size="sm" variant="outline" className="gap-1">
                      <ExternalLink className="h-3.5 w-3.5" /> Open in SharePoint
                    </Button>
                  </a>
                )}
                {viewing.status === "published" && viewing.slug && (
                  <a href={`/cfa/ai-consulting/blog`} target="_blank" rel="noopener noreferrer">
                    <Button size="sm" variant="outline" className="gap-1">
                      <Eye className="h-3.5 w-3.5" /> View on blog
                    </Button>
                  </a>
                )}
                <Button size="sm" variant="ghost" onClick={() => { setViewing(null); setViewBody(null) }}>
                  Close
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}
