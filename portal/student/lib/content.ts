/**
 * Content utility — reads markdown files with frontmatter from /content/.
 *
 * No external dependencies. Parses frontmatter via regex.
 * Works at request time via Next.js server components or API routes.
 */
import fs from "fs"
import path from "path"

const CONTENT_DIR = path.join(process.cwd(), "../../content")

export interface ContentMeta {
  title: string
  author: string
  date: string
  tags: string[]
  excerpt: string
  read_time: string
  slug: string
  featured_image: string | null
  content_type: "blog" | "research" | "case-studies"
  // Research-specific
  pdf_url?: string
  is_gated?: boolean
  // Case study-specific
  client?: string
  industry?: string
  challenge?: string
  solution?: string
  metrics?: Record<string, string>
}

export interface ContentItem extends ContentMeta {
  body: string
}

function parseFrontmatter(raw: string): { meta: Record<string, any>; body: string } {
  const match = raw.match(/^---\n([\s\S]*?)\n---\n([\s\S]*)$/)
  if (!match) return { meta: {}, body: raw }

  const frontmatter = match[1]
  const body = match[2].trim()
  const meta: Record<string, any> = {}

  for (const line of frontmatter.split("\n")) {
    const colonIdx = line.indexOf(":")
    if (colonIdx === -1) continue
    const key = line.slice(0, colonIdx).trim()
    let value: any = line.slice(colonIdx + 1).trim()

    // Remove surrounding quotes
    if ((value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'"))) {
      value = value.slice(1, -1)
    }
    // Handle arrays like ["tag1", "tag2"]
    if (value.startsWith("[") && value.endsWith("]")) {
      try {
        value = JSON.parse(value)
      } catch {
        value = value.slice(1, -1).split(",").map((s: string) => s.trim().replace(/^["']|["']$/g, ""))
      }
    }
    // Handle booleans
    if (value === "true") value = true
    if (value === "false") value = false
    if (value === "null") value = null

    meta[key] = value
  }

  // Handle multi-line metrics (YAML-like nested object)
  if (frontmatter.includes("metrics:")) {
    const metricsMatch = frontmatter.match(/metrics:\n((?:\s+\w+:.*\n?)+)/)
    if (metricsMatch) {
      const metrics: Record<string, string> = {}
      for (const line of metricsMatch[1].split("\n")) {
        const m = line.match(/^\s+(\w+):\s*"?([^"]*)"?\s*$/)
        if (m) metrics[m[1]] = m[2]
      }
      meta.metrics = metrics
    }
  }

  return { meta, body }
}

function resolveContentDir(): string {
  // Try multiple paths since cwd can vary
  const candidates = [
    path.join(process.cwd(), "../../content"),
    path.join(process.cwd(), "../content"),
    path.join(process.cwd(), "content"),
    "C:/Users/ritub/projects/wfd-os/content",
  ]
  for (const dir of candidates) {
    if (fs.existsSync(dir)) return dir
  }
  return candidates[0]
}

export function getContentByType(type: string): ContentMeta[] {
  const dir = path.join(resolveContentDir(), type)
  if (!fs.existsSync(dir)) return []

  const files = fs.readdirSync(dir).filter((f) => f.endsWith(".md"))
  const items: ContentMeta[] = []

  for (const file of files) {
    const raw = fs.readFileSync(path.join(dir, file), "utf-8")
    const { meta } = parseFrontmatter(raw)
    items.push({
      title: meta.title || file.replace(".md", ""),
      author: meta.author || "CFA",
      date: meta.date || "",
      tags: meta.tags || [],
      excerpt: meta.excerpt || "",
      read_time: meta.read_time || "",
      slug: meta.slug || file.replace(".md", ""),
      featured_image: meta.featured_image || null,
      content_type: type as any,
      pdf_url: meta.pdf_url,
      is_gated: meta.is_gated,
      client: meta.client,
      industry: meta.industry,
      challenge: meta.challenge,
      solution: meta.solution,
      metrics: meta.metrics,
    })
  }

  // Sort by date descending
  items.sort((a, b) => (b.date || "").localeCompare(a.date || ""))
  return items
}

export function getContentBySlug(type: string, slug: string): ContentItem | null {
  const dir = path.join(resolveContentDir(), type)
  const filePath = path.join(dir, `${slug}.md`)
  if (!fs.existsSync(filePath)) return null

  const raw = fs.readFileSync(filePath, "utf-8")
  const { meta, body } = parseFrontmatter(raw)

  return {
    title: meta.title || slug,
    author: meta.author || "CFA",
    date: meta.date || "",
    tags: meta.tags || [],
    excerpt: meta.excerpt || "",
    read_time: meta.read_time || "",
    slug: meta.slug || slug,
    featured_image: meta.featured_image || null,
    content_type: type as any,
    body,
    pdf_url: meta.pdf_url,
    is_gated: meta.is_gated,
    client: meta.client,
    industry: meta.industry,
    challenge: meta.challenge,
    solution: meta.solution,
    metrics: meta.metrics,
  }
}

export function getAllTags(type: string): string[] {
  const items = getContentByType(type)
  const tags = new Set<string>()
  for (const item of items) {
    for (const tag of item.tags) {
      tags.add(tag)
    }
  }
  return Array.from(tags).sort()
}

/**
 * Simple markdown to HTML renderer.
 * Handles: headings, bold, italic, links, lists, code blocks, paragraphs, tables, blockquotes.
 */
export function renderMarkdown(md: string): string {
  let html = md
    // Code blocks (``` ... ```)
    .replace(/```(\w*)\n([\s\S]*?)```/g, '<pre class="bg-muted rounded-lg p-4 overflow-x-auto my-4"><code>$2</code></pre>')
    // Headings
    .replace(/^#### (.+)$/gm, '<h4 class="text-base font-semibold text-foreground mt-6 mb-2">$1</h4>')
    .replace(/^### (.+)$/gm, '<h3 class="text-lg font-semibold text-foreground mt-8 mb-3">$1</h3>')
    .replace(/^## (.+)$/gm, '<h2 class="text-xl font-bold text-foreground mt-10 mb-4">$1</h2>')
    // Bold + italic
    .replace(/\*\*\*(.+?)\*\*\*/g, "<strong><em>$1</em></strong>")
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.+?)\*/g, "<em>$1</em>")
    // Links
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" class="text-primary hover:underline">$1</a>')
    // Blockquotes
    .replace(/^> (.+)$/gm, '<blockquote class="border-l-4 border-primary/30 pl-4 my-4 text-muted-foreground italic">$1</blockquote>')
    // Unordered lists
    .replace(/^- (.+)$/gm, '<li class="ml-4 list-disc text-foreground/80">$1</li>')
    // Ordered lists
    .replace(/^\d+\. (.+)$/gm, '<li class="ml-4 list-decimal text-foreground/80">$1</li>')
    // Horizontal rules
    .replace(/^---$/gm, '<hr class="my-8 border-border">')
    // Tables (basic)
    .replace(/^\|(.+)\|$/gm, (match) => {
      const cells = match.split("|").filter(Boolean).map((c) => c.trim())
      if (cells.every((c) => /^[-:]+$/.test(c))) return "" // separator row
      const tag = cells.length > 0 ? "td" : "td"
      return `<tr>${cells.map((c) => `<${tag} class="border border-border px-3 py-2 text-sm">${c}</${tag}>`).join("")}</tr>`
    })
    // Wrap table rows
    .replace(/((?:<tr>.*<\/tr>\n?)+)/g, '<table class="w-full border-collapse my-4">$1</table>')
    // Paragraphs (double newline)
    .replace(/\n\n(?!<)/g, '</p><p class="text-foreground/80 leading-relaxed mb-4">')
    // Single newlines within paragraphs
    .replace(/(?<!\n)\n(?!\n|<)/g, "<br>")

  // Wrap in paragraph if not already wrapped
  if (!html.startsWith("<")) {
    html = `<p class="text-foreground/80 leading-relaxed mb-4">${html}</p>`
  }

  // Wrap consecutive li elements in ul
  html = html.replace(/((?:<li[^>]*>.*?<\/li>\s*)+)/g, '<ul class="my-4 space-y-1">$1</ul>')

  return html
}
