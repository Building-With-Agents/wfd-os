"use client"

// Filter row for the Workday view. Hands partial updates up to
// workday-client via onChange; the client re-fetches /jobs when any
// filter changes.

import type { WorkdayFilters } from "../lib/types"

interface Props {
  filters: WorkdayFilters
  onChange: (next: WorkdayFilters) => void
}

const SENIORITY_OPTIONS = ["", "junior", "mid", "senior", "staff", "principal"]
const EMPLOYMENT_OPTIONS = ["", "full-time", "part-time", "contract", "internship"]

export function FilterChips({ filters, onChange }: Props) {
  return (
    <div className="workday-filter-row" role="search" aria-label="Filter jobs">
      <label className="workday-chip">
        <span className="workday-chip-label">City</span>
        <input
          type="text"
          placeholder="any"
          value={filters.city}
          onChange={(e) => onChange({ ...filters, city: e.target.value })}
          className="workday-chip-input"
        />
      </label>

      <label className="workday-chip">
        <span className="workday-chip-label">Seniority</span>
        <select
          value={filters.seniority}
          onChange={(e) => onChange({ ...filters, seniority: e.target.value })}
          className="workday-chip-select"
        >
          {SENIORITY_OPTIONS.map((opt) => (
            <option key={opt} value={opt}>
              {opt === "" ? "any" : opt}
            </option>
          ))}
        </select>
      </label>

      <label className="workday-chip workday-chip-toggle">
        <input
          type="checkbox"
          checked={filters.is_remote === true}
          onChange={(e) =>
            onChange({ ...filters, is_remote: e.target.checked ? true : null })
          }
        />
        <span>Remote only</span>
      </label>

      <label className="workday-chip">
        <span className="workday-chip-label">Type</span>
        <select
          value={filters.employment_type}
          onChange={(e) =>
            onChange({ ...filters, employment_type: e.target.value })
          }
          className="workday-chip-select"
        >
          {EMPLOYMENT_OPTIONS.map((opt) => (
            <option key={opt} value={opt}>
              {opt === "" ? "any" : opt}
            </option>
          ))}
        </select>
      </label>

      {(filters.city || filters.seniority || filters.employment_type || filters.is_remote !== null) && (
        <button
          type="button"
          className="workday-chip-clear"
          onClick={() => onChange({
            q: filters.q,
            city: "", state: "",
            is_remote: null, seniority: "", employment_type: "",
          })}
        >
          Clear filters
        </button>
      )}
    </div>
  )
}
