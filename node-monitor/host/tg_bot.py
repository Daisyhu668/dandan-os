#!/usr/local/bin/python3
"""Owner-only Telegram console. Long-polls getUpdates; does not print secrets.

Cron: once a minute. --selftest renders every screen and does not restart.
--menu sends the keyboard once.
"""
import json
import os
import subprocess
import sys
import time
import traceback
import urllib.error
import urllib.request

HOME = os.path.expanduser("~")
os.environ["PATH"] = os.path.expanduser("~/bin") + ":/usr/local/bin:/usr/bin:/bin:" + os.environ.get("PATH", "")
LOGF = os.path.join(HOME, ".tg_bot.log")
OFFF = os.path.join(HOME, ".tg_offset")
SEENF = os.path.join(HOME, ".tg_seen")
LOCKF = os.path.join(HOME, ".tg_bot.lock")
CONFF = os.path.join(HOME, ".tg_bot.conf")
STATUSF = os.path.join(HOME, ".node_status.json")
TZ_HOURS = 8

CMDS = {
    "/start": "menu",
    "/menu": "menu",
    "/status": "status",
    "/nodes": "sub",
    "/sub": "sub",
    "/speed": "speed",
    "/route": "route",
    "/restart_argo": "restart_argo",
    "/restart_main": "restart_main",
    "/help": "help",
}


def log(msg):
    try:
        with open(LOGF, "a", encoding="utf-8") as handle:
            handle.write(time.strftime("%m-%d %H:%M:%S") + " " + msg + "\n")
    except Exception:
        pass


def err_brief(exc):
    if isinstance(exc, urllib.error.HTTPError):
        return "HTTP %s" % exc.code
    text = str(exc)
    if "api.telegram.org" in text or "bot" in text.lower():
        return type(exc).__name__
    return (type(exc).__name__ + " " + text)[:120]


def load_conf(path=None, missing_ok=False):
    path = path or CONFF
    conf = {}
    if not os.path.isfile(path):
        if missing_ok:
            return conf
        log("conf missing")
        raise SystemExit(0)
    with open(path, encoding="utf-8", errors="replace") as handle:
        for line in handle:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            conf[key.strip()] = value.strip().strip("'\"")
    return conf


def load_status():
    if not os.path.isfile(STATUSF):
        return None
    try:
        with open(STATUSF, encoding="utf-8") as handle:
            data = json.load(handle)
    except Exception:
        return {"checked_at": "", "lines": [], "broken": True}
    if not isinstance(data, dict):
        return {"checked_at": "", "lines": [], "broken": True}
    data.setdefault("lines", [])
    return data


def api(token, method, payload, timeout=45):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        "https://api.telegram.org/bot%s/%s" % (token, method),
        data=data,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", "replace"))


def kb_main():
    return {"inline_keyboard": [
        [{"text": "📊状态", "callback_data": "status"}, {"text": "🔗订阅", "callback_data": "sub"}],
        [{"text": "⚡测速", "callback_data": "speed"}, {"text": "🧭分流", "callback_data": "route"}],
        [{"text": "🔄重启隧道", "callback_data": "restart_argo"}, {"text": "♻️重启主节点", "callback_data": "restart_main"}],
        [{"text": "❓帮助", "callback_data": "help"}],
    ]}


def kb_confirm(kind, ts):
    return {"inline_keyboard": [[
        {"text": "✅确认", "callback_data": "ok:%s:%s" % (kind, ts)},
        {"text": "取消", "callback_data": "menu"},
    ]]}


def actions_path():
    home_script = os.path.join(HOME, "tg_actions.sh")
    if os.path.isfile(home_script):
        return home_script
    here = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tg_actions.sh")
    if os.path.isfile(here):
        return here
    return home_script


def run_action(args, timeout):
    script = actions_path()
    if not os.path.isfile(script):
        return 1, "未找到 tg_actions.sh"
    try:
        result = subprocess.run(
            ["/bin/bash", script] + list(args),
            timeout=timeout,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
    except Exception as exc:
        return 1, "执行失败: %s" % type(exc).__name__
    out = (result.stdout or "").strip()
    if result.returncode != 0 and not out:
        out = "失败（退出码 %s）" % result.returncode
    return result.returncode, out or "无输出"


def aware_now():
    return datetime_now()


def datetime_now():
    import datetime
    tz = datetime.timezone(datetime.timedelta(hours=TZ_HOURS))
    return datetime.datetime.now(tz)


def parse_checked(raw):
    import datetime
    if not raw:
        return None
    try:
        dt = datetime.datetime.fromisoformat(raw)
    except Exception:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone(datetime.timedelta(hours=TZ_HOURS)))
    return dt


