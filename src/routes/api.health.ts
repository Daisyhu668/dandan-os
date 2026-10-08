import { createFileRoute } from '@tanstack/react-router'
import { bindings } from '../server/bindings'
export const Route = createFileRoute('/api/health')({server:{handlers:{GET:async()=>{
 const e=bindings()
 return Response.json({application:'dandan-os',version:'3.0.0',status:(e.AI&&e.DB&&e.PERSONA&&e.RATE_LIMIT_SALT)?'ready':'not-ready', bindings: {ai:!!e.AI, d1:!!e.DB, kv:!!e.PERSONA, rate_limit_secret:!!e.RATE_LIMIT_SALT}}, {headers:{'Cache-Control':'no-store'}})
}}}})
