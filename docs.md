# 部署前检查清单

1. Cloudflare 登录成功且确认正确账号。
2. D1 创建、KV 创建，ID 已写入 `wrangler.jsonc`。
3. `RATE_LIMIT_SALT` 使用 `wrangler secret put` 设置（不能写进源码）。
4. `npm install`、`npm run build` 都已成功。
5. D1 migration 已远程执行。
6. Workers AI 在账号所在区域可用；已知模型可正确响应。
7. `/api/health` 返回 ready，Guestbook pending 机制、AI 限流成功验证。
8. 部署 `workers.dev` 后先检查手机版 Dock、窗口与滚动。
9. 用户确认需要的完整域名后，再添加 Custom Domain。
10. 用真实授权照片替换钢镚和旅行的插画后，再决定是否让搜索引擎收录。
