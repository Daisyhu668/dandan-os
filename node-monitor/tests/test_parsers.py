#!/usr/bin/env python3
"""Parser and alert-state tests. URIs are fake; no live network."""
import base64
import datetime
import json
import os
import sys
import unittest
from urllib.parse import quote

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import check

UUID_WS = "11111111-1111-4111-8111-111111111111"
UUID_REAL = "22222222-2222-4222-8222-222222222222"
UUID_VMESS = "33333333-3333-4333-8333-333333333333"
UUID_ARGO = "44444444-4444-4444-8444-444444444444"
PBK = "AAA+BBBB/CCCCDDDDeeeeffffgggghhhh"
WS_PATH = "/assets/secret-path"
VMESS_PATH = "/vm-secret"
HY_PASS = "secretpass"
OBFS_PASS = "obfspass"
NOW = datetime.datetime(2026, 11, 8, 10, 37, tzinfo=check.TZ)


def vmess_link(obj, pad=True):
    raw = json.dumps(obj, separators=(",", ":")).encode()
    blob = base64.b64encode(raw).decode()
    if not pad:
        blob = blob.rstrip("=")
    return "vmess://" + blob


VLESS_WS = (
    "vless://%s@cdn.example.test:443?encryption=none&security=tls&type=ws"
    "&host=cdn.example.test&path=%s&sni=cdn.example.test&fp=chrome#cf-a"
    % (UUID_WS, quote(WS_PATH, safe=""))
)
VLESS_REAL = (
    "vless://%s@203.0.113.10:13547?encryption=none&security=reality&type=tcp"
    "&flow=xtls-rprx-vision&pbk=%s&sid=01234567&sni=www.example.test&fp=chrome#r"
    % (UUID_REAL, quote(PBK, safe=""))
)
VMESS_DIRECT = vmess_link({
    "v": "2", "ps": "direct", "add": "203.0.113.20", "port": "15201",
    "id": UUID_VMESS, "aid": "0", "scy": "auto", "net": "ws", "type": "none",
    "host": "www.example.test", "path": VMESS_PATH, "tls": "",
})
VMESS_ARGO = vmess_link({
    "v": "2", "ps": "argo", "add": "blue-bird.trycloudflare.com", "port": "443",
    "id": UUID_ARGO, "aid": "0", "scy": "auto", "net": "ws",
    "host": "blue-bird.trycloudflare.com", "path": "/argo", "tls": "tls",
    "sni": "blue-bird.trycloudflare.com",
}, pad=False)
HY2 = (
    "hysteria2://%s@203.0.113.30:38500?sni=www.example.test&insecure=1"
    "&obfs=salamander&obfs-password=%s#hy" % (quote(HY_PASS, safe=""), quote(OBFS_PASS, safe=""))
)
HY2_SAFE = "hy2://otherpass@203.0.113.31:443?sni=www.example.test&insecure=0#hy2"

SECRETS = (
    UUID_WS, UUID_REAL, UUID_VMESS, UUID_ARGO, PBK, WS_PATH, VMESS_PATH,
    HY_PASS, OBFS_PASS, "otherpass", "203.0.113.10", "203.0.113.20",
    "203.0.113.30", "cdn.example.test", "trycloudflare.com", "www.example.test",
)


def meta_of(line):
    return {
        "id": line["id"],
        "label": line["label"],
        "provider": line["provider"],
        "protocol": line["protocol"],
        "exit_ip": "",
    }


