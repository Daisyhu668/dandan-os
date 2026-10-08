import { createFileRoute } from '@tanstack/react-router'
import { bindings, jsonError, sameOrigin, limitKey } from '../server/bindings'
export const Route = createFileRoute('/api/guestbook')({
 server: { handlers: {
  GET: async () => {
   const {DB}=bindings();if(!DB) return jsonError('留言板数据库未绑定',503)
   try { const {results}=await DB.prepare(`SELECT id, nickname, message, created_at FROM guestbook WHERE status='approved' ORDER BY id DESC LIMIT 40`).all()
    return Response.json({ entries: results },{headers:{'Cache-Control':'public, max-age=60'}})
   }catch {return jsonError('留言板数据库尚未初始化',503)}
  },
  POST: async ({request}) => {
   if(!sameOrigin(request)) return jsonError('跨站请求不允许',403)
   if(Number(request.headers.get('content-length')||0)>1400)return jsonError('留言太长',413)
   const {DB,RATE_LIMIT_SALT}=bindings();if(!DB || !RATE_LIMIT_SALT)return jsonError('留言板数据库未绑定',503)
   let nickname = '', message = ''
   try { const p: unknown = await request.json(); if(p && typeof p==='object') {const v=p as Record<string,unknown>;nickname=typeof v.nickname==='string'?v.nickname.trim():'';message=typeof v.message==='string'?v.message.trim():''} }catch{return jsonError('JSON 解析失败')}
   if(!nickname||nickname.length>32||message.length<2||message.length>450) return jsonError('昵称或留言长度不符合要求')
   try {
    const key=await limitKey(request,RATE_LIMIT_SALT,'guest')
    const minute=Math.floor(Date.now()/60000)
    const count=await DB.prepare(`INSERT INTO rate_limits (key,minute,n) VALUES (?1,?2,1) ON CONFLICT(key,minute) DO UPDATE SET n=n+1 RETURNING n`).bind(key,minute).first<{n:number}>()
    if((count?.n??0)>3)return jsonError('提交太频繁',429)
    await DB.prepare(`INSERT INTO guestbook(nickname,message,status) VALUES (?1,?2,'pending')`).bind(nickname,message).run()
    return Response.json({ok:true,pending:true},{status:202,headers:{'Cache-Control':'no-store'}})
   }catch{return jsonError('数据库暂时不可用',503)}
  }
 }}
})
