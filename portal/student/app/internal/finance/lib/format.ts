// Number/currency formatters used across cockpit components. Matches
// the format choices in agents/finance/design/cockpit_data.py so React
// output reads the same as the Jinja-rendered HTML cockpit.

export function fmtUSD(n: number, opts: { compact?: boolean } = {}): string {
  if (opts.compact && Math.abs(n) >= 1000) {
    if (Math.abs(n) >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`
    return `$${Math.round(n / 1000)}k`
  }
  return `$${n.toLocaleString("en-US", { maximumFractionDigits: 0 })}`
}

export function fmtNum(n: number): string {
  return n.toLocaleString("en-US", { maximumFractionDigits: 0 })
}

export function fmtPct(n: number, digits = 0): string {
  return `${n.toFixed(digits)}%`
}

export function cn(...classes: Array<string | false | null | undefined>): string {
  return classes.filter(Boolean).join(" ")
}
