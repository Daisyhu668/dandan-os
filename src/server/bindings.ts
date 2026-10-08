import { env } from 'cloudflare:workers'
export type Bindings = { AI?: Ai, DB?: D1Database, PERSONA?: KVNamespace, PUBLIC_SITE_NAME?: string, RATE_LIMIT_SALT?: string }
// Secrets/bindings are only used in server routes and never returned to the client.
export function bindings(): Bindings { return env as unknown as Bindings }
export function sameOrigin(request: Request) {
 const origin = request.headers.get('Origin')
 return !origin || origin === new URL(request.url).origin
}
export function jsonError(message: string, status = 400) { return Response.json({ error: message }, { status, headers: { 'Cache-Control': 'no-store' } }) }

export async function limitKey(request: Request, salt: string, prefix: string) {
  const addr = request.headers.get('CF-Connecting-IP') || 'unknown'
  const bytes = new TextEncoder().encode(`${prefix}:${salt}:${addr}`)
  const digest = await crypto.subtle.digest('SHA-256', bytes)
  return prefix + ':' + [...new Uint8Array(digest)].map(x=>x.toString(16).padStart(2,'0')).join('')
}
