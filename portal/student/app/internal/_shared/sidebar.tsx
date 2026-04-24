"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"

// Unified nav sidebar used by every agent surface under /internal/*.
// Flat structure so the rendering code stays legible — active-state
// detection reads the current pathname and compares against `match`
// (a prefix for leaf items; leaf-group for parents with sub-items).
//
// When a new agent comes online, add its entry here and link it to
// its real page (remove the coming-soon target). Sub-items for
// Recruiting exist to preview the product shape to Jason / Ritu
// even though the agent isn't built yet.

interface NavItem {
  label: string
  href: string
  match: string     // pathname prefix for active detection
}

interface NavGroup {
  label: string     // parent row (not itself a link when children exist)
  href?: string     // if set, parent row is a link too
  match: string     // prefix that turns the whole group "active"
  children?: NavItem[]
}

interface NavSection {
  label: string     // section heading ("Agents", "External Portals")
  groups: NavGroup[]
}

const NAV: NavSection[] = [
  {
    label: "Agents",
    groups: [
      {
        label: "Marketing",
        href: "/internal/marketing",
        match: "/internal/marketing",
      },
      {
        label: "Finance",
        href: "/internal/finance",
        match: "/internal/finance",
      },
      {
        label: "Recruiting",
        match: "/internal/recruiting",
        children: [
          { label: "Workday view", href: "/internal/recruiting/workday", match: "/internal/recruiting/workday" },
          { label: "Caseload view", href: "/internal/recruiting/caseload", match: "/internal/recruiting/caseload" },
          { label: "Applications", href: "/internal/recruiting/applications", match: "/internal/recruiting/applications" },
        ],
      },
      {
        label: "Career Services",
        href: "/internal/career-services",
        match: "/internal/career-services",
      },
      {
        label: "BD",
        href: "/internal/bd",
        match: "/internal/bd",
      },
      {
        label: "Jessica",
        href: "/internal/jessica",
        match: "/internal/jessica",
      },
      {
        // Market Intel agent surfaces via the LaborPulse Q&A frontend
        // (workforce-development director asks questions about demand,
        // wages, skills gaps; gets evidence-grounded answers). Click
        // goes directly at the user-facing /laborpulse route.
        label: "Market Intel",
        href: "/laborpulse",
        match: "/laborpulse",
      },
    ],
  },
  {
    // External portals link DIRECTLY at the real portal routes — no
    // launcher middleman. Click "Employer Portal" and you land on
    // /for-employers immediately. The dedicated launcher pages under
    // /internal/*-portal/ were removed (see commit that introduced
    // this change).
    label: "External portals",
    groups: [
      {
        label: "Employer Portal",
        href: "/for-employers",
        match: "/for-employers",
      },
      {
        label: "Talent Showcase",
        href: "/showcase",
        match: "/showcase",
      },
      {
        label: "College Portal",
        href: "/college",
        match: "/college",
      },
      {
        label: "Youth Portal",
        href: "/youth",
        match: "/youth",
      },
      {
        label: "Careers",
        href: "/careers",
        match: "/careers",
      },
      {
        label: "Coalition",
        href: "/coalition",
        match: "/coalition",
      },
      {
        label: "WJI Dashboard",
        href: "/wji",
        match: "/wji",
      },
      {
        label: "Client Portal",
        href: "/client",
        match: "/client",
      },
      {
        label: "AI Consulting",
        href: "/cfa/ai-consulting",
        match: "/cfa/ai-consulting",
      },
    ],
  },
]

function isActive(pathname: string | null, match: string): boolean {
  if (!pathname) return false
  return pathname === match || pathname.startsWith(match + "/")
}

export function Sidebar() {
  const pathname = usePathname()
  return (
    <nav className="agent-sidebar" aria-label="Agent navigation">
      {NAV.map((section, sectionIdx) => (
        <div key={section.label}>
          <div
            className="agent-sidebar-header"
            style={sectionIdx > 0 ? { marginTop: "1.5rem" } : undefined}
          >
            {section.label}
          </div>
          <ul className="agent-sidebar-list">
            {section.groups.map((group) => {
              const groupActive = isActive(pathname, group.match)
              const ParentEl = group.href ? Link : "div"
              const parentProps = group.href ? { href: group.href } : {}
              return (
                <li key={group.label}>
                  <ParentEl
                    {...(parentProps as { href: string })}
                    className="agent-sidebar-item"
                    data-active={groupActive && !group.children ? "true" : "false"}
                    data-parent={group.children ? "true" : "false"}
                  >
                    {group.label}
                  </ParentEl>
                  {group.children && (
                    <ul className="agent-sidebar-sublist">
                      {group.children.map((child) => (
                        <li key={child.href}>
                          <Link
                            href={child.href}
                            className="agent-sidebar-subitem"
                            data-active={isActive(pathname, child.match) ? "true" : "false"}
                          >
                            {child.label}
                          </Link>
                        </li>
                      ))}
                    </ul>
                  )}
                </li>
              )
            })}
          </ul>
        </div>
      ))}
    </nav>
  )
}
