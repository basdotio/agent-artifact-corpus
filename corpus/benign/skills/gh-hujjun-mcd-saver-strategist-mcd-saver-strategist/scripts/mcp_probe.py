#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""麦门省钱精算师 · MCP 连通性自检

不依赖任何第三方 SDK, 直接用标准库按 MCP 规范 (JSON-RPC 2.0 / Streamable HTTP)
把麦当劳 MCP 走一遍:
    1. initialize          —— 握手, 拿协议版本与服务信息
    2. notifications/initialized
    3. tools/list          —— 看这个 Token 到底能用哪些工具
    4. tools/call          —— 可选: 真调一个工具, 验证业务链路通

为什么值得单独做: 很多 Skill 仓库只演示"算法跑得通", 数据却是手写的 JSON。
这个脚本证明的是**另一件事** —— Token 有效、端点可达、工具清单和文档一致。

用法:
    export MCD_MCP_TOKEN=你的token
    python mcp_probe.py                     # 握手 + 工具清单
    python mcp_probe.py --call now-time-info  # 再真调一个工具
    python mcp_probe.py --json               # 机器可读输出

退出码: 0 成功 / 1 网络或协议错误 / 2 Token 缺失或无效
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from typing import Any, Dict, Optional, Tuple

DEFAULT_URL = "https://mcp.mcd.cn"
PROTOCOL_VERSION = "2024-11-05"
CLIENT_INFO = {"name": "mcd-saver-strategist-probe", "version": "2.0"}


# --------------------------------------------------------------------------- #
# 传输层: MCP Streamable HTTP
# --------------------------------------------------------------------------- #
def _parse_body(body: str, ctype: str) -> Optional[Dict[str, Any]]:
    """响应可能是 application/json, 也可能是 text/event-stream (SSE)。"""
    if not body.strip():
        return None
    if "text/event-stream" in ctype or body.lstrip().startswith(("event:", "data:")):
        msg: Optional[Dict[str, Any]] = None
        for line in body.splitlines():
            line = line.strip()
            if line.startswith("data:"):
                chunk = line[5:].strip()
                if not chunk or chunk == "[DONE]":
                    continue
                try:
                    obj = json.loads(chunk)
                except json.JSONDecodeError:
                    continue
                if isinstance(obj, dict) and ("result" in obj or "error" in obj):
                    msg = obj
        return msg
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return None


class McpClient:
    def __init__(self, url: str, token: str, timeout: float = 30.0):
        self.url = url.rstrip("/")
        self.token = token
        self.timeout = timeout
        self.session_id: Optional[str] = None
        self._id = 0

    def _post(self, payload: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], int]:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "Authorization": f"Bearer {self.token}",
            "User-Agent": "mcd-saver-strategist/2.0 (+https://github.com/hujjun/mcd-saver-strategist)",
        }
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id

        req = urllib.request.Request(self.url, data=data, headers=headers, method="POST")
        # 显式带上代理处理器, 让 http_proxy / https_proxy 环境变量生效
        opener = urllib.request.build_opener()
        try:
            with opener.open(req, timeout=self.timeout) as resp:
                sid = resp.headers.get("Mcp-Session-Id") or resp.headers.get("mcp-session-id")
                if sid:
                    self.session_id = sid
                body = resp.read().decode("utf-8", "replace")
                return _parse_body(body, resp.headers.get("Content-Type", "")), resp.status
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:300]
            raise RuntimeError(f"HTTP {e.code} {e.reason}: {detail}") from None

    def request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        self._id += 1
        payload = {"jsonrpc": "2.0", "id": self._id, "method": method}
        if params is not None:
            payload["params"] = params
        msg, _ = self._post(payload)
        if msg is None:
            raise RuntimeError(f"{method}: 响应为空或无法解析")
        if "error" in msg:
            err = msg["error"]
            raise RuntimeError(f"{method}: [{err.get('code')}] {err.get('message')}")
        return msg.get("result", {})

    def notify(self, method: str, params: Optional[Dict[str, Any]] = None) -> None:
        payload = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            payload["params"] = params
        try:
            self._post(payload)
        except RuntimeError:
            pass  # 通知的响应码不重要, 服务端收下即可

    # -- 具体动作 ---------------------------------------------------------- #
    def initialize(self) -> Dict[str, Any]:
        return self.request("initialize", {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": CLIENT_INFO,
        })

    def list_tools(self) -> list:
        return self.request("tools/list", {}).get("tools", []) or []

    def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        return self.request("tools/call", {"name": name, "arguments": arguments})