class ParserTests(unittest.TestCase):
    def test_vless_ws_tls(self):
        parsed = check.parse_vless(VLESS_WS)
        self.assertEqual(parsed["uuid"], UUID_WS)
        self.assertEqual(parsed["server"], "cdn.example.test")
        self.assertEqual(parsed["port"], 443)
        self.assertEqual(parsed["security"], "tls")
        self.assertEqual(parsed["net"], "ws")
        self.assertEqual(parsed["path"], WS_PATH)
        self.assertEqual(parsed["sni"], "cdn.example.test")
        self.assertEqual(parsed["fp"], "chrome")
        outbound = check.build_outbound(parsed)
        self.assertEqual(outbound["type"], "vless")
        self.assertEqual(outbound["tls"]["server_name"], "cdn.example.test")
        self.assertTrue(outbound["tls"]["utls"]["enabled"])
        self.assertEqual(outbound["tls"]["utls"]["fingerprint"], "chrome")
        self.assertNotIn("reality", outbound["tls"])
        self.assertEqual(outbound["transport"]["type"], "ws")
        self.assertEqual(outbound["transport"]["path"], WS_PATH)
        self.assertEqual(outbound["transport"]["headers"]["Host"], "cdn.example.test")

    def test_vless_reality(self):
        parsed = check.parse_vless(VLESS_REAL)
        self.assertEqual(parsed["security"], "reality")
        self.assertEqual(parsed["pbk"], PBK)
        self.assertEqual(parsed["sid"], "01234567")
        self.assertEqual(parsed["flow"], "xtls-rprx-vision")
        self.assertEqual(parsed["sni"], "www.example.test")
        self.assertEqual(parsed["fp"], "chrome")
        self.assertEqual(parsed["net"], "tcp")
        outbound = check.build_outbound(parsed)
        self.assertEqual(outbound["flow"], "xtls-rprx-vision")
        self.assertEqual(outbound["tls"]["reality"]["public_key"], PBK)
        self.assertEqual(outbound["tls"]["reality"]["short_id"], "01234567")
        self.assertEqual(outbound["tls"]["utls"]["fingerprint"], "chrome")
        self.assertEqual(outbound["tls"]["server_name"], "www.example.test")
        self.assertNotIn("transport", outbound)
        line = check.make_line(parsed, "hostuno")
        self.assertEqual(line["protocol"], "vless-reality")
        self.assertIn(".10:13547", line["label"])
        self.assertNotIn("203.0.113.10", line["label"])

    def test_reality_without_key_is_not_probed(self):
        uri = VLESS_REAL.replace("pbk=%s&" % quote(PBK, safe=""), "")
        line = check.make_line(check.parse_link(uri), "hostuno")
        self.assertIsNone(line["outbound"])
        self.assertEqual(line["err"], "配置无法生成")

    def test_vmess_direct_and_argo(self):
        direct = check.parse_vmess(VMESS_DIRECT)
        self.assertEqual(direct["server"], "203.0.113.20")
        self.assertEqual(direct["port"], 15201)
        self.assertEqual(direct["uuid"], UUID_VMESS)
        self.assertEqual(direct["path"], VMESS_PATH)
        self.assertFalse(direct["tls"])
        outbound = check.build_outbound(direct)
        self.assertEqual(outbound["type"], "vmess")
        self.assertEqual(outbound["security"], "auto")
        self.assertEqual(outbound["alter_id"], 0)
        self.assertNotIn("tls", outbound)
        self.assertEqual(outbound["transport"]["path"], VMESS_PATH)
        line = check.make_line(direct, "hostuno")
        self.assertEqual(line["protocol"], "vmess-ws")
        self.assertIn(".20:15201", line["label"])

        argo = check.parse_vmess(VMESS_ARGO)
        self.assertTrue(argo["tls"])
        self.assertEqual(argo["server"], "blue-bird.trycloudflare.com")
        argo_line = check.make_line(argo, "hostuno")
        self.assertIn("argo:443", argo_line["label"])
        self.assertNotIn("trycloudflare", argo_line["label"])
        argo_out = check.build_outbound(argo)
        self.assertTrue(argo_out["tls"]["enabled"])
        self.assertEqual(argo_out["tls"]["utls"]["fingerprint"], "chrome")

    def test_hysteria2_and_hy2(self):
        parsed = check.parse_hysteria2(HY2)
        self.assertEqual(parsed["password"], HY_PASS)
        self.assertEqual(parsed["port"], 38500)
        self.assertTrue(parsed["insecure"])
        self.assertEqual(parsed["obfs"], "salamander")
        self.assertEqual(parsed["obfs_password"], OBFS_PASS)
        self.assertEqual(parsed["sni"], "www.example.test")
        outbound = check.build_outbound(parsed)
        self.assertEqual(outbound["type"], "hysteria2")
        self.assertEqual(outbound["password"], HY_PASS)
        self.assertTrue(outbound["tls"]["insecure"])
        self.assertEqual(outbound["obfs"]["type"], "salamander")
        self.assertEqual(outbound["obfs"]["password"], OBFS_PASS)
        line = check.make_line(parsed, "hostuno")
        self.assertEqual(line["protocol"], "hysteria2")
        self.assertIn(".30:38500", line["label"])

        safe = check.parse_link(HY2_SAFE)
        self.assertFalse(safe["insecure"])
        safe_out = check.build_outbound(safe)
        self.assertFalse(safe_out["tls"]["insecure"])
        self.assertNotIn("obfs", safe_out)

    def test_subscription_base64_and_plain(self):
        plain = "# comment\nnot-a-link\n%s\n%s\n" % (VLESS_REAL, HY2)
        lines = check.links_from_text(plain, "hostuno")
        self.assertEqual(len(lines), 2)
        protocols = sorted(line["protocol"] for line in lines)
        self.assertEqual(protocols, ["hysteria2", "vless-reality"])

        blob = base64.b64encode(("%s\n%s\n" % (VLESS_WS, VMESS_DIRECT)).encode()).decode()
        wrapped = "\n".join(blob[i:i + 60] for i in range(0, len(blob), 60))
        decoded = check.links_from_text(wrapped, "Cloudflare")
        self.assertEqual(len(decoded), 2)
        self.assertTrue(all(line["provider"] == "Cloudflare" for line in decoded))

        stripped = base64.b64encode(HY2_SAFE.encode()).decode().rstrip("=")
        again = check.links_from_text(stripped, "hostuno")
        self.assertEqual(len(again), 1)
        self.assertEqual(again[0]["protocol"], "hysteria2")

    def test_garbage_ignored(self):
        self.assertIsNone(check.parse_link("https://example.test"))
        self.assertIsNone(check.parse_link("vmess://not-base64"))
        self.assertIsNone(check.parse_link(""))
        self.assertEqual(check.links_from_text("hello\n# x\n", "hostuno"), [])

    def test_cloady_line_uses_chrome(self):
        line = check.cloady_line("edge.example.test", UUID_WS, WS_PATH)
        self.assertEqual(line["provider"], "Cloady")
        self.assertEqual(line["protocol"], "vless-ws")
        self.assertEqual(line["outbound"]["transport"]["path"], WS_PATH)
        self.assertEqual(line["outbound"]["tls"]["utls"]["fingerprint"], "chrome")
        self.assertNotIn("edge.example.test", line["label"])
        self.assertIsNone(check.cloady_line("", UUID_WS, WS_PATH))

    def test_public_labels_hide_secrets(self):
        env = {
            "NODE_HOST": "edge.example.test",
            "NODE_UUID": UUID_WS,
            "NODE_PATH": WS_PATH,
            "CF_SUB": base64.b64encode(VLESS_WS.encode()).decode(),
            "HU_LINKS": "\n".join([VLESS_REAL, VMESS_DIRECT, VMESS_ARGO, HY2, HY2_SAFE]),
        }
        lines = check.load_lines(env)
        self.assertGreaterEqual(len(lines), 6)
        blob = " ".join(line["label"] + " " + line["id"] for line in lines)
        for secret in SECRETS + ("edge.example.test",):
            self.assertNotIn(secret, blob)
        labels = [line["label"] for line in lines]
        self.assertTrue(any(label.startswith("Cloady vless-ws ") for label in labels))
        self.assertTrue(any("argo:443" in label for label in labels))
        self.assertTrue(any(label.startswith("hostuno hysteria2 ") for label in labels))

    def test_duplicate_last_octet_is_numbered(self):
        first = VLESS_WS.replace("cdn.example.test", "203.0.113.10")
        second = VLESS_WS.replace("cdn.example.test", "198.51.100.10").replace(UUID_WS, UUID_REAL)
        lines = check.disambiguate(check.links_from_text(first + "\n" + second, "Cloudflare"))
        labels = sorted(line["label"] for line in lines)
        self.assertEqual(len(labels), 2)
        self.assertTrue(labels[0].endswith("#1"))
        self.assertTrue(labels[1].endswith("#2"))

    def test_fetch_failure_and_empty_sub(self):
        failed = check.load_lines({"HU_FETCH_FAILED": "true", "HU_LINKS_FILE": "missing.txt"})
        self.assertEqual(failed[0]["err"], "订阅拉取失败")
        empty = check.load_lines({"HU_LINKS": "   ", "HU_LINKS_FILE": "list.txt"})
        self.assertEqual(empty[0]["err"], "订阅为空")
        bad = check.load_lines({"CF_SUB": "not links and not base64"})
        self.assertEqual(bad[0]["label"], "Cloudflare 订阅")

    def test_singbox_config_shape(self):
        line = check.make_line(check.parse_link(HY2), "hostuno")
        cfg = check.singbox_config(line["outbound"], 21007)
        self.assertEqual(cfg["inbounds"][0]["listen"], "127.0.0.1")
        self.assertEqual(cfg["inbounds"][0]["listen_port"], 21007)
        self.assertEqual(cfg["outbounds"][0]["type"], "hysteria2")
        self.assertEqual(len(cfg["outbounds"]), 1)


