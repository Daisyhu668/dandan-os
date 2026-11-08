#!/usr/bin/env python3
"""Overseas end-to-end probe for every Cloady, Cloudflare and hostuno line.

Python 3 stdlib only. Telegram text and status.json never include a UUID,
path, password, Reality key, or full server address.
"""
import base64
import datetime
import hashlib
import json
import os
import re
import socket
import ssl
import statistics
import subprocess
import tempfile
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

TZ = datetime.timezone(datetime.timedelta(hours=8))
STATE_PATH = "state.json"
STATUS_PATH = "status.json"
FAIL_THRESHOLD = 2
HIST_MAX = 48
DAY = 86400
UUID_RE = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)
LINK_RE = re.compile(r"(?:vless|vmess|hysteria2|hy2)://\S+", re.I)


def redact(text, extra=()):
    out = UUID_RE.sub("<uuid>", "" if text is None else str(text))
    for item in extra:
        raw = "" if item is None else str(item)
        if len(raw) >= 6:
            out = out.replace(raw, "***")
    return out


def b64_bytes(payload):
    compact = re.sub(r"\s+", "", payload or "")
    if not compact:
        return None
    pad = "=" * ((4 - len(compact) % 4) % 4)
    for decoder in (base64.b64decode, base64.urlsafe_b64decode):
        try:
            return decoder(compact + pad)
        except Exception:
            continue
    return None


def try_b64_text(payload):
    data = b64_bytes(payload)
    if not data:
        return None
    try:
        text = data.decode("utf-8")
    except Exception:
        return None
    if "://" not in text:
        return None
    return text


def decode_blob(text):
    """Return subscription text. Accepts plain links or base64 (whole file or per line)."""
    raw = (text or "").lstrip("\ufeff").strip()
    if not raw:
        return ""
    if "://" in raw:
        return raw
    decoded = try_b64_text(raw)
    if decoded:
        return decoded
    lines = []
    changed = False
    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped or "://" in stripped:
            lines.append(stripped)
            continue
        one = try_b64_text(stripped)
        if one:
            lines.append(one)
            changed = True
        else:
            lines.append(stripped)
    if changed:
        return "\n".join(lines)
    return raw


def _first(query, key, default=""):
    values = query.get(key)
    if not values:
        return default
    return urllib.parse.unquote(values[0] or default)


def parse_vless(uri):
    parts = urllib.parse.urlsplit(uri.strip())
    if parts.scheme.lower() != "vless":
        return None
    uuid = urllib.parse.unquote(parts.username or "")
    server = parts.hostname or ""
    if not uuid or not server:
        return None
    query = urllib.parse.parse_qs(parts.query, keep_blank_values=True)
    security = (_first(query, "security", "none") or "none").lower()
    net = (_first(query, "type", "tcp") or "tcp").lower()
    sni = _first(query, "sni") or _first(query, "peer") or _first(query, "host") or server
    host = _first(query, "host") or sni or server
    return {
        "kind": "vless",
        "uuid": uuid,
        "server": server,
        "port": int(parts.port or 443),
        "security": security,
        "net": net,
        "path": _first(query, "path", "/") or "/",
        "host": host,
        "sni": sni,
        "fp": _first(query, "fp") or _first(query, "fingerprint") or "chrome",
        "pbk": _first(query, "pbk") or _first(query, "publicKey") or _first(query, "public_key"),
        "sid": _first(query, "sid") or _first(query, "shortId") or _first(query, "short_id"),
        "flow": _first(query, "flow"),
        "service_name": _first(query, "serviceName") or _first(query, "service_name"),
    }


