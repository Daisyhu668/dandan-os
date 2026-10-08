// Fill Cloudflare binding IDs from Wrangler's create command outputs.
import fs from 'node:fs'
import path from 'node:path'
const [d1, kv, domain] = process.argv.slice(2)
if(!d1 || !kv || !/^[a-f0-9-]{32,36}$/i.test(d1) || !/^[a-f0-9]{32,}$/i.test(kv)) {
 console.error('用法: npm run setup:cloudflare -- <D1_UUID> <KV_NAMESPACE_ID> [自有完整子域名]')
 console.error('请先运行 npx wrangler d1 create dandan-os-db 和 npx wrangler kv namespace create DANDAN_PUBLIC_PERSONA')
 process.exit(1)
}
const f=path.resolve('wrangler.jsonc')
const config=JSON.parse(fs.readFileSync(f,'utf8'))
config.d1_databases=[{binding:'DB',database_name:'dandan-os-db',database_id:d1}]
config.kv_namespaces=[{binding:'PERSONA',id:kv}]
if(domain){
 if(!/^[a-z0-9][a-z0-9.-]+\.[a-z]{2,}$/i.test(domain)) throw new Error('请输入不含 https:// 的完整域名，如 os.example.com')
 console.log(`即将配置公开子域名: ${domain}`)
 config.routes=[{pattern:domain,custom_domain:true}]
 config.workers_dev=true
}
fs.writeFileSync(f,JSON.stringify(config,null,2)+'\n')
console.log('Wrangler 绑定已写入 wrangler.jsonc。下一步：设置 secret、初始化 D1 并部署。')
