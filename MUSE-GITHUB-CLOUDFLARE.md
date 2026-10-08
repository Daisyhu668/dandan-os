# 给 Muse 的完整接力任务｜Dandan OS → GitHub → Cloudflare

任务授权：请在我已登录的 GitHub 与 Cloudflare 账号中工作。目标是把附带的 `Dandan-OS-GitHub-Ready.zip` 作为独立项目发布到 GitHub，再部署 Cloudflare Worker。最终域名为 `os.coolkiy.qzz.io`。

## 目标与边界

1. 账户：GitHub 用户为 `Daisyhu668`。仓库名定为 `dandan-os`，预计地址 `https://github.com/Daisyhu668/dandan-os`。**先检查仓库是否存在**，不存在再提醒我；现有仓库为 **Public**，请保持公开。不要借用、覆盖其他现有仓库；不要误把个人站源文件提交到 `-`、`law`、`mylittleclaw` 等不相关项目。未完成创建不得宣称链接可用。
2. 解压收到的完整 ZIP，将解压出来的文件（ZIP 顶层即项目根目录）全部作为 Git 仓库根目录（包括隐藏 `.gitignore`、`src/`、`public/`、`migrations/`、`scripts/`、`package.json`、`vite.config.ts`、`wrangler.jsonc`）。保证实际 WebP 图片二进制文件也成功上传，不能只发布 zip/README。
3. 源码可以公开托管，网站公开访问。请保护账号认证信息，不要让我把 GitHub PAT、Cloudflare API Token、网页登录 cookie、密码或 `RATE_LIMIT_SALT` 发送给聊天，不要硬编码密钥进 Git。
4. 网站审美以已有 Dandan OS 为准：保留原版蓝色渐变、Mac 桌面 Dock、浮动视觉元素和已风格化的真实照片。个人内容和 AI 人格只用公开资料，绝不导入整个私人 Notion、内部信贷/客户资料或旅行财务数据。
5. 先验证，再上域名。不要擅自接管或替换已有 DNS 记录/Worker；有冲突先报告具体记录与影响，暂停绑定操作。

## A. GitHub 发布

- 使用现有 Public 仓库 `Daisyhu668/dandan-os`，不可另建重复仓库。可用 Git CLI 或 GitHub 浏览器完成认证；账号有安全确认就提示我自行确认。
- 在本地项目根目录初始化 `main`，安装依赖后如果能生成 `package-lock.json`，把 lockfile 一并提交；遵循 `.gitignore` 排除 `node_modules/`、`.dev.vars*`、`.env*`、`.wrangler/` 等。
- 首次 commit 建议 `feat: Dandan OS 3.0 Cloudflare portfolio and photo gallery`；push 到 `origin/main`。确认远端 README、源文件、`public/assets/photos/` 十张 WebP 照片都能打开。GitHub 仓库已由用户设为 Public；推送写入仍需要授权 Muse 的 GitHub integration。

## B. 正式构建与改错

- 开始前读取 README 和 `DEPLOY-os.coolkiy.qzz.io.md`，技术栈：React 19 + TanStack Start + Motion + PixiJS + Cloudflare Workers + D1 + KV + Workers AI。
- 用 Node.js 20.19+，执行 `npm install`、`npm run check:static`、`npm run build`。本地生成的项目未经完整 npm 生产构建验证；**若 build 报错，逐条修复编译/依赖问题并重新测试，更新并 push 修复的 GitHub 提交**。确认移动端布局与 Dock/多窗口/相册/旅行 tabs 正常，不要用全新模板替换设计。
- 只在有证据时写构建成功、测试通过；有问题在部署报告列明。

## C. Cloudflare Workers 部署

- 使用我当前授权的 Cloudflare 账号，先确认 Worker 名 `dandan-os` 是否已存在，以及 `coolkiy.qzz.io` 的 zone 管理权。若不是此账号托管的有效区域或为第三方子域名，先排查正确的接入/委托方式；不能编造 DNS zone 权限。
- 在 `wrangler.jsonc` 内已预设域名 `os.coolkiy.qzz.io`，但首次发布优先在 `.workers.dev` 临时地址验证；因此首次部署前暂时移除 `routes` 字段（保留记录，勿修改现有 DNS），预览与 API 检查通过后再恢复自定义域名的 `routes` 配置。
- 如果不存在，创建 D1 数据库 `dandan-os-db` 和 KV namespace `DANDAN_PUBLIC_PERSONA`。将真实 D1 ID 和 KV ID 写入 Wrangler 配置（可用 `npm run setup:cloudflare -- <D1_UUID> <KV_ID> os.coolkiy.qzz.io`），将更改同步提交 GitHub，确保只有公开资源标识写入仓库。
- 在 Cloudflare Secret 中添加至少 32 字符的随机 `RATE_LIMIT_SALT`，切勿公布其值。执行 `npm run db:remote` 创建数据库表，并把 `public-persona.txt` 写入绑定 `PERSONA` 的 KV Key `public:persona`。
- Workers AI 绑定为 `AI`；构建后 Wrangler 部署，检查健康端点 `/api/health`。同时现场测试 AI 对话、留言写入待审/公开只能显示 approved、所有照片、加载性能、网页移动端以及无明显 JS 错误。
- 如果模型或计费权限不可用，不能伪装 AI 可用；暂时隐藏或降级该功能，并告诉我如何开启。

## D. 自定义域名验收

- 当 Worker 临时地址验证成功，确认 `os.coolkiy.qzz.io` 现有 DNS 不会被覆盖，再设置 Worker Custom Domain；等待 Cloudflare TLS 证书和 DNS 生效。
- **最终只在真正可打开后报告已部署完成**：给我 Github 仓库真实 URL、Worker 临时 URL、正式 HTTPS URL、最后提交 commit SHA、构建结果、DNS/TLS 状态和 API/桌面/手机端测试结果。若有步骤需要我的手动授权，明确指出唯一下一步即可，勿让我重复配置。

如果你发现需要额外授权 GitHub 仓库创建权限或 Cloudflare DNS 权限，就停在权限动作前请我确认，不要发明凭据、密钥或成功结果。

## E. 免费优先（用户已明确）
- 在 Cloudflare 免费套餐内先部署基础网站；所有 AI 调用及 D1、KV 操作均需检查当前免费额度、配额和计费提示。任何需要付费的动作必须先停下征求许可。
- GitHub Public 仓库不产生额外的仓库订阅费用，但不要开启收费的 Actions runner 或第三方产品。
- 自定义域名 `os.coolkiy.qzz.io` 的 DNS 区域是否可由该 CF 账户管理，需要实测确认；若无法直接托管，提供免费接入方案并说明 DNS 改动。