def parse_vmess(uri):
    payload = uri.strip().split("://", 1)[1]
    payload = payload.split("#", 1)[0]
    data = b64_bytes(payload)
    if not data:
        return None
    try:
        obj = json.loads(data.decode("utf-8"))
    except Exception:
        return None
    server = str(obj.get("add") or "").strip()
    if not server:
        return None
    try:
        port = int(obj.get("port") or 443)
    except (TypeError, ValueError):
        port = 443
    tls_flag = str(obj.get("tls") or "").lower() in ("tls", "1", "true")
    net = str(obj.get("net") or "tcp").lower()
    host = str(obj.get("host") or server)
    return {
        "kind": "vmess",
        "uuid": str(obj.get("id") or ""),
        "server": server,
        "port": port,
        "aid": obj.get("aid") or 0,
        "scy": str(obj.get("scy") or "auto") or "auto",
        "net": net,
        "path": str(obj.get("path") or "/") or "/",
        "host": host,
        "sni": str(obj.get("sni") or host or server),
        "tls": tls_flag,
        "fp": str(obj.get("fp") or "chrome") or "chrome",
    }


def _flag_true(value):
    return str(value or "").lower() in ("1", "true", "yes", "on")


def parse_hysteria2(uri):
    parts = urllib.parse.urlsplit(uri.strip())
    if parts.scheme.lower() not in ("hysteria2", "hy2"):
        return None
    server = parts.hostname or ""
    if not server:
        return None
    password = urllib.parse.unquote(parts.username or "")
    if parts.password:
        password = password + ":" + urllib.parse.unquote(parts.password)
    query = urllib.parse.parse_qs(parts.query, keep_blank_values=True)
    if not password:
        password = _first(query, "auth") or _first(query, "password")
    if not password:
        return None
    insecure = _flag_true(_first(query, "insecure")) or _flag_true(_first(query, "allowInsecure"))
    obfs = _first(query, "obfs")
    obfs_password = _first(query, "obfs-password") or _first(query, "obfsPassword")
    return {
        "kind": "hysteria2",
        "password": password,
        "server": server,
        "port": int(parts.port or 443),
        "sni": _first(query, "sni") or server,
        "insecure": insecure,
        "obfs": obfs,
        "obfs_password": obfs_password,
    }


def parse_link(uri):
    text = (uri or "").strip()
    lower = text.lower()
    if lower.startswith("vless://"):
        return parse_vless(text)
    if lower.startswith("vmess://"):
        return parse_vmess(text)
    if lower.startswith("hysteria2://") or lower.startswith("hy2://"):
        return parse_hysteria2(text)
    return None


def iter_links(text):
    plain = decode_blob(text)
    for line in plain.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("//"):
            continue
        for match in LINK_RE.findall(stripped):
            yield match.rstrip("),;")


def is_ipv4(host):
    parts = (host or "").split(".")
    if len(parts) != 4:
        return False
    for part in parts:
        if not part.isdigit():
            return False
        if int(part) > 255:
            return False
    return True


def host_tag(host):
    """Public host label: IPv4 last octet, argo, or a short non-reversible tag."""
    raw = (host or "").strip().lower().rstrip(".")
    if is_ipv4(raw):
        return "." + raw.split(".")[-1]
    if raw.endswith("trycloudflare.com") or ".trycloudflare.com" in raw:
        return "argo"
    digest = hashlib.sha256(raw.encode()).hexdigest()[:4]
    return "d" + digest


def protocol_of(parsed):
    kind = parsed.get("kind")
    if kind == "vless":
        if parsed.get("security") == "reality":
            return "vless-reality"
        if parsed.get("net") == "ws":
            return "vless-ws"
        return "vless-tcp"
    if kind == "vmess":
        if parsed.get("net") == "ws":
            return "vmess-ws"
        return "vmess"
    if kind == "hysteria2":
        return "hysteria2"
    return kind or "unknown"


def _transport(parsed):
    net = parsed.get("net") or "tcp"
    if net == "ws":
        return {
            "type": "ws",
            "path": parsed.get("path") or "/",
            "headers": {"Host": parsed.get("host") or parsed.get("sni") or parsed["server"]},
        }
    if net == "grpc":
        return {"type": "grpc", "service_name": parsed.get("service_name") or ""}
    return None


