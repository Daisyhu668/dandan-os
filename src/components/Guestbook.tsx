import { useEffect, useState, type FormEvent } from 'react'
import { AnimatePresence, motion } from 'motion/react'

type Entry = { id: number, nickname: string, message: string, created_at: string }
export function Guestbook() {
 const [open, setOpen] = useState(false)
 const [entries, setEntries] = useState<Entry[]>([])
 const [loading, setLoading] = useState(false)
 const [name, setName] = useState('')
 const [message, setMessage] = useState('')
 const [status, setStatus] = useState('')
 useEffect(() => {
   if (!open) return
   let live = true
   fetch('/api/guestbook').then(async r => { if(!r.ok) throw new Error('留言板尚未配置 D1'); return r.json() })
     .then(data => { if(live) {setEntries(Array.isArray(data.entries) ? data.entries : [])} })
     .catch(()=>{ if(live) setStatus('留言板数据库尚未开通，暂时只能浏览页面。') })
   return () => { live = false }
 }, [open])
 async function submit(e: FormEvent<HTMLFormElement>) {
   e.preventDefault()
   setLoading(true); setStatus('')
   try {
     const response=await fetch('/api/guestbook',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({nickname:name,message})})
     const data=await response.json()
     if(!response.ok) throw new Error(data.error ?? '发送失败')
     setName('');setMessage('');setStatus('已提交。为避免垃圾信息，留言审核后展示。')
   } catch(e) {setStatus(e instanceof Error?e.message:'稍后再试')}
   finally {setLoading(false)}
 }
 return <>
   <motion.button className="cloud-guest-trigger" onClick={()=>setOpen(true)} whileHover={{scale:1.07, rotate:-2}} whileTap={{scale:.94}}>✉ Guestbook</motion.button>
   <AnimatePresence>
   {open&&<motion.div key="guestbook" className="cloud-guest-mask" role="presentation" onMouseDown={(e)=>{if(e.target===e.currentTarget)setOpen(false)}} initial={{opacity:0}} animate={{opacity:1}} exit={{opacity:0}}>
     <motion.section role="dialog" aria-modal="true" aria-labelledby="guest-title" className="cloud-guest-window" initial={{opacity:0,scale:.87,y:45}} animate={{opacity:1,scale:1,y:0}} exit={{opacity:0,scale:.88,y:35}} transition={{type:'spring', stiffness:260,damping:24}}>
      <header className="cloud-guest-bar"><span>● ● ●　Guestbook.app</span><button aria-label="关闭留言板" onClick={()=>setOpen(false)}>×</button></header>
      <div className="cloud-guest-body"><h2 id="guest-title">Leave a little hello ✳</h2><p>给未来路过这里的人，留下一句温柔的话。</p>
       <div className="cloud-guest-list">{entries.length?entries.map(entry=><div className="cloud-guest-entry" key={entry.id}><strong>{entry.nickname}</strong><time>{entry.created_at.slice(0,10)}</time><p>{entry.message}</p></div>):<p>还没有公开的留言，欢迎第一个来打招呼。</p>}</div>
       <form onSubmit={submit}><label>昵称<input maxLength={32} required value={name} onChange={e=>setName(e.target.value)} placeholder="怎么称呼你？" /></label><label>留言<textarea required minLength={2} maxLength={450} value={message} onChange={e=>setMessage(e.target.value)} placeholder="Say something nice…" /></label><button disabled={loading || !name.trim() || message.trim().length < 2}>{loading?'Sending…':'SEND NOTE ↗'}</button></form>
       {status&&<div className="cloud-guest-status" role="status">{status}</div>}
      </div>
     </motion.section>
   </motion.div>}
   </AnimatePresence>
 </>
}