def fmt_age(minutes):
    if minutes is None:
        return "时间未知"
    if minutes < 1:
        return "刚刚"
    whole = int(minutes)
    if whole < 120:
        return "%s 分钟前" % whole
    return "%s 小时前" % (whole // 60)


def render_lines(lines):
    if not lines:
        return "没有线路记录。"
    order = []
    groups = {}
    for line in lines:
        if not isinstance(line, dict):
            continue
        key = "%s %s" % (line.get("provider") or "?", line.get("protocol") or "?")
        if key not in groups:
            order.append(key)
            groups[key] = []
        groups[key].append(line)
    out = []
    for key in order:
        out.append(key)
        for line in groups[key]:
            label = line.get("label") or ""
            parts = label.split()
            short = parts[-1] if parts else label
            avail = line.get("avail_24h")
            avail_s = "%s%%" % avail if isinstance(avail, int) else "—"
            if line.get("ok") and isinstance(line.get("latency_ms"), (int, float)):
                ip = line.get("exit_ip") or "未知"
                out.append("✅ %s  %sms  出口 %s  24h %s" % (short, int(line["latency_ms"]), ip, avail_s))
            else:
                out.append("❌ %s  失败  24h %s" % (short, avail_s))
        out.append("")
    return "\n".join(out).rstrip()


def screen_menu():
    return "节点控制台\n点下面的按钮，或发送 /help。\n海外视角不能证明国内可连。"


def screen_status(status, local_text, now=None):
    now = now or aware_now()
    parts = [
        "📊状态",
        "海外视角：检测来自美国 GitHub Actions，不能证明国内可连。",
        "",
    ]
    if not status:
        parts.append("还没有 ~/.node_status.json。")
    elif status.get("broken"):
        parts.append("结果文件无法读取。")
    else:
        checked = parse_checked(status.get("checked_at") or "")
        if checked is None:
            parts.append("检测时间未知")
        else:
            local = checked.astimezone(now.tzinfo)
            minutes = (now - local).total_seconds() / 60.0
            parts.append("检测 %s（%s）" % (local.strftime("%m-%d %H:%M"), fmt_age(minutes)))
            if minutes > 70:
                parts.append("⚠️ 结果已超过 70 分钟，可能过期。")
        parts.append("")
        parts.append(render_lines(status.get("lines") or []))
    parts.append("")
    parts.append("本地")
    parts.append((local_text or "").strip() or "无")
    return "\n".join(parts)


def screen_sub(conf):
    rows = []
    mapping = [
        ("HN_SUB", "hostuno 订阅（小火箭 / Karing）"),
        ("HN_CLASH", "hostuno 订阅（Clash Meta）"),
        ("CF_SUB", "Cloudflare 订阅（小火箭 / Karing）"),
        ("CLOADY_SUB", "Cloady 订阅（小火箭 / Karing）"),
    ]
    for key, title in mapping:
        value = (conf.get(key) or "").strip()
        if not value:
            continue
        rows.append("%s\n%s" % (title, value))
    if not rows:
        return (
            "🔗订阅\n\n"
            "未配置订阅。请在 ~/.tg_bot.conf 写入 HN_SUB、HN_CLASH、CF_SUB、CLOADY_SUB，"
            "没有的项会自动跳过。"
        )
    return "🔗订阅\n\n" + "\n\n".join(rows)


def screen_speed(status):
    lines = []
    for line in (status or {}).get("lines") or []:
        if isinstance(line, dict) and line.get("ok") and isinstance(line.get("latency_ms"), (int, float)):
            lines.append(line)
    lines.sort(key=lambda line: line["latency_ms"])
    out = [
        "⚡测速（海外视角）",
        "来自美国 GitHub Actions，不能证明国内可连。",
        "",
    ]
    if not lines:
        out.append("没有通过的节点。")
        return "\n".join(out)
    for index, line in enumerate(lines, 1):
        out.append("%s. %s  %sms" % (index, line.get("label") or "?", int(line["latency_ms"])))
    out.append("")
    out.append("建议：优先 %s。国内是否可连，请在本地再确认。" % (lines[0].get("label") or "最快的一条"))
    return "\n".join(out)


def screen_route(conf):
    clash = (conf.get("HN_CLASH") or "").strip()
    link = clash if clash else "未配置 HN_CLASH"
    return (
        "🧭分流\n\n"
        "规则模式：中国大陆域名和 IP 直连，其余走代理。\n"
        "客户端用 Clash Meta，导入订阅后选择规则（rule）模式。\n\n"
        "Clash Meta：\n%s" % link
    )


def screen_help():
    return (
        "❓帮助\n\n"
        "📊状态 /status — 海外拨测和本机进程\n"
        "🔗订阅 /sub — 订阅链接（小火箭 / Karing / Clash Meta）\n"
        "⚡测速 /speed — 按延迟排行\n"
        "🧭分流 /route — 大陆直连、其余代理\n"
        "🔄重启隧道 /restart_argo — 二次确认后重启 Argo\n"
        "♻️重启主节点 /restart_main — 二次确认后重启 sing-box\n"
        "❓帮助 /help — 本说明\n\n"
        "海外结果来自美国，不代表国内可连。重启确认 5 分钟后失效。"
    )


def screen_confirm(kind):
    if kind == "argo":
        return "确认重启隧道？将结束 cloudflared，再执行和 keepalive 相同的恢复命令。5 分钟内有效。"
    return "确认重启主节点？将结束 sing-box 并重新启动。5 分钟内有效。"


def render(action, conf):
    if action == "menu":
        return screen_menu(), kb_main()
    if action == "status":
        _rc, local = run_action(["local"], 40)
        return screen_status(load_status(), local, aware_now()), kb_main()
    if action == "sub":
        return screen_sub(conf), kb_main()
    if action == "speed":
        return screen_speed(load_status() or {}), kb_main()
    if action == "route":
        return screen_route(conf), kb_main()
    if action == "help":
        return screen_help(), kb_main()
    if action == "restart_argo":
        return screen_confirm("argo"), kb_confirm("argo", int(time.time()))
    if action == "restart_main":
        return screen_confirm("main"), kb_confirm("main", int(time.time()))
    return screen_help(), kb_main()


def render_confirm(kind, ts):
    try:
        stamp = int(ts)
    except (TypeError, ValueError):
        return "确认无效。", kb_main()
    if kind not in ("argo", "main"):
        return "确认无效。", kb_main()
    if abs(time.time() - stamp) > 300:
        return "确认已过期，请重新点重启。", kb_main()
    if kind == "argo":
        rc, out = run_action(["restart-argo"], 90)
        title = "🔄重启隧道"
    else:
        rc, out = run_action(["restart-main"], 45)
        title = "♻️重启主节点"
    mark = "成功" if rc == 0 else "失败"
    return "%s%s\n%s" % (title, mark, out), kb_main()


def deliver(token, chat, text, markup, message_id=None):
    payload = {
        "chat_id": chat,
        "text": (text or "")[:4000],
        "disable_web_page_preview": True,
        "reply_markup": markup,
    }
    if message_id:
        payload["message_id"] = message_id
        try:
            res = api(token, "editMessageText", payload, timeout=20)
            if res.get("ok"):
                return
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", "replace")
            if "message is not modified" in body:
                return
            log("edit err HTTP %s" % exc.code)
        except Exception as exc:
            log("edit err " + err_brief(exc))
        payload.pop("message_id", None)
    api(token, "sendMessage", payload, timeout=20)


def answer(token, callback_id, text=""):
    try:
        api(token, "answerCallbackQuery", {
            "callback_query_id": callback_id,
            "text": (text or "")[:180],
        }, timeout=15)
    except Exception as exc:
        log("answer err " + err_brief(exc))


def read_offset():
    try:
        with open(OFFF, encoding="utf-8") as handle:
            return int(handle.read().strip() or 0)
    except Exception:
        return 0


def read_seen():
    try:
        with open(SEENF, encoding="utf-8") as handle:
            return set(int(item) for item in handle.read().split() if item.strip())
    except Exception:
        return set()


def save_progress(offset, seen):
    keep = sorted(seen)[-500:]
    try:
        with open(SEENF, "w", encoding="utf-8") as handle:
            handle.write(" ".join(str(item) for item in keep))
        with open(OFFF, "w", encoding="utf-8") as handle:
            handle.write(str(offset))
    except Exception as exc:
        log("save err " + type(exc).__name__)


def command_of(text):
    if not text:
        return None
    head = text.strip().split()[0].split("@")[0]
    if head in CMDS:
        return CMDS[head]
    if head.startswith("/"):
        return "help"
    return None


def handle_update(token, chat, update, conf):
    callback = update.get("callback_query")
    if callback:
        message = callback.get("message") or {}
        cid = str((message.get("chat") or {}).get("id", ""))
        if cid != str(chat):
            answer(token, callback.get("id") or "")
            log("skip non-owner callback")
            return
        data = str(callback.get("data") or "")
        answer(token, callback.get("id") or "", "收到")
        mid = message.get("message_id")
        if data.startswith("ok:"):
            _tag, kind, stamp = (data.split(":", 2) + ["", ""])[:3]
            text, markup = render_confirm(kind, stamp)
        else:
            action = data if data in (
                "menu", "status", "sub", "speed", "route", "help", "restart_argo", "restart_main"
            ) else "help"
            text, markup = render(action, conf)
        deliver(token, chat, text, markup, mid)
        return
    message = update.get("message") or {}
    cid = str((message.get("chat") or {}).get("id", ""))
    text = (message.get("text") or "").strip()
    if cid != str(chat):
        log("skip non-owner")
        return
    action = command_of(text)
    if not action:
        return
    log("dispatch cmd=%s" % action)
    reply, markup = render(action, conf)
    deliver(token, chat, reply, markup)


def poll(conf):
    token = conf.get("TG_TOKEN") or conf.get("token") or ""
    chat = conf.get("TG_CHAT_ID") or conf.get("chat") or ""
    if not token or not chat:
        log("conf incomplete")
        return
    offset = read_offset()
    seen = read_seen()
    try:
        data = api(token, "getUpdates", {"offset": offset, "timeout": 25}, timeout=45)
    except Exception as exc:
        log("getUpdates err " + err_brief(exc))
        return
    maxid = offset - 1
    try:
        for update in data.get("result") or []:
            uid = int(update.get("update_id") or 0)
            if uid > maxid:
                maxid = uid
            if uid in seen:
                continue
            seen.add(uid)
            save_progress(maxid + 1 if maxid >= offset else offset, seen)
            try:
                handle_update(token, chat, update, conf)
            except Exception:
                log("LOOP FAIL\n" + traceback.format_exc(limit=3))
    finally:
        if maxid >= offset:
            save_progress(maxid + 1, seen)
        else:
            save_progress(offset, seen)


def selftest():
    conf = load_conf(missing_ok=True)
    status = load_status()
    _rc, local = run_action(["local"], 25)
    now = aware_now()
    screens = [
        ("MENU", screen_menu()),
        ("STATUS", screen_status(status, "（selftest 不重启）\n" + local, now)),
        ("SUB", screen_sub(conf)),
        ("SPEED", screen_speed(status or {})),
        ("ROUTE", screen_route(conf)),
        ("HELP", screen_help()),
        ("CONFIRM_ARGO", screen_confirm("argo")),
        ("CONFIRM_MAIN", screen_confirm("main")),
    ]
    for name, text in screens:
        sys.stdout.write("===== %s =====\n%s\n\n" % (name, text))
    sys.stdout.write("SELFTEST_OK\n")


def send_menu():
    conf = load_conf()
    token = conf.get("TG_TOKEN") or ""
    chat = conf.get("TG_CHAT_ID") or ""
    if not token or not chat:
        log("conf incomplete")
        raise SystemExit(1)
    deliver(token, chat, screen_menu(), kb_main())


def main():
    if "--selftest" in sys.argv:
        selftest()
        return
    if "--menu" in sys.argv:
        send_menu()
        return
    owned = False
    try:
        if os.path.exists(LOCKF) and time.time() - os.path.getmtime(LOCKF) < 180:
            return
        with open(LOCKF, "w", encoding="utf-8") as handle:
            handle.write(str(os.getpid()))
        owned = True
    except SystemExit:
        raise
    except Exception as exc:
        log("lock err " + type(exc).__name__)
    try:
        conf = load_conf()
        poll(conf)
    finally:
        if owned:
            try:
                os.unlink(LOCKF)
            except Exception:
                pass


if __name__ == "__main__":
    main()