def build_outbound(parsed):
    kind = parsed.get("kind")
    server = parsed.get("server")
    port = int(parsed.get("port") or 0)
    if not server or not port:
        raise ValueError("incomplete")
    if kind == "vless":
        if not parsed.get("uuid"):
            raise ValueError("incomplete")
        outbound = {
            "type": "vless",
            "tag": "proxy",
            "server": server,
            "server_port": port,
            "uuid": parsed["uuid"],
        }
        if parsed.get("flow"):
            outbound["flow"] = parsed["flow"]
        security = (parsed.get("security") or "none").lower()
        if security in ("tls", "reality"):
            tls = {
                "enabled": True,
                "server_name": parsed.get("sni") or server,
                "utls": {"enabled": True, "fingerprint": parsed.get("fp") or "chrome"},
            }
            if security == "reality":
                if not parsed.get("pbk"):
                    raise ValueError("incomplete")
                tls["reality"] = {
                    "enabled": True,
                    "public_key": parsed["pbk"],
                    "short_id": parsed.get("sid") or "",
                }
            outbound["tls"] = tls
        transport = _transport(parsed)
        if transport:
            outbound["transport"] = transport
        return outbound
    if kind == "vmess":
        if not parsed.get("uuid"):
            raise ValueError("incomplete")
        try:
            alter = int(parsed.get("aid") or 0)
        except (TypeError, ValueError):
            alter = 0
        security = parsed.get("scy") or "auto"
        if security not in ("auto", "aes-128-gcm", "chacha20-poly1305", "none", "zero"):
            security = "auto"
        outbound = {
            "type": "vmess",
            "tag": "proxy",
            "server": server,
            "server_port": port,
            "uuid": parsed["uuid"],
            "security": security,
            "alter_id": alter,
        }
        if parsed.get("tls"):
            outbound["tls"] = {
                "enabled": True,
                "server_name": parsed.get("sni") or parsed.get("host") or server,
                "utls": {"enabled": True, "fingerprint": parsed.get("fp") or "chrome"},
            }
        transport = _transport(parsed)
        if transport:
            outbound["transport"] = transport
        return outbound
    if kind == "hysteria2":
        if not parsed.get("password"):
            raise ValueError("incomplete")
        outbound = {
            "type": "hysteria2",
            "tag": "proxy",
            "server": server,
            "server_port": port,
            "password": parsed["password"],
            "tls": {
                "enabled": True,
                "server_name": parsed.get("sni") or server,
                "insecure": bool(parsed.get("insecure")),
            },
        }
        if parsed.get("obfs"):
            outbound["obfs"] = {
                "type": parsed["obfs"],
                "password": parsed.get("obfs_password") or "",
            }
        return outbound
    raise ValueError("unsupported")


def line_id(provider, protocol, server, port):
    material = "%s|%s|%s" % (server, port, protocol)
    digest = hashlib.sha256(material.encode()).hexdigest()[:8]
    return "%s:%s:%s:%s" % (provider, protocol, digest, port)


def make_line(parsed, provider):
    protocol = protocol_of(parsed)
    server = parsed.get("server") or ""
    try:
        port = int(parsed.get("port") or 0)
    except (TypeError, ValueError):
        port = 0
    tag = host_tag(server)
    line = {
        "id": line_id(provider, protocol, server, port),
        "provider": provider,
        "protocol": protocol,
        "label": "%s %s %s:%s" % (provider, protocol, tag, port),
        "tag": tag,
        "port": port,
        "outbound": None,
        "err": "",
        "public": True,
    }
    try:
        line["outbound"] = build_outbound(parsed)
    except Exception:
        line["err"] = "配置无法生成"
    return line


