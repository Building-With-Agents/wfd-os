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

const NAV: NavGroup[] = [
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
    label: "Market Intel",
    href: "/internal/market-intel",
    match: "/internal/market-intel",
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
      <div className="agent-sidebar-header">Agents</div>
      <ul className="agent-sidebar-list">
        {NAV.map((group) => {
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
    </nav>
  )
}
