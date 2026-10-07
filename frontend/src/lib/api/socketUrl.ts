/** WebSocket address for the pipeline event stream.
 *
 * `base` is VITE_API_BASE_URL: absolute in development (`http://localhost:8000/api`)
 * and relative in the single-service build (`/api`), where the page and the API
 * share an origin. */
export function socketUrl(
  base: string,
  page: { protocol: string; host: string },
): string {
  const absolute = /^https?:/.test(base) ? base : `${page.protocol}//${page.host}${base}`;
  return `${absolute.replace(/^http/, 'ws').replace(/\/$/, '')}/pipeline/events`;
}