def cloady_line(host, uuid, path):
    if not (host and uuid and path):
        return None
    parsed = {
        "kind": "vless",
        "uuid": uuid,
        "server": host,
        "port": 443,
        "security": "tls",
        "net": "ws",
        "path": path,
        "host": host,
        "sni": host,
        "fp": "chrome",
        "flow": "",
        "pbk": "",
        "sid": "",
    }
    return make_line(parsed, "Cloady")


def links_from_text(text, provider):
    found = []
    seen = set()
    for uri in iter_links(text):
        parsed = parse_link(uri)
        if not parsed:
            continue
        line = make_line(parsed, provider)
        if line["id"] in seen:
            continue
        seen.add(line["id"])
        found.append(line)
    return found


def disambiguate(lines):
    groups = {}
    for line in lines:
        groups.setdefault(line["label"], []).append(line)
    for label, group in groups.items():
        if len(group) < 2:
            continue
        for index, line in enumerate(group, 1):
            line["label"] = "%s#%s" % (label, index)
    return lines


def placeholder(provider, protocol, label, err, public=True):
    return {
        "id": "%s:%s:none:0" % (provider, protocol),
        "provider": provider,
        "protocol": protocol,
        "label": label,
        "tag": "",
        "port": 0,
        "outbound": None,
        "err": err,
        "public": public,
    }


def load_lines(env):
    lines = []
    cloady = cloady_line(env.get("NODE_HOST", ""), env.get("NODE_UUID", ""), env.get("NODE_PATH", ""))
    if cloady:
        lines.append(cloady)
    cf = env.get("CF_SUB") or ""
    if cf.strip():
        parsed = links_from_text(cf, "Cloudflare")
        if parsed:
            lines.extend(parsed)
        else:
            lines.append(placeholder("Cloudflare", "订阅", "Cloudflare 订阅", "订阅解析失败"))
    hu = env.get("HU_LINKS") or ""
    hu_file = env.get("HU_LINKS_FILE") or ""
    if not hu and hu_file and os.path.isfile(hu_file):
        with open(hu_file, encoding="utf-8", errors="replace") as handle:
            hu = handle.read()
    fetch_failed = str(env.get("HU_FETCH_FAILED", "")).lower() == "true"
    if fetch_failed and not hu.strip():
        lines.append(placeholder("hostuno", "订阅", "hostuno 订阅", "订阅拉取失败"))
    elif hu.strip():
        parsed = links_from_text(hu, "hostuno")
        if parsed:
            lines.extend(parsed)
        else:
            lines.append(placeholder("hostuno", "订阅", "hostuno 订阅", "订阅解析失败"))
    elif hu_file:
        lines.append(placeholder("hostuno", "订阅", "hostuno 订阅", "订阅为空"))
    return disambiguate(lines)


def singbox_config(outbound, port):
    """One mixed inbound whose default outbound is this line.

    Same shape as the working single-node monitor: no route block, so the
    first outbound is the default. Matches sing-box 1.12.12.
    """
    proxy = dict(outbound)
    proxy.pop("tag", None)
    return {
        "log": {"level": "error", "timestamp": False},
        "inbounds": [{
            "type": "mixed",
            "listen": "127.0.0.1",
            "listen_port": int(port),
        }],
        "outbounds": [proxy],
    }


def _curl(port, url, timeout, want_body):
    cmd = [
        "curl", "-sS", "--max-time", str(timeout),
        "-x", "socks5h://127.0.0.1:%s" % port,
        "-o", "-" if want_body else "/dev/null",
        "-w", "\n%{http_code} %{time_total}",
        url,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 5)
    except subprocess.TimeoutExpired:
        return "000", "", None, "超时"
    except FileNotFoundError:
        return "000", "", None, "无 curl"
    text = result.stdout or ""
    if "\n" in text:
        body, meta = text.rsplit("\n", 1)
    else:
        body, meta = "", text
    parts = meta.split()
    code = parts[0] if parts else "000"
    elapsed = None
    if len(parts) > 1:
        try:
            elapsed = int(round(float(parts[1]) * 1000))
        except ValueError:
            elapsed = None
    if code in ("", "000"):
        err = "超时" if "timed out" in (result.stderr or "").lower() else "连接失败"
        return "000", body.strip(), elapsed, err
    return code, body.strip(), elapsed, ""


