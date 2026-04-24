/**
 * Wrapper around fetch() that adds the ngrok-skip-browser-warning header
 * to all requests. This prevents ngrok's free-tier interstitial page from
 * intercepting API calls when the app is accessed through an ngrok tunnel.
 *
 * Usage: Replace `fetch(url)` with `apiFetch(url)` in any client component
 * that calls internal APIs (/api/*).
 */
export function apiFetch(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  const headers = new Headers(init?.headers)
  headers.set("ngrok-skip-browser-warning", "true")
  return fetch(input, { ...init, headers })
}
