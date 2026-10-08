# Dandan OS 3.0 — 架构与隐私边界

```text
Browser / React 19 + TanStack Router
  ├─ Legacy Desktop Shell (2.0 视觉与交互兼容层)
  ├─ React / Motion Guestbook.app
  └─ PixiJS Canvas atmospheric particles
          │ HTTPS same-origin
          ▼
Cloudflare Workers / TanStack Start SSR + Server Routes
  ├─ GET /api/health  ──→ binding readiness
  ├─ POST /api/chat   ──→ D1 salted rate-limit → Workers AI
  │                          │
  │                          └── KV public:persona or approved source fallback
  └─ GET/POST /api/guestbook ──→ D1 pending/approved messages
```

## 数据治理

- **公开站点内容**：从手动审核的个人介绍和旅行故事生成，不直连私人 Notion；隐私与客户数据不能发布。
- **KV**：只维护公开人格配置，禁止收录私人源文件、银行卡、邮箱或客户数据。
- **D1**：留言只显示 approved；聊天不存原文；速率控制只存加盐 SHA-256 IP 摘要。
- **Workers AI**：仅在服务端调用，访客端看不到模型绑定；请求信息由 Cloudflare 处理。
- **费用控制**：10 次/分钟/访客、250 次/天/全站；不是硬预算上限，因为其他资源调用和价格另计。
- **上线策略**：先 workers.dev，再绑定指定子域名。robots.txt 禁止索引；公开上线时由所有人核验后再决定放行索引。

## 开发阶段说明

3.0 是**渐进迁移版本**：TanStack Start SSR 提供主站和服务端 API，React 目前管理留言应用，PixiJS 与 Motion 已集成；2.0 全套桌面窗口尚在独立的 DOM 控制器里。后续可以按 Dock→窗口系统→应用注册表顺序继续用 React 组件替换，而无需牺牲原版 UI 的稳定性。