class StateTests(unittest.TestCase):
    def meta(self):
        line = check.make_line(check.parse_link(VLESS_REAL), "hostuno")
        return meta_of(line), line

    def test_alert_once_then_recovery(self):
        meta, line = self.meta()
        state = {"lines": {}}
        now = 1_700_000_000
        first = check.apply_sample(state, meta, False, None, "连接失败", now)
        self.assertEqual(first, [])
        self.assertEqual(state["lines"][meta["id"]]["fails"], 1)
        self.assertFalse(state["lines"][meta["id"]]["down"])

        second = check.apply_sample(state, meta, False, None, "代理测试 0/3（连接失败）", now + 1800)
        self.assertEqual(len(second), 1)
        self.assertEqual(second[0]["kind"], "down")
        self.assertEqual(second[0]["fails"], 2)
        self.assertTrue(state["lines"][meta["id"]]["down"])
        text = check.format_batch(second, NOW)
        self.assertIn("节点告警", text)
        self.assertIn(line["label"], text)
        self.assertIn("连续 2 次失败", text)
        self.assertIn("vless-reality", text)
        self.assertIn(".10:13547", text)
        for secret in (UUID_REAL, PBK, "203.0.113.10", WS_PATH):
            self.assertNotIn(secret, text)
        leaked = dict(second[0])
        leaked["err"] = "握手失败 " + UUID_REAL
        hidden = check.format_alert(leaked)
        self.assertNotIn(UUID_REAL, hidden)
        self.assertIn("<uuid>", hidden)

        third = check.apply_sample(state, meta, False, None, "连接失败", now + 3600)
        self.assertEqual(third, [])
        self.assertEqual(state["lines"][meta["id"]]["fails"], 3)

        meta["exit_ip"] = "198.51.100.8"
        recovered = check.apply_sample(state, meta, True, 86, "", now + 5400)
        self.assertEqual(recovered[0]["kind"], "recovery")
        self.assertEqual(state["lines"][meta["id"]]["fails"], 0)
        self.assertFalse(state["lines"][meta["id"]]["down"])
        notice = check.format_alert(recovered[0])
        self.assertIn("已恢复", notice)
        self.assertIn("86 ms", notice)
        self.assertIn("198.51.100.8", notice)
        batched = check.format_batch(second + recovered, NOW)
        self.assertEqual(batched.count("节点告警"), 1)
        self.assertIn("已恢复", batched)
        self.assertIn("连续 2 次失败", batched)

    def test_hist_cap_and_availability(self):
        meta, _line = self.meta()
        state = {"lines": {}}
        base = 1_700_000_000
        for i in range(60):
            check.apply_sample(state, meta, i % 2 == 0, 40 + i, "", base + i)
        hist = state["lines"][meta["id"]]["hist"]
        self.assertEqual(len(hist), 48)
        now = base + 100
        older = [[now - 90_000, True, 10], [now - 100, True, 10], [now - 50, False, None], [now - 10, True, 10]]
        self.assertEqual(check.availability(older, now), 66)
        self.assertEqual(check.availability([], now), 0)

    def test_rollback_retries_the_down_alert(self):
        meta, _line = self.meta()
        state = {"lines": {}, "cert_warn": "2026-11-01"}
        now = 1_700_000_000
        check.apply_sample(state, meta, False, None, "连接失败", now)
        alerts = check.apply_sample(state, meta, False, None, "连接失败", now + 1)
        self.assertTrue(state["lines"][meta["id"]]["down"])
        check.rollback_notify(state, alerts, "2026-11-01")
        self.assertFalse(state["lines"][meta["id"]]["down"])
        self.assertGreaterEqual(state["lines"][meta["id"]]["fails"], 2)
        again = check.apply_sample(state, meta, False, None, "连接失败", now + 2)
        self.assertEqual(again[0]["kind"], "down")

    def test_report_groups_and_fastest_three(self):
        rows = [
            {"provider": "hostuno", "protocol": "vless-reality", "label": "hostuno vless-reality .10:13547",
             "ok": True, "latency_ms": 90, "avail_24h": 100, "public": True},
            {"provider": "hostuno", "protocol": "hysteria2", "label": "hostuno hysteria2 .30:38500",
             "ok": True, "latency_ms": 40, "avail_24h": 96, "public": True},
            {"provider": "Cloudflare", "protocol": "vless-ws", "label": "Cloudflare vless-ws dabcd:443",
             "ok": False, "latency_ms": None, "avail_24h": 50, "public": True},
            {"provider": "Cloady", "protocol": "vless-ws", "label": "Cloady vless-ws dffff:443",
             "ok": True, "latency_ms": 70, "avail_24h": 100, "public": True},
            {"provider": "Cloady", "protocol": "sub", "label": "Cloady 订阅",
             "ok": False, "latency_ms": None, "avail_24h": 0, "public": False},
        ]
        morning = datetime.datetime(2026, 11, 8, 9, 7, tzinfo=check.TZ)
        text = check.format_report(rows, {"tls_days": 12, "sub": "200"}, morning)
        self.assertIn("📊 节点日报 2026-11-08", text)
        self.assertIn("Cloady vless-ws", text)
        self.assertIn("Cloudflare vless-ws", text)
        self.assertIn("hostuno vless-reality", text)
        self.assertIn("hostuno hysteria2", text)
        self.assertIn("❌ dabcd:443 失败 24h 50%", text)
        self.assertIn("1. hostuno hysteria2 .30:38500 40ms", text)
        self.assertIn("2. Cloady vless-ws dffff:443 70ms", text)
        self.assertIn("3. hostuno vless-reality .10:13547 90ms", text)
        self.assertIn("Cloady 证书剩 12 天", text)
        self.assertIn("订阅正常", text)
        self.assertNotIn("Cloady 订阅", text)
        for secret in SECRETS:
            self.assertNotIn(secret, text)
        self.assertTrue(check.should_report(morning, "", ""))
        self.assertFalse(check.should_report(morning, "2026-11-08", ""))
        later = datetime.datetime(2026, 11, 8, 10, 7, tzinfo=check.TZ)
        self.assertFalse(check.should_report(later, "", "false"))
        self.assertTrue(check.should_report(later, "2026-11-08", "true"))

    def test_cert_and_sub_alerts(self):
        state = {"lines": {}}
        first = check.extra_alerts(state, {"tls_days": 3, "sub": "502"}, NOW)
        self.assertTrue(any(item["kind"] == "cert" for item in first))
        self.assertFalse(any(item["kind"] == "down" for item in first))
        second = check.extra_alerts(state, {"tls_days": 3, "sub": "502"}, NOW)
        self.assertFalse(any(item["kind"] == "cert" for item in second))
        self.assertTrue(any(item["kind"] == "down" for item in second))
        text = check.format_batch(second, NOW)
        self.assertIn("Cloady 订阅", text)
        self.assertIn("订阅 HTTP 502", text)
        self.assertNotIn("://", text)

    def test_status_document_has_no_secrets(self):
        line = check.make_line(check.parse_link(HY2), "hostuno")
        probed = check.public_fields(line, True, 40, "198.51.100.9", "")
        state = {"lines": {}}
        rows, _alerts = check.enrich(state, [probed], 1_700_000_000)
        doc = check.status_document(rows, NOW)
        self.assertEqual(set(doc.keys()), {"checked_at", "lines"})
        item = doc["lines"][0]
        self.assertEqual(set(item.keys()), {
            "id", "provider", "protocol", "label", "ok", "latency_ms", "exit_ip", "fails", "avail_24h",
        })
        self.assertEqual(item["exit_ip"], "198.51.100.9")
        self.assertNotIn(HY_PASS, json.dumps(doc))
        self.assertNotIn("203.0.113.30", json.dumps(doc))
        self.assertTrue(item["ok"])
        self.assertEqual(item["fails"], 0)


if __name__ == "__main__":
    unittest.main()
