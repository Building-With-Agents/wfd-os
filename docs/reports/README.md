# Reports — point-in-time outputs

This directory holds **one-time generated reports**: snapshots of the
state of a particular pipeline run on a particular date, intended for
human review (Ritu, Gary, Alma, etc.). They are not living
documentation.

Filename convention: `<topic>_<YYYY-MM-DD>.md`. The date is the data
cut, not the file's last edit. Once a report is written it should not
be modified — generate a new dated copy instead, so historical
artifacts stay reproducible alongside the DB snapshot they came from.

These files are **not authoritative**. The authoritative source is the
DB state at the time the report was generated (e.g. `cohort_matches`,
`gap_analyses`, `match_narratives` for placement reports). If a report
disagrees with the DB, the DB wins.
