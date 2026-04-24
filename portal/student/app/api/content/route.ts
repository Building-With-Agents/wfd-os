import { NextResponse } from "next/server"
import { getContentByType, getContentBySlug, getAllTags, renderMarkdown } from "@/lib/content"

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url)
  const type = searchParams.get("type") || "blog"
  const slug = searchParams.get("slug")
  const tagsOnly = searchParams.get("tags") === "true"
  const render = searchParams.get("render") === "true"

  // Single item by slug
  if (slug) {
    const item = getContentBySlug(type, slug)
    if (!item) return NextResponse.json({ error: "Not found" }, { status: 404 })
    return NextResponse.json({
      ...item,
      html: render ? renderMarkdown(item.body) : undefined,
    })
  }

  // Tags list
  if (tagsOnly) {
    return NextResponse.json({ tags: getAllTags(type) })
  }

  // List all of type
  const items = getContentByType(type)
  return NextResponse.json({ items, count: items.length })
}
