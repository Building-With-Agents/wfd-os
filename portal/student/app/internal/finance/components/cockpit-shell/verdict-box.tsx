import type { Tone } from "../../lib/types"

export function VerdictBox({
  tone = "watch",
  label = "Verdict",
  headline,
  body,
}: {
  tone?: Tone
  label?: string
  headline: React.ReactNode
  body: React.ReactNode
}) {
  return (
    <div className="cockpit-verdict" data-tone={tone}>
      <div className="cockpit-verdict-label">{label}</div>
      <div className="cockpit-verdict-headline">{headline}</div>
      <div className="cockpit-verdict-body">{body}</div>
    </div>
  )
}
