#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
aihot-finance MCP Server (stdio)
把财经热点 API 包装成 MCP 工具，供 Claude Desktop / Cursor / Codex 等客户端调用。

用法:
    export AIHOT_API_KEY=ah_xxx
    python server.py

Claude Desktop 配置见 README.md
"""
import json
import os
import sys
import urllib.request
import urllib.parse

BASE = os.environ.get("AIHOT_BASE", "http://123.56.157.68")
KEY = os.environ.get("AIHOT_API_KEY", "")

TOOLS = [
    {
        "name": "get_hot",
        "description": "获取财经热点新闻，可按分类过滤。分类：宏观/A股/美股/港股/商品/外汇",
        "inputSchema": {
            "type": "object",
            "properties": {
                "cat": {"type": "string", "description": "分类，留空为全部"},
                "limit": {"type": "integer", "description": "返回条数，默认 10"},
            },
        },
    },
    {
        "name": "get_mood",
        "description": "获取市场情绪指数（0-100），越高越乐观",
        "inputSchema": {
            "type": "object",
            "properties": {"hours": {"type": "integer", "description": "回看小时数，默认 48"}},
        },
    },
    {
        "name": "search_news",
        "description": "按关键词搜索财经快讯，例如「降息」「黄金」",
        "inputSchema": {
            "type": "object",
            "properties": {
                "q": {"type": "string", "description": "关键词"},
                "limit": {"type": "integer", "description": "返回条数，默认 10"},
            },
            "required": ["q"],
        },
    },
    {
        "name": "get_digest",
        "description": "生成今日财经热点简报（Markdown），适合直接发公众号",
        "inputSchema": {"type": "object", "properties": {}},
    },
]


def api(path, params=None):
    url = BASE.rstrip("/") + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"X-API-Key": KEY, "User-Agent": "aihot-mcp/1.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))


def fmt(items):
    if not items:
        return "暂无数据"
    out = []
    for i, it in enumerate(items, 1):
        out.append(f"{i}. [{it.get('category','')}] {it.get('title','')}")
        out.append(f"   {it.get('url','')}")
    return "\n".join(out)


def call_tool(name, args):
    if name == "get_hot":
        p = {"limit": int(args.get("limit", 10))}
        if args.get("cat"):
            p["cat"] = args["cat"]
        d = api("/v1/hot", p)
        return fmt(d.get("data", []))
    if name == "get_mood":
        d = api("/v1/mood", {"hours": int(args.get("hours", 48))})
        return f"市场情绪指数：{d.get('current')}/100（{d.get('label')}）"
    if name == "search_news":
        d = api("/v1/search", {"q": args.get("q", ""), "limit": int(args.get("limit", 10))})
        return fmt(d.get("data", []))
    if name == "get_digest":
        d = api("/v1/digest", {})
        return d.get("markdown", "暂无数据")
    raise ValueError(f"unknown tool: {name}")


def handle(msg):
    mid = msg.get("id")
    method = msg.get("method")

    def ok(result):
        return {"jsonrpc": "2.0", "id": mid, "result": result}

    def err(code, message):
        return {"jsonrpc": "2.0", "id": mid, "error": {"code": code, "message": message}}

    if method == "initialize":
        return ok({
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "aihot-finance", "version": "1.0.0"},
        })
    if method in ("notifications/initialized", "initialized"):
        return None
    if method == "tools/list":
        return ok({"tools": TOOLS})
    if method == "tools/call":
        params = msg.get("params") or {}
        try:
            text = call_tool(params.get("name"), params.get("arguments") or {})
        except Exception as e:
            return ok({"content": [{"type": "text", "text": f"调用失败: {e}"}], "isError": True})
        return ok({"content": [{"type": "text", "text": text}], "isError": False})
    return err(-32601, "method not found")


def main():
    if not KEY:
        sys.stderr.write("warning: AIHOT_API_KEY not set\n")
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except Exception:
            continue
        resp = handle(msg)
        if resp is not None:
            sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
