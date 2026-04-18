// Minimal stub for `apiFetch` referenced by app/internal/page.tsx.
//
// The canonical helper lives on the grant-compliance branch (which
// this branch doesn't share history with — see
// agents/finance/design/deferred_fixes.md "Repo hygiene"). Without a
// stub, the /internal/ route fails to compile and blocks every
// /internal/* page including the Finance cockpit in dev.
//
// Intentionally tiny: this forwards to window.fetch. When the two
// histories reconcile and the real helper lands, this file is
// overwritten. Nothing on feature/finance-cockpit calls apiFetch
// directly (only the cherry-picked /internal/page.tsx does).

export async function apiFetch(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  return fetch(input, init)
}
