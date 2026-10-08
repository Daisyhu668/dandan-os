import { createFileRoute } from '@tanstack/react-router'
import { bindings, jsonError, sameOrigin, limitKey } from '../server/bindings'
import { publicPersona } from '../server/public-persona'
export const Route = createFileRoute('/api/chat')({
 server: { handlers: {
  POST: async ({request}) => {
   if (!sameOrigin(request)) return jsonError('跨站请求不允许',403)
   if (Number(request.headers.get('content-length')||0)>2048) return jsonError('消息太长',413)
   let message = ''
   try { const payload: unknown = await request.json(); if (payload && typeof payload==='object' && 'message' in payload && typeof payload.message === 'string') message=payload.message.trim() }catch{return jsonError('请求内容不是有效 JSON')}
   if(message.length<1||message.length>450) return jsonError('请输入 1–450 字的问题')
   const env=bindings()
   if (!env.RATE_LIMIT_SALT) return jsonError('AI 尚未配置安全限流密钥',503)
   if (!env.AI) return jsonError('Workers AI 尚未绑定，请先部署配置',503)
   // IP is not stored; hash with a small rolling window if enabling analytics later.
   if(env.DB){
     try {
       const key=await limitKey(request,env.RATE_LIMIT_SALT,'chat')
       const windowId=Math.floor(Date.now()/60000)
       const result=await env.DB.prepare(`INSERT INTO rate_limits (key, minute, n) VALUES (?1, ?2, 1) ON CONFLICT(key, minute) DO UPDATE SET n = n + 1 RETURNING n`).bind(key,windowId).first<{n:number}>()
       if((result?.n ?? 0)>10) return jsonError('请求太频繁，请稍后再试',429)
       const utcDay = Math.floor(Date.now()/86400000)
       const global = await env.DB.prepare(`INSERT INTO rate_limits (key, minute, n) VALUES ('global:ai',?1,1) ON CONFLICT(key, minute) DO UPDATE SET n=n+1 RETURNING n`).bind(utcDay).first<{n:number}>()
       if ((global?.n ?? 0) > 250) return jsonError('今日 AI 额度已经用完，请明天再来',429)
     }catch{ return jsonError('限流数据库尚未完成初始化',503) }
   } else { return jsonError('为安全起见，启用 D1 限流后才能开放 AI 对话',503) }
   const persona=await env.PERSONA?.get('public:persona')?.catch(()=>null)
   const system=(persona && persona.length<6000)?persona:publicPersona
   try {
     const answer=await env.AI.run('@cf/meta/llama-3.1-8b-instruct', {messages:[{role:'system',content:system},{role:'user',content:message}],max_tokens:350,temperature:.45}) as {response?: string}
     return Response.json({answer:answer?.response ?? '我暂时无法回答这个问题。'}, {headers:{'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'}})
   }catch{return jsonError('AI 服务暂时不可用，请稍后再试',502)}
  }
 }}
})
