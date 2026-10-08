# Muse · Dandan OS · Cloudflare 免费部署任务

**目标 GitHub**：https://github.com/Daisyhu668/dandan-os （**Public**，已创建）  
**目标网站**：https://os.coolkiy.qzz.io  
**项目来源**：用户在 ChatGPT 对话中取得的 `Dandan-OS-GitHub-Ready.zip`。请将该 ZIP 作为完整项目源文件；不要把 README 当成完整源代码。

## 1. 发布 GitHub
1. 下载用户提供的项目 ZIP，完整解压，将根目录文件、隐藏文件、`src/`、`public/assets/photos/` 中的 **10 张 WebP 图片**、`migrations/`、`scripts/` 全部提交到这个既有的公开仓库 `main` 分支。
2. 保留原有蓝色渐变、Mac 风格 Dock、窗口交互、旅行相册、真实钢镚与多洛米蒂图片，不要替换为模板。
3. 不要上传 `.env`、`.dev.vars`、访问令牌、cookie、银行内部客户资料或私密 Notion 原始页面。GitHub 免费公共仓库即可。

## 2. 构建前 QA
用 Node.js 20.19+ 执行 `npm install`、`npm run check:static`、`npm run build`，记录错误并修复源码再提交（包括 lockfile）。项目此前只做了静态检查，尚未完成真正生产构建；**不要将其描述为已构建通过**。
检查桌面及移动设备中 Dock、Finder、相册、旅行篇、留言、AI 对话的导航和交互。

## 3. Cloudflare Workers
使用用户本人 Cloudflare 账号，优先免费套餐，不开通付费服务。
1. 检查 `dandan-os` Worker 和 `os.coolkiy.qzz.io` 已有 DNS 记录；不能覆盖他人服务。
2. 在免费额度可用的条件下新建 D1 数据库 `dandan-os-db`、KV namespace `DANDAN_PUBLIC_PERSONA`，把资源 ID 配到 `wrangler.jsonc`。若涉及升级/付费先暂停取得用户许可。
3. 使用 `RATE_LIMIT_SALT` secret（随机高熵值，绝不提交 GitHub）；初始化 `migrations/0001_initial.sql`，写入仅公开信息的 KV persona。
4. Workers AI 功能应做免费额度核实；不能免费开启时先关闭 AI 入口，静态网站仍应正常运行。
5. **先删除/暂时禁用 Wrangler routes** 以部署 workers.dev 测试地址，完成健康检查和交互测试后再恢复自定义域名设置。
6. 确认 DNS 归属、证书、原有解析情况后，再启用 `os.coolkiy.qzz.io` Custom Domain。

## 4. 最终验收
仅在实测通过后报告部署成功：提供 commit SHA、workers.dev 临时 URL、`https://os.coolkiy.qzz.io` 正式 URL、构建日志摘要、DNS/HTTPS 检查、AI/D1/KV 实际状态和测试结果。

**预算规则：免费为先，任何会扣费、开通订阅、升级套餐的动作必须在执行前征得用户同意。**
