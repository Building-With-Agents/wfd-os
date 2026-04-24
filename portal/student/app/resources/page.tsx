import { getContentByType } from "@/lib/content"
import Link from "next/link"
import { ArrowRight, BookOpen, BarChart3, Award, Compass } from "lucide-react"
import NewsletterSubscribe from "@/components/newsletter-subscribe"

const SECTIONS = [
  { type: "blog", label: "Blog", description: "Thought leadership on AI, workforce intelligence, and building with data.", icon: "BookOpen", color: "text-blue-600", gradient: "from-blue-500/20 to-primary/10", href: "/resources/blog" },
  { type: "research", label: "Research", description: "Data-driven reports and labor market intelligence from the CFA Job Intelligence Engine.", icon: "BarChart3", color: "text-purple-600", gradient: "from-purple-500/20 to-primary/10", href: "/resources/research" },
  { type: "case-studies", label: "Case Studies", description: "How organizations are using agentic AI to solve real operational problems.", icon: "Award", color: "text-green-600", gradient: "from-green-500/20 to-primary/10", href: "/resources/case-studies" },
]

const ICONS: Record<string, typeof BookOpen> = { BookOpen, BarChart3, Award }

export default function ResourcesLanding() {
  const data: Record<string, any[]> = {}
  for (const s of SECTIONS) {
    data[s.type] = getContentByType(s.type)
  }

  return (
    <div className="min-h-screen bg-background">
      <header className="sticky top-0 z-50 border-b bg-card/95 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
          <Link href="/" className="flex items-center gap-2">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary">
              <Compass className="h-5 w-5 text-primary-foreground" />
            </div>
            <span className="text-lg font-bold">Computing for All</span>
          </Link>
          <nav className="flex items-center gap-4 text-sm">
            <Link href="/cfa/ai-consulting" className="text-muted-foreground hover:text-primary">AI Consulting</Link>
            <Link href="/youth" className="text-muted-foreground hover:text-primary">Youth Program</Link>
            <Link href="/coalition" className="text-muted-foreground hover:text-primary">Coalition</Link>
            <Link href="/resources/blog" className="text-muted-foreground hover:text-primary">Blog</Link>
            <Link href="/resources/research" className="text-muted-foreground hover:text-primary">Research</Link>
            <Link href="/resources/case-studies" className="text-muted-foreground hover:text-primary">Case Studies</Link>
            <Link href="/resources/newsletter" className="text-muted-foreground hover:text-primary">Newsletter</Link>
            <Link href="/cfa/ai-consulting" className="rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground">Get in touch</Link>
          </nav>
        </div>
      </header>

      <section className="bg-gradient-to-b from-primary/5 to-background px-4 py-20 text-center">
        <h1 className="text-4xl font-bold text-foreground sm:text-5xl">Resources</h1>
        <p className="mx-auto mt-4 max-w-xl text-lg text-muted-foreground">
          Insights on agentic AI, workforce intelligence, and building systems that work.
        </p>
      </section>

      <main className="mx-auto max-w-6xl space-y-16 px-4 py-12">
        {SECTIONS.map((section) => {
          const items = data[section.type] || []
          const Icon = ICONS[section.icon] || BookOpen
          return (
            <section key={section.type}>
              <div className="mb-6 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Icon className={`h-6 w-6 ${section.color}`} />
                  <div>
                    <h2 className="text-2xl font-bold text-foreground">{section.label}</h2>
                    <p className="text-sm text-muted-foreground">{section.description}</p>
                  </div>
                </div>
                <Link href={section.href} className="inline-flex items-center gap-1 rounded-md border px-3 py-1.5 text-xs font-medium hover:bg-muted">
                  View all <ArrowRight className="h-3 w-3" />
                </Link>
              </div>
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {items.slice(0, 3).map((item) => (
                  <Link key={item.slug} href={`/resources/${section.type}/${item.slug}`} className="group block">
                    <div className="overflow-hidden rounded-xl border bg-card shadow-sm transition-all hover:shadow-md hover:border-primary/30">
                      <div className={`h-40 bg-gradient-to-br ${section.gradient} flex items-center justify-center`}>
                        {item.is_gated && <span className="rounded-full bg-amber-500 px-3 py-1 text-xs font-medium text-white">PDF Report</span>}
                      </div>
                      <div className="p-4 space-y-2">
                        <div className="flex flex-wrap gap-1">
                          {(item.tags || []).slice(0, 2).map((t: string) => (
                            <span key={t} className="rounded-full border px-2 py-0.5 text-[10px]">{t}</span>
                          ))}
                        </div>
                        <h3 className="font-bold text-foreground group-hover:text-primary transition-colors line-clamp-2">{item.title}</h3>
                        <p className="text-xs text-muted-foreground line-clamp-2">{item.excerpt}</p>
                        <div className="flex items-center justify-between text-[10px] text-muted-foreground pt-1">
                          <span>{item.author}</span>
                          <span>{item.date ? new Date(item.date + "T00:00:00").toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }) : ""}</span>
                        </div>
                      </div>
                    </div>
                  </Link>
                ))}
                {items.length === 0 && (
                  <p className="col-span-full py-8 text-center text-sm italic text-muted-foreground">Content coming soon.</p>
                )}
              </div>
            </section>
          )
        })}
      </main>

      <footer className="border-t bg-card py-8 text-center">
        <NewsletterSubscribe />
        <p className="text-xs text-muted-foreground">Computing for All &middot; Bellevue, WA &middot; <Link href="/cfa/ai-consulting" className="text-primary hover:underline">computingforall.org</Link></p>
      </footer>
    </div>
  )
}
