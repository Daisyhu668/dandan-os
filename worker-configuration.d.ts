// Binding types. Run `npm run types:cf` after provisioning D1 and KV.
interface Env {
  AI: Ai
  DB: D1Database
  PERSONA: KVNamespace
  PUBLIC_SITE_NAME: string
}
