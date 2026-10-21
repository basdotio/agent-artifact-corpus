# -*- coding: utf-8 -*-
"""麦当劳 MCP 客户端（Streamable HTTP，只用标准库，不装任何依赖）。

协议：MCP Streamable HTTP，服务端 https://mcp.mcd.cn
鉴权：请求头 Authorization: Bearer <MCP_TOKEN>

只做三件事，保持最小依赖面：
  1. initialize / notifications/initialized 握手（含 Mcp-Session-Id 透传）
  2. tools/list —— 列出服务端有哪些工具
  3. tools/call —— 调用工具，返回解析后的 JSON（兼容 SSE 与纯 JSON 两种响应）
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request

DEFAULT_URL = "https://mcp.mcd.cn"
PROTOCOL_VERSION = "2025-06-18"
CLIENT_NAME = "mcd-lottery-quant"
CLIENT_VERSION = "1.0.0"


class McpError(RuntimeError):
    """MCP 调用失败。"""


class McdMcpClient:
    def __init__(self, token: str, url: str = DEFAULT_URL, timeout: float = 30.0):
        if not token or not token.strip():
            raise McpError("MCP Token 为空。请先申请 Token，再设置环境变量 MCD_MCP_TOKEN。")
        self.token = token.strip()
        self.url = url.rstrip("/")
        self.timeout = timeout
        self._session_id: str | None = None
        self._next_id = 1
        self._initialized = False

    # ------------------------------------------------------------------ #
    # 传输层
    # ------------------------------------------------------------------ #
    def _rid(self) -> int:
        rid = self._next_id
        self._next_id += 1
        return rid

    def _post(self, message: dict, expect_response: bool = True):
        payload = json.dumps(message, ensure_ascii=False).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "Authorization": f"Bearer {self.token}",
            "MCP-Protocol-Version": PROTOCOL_VERSION,
        }
        if self._session_id:
            headers["Mcp-Session-Id"] = self._session_id

        req = urllib.request.Request(self.url, data=payload, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                sid = resp.headers.get("Mcp-Session-Id")
                if sid:
                    self._session_id = sid
                ctype = resp.headers.get("Content-Type", "") or ""
                body = resp.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:400]
            if exc.code == 401:
                raise McpError("401：MCP Token 无效、已过期或未提供。") from exc
            if exc.code == 429:
                raise McpError("429：触发限流（600 次/分钟），请降低请求频率。") from exc
            raise McpError(f"HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise McpError(f"网络不可达：{exc.reason}") from exc

        if not expect_response or not body.strip():
            return None
        if "text/event-stream" in ctype:
            return self._parse_sse(body)
        try:
            return json.loads(body)
        except json.JSONDecodeError as exc:
            raise McpError(f"响应不是合法 JSON：{body[:200]}") from exc

    @staticmethod
    def _parse_sse(body: str):
        """从 SSE 流里取出最后一条 data: 的 JSON 对象。"""
        last = None
        for line in body.splitlines():
            line = line.strip()
            if line.startswith("data:"):
                chunk = line[5:].strip()
                if not chunk or chunk == "[DONE]":
                    continue
                try:
                    last = json.loads(chunk)
                except json.JSONDecodeError:
                    continue
        if last is None:
            raise McpError("SSE 流中未找到可解析的 JSON 响应。")
        return last

    # ------------------------------------------------------------------ #
    # 协议层
    # ------------------------------------------------------------------ #
    def initialize(self) -> dict:
        res = self._post(
            {
                "jsonrpc": "2.0",
                "id": self._rid(),
                "method": "initialize",
                "params": {
                    "protocolVersion": PROTOCOL_VERSION,
                    "capabilities": {},
                    "clientInfo": {"name": CLIENT_NAME, "version": CLIENT_VERSION},
                },
            }
        )
        if not res or "error" in res:
            raise McpError(f"initialize 失败：{res}")
        self._post(
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            expect_response=False,
        )
        self._initialized = True
        return res.get("result", {})

    def list_tools(self) -> list[dict]:
        self._ensure_init()
        res = self._post({"jsonrpc": "2.0", "id": self._rid(), "method": "tools/list", "params": {}})
        if not res or "error" in res:
            raise McpError(f"tools/list 失败：{res}")
        return (res.get("result") or {}).get("tools", [])

    def call_tool(self, name: str, arguments: dict | None = None):
        self._ensure_init()
        res = self._post(
            {
                "jsonrpc": "2.0",
                "id": self._rid(),
                "method": "tools/call",
                "params": {"name": name, "arguments": arguments or {}},
            }
        )
        if not res:
            raise McpError(f"{name} 无响应")
        if "error" in res:
            raise McpError(f"{name} 调用失败：{res['error']}")
        return res.get("result")

    def call_tool_json(self, name: str, arguments: dict | None = None):
        """调用工具，并把 content 里的文本尽量解析成 JSON。"""
        return extract_json(self.call_tool(name, arguments))

    def _ensure_init(self):
        if not self._initialized:
            self.initialize()


def extract_json(result):
    """MCP tools/call 的 result 一般是 {"content":[{"type":"text","text":"..."}]}。

    这里有个真实的坑：麦当劳 MCP 返回给模型的文本**不是纯 JSON**，而是包了一层
    给人看的 Markdown 说明（字段释义 + 输出格式），真正的响应体挂在
    "## Original Response" 后面。所以按三级降级解析：
        纯 JSON → 代码块里的 JSON → Original Response 之后的 JSON → 原样返回
    活动日历那个工具本来就是纯 Markdown，走到最后一级是对的。
    """
    if result is None:
        return None
    if isinstance(result, str):
        return _parse_text(result)
    if isinstance(result, (dict, list)):
        content = result.get("content") if isinstance(result, dict) else None
        if content is None and isinstance(result, dict):
            return result
        texts = [
            block.get("text", "")
            for block in (content or [])
            if isinstance(block, dict) and block.get("type") == "text"
        ]
        if not texts:
            return result
        return _parse_text("\n".join(texts).strip())
    return result


_ORIGINAL_RE = re.compile(r"^##\s*Original Response\s*$", re.M)
_FENCE_RE = re.compile(r"```(?:json)?\s*(.+?)\s*```", re.S)


def _parse_text(text: str):
    """把一段文本变成 JSON；解析不了就原样返回字符串。"""
    text = (text or "").strip()
    if not text:
        return text

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    m = _FENCE_RE.search(text)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass

    m = _ORIGINAL_RE.search(text)
    if m:
        body = _first_json(text[m.end():])
        if body is not None:
            return body

    return text


def _first_json(text: str):
    """从文本里扫出第一个完整的 JSON 值。

    优先看开头 —— "## Original Response" 后面紧跟的就是响应体本身；
    开头不是括号时（响应体后面还挂了别的话），才退化成全文找最靠前的括号。
    """
    stripped = text.lstrip()
    offset = len(text) - len(stripped)

    if stripped[:1] in ("{", "["):
        got = _match_json(text, offset)
        if got is not None:
            return got

    positions = [p for p in (text.find("{"), text.find("[")) if p != -1]
    if not positions:
        return None
    return _match_json(text, min(positions))


def _match_json(text: str, start: int):
    """从 start 处的括号开始配平。字符串里的括号和引号必须跳过。"""
    opener = text[start]
    closer = {"{": "}", "[": "]"}[opener]
    depth = 0
    in_str = False
    escaped = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_str:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == opener:
            depth += 1
        elif ch == closer:
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start:i + 1])
                except json.JSONDecodeError:
                    return None
    return None