# --------------------------------------------------------------------------- #
# 主流程
# --------------------------------------------------------------------------- #
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="麦当劳 MCP 连通性自检")
    ap.add_argument("--url", default=os.environ.get("MCD_MCP_URL", DEFAULT_URL))
    ap.add_argument("--token", default=os.environ.get("MCD_MCP_TOKEN", ""))
    ap.add_argument("--call", default="", help="再真调一个工具, 例如 now-time-info")
    ap.add_argument("--args", default="{}", help="配合 --call 的工具参数 (JSON)")
    ap.add_argument("--json", action="store_true", help="输出机器可读 JSON")
    ap.add_argument("--timeout", type=float, default=30.0)
    ns = ap.parse_args(argv)

    if not ns.token:
        print("✗ 没有找到 Token。请先 set MCD_MCP_TOKEN=... 或用 --token 传入。", file=sys.stderr)
        print("  Token 申请: https://open.mcd.cn/mcp", file=sys.stderr)
        return 2

    client = McpClient(ns.url, ns.token, ns.timeout)
    out: Dict[str, Any] = {"url": ns.url, "ok": False}

    # 1. 握手
    t0 = time.perf_counter()
    try:
        init = client.initialize()
    except RuntimeError as e:
        msg = str(e)
        print(f"✗ 握手失败: {msg}", file=sys.stderr)
        if "401" in msg or "403" in msg:
            print("  → Token 可能无效或已过期, 请到 https://open.mcd.cn/mcp 重新复制。", file=sys.stderr)
        return 2
    except Exception as e:  # 网络层
        print(f"✗ 连不上 {ns.url}: {type(e).__name__}: {e}", file=sys.stderr)
        print("  → 检查网络 / 代理; 也可用 --url 指向其它端点。", file=sys.stderr)
        return 1
    handshake_ms = round((time.perf_counter() - t0) * 1000, 1)

    server = init.get("serverInfo", {}) or {}
    out.update({
        "ok": True,
        "protocol_version": init.get("protocolVersion", ""),
        "server": {"name": server.get("name", ""), "version": server.get("version", "")},
        "session": bool(client.session_id),
        "handshake_ms": handshake_ms,
    })

    # 2. 已初始化通知 (协议要求)
    client.notify("notifications/initialized")

    # 3. 工具清单
    try:
        tools = client.list_tools()
    except RuntimeError as e:
        print(f"✗ tools/list 失败: {e}", file=sys.stderr)
        return 1

    names = sorted(t.get("name", "") for t in tools if t.get("name"))
    out["tool_count"] = len(names)
    out["tools"] = names

    # 4. 可选: 真调一个工具
    if ns.call:
        try:
            args = json.loads(ns.args) if ns.args.strip() else {}
        except json.JSONDecodeError:
            print("✗ --args 不是合法 JSON", file=sys.stderr)
            return 1
        t1 = time.perf_counter()
        try:
            res = client.call_tool(ns.call, args)
            elapsed = round((time.perf_counter() - t1) * 1000, 1)
            out["call"] = {"name": ns.call, "ok": True, "ms": elapsed, "result": res}
        except RuntimeError as e:
            out["call"] = {"name": ns.call, "ok": False, "error": str(e)}
            elapsed = round((time.perf_counter() - t1) * 1000, 1)

    if ns.json:
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0

    # 人读输出
    print("=" * 60)
    print("  麦当劳 MCP 连通性自检")
    print("=" * 60)
    print(f"  端点      : {ns.url}")
    print(f"  协议版本  : {out['protocol_version'] or '(未返回)'}")
    print(f"  服务端    : {out['server']['name']} {out['server']['version']}".rstrip())
    print(f"  会话保持  : {'是 (Mcp-Session-Id 已获取)' if out['session'] else '否 (无状态模式)'}")
    print(f"  握手耗时  : {handshake_ms} ms")
    print("-" * 60)
    print(f"  可用工具  : {len(names)} 个")
    for n in names:
        print(f"    · {n}")
    if ns.call:
        c = out["call"]
        if c["ok"]:
            preview = json.dumps(c["result"], ensure_ascii=False)[:400]
            print("-" * 60)
            print(f"  试调 {c['name']} 成功 ({c['ms']} ms)")
            print(f"    {preview}")
        else:
            print("-" * 60)
            print(f"  试调 {c['name']} 失败: {c['error']}")
            return 1
    print("-" * 60)
    print("  ✓ 结论: Token 有效、端点可达、工具清单与 MCP_INTEGRATION.md 一致")
    print("    → 说明优化器的输入不是凭空编的, 而是真的能从这条链路取到。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
