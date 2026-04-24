// Shared launcher page component for external portal staff entry
// points. Pattern: stays inside the internal cockpit, describes the
// portal, provides a "Launch in new tab" button. Mirrors how
// /internal/career-services gateways into /student for the Student
// Portal — the staff never loses their place in the cockpit.

import type { ReactNode } from "react"

export interface PortalLauncherProps {
  eyebrow?: string            // small uppercase label above the title
  title: string               // portal name, displayed large
  tagline: string             // one-line pitch shown under the title
  description: ReactNode      // longer prose, ~2-3 sentences
  targetUrl: string           // the external portal route to open
  cta?: string                // launch button label (default: "Launch in new tab →")
  caveat?: ReactNode          // optional auth/compatibility note shown under the button
}

export function PortalLauncher({
  eyebrow = "External portal",
  title,
  tagline,
  description,
  targetUrl,
  cta = "Launch in new tab →",
  caveat,
}: PortalLauncherProps) {
  return (
    <div style={{ padding: "2rem 2.5rem", maxWidth: 900 }}>
      <div
        style={{
          marginBottom: "0.5rem",
          fontSize: "0.75rem",
          color: "var(--cockpit-text-3)",
          letterSpacing: "0.08em",
          textTransform: "uppercase",
        }}
      >
        {eyebrow}
      </div>
      <h1
        className="cockpit-display"
        style={{ margin: "0 0 0.5rem", fontSize: "2rem" }}
      >
        {title}
      </h1>
      <p
        style={{
          color: "var(--cockpit-text-2)",
          fontSize: "1.125rem",
          margin: "0 0 1.5rem",
        }}
      >
        {tagline}
      </p>

      <div
        style={{
          color: "var(--cockpit-text-2)",
          maxWidth: 700,
          lineHeight: 1.6,
          marginBottom: "2rem",
        }}
      >
        {description}
      </div>

      <a
        href={targetUrl}
        target="_blank"
        rel="noopener noreferrer"
        style={{
          display: "inline-block",
          padding: "0.625rem 1.25rem",
          fontSize: "0.9375rem",
          fontWeight: 500,
          color: "var(--cockpit-text-1)",
          background: "var(--cockpit-accent, #F5F2E8)",
          border: "1px solid var(--cockpit-border)",
          borderRadius: "0.25rem",
          textDecoration: "none",
        }}
      >
        {cta}
      </a>

      {caveat ? (
        <p
          style={{
            fontSize: "0.8125rem",
            color: "var(--cockpit-text-3)",
            marginTop: "1.5rem",
            maxWidth: 700,
            lineHeight: 1.5,
          }}
        >
          {caveat}
        </p>
      ) : null}
    </div>
  )
}
