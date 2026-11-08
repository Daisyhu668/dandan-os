#!/bin/bash
# Host-side actions for the Telegram console and for keepalive.sh.
# keepalive calls: ~/tg_push.sh argo-changed <host>
# The bot calls: local | restart-argo | restart-main
export PATH="$HOME/bin:/usr/local/bin:/usr/bin:/bin:${PATH:-}"
CONF="$HOME/.tg_bot.conf"
set -eu

find_workdir() {
  for d in "$HOME"/domains/*/logs; do
    [ -f "$d/sb.txt" ] || continue
    printf "%s\n" "$d"
    return 0
  done
  return 1
}

cur_host() {
  wd=$(find_workdir) || return 0
  [ -f "$wd/boot.log" ] || return 0
  grep -a "trycloudflare.com" "$wd/boot.log" 2>/dev/null \
    | tail -n 1 \
    | grep -aoE "https://[a-z0-9.-]*trycloudflare.com" \
    | head -n 1 \
    | sed "s|https://||" || true
}

tunnel_pids() {
  ps aux 2>/dev/null | awk '/[t]unnel --u/ {print $2}'
}

local_status() {
  wd=$(find_workdir || true)
  if [ -n "$wd" ]; then
    echo "工作目录已找到"
  else
    echo "❌ 未找到 ~/domains/*/logs/sb.txt"
  fi
  sbb=""
  if [ -n "$wd" ] && [ -f "$wd/sb.txt" ]; then
    sbb=$(tr -d '[:space:]' < "$wd/sb.txt" || true)
  fi
  if [ -n "$sbb" ] && pgrep -x "$sbb" >/dev/null 2>&1; then
    echo "✅ sing-box 运行中"
  else
    echo "❌ sing-box 未运行"
  fi
  if [ -n "$(tunnel_pids)" ]; then
    echo "✅ 隧道进程在"
  else
    echo "❌ 隧道进程不在"
  fi
  h=$(cur_host || true)
  if [ -n "$h" ]; then
    code=$(curl --max-time 8 -o /dev/null -s -w "%{http_code}" "https://$h" 2>/dev/null || true)
    if [ "$code" = "404" ]; then
      echo "✅ argo 返回 404"
      echo "$h"
    else
      echo "❌ argo HTTP ${code:-无}"
      echo "$h"
    fi
  else
    echo "❌ 未读到 argo 域名"
  fi
  echo "-- 端口 --"
  if command -v devil >/dev/null 2>&1; then
    devil port list 2>&1 | head -n 30 || true
  else
    echo "devil 不可用"
  fi
}

listen_ok() {
  pid="$1"
  command -v sockstat >/dev/null 2>&1 || return 1
  sockstat -l 2>/dev/null | awk -v p="$pid" 'NR > 1 && $3 == p { found = 1 } END { exit found ? 0 : 1 }'
}

restart_main() {
  wd=$(find_workdir) || { echo "FAIL 找不到工作目录（~/domains/*/logs/sb.txt）"; exit 1; }
  sbb=$(tr -d '[:space:]' < "$wd/sb.txt" || true)
  [ -n "$sbb" ] || { echo "FAIL sb.txt 为空"; exit 1; }
  [ -x "$wd/$sbb" ] || { echo "FAIL 二进制不可执行"; exit 1; }
  [ -f "$wd/config.json" ] || { echo "FAIL 没有 config.json"; exit 1; }
  pids=$(pgrep -x "$sbb" || true)
  if [ -n "$pids" ]; then
    kill $pids 2>/dev/null || true
    sleep 1
    pids=$(pgrep -x "$sbb" || true)
    if [ -n "$pids" ]; then
      kill -9 $pids 2>/dev/null || true
      sleep 1
    fi
  fi
  if pgrep -x "$sbb" >/dev/null 2>&1; then
    echo "FAIL 旧进程未能结束"
    exit 1
  fi
  (
    cd "$wd" || exit 1
    nohup ./"$sbb" run -c config.json >/dev/null 2>&1 &
    disown >/dev/null 2>&1 || true
  ) || { echo "FAIL 启动命令失败"; exit 1; }
  pid=""
  i=0
  while [ "$i" -lt 10 ]; do
    i=$((i + 1))
    pid=$(pgrep -x "$sbb" | head -n 1 || true)
    if [ -n "$pid" ] && listen_ok "$pid"; then
      echo "OK sing-box 已监听 pid=$pid"
      exit 0
    fi
    sleep 1
  done
  if [ -z "$pid" ]; then
    echo "FAIL 进程没有起来"
  elif ! command -v sockstat >/dev/null 2>&1; then
    echo "FAIL 进程在，但没有 sockstat，无法确认监听 pid=$pid"
  else
    echo "FAIL 进程在但未监听到端口 pid=$pid"
  fi
  exit 1
}

