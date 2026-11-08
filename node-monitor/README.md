# 节点监控

GitHub Actions 每 30 分钟从美国真实拨测全部线路，Telegram 汇总告警。host.uno 上的机器人读 `~/.node_status.json`，提供状态、订阅、测速和二次确认的重启。

拨测结果是海外视角，不能证明国内可连。

## 放到私有仓库

把**本目录里的内容**放到 `huqi02951-gif/node-monitor` 的仓库根目录，使 `check.py` 和 `.github/workflows/` 位于仓库根。多套一层 `node-monitor/` 时 Actions 不会运行。

不要把密钥写进代码或日志。密钥只放在私有仓库的 Actions secrets：

`TG_TOKEN` `TG_CHAT` `NODE_HOST` `NODE_UUID` `NODE_PATH` `SUB_URL` `CF_SUB` `HU_HOST` `HU_USER` `HU_PORT` `HU_PASS`

`monitor.yml` 定时 `7,37 * * * *`（UTC）。每天 09:07（上海）那次发送日报；手动运行可勾选立即报告。`deploy-host.yml` 只在手动触发时更新主机上的机器人。

## 主机

已有 crontab 每分钟执行 `/usr/local/bin/python3 ~/tg_bot.py`。本工作流不改 crontab。

`~/.tg_bot.conf` 需要：

```
TG_TOKEN='...'
TG_CHAT_ID='...'
HN_SUB='https://...'
HN_CLASH='https://...'
CF_SUB='https://...'
CLOADY_SUB='https://...'
```

缺哪个订阅就跳过哪个。部署后 `~/tg_push.sh` 换成同一套脚本，`keepalive.sh` 的 `argo-changed <host>` 仍然可用。

注册命令菜单：`/usr/local/bin/python3 ~/setup_bot.py`（部署工作流会调用）。

## 测试

```
python3 -m py_compile check.py host/tg_bot.py host/setup_bot.py
bash -n host/tg_actions.sh
python3 tests/test_parsers.py
```

## 部署前要核对

- 工作目录按 `~/domains/*/logs/sb.txt` 找。有多个匹配时用字母序的第一个。
- `list.txt` 为空或不存在时才读 `jh.txt`。`jh.txt` 若不是 vless/vmess/hysteria2 链接，会报「订阅解析失败」。
- 旧 `tg_push.sh` 把订阅链接写在脚本里。替换后必须把 `HN_SUB`、`HN_CLASH`、`CF_SUB`、`CLOADY_SUB` 写入 `~/.tg_bot.conf`，否则订阅按钮是空的。
- `devil port list` 只原样截断展示，不按端口名判断对错。
- 重启隧道执行 `printf "4\n0\n" | ~/bin/sb`，并等 `boot.log` 里出现新的 trycloudflare 域名且返回 404。`sb` 若必须有终端，重启会失败并如实说明。60 秒内域名没变、但进程在且返回 404 时，报告「域名未变」。
- 主节点重启后用 `sockstat` 确认在监听。没有 `sockstat` 会报失败。
- 线路名只显示服务商、协议和 IPv4 最后一段（或 `argo` / 短标记），不显示完整地址、UUID、路径、密码。
- 默认分支若禁止 Actions 推送，`state.json` 保存会失败。
- SSH 使用 `StrictHostKeyChecking=accept-new`。
- `~/backups/tgbot-<时间>/selftest.out` 可能含订阅链接，目录必须在网站根目录之外。
- `list.txt` 里的 Argo 域名如果没有随隧道更新，海外拨测会打到旧域名。
- 空的 `getUpdates` 不再把 `~/.tg_offset` 加一。旧脚本在没有消息时也会加一，时间久了会丢掉后面的按钮。
- 远程命令用 `/bin/bash -s`，不依赖登录 shell 是不是 bash。
