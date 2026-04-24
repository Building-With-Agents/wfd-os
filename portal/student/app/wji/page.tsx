"use client"
import { apiFetch } from "@/lib/fetch"

import { useEffect, useRef, useState } from "react"
import {
  Upload, FileSpreadsheet, FileText, CheckCircle2, AlertCircle,
  Users, Building, Briefcase, DollarSign, TrendingUp, Calendar,
  Loader2, X, Trash2, RefreshCw,
} from "lucide-react"
import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"

const API_BASE = "/api/wji"

interface Summary {
  placements_summary: {
    total_placements: number
    unique_students: number
    unique_employers: number
    unique_programs: number
    avg_wage: number | null
    latest_placement: string | null
  }
  payments_summary: {
    total_payments: number
    total_spent: number | null
    unique_vendors: number
    latest_payment: string | null
  }
  placements_by_program: { program: string; placements: number; avg_wage: number | null }[]
  placements_by_month: { month: string; placements: number }[]
  payments_by_category: { category: string; payments: number; total: number | null }[]
  recent_uploads: {
    id: number
    upload_type: string
    filename: string
    uploaded_by: string
    uploaded_at: string
    row_count: number
    success_count: number
    error_count: number
    status: string
  }[]
}

interface UploadResult {
  batch_id: number
  filename: string
  total_rows: number
  success_count: number
  error_count: number
  status: string
  column_mapping: Record<string, string>
  unmapped_headers: string[]
  errors: { row: number; error: string }[]
}

function formatCurrency(n: number | null): string {
  if (n === null || n === undefined) return "—"
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(n)
}

function formatDate(iso: string | null): string {
  if (!iso) return "—"
  return new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })
}

function formatDateTime(iso: string): string {
  const d = new Date(iso)
  const diffHours = Math.floor((Date.now() - d.getTime()) / 3600000)
  if (diffHours < 1) return "just now"
  if (diffHours < 24) return `${diffHours}h ago`
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" })
}