restart_argo() {
  [ -x "$HOME/bin/sb" ] || { echo "FAIL 没有 ~/bin/sb"; exit 1; }
  old=$(cur_host || true)
  pids=$(tunnel_pids || true)
  if [ -n "$pids" ]; then
    kill $pids 2>/dev/null || true
    sleep 1
    pids=$(tunnel_pids || true)
    if [ -n "$pids" ]; then
      kill -9 $pids 2>/dev/null || true
    fi
  fi
  printf "4\n0\n" | "$HOME/bin/sb" >/dev/null 2>&1 &
  deadline=$((SECONDS + 60))
  new=""
  last_code=""
  while [ "$SECONDS" -lt "$deadline" ]; do
    h=$(cur_host || true)
    if [ -n "$h" ] && [ "$h" != "$old" ]; then
      last_code=$(curl --max-time 8 -o /dev/null -s -w "%{http_code}" "https://$h" 2>/dev/null || true)
      if [ "$last_code" = "404" ]; then
        new=$h
        break
      fi
    fi
    sleep 2
  done
  if [ -n "$new" ]; then
    printf "%s\n" "$new" > "$HOME/.argo_last_host"
    echo "OK 新域名 $new 返回 404"
    exit 0
  fi
  h=$(cur_host || true)
  code=$(curl --max-time 8 -o /dev/null -s -w "%{http_code}" "https://$h" 2>/dev/null || true)
  if [ -n "$(tunnel_pids)" ] && [ "$code" = "404" ] && [ -n "$h" ]; then
    printf "%s\n" "$h" > "$HOME/.argo_last_host"
    echo "OK 隧道已恢复，域名未变：$h 返回 404"
    exit 0
  fi
  echo "FAIL 60 秒内隧道未恢复（域名 ${h:-无}，HTTP ${code:-无}）"
  exit 1
}

argo_changed() {
  host="${1:-}"
  [ -f "$CONF" ] && . "$CONF"
  if [ -z "${TG_TOKEN:-}" ] || [ -z "${TG_CHAT_ID:-}" ]; then
    echo "no telegram conf" >&2
    exit 1
  fi
  text="Hostuno Argo 域名已更新
新域名: ${host:-未知}
请在客户端刷新订阅。"
  if [ -n "${HN_SUB:-}" ]; then
    text="${text}
${HN_SUB}"
  fi
  curl -sS --max-time 20 -G "https://api.telegram.org/bot${TG_TOKEN}/sendMessage" \
    --data-urlencode "chat_id=${TG_CHAT_ID}" \
    --data-urlencode "text=${text}" \
    --data-urlencode "disable_web_page_preview=true" >/dev/null
}

cmd="${1:-}"
if [ "$#" -gt 0 ]; then
  shift
fi
case "$cmd" in
  local) local_status ;;
  restart-main) restart_main ;;
  restart-argo) restart_argo ;;
  argo-changed) argo_changed "${1:-}" ;;
  *)
    echo "用法: tg_actions.sh local|restart-argo|restart-main|argo-changed <host>"
    exit 1
    ;;
esac
