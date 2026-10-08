# Muse 部署任务｜Dandan OS → Cloudflare Workers（免费优先）

**用户已完成 GitHub 发布：** https://github.com/Daisyhu668/dandan-os （Public，`main` 分支包含完整代码及 10 张 WebP 照片；请直接 clone）。  
**唯一目标域名：** `https://os.coolkiy.qzz.io`。  
**预算：** 优先免费；任何需要订阅、升级、付费账户或可能产生费用的动作，在执行前暂停并征求用户许可。

## 1. 直接拉取并做构建验收
- 从现有 GitHub 公共仓库 clone，勿重新建仓、勿上传 ZIP 覆盖现有源码。
- 安装 Node.js >=20.19，执行 `npm install`、`npm run check:static`、`npm run build`。
- 当前只是代码/素材同步及静态检查通过，**此前没有完成 npm 生产构建**；请修复依赖、TanStack Start SSR/Vite、类型与构建错误。产生的 lockfile 和修复提交到 `main`。
- 视觉保持现有蓝色渐变 / Macintosh 桌面 Dock / 窗口 / 旅行相册 / 钢镚肖像，不要重建成套用的模板。
- 检查移动端、Finder、Photos、Travel、AI 对话、留言窗口的交互、路由、页面滚动及可访问性。

## 2. Cloudflare 免费配置
- 登录用户 Cloudflare 账号，核实 `dandan-os` Worker、`coolkiy.qzz.io` 域名/子域名区域、现有 DNS 记录及可用免费配额。
- 先检查 Worker 的 `wrangler.jsonc`；首次预览部署暂时去掉 `routes` 配置，在 `workers.dev` 上验证，待成功后恢复自定义域名。
- 需要时创建 D1 `dandan-os-db` 和 KV namespace `DANDAN_PUBLIC_PERSONA`；填入真实 database_id 和 namespace id，应用 `migrations/0001_initial.sql` 并写入公开资料 `public-persona.txt` 到 KV `public:persona`。
- Workers AI 使用绑定 `AI`，**先核实免费请求额度和当前账户是否允许该模型**。如果需要支付，暂时停用 AI，对外静态网站先正常上线。
- 给 Worker 设置高熵 Secret `RATE_LIMIT_SALT`，不要上传到 GitHub，也不要让用户在聊天中发送 Token、密码或 cookie。
- 先运行 `npm run build` 再 `npm run deploy`，通过 `/api/health`、图片、API、留言、控制台等检查 Worker。
- 如果域名 DNS 未托管在可用的 Cloudflare zone，不能擅自覆盖原有记录；先说明实际可用的免费域名接入办法及需要用户授权的最小步骤。

## 3. DNS 与正式验收
- 确认 `os.coolkiy.qzz.io` 现存 DNS 冲突、zone 归属及 TLS 证书签发条件后，用 Cloudflare Worker Custom Domain 绑定；请勿覆盖其他网站。
- 只有当 HTTPS 真正访问成功，并且 Dock、照片、手机端、AI（如开启）及留言接口均有实测结果时，才能说已上线。
- 完成后给用户准确的 GitHub commit SHA、`workers.dev` URL、正式 HTTPS URL、构建结果、DNS/TLS 状态及费用为 0 的核验情况。
- 遇到 Cloudflare 登录、安全验证或需要费用时，只让用户完成该必要授权，不要擅自修改账单设置。

注意：本项目原站设计属于第三方公开参考，未复制其私有源码；只发布用户批准公开的个人经历与旅行图片。