def fetch_exit_ip(port):
    code, body, _elapsed, _err = _curl(port, "https://api.ipify.org", 8, True)
    if code != "200":
        return ""
    if re.fullmatch(r"[0-9.]+|[0-9A-Fa-f:]+", body or ""):
        return body
    return ""


def public_fields(line, ok, latency, exit_ip, err):
    return {
        "id": line["id"],
        "provider": line["provider"],
        "protocol": line["protocol"],
        "label": line["label"],
        "ok": bool(ok),
        "latency_ms": latency,
        "exit_ip": exit_ip or "",
        "err": err or "",
        "public": bool(line.get("public", True)),
        "fails": 0,
        "avail_24h": 0,
    }


def probe_line(line, port, binary):
    if not line.get("outbound"):
        return public_fields(line, False, None, "", line.get("err") or "配置无法生成")
    if not (os.path.isfile(binary) and os.access(binary, os.X_OK)):
        return public_fields(line, False, None, "", "sing-box 不可用")
    fd, path = tempfile.mkstemp(prefix="nm-%s-" % port, suffix=".json")
    os.close(fd)
    os.chmod(path, 0o600)
    proc = None
    try:
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(singbox_config(line["outbound"], port), handle)
        proc = subprocess.Popen(
            [binary, "run", "-c", path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        time.sleep(1.2)
        if proc.poll() is not None:
            return public_fields(line, False, None, "", "进程退出")
        samples = []
        last_err = "连接失败"
        for _ in range(3):
            code, _body, elapsed, err = _curl(
                port, "https://www.gstatic.com/generate_204", 10, False
            )
            if code == "204" and elapsed is not None:
                samples.append(elapsed)
            else:
                last_err = err or ("HTTP %s" % code)
        latency = int(round(statistics.median(samples))) if samples else None
        exit_ip = fetch_exit_ip(port) if samples else ""
        ok = len(samples) >= 2
        err = "" if ok else "代理测试 %s/3（%s）" % (len(samples), last_err)
        return public_fields(line, ok, latency, exit_ip, err)
    finally:
        if proc is not None and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
        try:
            os.remove(path)
        except OSError:
            pass


def run_lines(lines, binary="./sing-box"):
    if not lines:
        return []
    results = [None] * len(lines)
    workers = max(1, min(len(lines), 64))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {}
        for index, line in enumerate(lines):
            futures[pool.submit(probe_line, line, 21000 + index, binary)] = index
        for future in as_completed(futures):
            index = futures[future]
            try:
                results[index] = future.result()
            except Exception:
                results[index] = public_fields(lines[index], False, None, "", "检测异常")
    return results


def tls_days_left(host):
    if not host:
        return None
    ctx = ssl.create_default_context()
    try:
        with socket.create_connection((host, 443), timeout=10) as raw:
            with ctx.wrap_socket(raw, server_hostname=host) as wrapped:
                cert = wrapped.getpeercert()
        expires = ssl.cert_time_to_seconds(cert["notAfter"])
        return int((expires - time.time()) / 86400)
    except Exception:
        return None


def http_code(url):
    if not url:
        return ""
    cmd = [
        "curl", "-sS", "-o", "/dev/null", "-L", "--max-redirs", "2",
        "--max-time", "15", "-w", "%{http_code}", url,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
    except Exception:
        return "000"
    code = (result.stdout or "").strip()
    return code if re.fullmatch(r"\d{3}", code) else "000"


def load_state(path=STATE_PATH):
    if not os.path.exists(path):
        return {"lines": {}, "last_daily": ""}
    try:
        with open(path, encoding="utf-8") as handle:
            state = json.load(handle)
    except Exception:
        return {"lines": {}, "last_daily": ""}
    if not isinstance(state, dict):
        return {"lines": {}, "last_daily": ""}
    state.setdefault("lines", {})
    state.setdefault("last_daily", "")
    return state


def save_json(path, obj):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(obj, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    os.replace(tmp, path)


def apply_sample(state, meta, ok, latency, err, now_ts):
    """Update one line. Alert on the 2nd consecutive failure, and once on recovery."""
    lines = state.setdefault("lines", {})
    rec = lines.setdefault(meta["id"], {"fails": 0, "down": False, "hist": []})
    hist = rec.get("hist") or []
    hist.append([int(now_ts), bool(ok), latency if isinstance(latency, int) else None])
    rec["hist"] = hist[-HIST_MAX:]
    alerts = []
    if ok:
        if rec.get("down"):
            alerts.append({
                "kind": "recovery",
                "id": meta["id"],
                "label": meta["label"],
                "provider": meta["provider"],
                "protocol": meta["protocol"],
                "latency": latency,
                "exit_ip": meta.get("exit_ip") or "",
            })
        rec["fails"] = 0
        rec["down"] = False
    else:
        rec["fails"] = int(rec.get("fails") or 0) + 1
        if rec["fails"] >= FAIL_THRESHOLD and not rec.get("down"):
            rec["down"] = True
            alerts.append({
                "kind": "down",
                "id": meta["id"],
                "label": meta["label"],
                "provider": meta["provider"],
                "protocol": meta["protocol"],
                "fails": rec["fails"],
                "err": err or "失败",
            })
    return alerts


def availability(hist, now_ts):
    rows = []
    for item in hist or []:
        try:
            ts = int(item[0])
        except (TypeError, ValueError, IndexError):
            continue
        if now_ts - ts <= DAY:
            rows.append(item)
    if not rows:
        rows = list(hist or [])
    if not rows:
        return 0
    good = sum(1 for item in rows if item[1])
    return good * 100 // len(rows)


def rollback_notify(state, alerts, prev_cert):
    """If Telegram did not accept the message, arm the same alerts for the next run."""
    for alert in alerts:
        rec = state.get("lines", {}).get(alert.get("id") or "")
        if not rec:
            continue
        if alert.get("kind") == "down":
            rec["down"] = False
        elif alert.get("kind") == "recovery":
            rec["down"] = True
            rec["fails"] = max(int(rec.get("fails") or 0), FAIL_THRESHOLD)
    if any(alert.get("kind") == "cert" for alert in alerts):
        if prev_cert:
            state["cert_warn"] = prev_cert
        else:
            state.pop("cert_warn", None)


def prune_state(state, current_ids, now_ts):
    drop = []
    for lid, rec in (state.get("lines") or {}).items():
        if lid in current_ids:
            continue
        hist = rec.get("hist") or []
        last = 0
        if hist:
            try:
                last = int(hist[-1][0])
            except (TypeError, ValueError, IndexError):
                last = 0
        if now_ts - last > 7 * DAY:
            drop.append(lid)
    for lid in drop:
        del state["lines"][lid]


def should_report(now, last_daily, force):
    if str(force).lower() == "true":
        return True
    today = now.strftime("%Y-%m-%d")
    return now.hour == 9 and (last_daily or "") != today


def group_rows(rows):
    order = []
    groups = {}
    for row in rows:
        key = "%s %s" % (row.get("provider") or "?", row.get("protocol") or "?")
        if key not in groups:
            order.append(key)
            groups[key] = []
        groups[key].append(row)
    return [(key, groups[key]) for key in order]


def fastest(rows, limit=3):
    ok_rows = [
        row for row in rows
        if row.get("ok") and isinstance(row.get("latency_ms"), int)
    ]
    ok_rows.sort(key=lambda row: row["latency_ms"])
    return ok_rows[:limit]


def short_of(row):
    label = row.get("label") or ""
    parts = label.split()
    return parts[-1] if parts else label


def format_alert(alert):
    kind = alert.get("kind")
    if kind == "down":
        return "🔴 %s 连续 %s 次失败：%s" % (
            alert.get("label"), alert.get("fails"), redact(alert.get("err") or "失败")
        )
    if kind == "recovery":
        latency = alert.get("latency")
        lat = "%s ms" % latency if isinstance(latency, int) else "—"
        ip = alert.get("exit_ip") or "未知"
        return "✅ %s 已恢复：延迟 %s，出口 %s" % (alert.get("label"), lat, ip)
    if kind == "cert":
        return "⚠️ Cloady 证书只剩 %s 天" % alert.get("days")
    return ""


def format_batch(alerts, now):
    lines = ["节点告警 %s" % now.strftime("%m-%d %H:%M")]
    for alert in alerts:
        text = format_alert(alert)
        if text:
            lines.append(text)
    if len(lines) == 1:
        return ""
    return "\n".join(lines)


def format_report(rows, extra, now):
    visible = [row for row in rows if row.get("public", True)]
    parts = ["📊 节点日报 %s" % now.strftime("%Y-%m-%d")]
    if not visible:
        parts.append("没有可测节点")
    for key, items in group_rows(visible):
        parts.append("")
        parts.append(key)
        for item in items:
            mark = "✅" if item.get("ok") else "❌"
            avail = item.get("avail_24h")
            avail_s = "%s%%" % avail if avail is not None else "—"
            if item.get("ok") and isinstance(item.get("latency_ms"), int):
                parts.append("%s %s %sms 24h %s" % (mark, short_of(item), item["latency_ms"], avail_s))
            else:
                parts.append("%s %s 失败 24h %s" % (mark, short_of(item), avail_s))
    notes = []
    if isinstance(extra.get("tls_days"), int):
        notes.append("Cloady 证书剩 %s 天" % extra["tls_days"])
    elif extra.get("tls_checked"):
        notes.append("Cloady 证书检查失败")
    sub = extra.get("sub") or ""
    if sub:
        notes.append("订阅正常" if sub == "200" else "订阅 HTTP %s" % sub)
    if notes:
        parts.append("")
        parts.append("，".join(notes))
    parts.append("")
    parts.append("最快")
    top = fastest(visible, 3)
    if not top:
        parts.append("无可用节点")
    else:
        for index, item in enumerate(top, 1):
            parts.append("%s. %s %sms" % (index, item["label"], item["latency_ms"]))
    return "\n".join(parts)


def extra_alerts(state, extra, now):
    alerts = []
    today = now.strftime("%Y-%m-%d")
    days = extra.get("tls_days")
    if isinstance(days, int) and days < 7 and state.get("cert_warn") != today:
        alerts.append({"kind": "cert", "days": days})
        state["cert_warn"] = today
    elif isinstance(days, int) and days >= 7:
        state.pop("cert_warn", None)
    sub = extra.get("sub") or ""
    if sub:
        meta = {
            "id": "Cloady:sub:http:0",
            "provider": "Cloady",
            "protocol": "sub",
            "label": "Cloady 订阅",
            "exit_ip": "",
        }
        alerts.extend(apply_sample(
            state, meta, sub == "200", None, "" if sub == "200" else "订阅 HTTP %s" % sub,
            int(now.timestamp()),
        ))
    return alerts


def status_document(rows, now):
    lines = []
    for row in rows:
        if not row.get("public", True):
            continue
        lines.append({
            "id": row["id"],
            "provider": row["provider"],
            "protocol": row["protocol"],
            "label": row["label"],
            "ok": bool(row["ok"]),
            "latency_ms": row.get("latency_ms"),
            "exit_ip": row.get("exit_ip") or "",
            "fails": int(row.get("fails") or 0),
            "avail_24h": row.get("avail_24h"),
        })
    return {"checked_at": now.isoformat(timespec="seconds"), "lines": lines}


def combine_text(alert_text, report_text):
    chunks = [chunk for chunk in (alert_text, report_text) if chunk]
    if not chunks:
        return ""
    text = "\n\n".join(chunks)
    if len(text) <= 4000:
        return text
    return text[:3990] + "\n…（已截断）"


def tg_send(token, chat, text):
    url = "https://api.telegram.org/bot%s/sendMessage" % token
    data = json.dumps({
        "chat_id": chat,
        "text": text,
        "disable_web_page_preview": True,
    }).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            resp.read()
        return True
    except Exception as exc:
        print("tg send failed", type(exc).__name__)
        return False


def enrich(state, probed, now_ts):
    alerts = []
    rows = []
    for item in probed:
        meta = {
            "id": item["id"],
            "label": item["label"],
            "provider": item["provider"],
            "protocol": item["protocol"],
            "exit_ip": item.get("exit_ip") or "",
        }
        alerts.extend(apply_sample(
            state, meta, item["ok"], item.get("latency_ms"), item.get("err") or "", now_ts
        ))
        rec = state["lines"][item["id"]]
        row = dict(item)
        row["fails"] = int(rec.get("fails") or 0)
        row["avail_24h"] = availability(rec.get("hist") or [], now_ts)
        row.pop("err", None)
        rows.append(row)
    return rows, alerts


def main():
    env = os.environ
    now = datetime.datetime.now(TZ)
    now_ts = int(now.timestamp())
    state = load_state()
    lines = load_lines(env)
    binary = env.get("SING_BOX") or "./sing-box"
    extra = {}
    host = env.get("NODE_HOST") or ""
    sub_url = env.get("SUB_URL") or ""
    with ThreadPoolExecutor(max_workers=2) as pool:
        tls_future = pool.submit(tls_days_left, host) if host else None
        sub_future = pool.submit(http_code, sub_url) if sub_url else None
        probed = run_lines(lines, binary)
        if tls_future:
            extra["tls_days"] = tls_future.result()
            extra["tls_checked"] = True
        if sub_future:
            extra["sub"] = sub_future.result()
    rows, alerts = enrich(state, probed, now_ts)
    prev_cert = state.get("cert_warn")
    prev_daily = state.get("last_daily") or ""
    alerts.extend(extra_alerts(state, extra, now))
    keep_ids = {row["id"] for row in rows}
    if extra.get("sub"):
        keep_ids.add("Cloady:sub:http:0")
    prune_state(state, keep_ids, now_ts)
    force = str(env.get("FORCE_REPORT", "")).lower() == "true"
    reporting = should_report(now, prev_daily, env.get("FORCE_REPORT", ""))
    report = format_report(rows, extra, now) if reporting else ""
    if reporting and not force:
        state["last_daily"] = now.strftime("%Y-%m-%d")
    text = combine_text(format_batch(alerts, now), report)
    token = env.get("TG_TOKEN") or ""
    chat = env.get("TG_CHAT") or ""
    if text and token and chat:
        if not tg_send(token, chat, text):
            rollback_notify(state, alerts, prev_cert)
            if reporting and not force:
                state["last_daily"] = prev_daily
    elif text and not (token and chat):
        print("telegram not configured")
    save_json(STATE_PATH, state)
    save_json(STATUS_PATH, status_document(rows, now))
    ok_n = sum(1 for row in rows if row.get("ok") and row.get("public", True))
    pub = [row for row in rows if row.get("public", True)]
    print("lines %s ok %s fail %s alerts %s report %s" % (
        len(pub), ok_n, len(pub) - ok_n, len(alerts), "yes" if report else "no"
    ))
    for row in pub:
        flag = "OK" if row.get("ok") else "FAIL"
        lat = row["latency_ms"] if isinstance(row.get("latency_ms"), int) else "-"
        print("%s %s %s" % (flag, row["label"], lat))


if __name__ == "__main__":
    main()
