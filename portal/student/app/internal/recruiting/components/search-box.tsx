"use client"

// Natural-language search box. Scaffold-only for 2C — the q param
// isn't wired to the filter state yet. Real wiring (type → debounce
// → refetch /jobs with q=...) is a small follow-up; today this is
// here to communicate the product direction.

export function SearchBox() {
  return (
    <div className="workday-search">
      <span className="workday-search-icon" aria-hidden="true">
        ⌕
      </span>
      <input
        type="text"
        className="workday-search-input"
        placeholder="Describe what you need — 'senior Python remote over 170K'"
        disabled
        aria-label="Search jobs"
      />
      <span className="workday-search-hint">coming soon</span>
    </div>
  )
}