export default function WJIDashboard() {
  const [summary, setSummary] = useState<Summary | null>(null)
  const [loading, setLoading] = useState(true)
  const [uploadingType, setUploadingType] = useState<"placements" | "payments" | null>(null)
  const [result, setResult] = useState<UploadResult | null>(null)
  const [resultType, setResultType] = useState<"placements" | "payments" | null>(null)
  const [error, setError] = useState<string | null>(null)

  const placementsInput = useRef<HTMLInputElement>(null)
  const paymentsInput = useRef<HTMLInputElement>(null)

  const loadDashboard = () => {
    apiFetch(`${API_BASE}/dashboard`)
      .then((r) => (r.ok ? r.json() : null))
      .then(setSummary)
      .catch(() => setSummary(null))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    loadDashboard()
  }, [])

  const handleUpload = async (file: File, type: "placements" | "payments") => {
    setUploadingType(type)
    setError(null)
    setResult(null)
    setResultType(null)

    const form = new FormData()
    form.append("file", file)

    try {
      const res = await apiFetch(`${API_BASE}/upload/${type}`, {
        method: "POST",
        body: form,
      })
      if (!res.ok) {
        const txt = await res.text()
        throw new Error(`HTTP ${res.status}: ${txt.slice(0, 200)}`)
      }
      const data: UploadResult = await res.json()
      setResult(data)
      setResultType(type)
      loadDashboard()
    } catch (e: any) {
      setError(e.message || "Upload failed")
    } finally {
      setUploadingType(null)
      if (placementsInput.current) placementsInput.current.value = ""
      if (paymentsInput.current) paymentsInput.current.value = ""
    }
  }

  const deleteBatch = async (batchId: number) => {
    if (!confirm(`Delete upload batch #${batchId}? This removes all rows from that upload.`)) return
    try {
      const res = await apiFetch(`${API_BASE}/batches/${batchId}`, { method: "DELETE" })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      loadDashboard()
    } catch (e: any) {
      alert(`Delete failed: ${e.message}`)
    }
  }

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <Loader2 className="h-12 w-12 animate-spin text-primary" />
      </div>
    )
  }

  const p = summary?.placements_summary
  const pay = summary?.payments_summary

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b bg-white">
        <div className="mx-auto max-w-7xl px-4 py-4 sm:px-6">
          <nav className="mb-3 flex items-center justify-between text-sm">
            <a href="/" className="font-semibold text-foreground hover:text-primary">Computing for All</a>
            <div className="hidden items-center gap-5 md:flex">
              <a href="/cfa/ai-consulting" className="text-muted-foreground hover:text-foreground">AI Consulting</a>
              <a href="/youth" className="text-muted-foreground hover:text-foreground">Youth Program</a>
              <a href="/coalition" className="text-muted-foreground hover:text-foreground">Coalition</a>
              <a href="/resources" className="text-muted-foreground hover:text-foreground">Resources</a>
            </div>
          </nav>
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-foreground">WJI Grant Closeout Dashboard</h1>
              <p className="mt-1 text-sm text-muted-foreground">
                Upload WSAC placement reports and QuickBooks payment exports to track grant deliverables.
              </p>
            </div>
            <Button variant="outline" size="sm" className="gap-1" onClick={loadDashboard}>
              <RefreshCw className="h-4 w-4" /> Refresh
            </Button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl space-y-6 px-4 py-6 sm:px-6">
        {/* Data Status Banner */}
        {p && p.total_placements > 0 ? (
          <div className="flex items-center gap-3 rounded-lg border border-green-200 bg-green-50 p-4">
            <CheckCircle2 className="h-5 w-5 flex-shrink-0 text-green-600" />
            <div className="flex-1">
              <p className="text-sm font-medium text-green-800">
                Data loaded — last updated {summary?.recent_uploads?.[0]?.uploaded_at
                  ? new Date(summary.recent_uploads[0].uploaded_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })
                  : "recently"}
              </p>
              <p className="text-xs text-green-700">
                {p.total_placements} placements | {pay?.total_payments ?? 0} payments | {p.unique_employers ?? 0} employers
              </p>
            </div>
          </div>
        ) : (
          <div className="flex items-center gap-3 rounded-lg border border-amber-200 bg-amber-50 p-4">
            <AlertCircle className="h-5 w-5 flex-shrink-0 text-amber-600" />
            <div className="flex-1">
              <p className="text-sm font-medium text-amber-800">
                Placement data not yet loaded
              </p>
              <p className="text-xs text-amber-700">
                Upload WSAC export to activate placement tracking. Data expected: April 6, 2026
              </p>
            </div>
          </div>
        )}

        {/* Upload Cards */}
        <div className="grid gap-4 md:grid-cols-2">
          {/* Placements Upload */}
          <Card className="border-2 border-dashed border-primary/30 bg-primary/5 p-6">
            <div className="flex items-start gap-3">
              <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg bg-primary/10">
                <FileSpreadsheet className="h-5 w-5 text-primary" />
              </div>
              <div className="flex-1">
                <h3 className="font-semibold text-foreground">WSAC Placement Report</h3>
                <p className="mt-1 text-xs text-muted-foreground">
                  Upload the monthly WSAC Excel file (.xlsx). Columns are auto-detected.
                </p>
                <input
                  ref={placementsInput}
                  type="file"
                  accept=".xlsx,.xls,.xlsm"
                  className="hidden"
                  onChange={(e) => {
                    const f = e.target.files?.[0]
                    if (f) handleUpload(f, "placements")
                  }}
                />
                <Button
                  size="sm"
                  className="mt-3 gap-1"
                  disabled={uploadingType === "placements"}
                  onClick={() => placementsInput.current?.click()}
                >
                  {uploadingType === "placements" ? (
                    <>
                      <Loader2 className="h-3.5 w-3.5 animate-spin" /> Uploading…
                    </>
                  ) : (
                    <>
                      <Upload className="h-3.5 w-3.5" /> Choose Excel file
                    </>
                  )}
                </Button>
              </div>
            </div>
          </Card>

          {/* Payments Upload */}
          <Card className="border-2 border-dashed border-green-400/30 bg-green-50 p-6">
            <div className="flex items-start gap-3">
              <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg bg-green-100">
                <FileText className="h-5 w-5 text-green-700" />
              </div>
              <div className="flex-1">
                <h3 className="font-semibold text-foreground">QuickBooks Payment Export</h3>
                <p className="mt-1 text-xs text-muted-foreground">
                  Upload the QB CSV export (.csv). Date, Vendor, Amount, Category auto-mapped.
                </p>
                <input
                  ref={paymentsInput}
                  type="file"
                  accept=".csv"
                  className="hidden"
                  onChange={(e) => {
                    const f = e.target.files?.[0]
                    if (f) handleUpload(f, "payments")
                  }}
                />
                <Button
                  size="sm"
                  className="mt-3 gap-1 bg-green-600 hover:bg-green-700"
                  disabled={uploadingType === "payments"}
                  onClick={() => paymentsInput.current?.click()}
                >
                  {uploadingType === "payments" ? (
                    <>
                      <Loader2 className="h-3.5 w-3.5 animate-spin" /> Uploading…
                    </>
                  ) : (
                    <>
                      <Upload className="h-3.5 w-3.5" /> Choose CSV file
                    </>
                  )}
                </Button>
              </div>
            </div>
          </Card>
        </div>

        {/* Upload Result Banner */}
        {error && (
          <Card className="border-2 border-destructive/30 bg-destructive/5 p-4">
            <div className="flex items-start gap-2">
              <AlertCircle className="mt-0.5 h-5 w-5 flex-shrink-0 text-destructive" />
              <div className="flex-1">
                <p className="font-semibold text-destructive">Upload failed</p>
                <p className="text-xs text-destructive/80">{error}</p>
              </div>
              <button onClick={() => setError(null)}>
                <X className="h-4 w-4 text-destructive" />
              </button>
            </div>
          </Card>
        )}

        {result && (
          <Card
            className={`border-2 p-4 ${
              result.error_count === 0
                ? "border-green-300 bg-green-50"
                : result.success_count > 0
                ? "border-amber-300 bg-amber-50"
                : "border-destructive/30 bg-destructive/5"
            }`}
          >
            <div className="flex items-start gap-3">
              <CheckCircle2
                className={`mt-0.5 h-5 w-5 flex-shrink-0 ${
                  result.error_count === 0 ? "text-green-600" : "text-amber-600"
                }`}
              />
              <div className="flex-1">
                <div className="flex items-center justify-between gap-2">
                  <p className="font-semibold text-foreground">
                    {resultType === "placements" ? "Placements" : "Payments"} uploaded — batch #{result.batch_id}
                  </p>
                  <button onClick={() => setResult(null)}>
                    <X className="h-4 w-4 text-muted-foreground" />
                  </button>
                </div>
                <div className="mt-2 flex flex-wrap gap-2 text-xs">
                  <Badge variant="secondary">{result.total_rows} rows read</Badge>
                  <Badge className="bg-green-600">{result.success_count} imported</Badge>
                  {result.error_count > 0 && (
                    <Badge variant="destructive">{result.error_count} errors</Badge>
                  )}
                  <Badge variant="outline">{result.filename}</Badge>
                </div>
                {Object.keys(result.column_mapping).length > 0 && (
                  <div className="mt-3">
                    <p className="text-[10px] font-semibold uppercase text-muted-foreground">
                      Column mapping
                    </p>
                    <div className="mt-1 grid grid-cols-2 gap-x-3 gap-y-0.5 text-[11px]">
                      {Object.entries(result.column_mapping).map(([canonical, header]) => (
                        <div key={canonical} className="truncate">
                          <span className="font-mono text-muted-foreground">{canonical}</span>
                          <span className="mx-1 text-muted-foreground">←</span>
                          <span className="font-medium">{header}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                {result.unmapped_headers.length > 0 && (
                  <p className="mt-2 text-[11px] text-muted-foreground">
                    <span className="font-semibold">Preserved in raw data:</span>{" "}
                    {result.unmapped_headers.slice(0, 8).join(", ")}
                    {result.unmapped_headers.length > 8 && ` (+${result.unmapped_headers.length - 8} more)`}
                  </p>
                )}
                {result.errors.length > 0 && (
                  <details className="mt-2">
                    <summary className="cursor-pointer text-[11px] font-semibold text-amber-700">
                      View {result.errors.length} error{result.errors.length === 1 ? "" : "s"}
                    </summary>
                    <div className="mt-1 max-h-32 overflow-y-auto rounded bg-white p-2 font-mono text-[10px]">
                      {result.errors.map((e, i) => (
                        <div key={i}>row {e.row}: {e.error}</div>
                      ))}
                    </div>
                  </details>
                )}
              </div>
            </div>
          </Card>
        )}

        {/* Stats Grid */}
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          <Card className="p-4 border-l-4 border-primary">
            <div className="flex items-center gap-2">
              <Users className="h-4 w-4 text-primary" />
              <p className="text-xs text-muted-foreground">Placements</p>
            </div>
            <p className="mt-1 text-2xl font-bold text-foreground">{p?.total_placements ?? 0}</p>
            <p className="text-[10px] text-muted-foreground">
              {p?.unique_students ?? 0} unique students
            </p>
          </Card>

          <Card className="p-4 border-l-4 border-blue-500">
            <div className="flex items-center gap-2">
              <Building className="h-4 w-4 text-blue-600" />
              <p className="text-xs text-muted-foreground">Employers</p>
            </div>
            <p className="mt-1 text-2xl font-bold text-foreground">{p?.unique_employers ?? 0}</p>
            <p className="text-[10px] text-muted-foreground">
              {p?.unique_programs ?? 0} programs
            </p>
          </Card>

          <Card className="p-4 border-l-4 border-purple-500">
            <div className="flex items-center gap-2">
              <TrendingUp className="h-4 w-4 text-purple-600" />
              <p className="text-xs text-muted-foreground">Avg wage/hr</p>
            </div>
            <p className="mt-1 text-2xl font-bold text-foreground">
              {p?.avg_wage ? `$${Number(p.avg_wage).toFixed(2)}` : "—"}
            </p>
            <p className="text-[10px] text-muted-foreground">
              latest: {formatDate(p?.latest_placement ?? null)}
            </p>
          </Card>

          <Card className="p-4 border-l-4 border-green-500">
            <div className="flex items-center gap-2">
              <DollarSign className="h-4 w-4 text-green-600" />
              <p className="text-xs text-muted-foreground">Total spent</p>
            </div>
            <p className="mt-1 text-2xl font-bold text-foreground">
              {formatCurrency(pay?.total_spent ?? null)}
            </p>
            <p className="text-[10px] text-muted-foreground">
              {pay?.total_payments ?? 0} txns · {pay?.unique_vendors ?? 0} vendors
            </p>
          </Card>
        </div>

        {/* Two-column: By Program + By Category */}
        <div className="grid gap-4 md:grid-cols-2">
          <Card className="p-5">
            <h3 className="mb-3 flex items-center gap-2 font-semibold">
              <Briefcase className="h-4 w-4 text-primary" /> Placements by Program
            </h3>
            {(summary?.placements_by_program || []).length === 0 ? (
              <p className="text-xs italic text-muted-foreground">No placements uploaded yet.</p>
            ) : (
              <div className="space-y-2">
                {summary!.placements_by_program.map((row) => {
                  const max = Math.max(...summary!.placements_by_program.map((r) => r.placements))
                  const pct = (row.placements / max) * 100
                  return (
                    <div key={row.program}>
                      <div className="flex justify-between text-xs">
                        <span className="font-medium text-foreground">{row.program}</span>
                        <span className="text-muted-foreground">
                          {row.placements} · ${Number(row.avg_wage ?? 0).toFixed(2)}/hr
                        </span>
                      </div>
                      <Progress value={pct} className="h-1.5 mt-1" />
                    </div>
                  )
                })}
              </div>
            )}
          </Card>

          <Card className="p-5">
            <h3 className="mb-3 flex items-center gap-2 font-semibold">
              <DollarSign className="h-4 w-4 text-green-600" /> Payments by Category
            </h3>
            {(summary?.payments_by_category || []).length === 0 ? (
              <p className="text-xs italic text-muted-foreground">No payments uploaded yet.</p>
            ) : (
              <div className="space-y-2">
                {summary!.payments_by_category.map((row) => {
                  const max = Math.max(...summary!.payments_by_category.map((r) => Number(r.total ?? 0)))
                  const pct = max > 0 ? (Number(row.total ?? 0) / max) * 100 : 0
                  return (
                    <div key={row.category}>
                      <div className="flex justify-between text-xs">
                        <span className="font-medium text-foreground">{row.category}</span>
                        <span className="text-muted-foreground">
                          {formatCurrency(row.total)} ({row.payments})
                        </span>
                      </div>
                      <Progress value={pct} className="h-1.5 mt-1 [&>div]:bg-green-500" />
                    </div>
                  )
                })}
              </div>
            )}
          </Card>
        </div>

        {/* Recent Uploads */}
        <Card className="p-5">
          <h3 className="mb-3 flex items-center gap-2 font-semibold">
            <Calendar className="h-4 w-4 text-primary" /> Recent Uploads
          </h3>
          {(summary?.recent_uploads || []).length === 0 ? (
            <p className="text-xs italic text-muted-foreground">No uploads yet. Use the buttons above to get started.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b text-[10px] uppercase text-muted-foreground">
                    <th className="px-2 py-2 text-left">Type</th>
                    <th className="px-2 py-2 text-left">File</th>
                    <th className="px-2 py-2 text-left">By</th>
                    <th className="px-2 py-2 text-right">Rows</th>
                    <th className="px-2 py-2 text-right">OK</th>
                    <th className="px-2 py-2 text-right">Err</th>
                    <th className="px-2 py-2 text-left">Status</th>
                    <th className="px-2 py-2 text-left">When</th>
                    <th className="px-2 py-2"></th>
                  </tr>
                </thead>
                <tbody>
                  {summary!.recent_uploads.map((u) => (
                    <tr key={u.id} className="border-b last:border-0">
                      <td className="px-2 py-2">
                        <Badge variant={u.upload_type === "placements" ? "default" : "secondary"} className="text-[10px]">
                          {u.upload_type}
                        </Badge>
                      </td>
                      <td className="px-2 py-2 font-mono text-[11px]">{u.filename}</td>
                      <td className="px-2 py-2 text-muted-foreground">{u.uploaded_by}</td>
                      <td className="px-2 py-2 text-right">{u.row_count}</td>
                      <td className="px-2 py-2 text-right font-semibold text-green-600">{u.success_count}</td>
                      <td className="px-2 py-2 text-right text-destructive">
                        {u.error_count > 0 ? u.error_count : ""}
                      </td>
                      <td className="px-2 py-2">
                        <Badge
                          variant="outline"
                          className={`text-[10px] ${
                            u.status === "processed"
                              ? "border-green-500 text-green-700"
                              : u.status === "partial"
                              ? "border-amber-500 text-amber-700"
                              : "border-destructive text-destructive"
                          }`}
                        >
                          {u.status}
                        </Badge>
                      </td>
                      <td className="px-2 py-2 text-muted-foreground">{formatDateTime(u.uploaded_at)}</td>
                      <td className="px-2 py-2">
                        <button
                          onClick={() => deleteBatch(u.id)}
                          className="text-muted-foreground hover:text-destructive"
                          title="Delete this upload batch (and all its rows)"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </main>
    </div>
  )
}
