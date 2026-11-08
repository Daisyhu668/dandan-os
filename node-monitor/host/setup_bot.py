#!/usr/local/bin/python3
"""Register bot commands and the public description. Reads ~/.tg_bot.conf."""
import json
import os
import sys
import urllib.error
import urllib.request

HOME = os.path.expanduser("~")
CONF = os.path.join(HOME, ".tg_bot.conf")

COMMANDS = [
    {"command": "status", "description": "查看节点状态"},
    {"command": "sub", "description": "订阅链接"},
    {"command": "speed", "description": "测速排行"},
    {"command": "route", "description": "分流说明"},
    {"command": "restart_argo", "description": "重启 Argo 隧道"},
    {"command": "restart_main", "description": "重启主节点"},
    {"command": "help", "description": "帮助"},
]
DESCRIPTION = (
    "查看海外拨测状态、订阅链接、测速和分流。"
    "重启隧道或主节点前需要再点一次确认。"
    "海外结果不能代表国内连通性。"
)
SHORT = "节点状态、订阅与重启"


def load_conf(path):
    conf = {}
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


def call(token, method, payload):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        "https://api.telegram.org/bot%s/%s" % (token, method),
        data=data,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = json.loads(resp.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")
        print("telegram HTTP %s" % exc.code)
        try:
            parsed = json.loads(detail)
            desc = parsed.get("description") or ""
        except Exception:
            desc = ""
        if desc:
            print(desc[:200])
        return False
    except Exception as exc:
        print("telegram %s" % type(exc).__name__)
        return False
    if not body.get("ok"):
        print("telegram rejected %s" % method)
        return False
    print("ok %s" % method)
    return True


def main():
    if not os.path.isfile(CONF):
        print("missing conf")
        return 1
    conf = load_conf(CONF)
    token = conf.get("TG_TOKEN") or ""
    if not token:
        print("missing token")
        return 1
    ok = True
    ok = call(token, "setMyCommands", {"commands": COMMANDS}) and ok
    ok = call(token, "setMyDescription", {"description": DESCRIPTION}) and ok
    ok = call(token, "setMyShortDescription", {"short_description": SHORT}) and ok
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
