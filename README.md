# Dandan / OS 3.0 — Cloudflare 原生项目（部署前版本）

以 Dandan OS v2 的静态体验为基础进行**渐进式迁移**：React 19 + TanStack Start SSR 路由承载网站；既有的桌面 UI/Dock 暂时由兼容脚本负责，新增留言板和窗口动画为原生 React + Motion 组件，背景使用 PixiJS v8。后端完全通过 Cloudflare Workers（TanStack Start server routes）提供，使用 D1、KV 和 Workers AI。

> **状态说明：代码、图片、部署配置已准备并通过基础静态检查；但当前环境不能从 npm 完整安装依赖，尚未执行 Cloudflare 生产构建、在线交互验收或远端部署。GitHub 公共仓库已上传完整源码和 10 张 WebP 照片；Cloudflare 部署状态仍须以控制台及线上验收为准。发布需在获授权的环境里执行并逐项验证。**

## 1. 安装和登录

要求 Node.js 20.19+。在电脑上解压进入目录后：

```sh
npm install
npx wrangler login
```

不要把 Cloudflare API Token、会话 cookie 或其他密钥放进聊天、仓库或截图。

## 2. Cloudflare 创建资源并绑定

```sh
npx wrangler d1 create dandan-os-db --location apac
npx wrangler kv namespace create DANDAN_PUBLIC_PERSONA
```

从两段命令输出中分别复制 **D1 database_id** 和 **KV namespace id**。配置完整子域名之前，建议先部署到 `workers.dev` 测试地址：

```sh
npm run setup:cloudflare -- <D1数据库UUID> <KV命名空间ID>
```

例如欲绑定 `os.example.com`，可在命令末尾追加该子域名；`os.example.com` 必须是自己 Cloudflare 账号已激活的 zone 的子域名，不建议在尚未验证时覆盖根域名。

## 3. 必需的速率限制密钥（保存在 Cloudflare Secret）

```sh
npx wrangler secret put RATE_LIMIT_SALT
```

在提示符输入独立生成的高熵随机字符串（至少 32 个字符）。此值**不应该**上传 Git、发送到聊天或放入 Wrangler vars。

## 4. 初始化数据库和 KV

```sh
npm run db:local
npm run db:remote
npx wrangler kv key put public:persona --path=public-persona.txt --binding=PERSONA --remote
```

KV 存放的仅是可以公开的个人介绍文案；私人 Notion 页面不要直接同步到公开网站。

## 5. 构建及部署

```sh
npm run dev     # 本地开发：Vite + workerd
npm run build   # 正式构建
npm run preview # 预览构建物
npm run deploy  # Cloudflare Workers 部署
```

先访问 Worker 返回的 `*.workers.dev` 地址，打开 `/api/health` 确认 AI、D1、KV 和 rate-limit secret 为 `true`，然后测试聊天与留言。域名正式接入可以手动在 `wrangler.jsonc` 中增加：

```json
"routes": [{ "pattern": "os.yourdomain.com", "custom_domain": true }]
```

在 Cloudflare 中，Worker Custom Domain 可自动办理 DNS 和 TLS。替换已有根域名或重要子域名之前，请检查线上 DNS 和现有服务。

## 6. 留言审核与访问控制

留言写入 D1 的默认状态为 `pending`，游客只能查询 `approved`。审核可在已登录的开发终端执行：

```sh
npx wrangler d1 execute dandan-os-db --remote --command "SELECT id,nickname,message FROM guestbook WHERE status='pending' ORDER BY id DESC LIMIT 20;"
npx wrangler d1 execute dandan-os-db --remote --command "UPDATE guestbook SET status='approved' WHERE id=1 AND status='pending';"
```

任何互联网访客都可以向 AI 发送问题，Workers AI 可能产生费用；已设置每 IP 每分钟 10 次、全站每天 250 次的数据库限流（只存储加盐后的 IP 摘要）。D1 中的速率计数需要定期清理以避免长期增长。留言每 IP 每分钟 3 次，先审核再展示。对于大流量网站，建议另加 Turnstile 及 WAF 规则。

## 7. 改内容和照片

- 主要页面内容：`src/legacy/desktop.html`
- Dock 和应用窗口交互：`src/legacy/desktop.js`（逐步迁往 React）
- 视觉样式：`src/styles/base.css`
- 个人、钢镚、旅行摄影：`public/assets/photos/*.webp`，目前是用户照片的艺术处理版本
- 装饰用插画：`public/assets/gangbeng.svg`、`mountains.svg`、`lake.svg`、`city.svg`
- AI 公开人格：`public-persona.txt`；服务端回退版本：`src/server/public-persona.ts`
- 访客留言：`src/components/Guestbook.tsx` 和 `src/routes/api.guestbook.ts`
- AI API：`src/routes/api.chat.ts`

已使用用户提供的个人、钢镚与旅行照片的风格化版本；`public/assets/photos/` 为经过艺术加工的 WebP 图像。部分装饰物仍为 CSS/SVG 插画。所有涉及银行与 APEX 的内容均为公开脱敏介绍。

## 8. 授权和参考

设计灵感：[elliothu.me](https://elliothu.me/)；原作者公开 GitHub 只含概览和 CMS 配置，未发布其完整私有源码；本项目是独立实现，不使用原作者私有代码。请自行确认第三方照片、音乐及字体的授权。

技术参考：
- Cloudflare TanStack Start：https://developers.cloudflare.com/workers/framework-guides/web-apps/tanstack-start/
- Cloudflare Workers AI：https://developers.cloudflare.com/workers-ai/configuration/bindings/
- D1：https://developers.cloudflare.com/d1/
- KV：https://developers.cloudflare.com/kv/
- Motion：https://motion.dev/docs/react
- PixiJS：https://pixijs.com/8.x/

## GitHub / Muse 交接

- GitHub 仓库为 [`Daisyhu668/dandan-os`](https://github.com/Daisyhu668/dandan-os)，已公开并完成代码与照片提交。
- **Muse 从现有仓库直接 clone 并部署**；不需要重新上传 ZIP 或创建仓库。参见 [`MUSE-DEPLOY.md`](MUSE-DEPLOY.md)。
- 发布状态：未经云端编译和测试，不能把源代码检查视为上线成功；AI、留言板在正确绑定资源前不可用。

**成本政策：优先 GitHub / Cloudflare 免费套餐；任何升级、订阅或产生实际费用前必须获得网站所有者批准。**
