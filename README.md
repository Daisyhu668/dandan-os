# Dandan / OS

Dandan 的个人网站：Banking · AI Workflows · Mountains · Light。

**公开仓库 / Public repository**。计划运行于 Cloudflare Workers，正式域名：`https://os.coolkiy.qzz.io`。

## 状态 / Status
本仓库当前处于 **源码同步准备阶段**。完整应用源码与 10 张经艺术风格化处理的个人、钢镚和多洛米蒂照片仍在项目交接 ZIP 中，待 Muse 将源码、图片完整推送到 `main` 后才具备构建条件。仓库出现 README 不代表网站已经上线。

## 技术 / Stack
React 19 · TanStack Start · Motion · PixiJS · Cloudflare Workers · D1 · KV · Workers AI。

## Muse 部署目标
1. 从用户提供的 **Dandan-OS-GitHub-Ready.zip** 解压，将**所有文件和图片**上传至此仓库根目录，不是仅上传压缩包。
2. 优先在 Cloudflare 免费额度内完成 `npm install`、`npm run check:static`、`npm run build`，修复可能存在的兼容或构建错误，生成 lockfile 一并提交。
3. 创建 Cloudflare Worker `dandan-os`，如需使用 D1/KV/Workers AI，确认免费配额后再创建和绑定；任何可能扣费的功能必须先征得用户同意。
4. 首先在 `workers.dev` 临时地址完成验证，再确认 `os.coolkiy.qzz.io` DNS 控制权和现有解析记录，避免覆盖现有服务；然后绑定 HTTPS 域名。
5. 检查 Dock、Finder、Gallery、Travel、Mobile 布局、AI 对话、留言和照片是否可以正常访问，并向用户提供真实上线链接、commit SHA 和测试情况。

## 安全 / Safety
本仓库公开，**不要提交** Cloudflare API Token、GitHub PAT、`.env`、`.dev.vars`、用户隐私、内部银行材料和未经脱敏的 Notion 文档。不得将项目内的 AI 功能标注为已可用，除非实际完成 Worker、D1、KV 和模型调用测试。

网站视觉参考 [Elliot Hu](https://elliothu.me/) 的公开作品；本项目为独立实现，未经授权不使用原作者私有源码。
