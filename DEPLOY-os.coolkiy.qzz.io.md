# 发布目标：os.coolkiy.qzz.io

本版本已将域名添加到 `wrangler.jsonc` 的 Worker Custom Domain 路由中，但尚未在 Cloudflare 账号中创建生产 Worker。**域名预设不代表已上线。**

## 适用前提

- 在 Cloudflare 登录后，确认 `coolkiy.qzz.io`（或能够管理 `os.coolkiy.qzz.io` 的 DNS zone）处于当前账号管理之下。`qzz.io` 可能涉及第三方子域名授权；若该 hostname 不属于已激活的 Cloudflare zone，`custom_domain` 将无法直接绑定，需要管理该 zone 的人员协作。
- 现有 `os.coolkiy.qzz.io` 不应存在与目标冲突的 CNAME 记录 / 其他服务；先备份 DNS。
- Cloudflare Workers AI、D1、KV 资源绑定需要自行登录创建，密钥不得分享到聊天。

## 建议的发布流程（命令在解压后的项目目录执行）

1. `npm install`
2. `npx wrangler login`（浏览器授权，勿传密码）
3. `npx wrangler d1 create dandan-os-db --location apac`
4. `npx wrangler kv namespace create DANDAN_PUBLIC_PERSONA`
5. `npm run setup:cloudflare -- <D1_UUID> <KV_ID> os.coolkiy.qzz.io`
6. `npx wrangler secret put RATE_LIMIT_SALT`（粘贴自行生成的随机高熵值）
7. `npm run db:remote`
8. `npx wrangler kv key put public:persona --path=public-persona.txt --binding=PERSONA --remote`
9. `npm run build && npx wrangler deploy`
10. 验证 `https://os.coolkiy.qzz.io/api/health` 返回的 D1、KV、AI 和限流密钥绑定均为 true。手工测试聊天、表单和手机端。

注意：先在独立的 `*.workers.dev` 预览验证，最后再启用自定义域名更稳妥。要先单独发布测试版，可暂时删掉 `wrangler.jsonc` 的 routes 后发布，校验成功再添加回来。

项目尚无 lockfile；`npm install` 时会解析依赖，完成后推荐保存 package-lock.json，锁定依赖版本。此环境 DNS 无法访问 npm/Cloudflare，不能代替实际生产构建测试。
