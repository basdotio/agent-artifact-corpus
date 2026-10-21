"""标准 HAR (HTTP Archive) 1.2 会话归档导出引擎。

将存储层捕获的 HttpFlow 与无损 BodyPayload 组装并导出为符合 HAR 1.2 规范的 JSON 归档文件。

@author Ateng
@since 2026-10-13
"""

from __future__ import annotations

import base64
import json
import logging
import urllib.parse
from contextlib import closing
from datetime import UTC, datetime
from http import HTTPStatus
from pathlib import Path
from typing import Any

from mcp_server_traffic_inspector import __version__ as VERSION
from mcp_server_traffic_inspector.storage import StorageBus

logger = logging.getLogger("mcp_server_traffic_inspector.har_exporter")


class HarExporter:
    """标准 HAR 1.2 会话归档导出器。"""

    def __init__(self, storage: StorageBus) -> None:
        """初始化 HAR 导出器。

        Args:
            storage: 共享 SQLite WAL 数据总线实例。
        """
        self.storage = storage

    def export_session(
        self,
        output_path: str | Path,
        session_id: str | None = None,
        format: str = "har",
    ) -> dict[str, Any]:
        """将指定会话（或最新会话）的所有流量导出为标准 HAR 1.2 文件。

        Args:
            output_path: 导出的目标文件绝对或相对路径。
            session_id: 可选的目标会话 ID；未提供时自动定位最新抓包会话。
            format: 导出文件格式，当前仅支持 'har'。

        Returns:
            包含导出文件绝对路径、格式、流数量与文件字节大小的结构化字典。

        Raises:
            ValueError: 当指定了不支持的格式或未查询到可用流量时抛出。
        """
        # 1. 前置参数校验与会话定位
        if format.lower() != "har":
            raise ValueError(f"不支持的导出格式: '{format}'，当前仅支持 'har'")

        resolved_session_id = session_id
        with closing(self.storage._connect()) as conn:
            if resolved_session_id is None:
                latest_row = conn.execute(
                    "SELECT session_id FROM http_flows ORDER BY timestamp DESC LIMIT 1;"
                ).fetchone()
                if latest_row and latest_row["session_id"]:
                    resolved_session_id = str(latest_row["session_id"])

            if resolved_session_id is None:
                raise ValueError("未找到可导出的 HTTP 会话数据（存储总线为空）。")

            rows = conn.execute(
                """
                SELECT
                    f.id, f.session_id, f.timestamp, f.method, f.scheme, f.host, f.port, f.path,
                    f.status_code, f.duration_ms, f.request_headers, f.response_headers,
                    f.request_content_type, f.response_content_type,
                    f.request_body_size, f.response_body_size, f.has_error, f.error_message,
                    b.request_body, b.response_body,
                    b.request_body_path, b.response_body_path
                FROM http_flows f
                LEFT JOIN http_bodies b ON f.id = b.flow_id
                WHERE f.session_id = ?
                ORDER BY f.timestamp ASC;
                """,
                [resolved_session_id],
            ).fetchall()

            ws_by_flow: dict[str, list[dict[str, Any]]] = {}
            try:
                ws_rows = conn.execute(
                    """
                    SELECT id, flow_id, timestamp, direction, opcode, opcode_name,
                           is_binary, payload_preview, payload_blob, payload_path
                    FROM ws_messages
                    WHERE session_id = ?
                    ORDER BY timestamp ASC;
                    """,
                    [resolved_session_id],
                ).fetchall()
                for wsr in ws_rows:
                    fid = str(wsr["flow_id"])
                    if fid not in ws_by_flow:
                        ws_by_flow[fid] = []
                    raw_b = self.storage.resolve_raw_body(wsr["payload_blob"], wsr["payload_path"])
                    if wsr["is_binary"]:
                        data_str = base64.b64encode(raw_b).decode("ascii") if raw_b else ""
                    else:
                        data_str = (
                            raw_b.decode("utf-8", errors="replace")
                            if raw_b
                            else (wsr["payload_preview"] or "")
                        )
                    ws_by_flow[fid].append(
                        {
                            "type": (
                                "send" if str(wsr["direction"]) == "client_to_server" else "receive"
                            ),
                            "time": float(wsr["timestamp"]),
                            "opcode": int(wsr["opcode"]),
                            "data": data_str,
                        }
                    )
            except Exception as exc:
                logger.debug("读取 WebSocket 消息失败或表未就绪: %s", exc)

        # 2. 组装 HAR 1.2 entries 列表（会话无流量时导出合法空 entries 归档，确保契约始终合法）
        entries: list[dict[str, Any]] = []
        if rows:
            for r in rows:
                fid = str(r["id"])
                entry = self._build_har_entry(r, ws_messages=ws_by_flow.get(fid))
                entries.append(entry)

        har_content = {
            "log": {
                "version": "1.2",
                "creator": {
                    "name": "mcp-server-traffic-inspector",
                    "version": VERSION,
                },
                "pages": [],
                "entries": entries,
            }
        }

        # 3. 落盘写出 HAR 1.2 JSON 文件
        target = Path(output_path).resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        raw_json = json.dumps(har_content, ensure_ascii=False, indent=2)
        target.write_text(raw_json, encoding="utf-8")

        file_size = target.stat().st_size
        logger.info(
            "成功将会话 %s 的 %d 条流导出至 HAR: %s (%d 字节)",
            resolved_session_id,
            len(entries),
            target,
            file_size,
        )

        return {
            "exported_path": str(target),
            "format": "har",
            "flow_count": len(entries),
            "file_size_bytes": file_size,
        }

    def _build_har_entry(
        self,
        row: Any,
        ws_messages: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """将一条数据库 http_flows 行记录组装为 HAR 1.2 Entry。"""
        # 1. 时间戳转换与基础指标提取
        ts = float(row["timestamp"])
        dt_str = datetime.fromtimestamp(ts, tz=UTC).isoformat()
        duration_ms = float(row["duration_ms"]) if row["duration_ms"] is not None else 0.0

        scheme = str(row["scheme"])
        host = str(row["host"])
        port = int(row["port"])
        path = str(row["path"])
        url = self._format_url(scheme, host, port, path)

        # 2. 解析请求/响应头与 QueryString
        req_hdrs = self._safe_json_loads(row["request_headers"])
        resp_hdrs = self._safe_json_loads(row["response_headers"])

        req_headers_list = [{"name": str(k), "value": str(v)} for k, v in req_hdrs.items()]
        resp_headers_list = [{"name": str(k), "value": str(v)} for k, v in resp_hdrs.items()]

        parsed_url = urllib.parse.urlsplit(url)
        query_list = [{"name": k, "value": v} for k, v in urllib.parse.parse_qsl(parsed_url.query)]

        # 3. 读取完整无损的请求/响应 BodyPayload
        req_bytes = self.storage.resolve_raw_body(row["request_body"], row["request_body_path"])
        resp_bytes = self.storage.resolve_raw_body(row["response_body"], row["response_body_path"])

        # 4. 组装 request 对象
        req_entry: dict[str, Any] = {
            "method": str(row["method"]),
            "url": url,
            "httpVersion": "HTTP/1.1",
            "cookies": [],
            "headers": req_headers_list,
            "queryString": query_list,
            "headersSize": -1,
            "bodySize": int(row["request_body_size"] or 0),
        }

        if req_bytes:
            req_mime = self._get_header_val(req_hdrs, "content-type", "application/octet-stream")
            post_data = self._encode_body_for_har(req_bytes, req_mime)
            req_entry["postData"] = post_data

        # 5. 组装 response 对象
        status_code = int(row["status_code"]) if row["status_code"] is not None else 0
        status_text = ""
        if status_code > 0:
            try:
                status_text = HTTPStatus(status_code).phrase
            except ValueError:
                status_text = str(status_code)

        resp_mime = self._get_header_val(resp_hdrs, "content-type", "application/octet-stream")
        resp_content = self._encode_content_for_har(resp_bytes, resp_mime)

        resp_entry: dict[str, Any] = {
            "status": status_code,
            "statusText": status_text,
            "httpVersion": "HTTP/1.1",
            "cookies": [],
            "headers": resp_headers_list,
            "content": resp_content,
            "redirectURL": self._get_header_val(resp_hdrs, "location", ""),
            "headersSize": -1,
            "bodySize": int(row["response_body_size"] or 0),
        }

        entry: dict[str, Any] = {
            "startedDateTime": dt_str,
            "time": duration_ms,
            "request": req_entry,
            "response": resp_entry,
            "cache": {},
            "timings": {
                "send": 0,
                "wait": duration_ms,
                "receive": 0,
            },
        }
        if ws_messages:
            entry["_webSocketMessages"] = ws_messages

        return entry

    def _encode_body_for_har(self, data: bytes, mime_type: str) -> dict[str, Any]:
        """将请求体字节转为 HAR postData 结构。"""
        try:
            text = data.decode("utf-8")
            return {"mimeType": mime_type, "text": text}
        except UnicodeDecodeError:
            b64 = base64.b64encode(data).decode("ascii")
            return {"mimeType": mime_type, "text": b64, "encoding": "base64"}

    def _encode_content_for_har(self, data: bytes, mime_type: str) -> dict[str, Any]:
        """将响应体字节转为 HAR response content 结构。"""
        content_dict: dict[str, Any] = {
            "size": len(data),
            "mimeType": mime_type,
        }
        if not data:
            content_dict["text"] = ""
            return content_dict

        try:
            content_dict["text"] = data.decode("utf-8")
        except UnicodeDecodeError:
            content_dict["text"] = base64.b64encode(data).decode("ascii")
            content_dict["encoding"] = "base64"
        return content_dict

    def _safe_json_loads(self, raw: str | None) -> dict[str, Any]:
        """安全解析 JSON 头部字典。"""
        if not raw:
            return {}
        try:
            val = json.loads(raw)
            return val if isinstance(val, dict) else {}
        except Exception:
            return {}

    def _get_header_val(self, headers: dict[str, Any], target_key: str, default: str) -> str:
        """不区分大小写匹配获取头部键值。"""
        t = target_key.lower()
        for k, v in headers.items():
            if str(k).lower() == t:
                return str(v)
        return default

    def _format_url(self, scheme: str, host: str, port: int, path: str) -> str:
        """格式化标准绝对 URL。"""
        clean_path = path if path.startswith("/") else f"/{path}"
        default_port = (scheme == "http" and port == 80) or (scheme == "https" and port == 443)
        netloc = host if default_port else f"{host}:{port}"
        return f"{scheme}://{netloc}{clean_path}"
