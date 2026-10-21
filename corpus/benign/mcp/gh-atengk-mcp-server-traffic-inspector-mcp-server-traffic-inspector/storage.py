"""基于共享 SQLite WAL 的进程间数据总线与保真载荷存储模块。

@author Ateng
@since 2026-10-13
"""

from __future__ import annotations

import json
import logging
import shutil
import sqlite3
import time
from collections.abc import Mapping
from contextlib import closing
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from mcp_server_traffic_inspector.config import LOGGER_NAME, ServerConfig

logger = logging.getLogger(LOGGER_NAME)

MAX_INLINE_BODY_BYTES = 256 * 1024
DEFAULT_PREVIEW_CHARS = 2048

TEXTUAL_MIME_KEYWORDS = (
    "text/",
    "json",
    "xml",
    "javascript",
    "ecmascript",
    "x-www-form-urlencoded",
    "graphql",
    "yaml",
    "csv",
    "html",
)

SCHEMA_DDL = """
CREATE TABLE IF NOT EXISTS http_flows (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    timestamp REAL NOT NULL,
    method TEXT NOT NULL,
    scheme TEXT NOT NULL,
    host TEXT NOT NULL,
    port INTEGER NOT NULL,
    path TEXT NOT NULL,
    status_code INTEGER,
    duration_ms REAL,
    request_headers TEXT,
    response_headers TEXT,
    request_content_type TEXT,
    response_content_type TEXT,
    request_body_size INTEGER DEFAULT 0,
    response_body_size INTEGER DEFAULT 0,
    has_error INTEGER DEFAULT 0,
    error_message TEXT
);
CREATE INDEX IF NOT EXISTS idx_flows_session ON http_flows(session_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_flows_host_status ON http_flows(host, status_code);
CREATE INDEX IF NOT EXISTS idx_flows_duration ON http_flows(duration_ms DESC);

CREATE TABLE IF NOT EXISTS http_bodies (
    flow_id TEXT PRIMARY KEY,
    request_body_preview TEXT,
    response_body_preview TEXT,
    request_body BLOB,
    response_body BLOB,
    is_request_binary INTEGER DEFAULT 0,
    is_response_binary INTEGER DEFAULT 0,
    request_body_path TEXT,
    response_body_path TEXT,
    FOREIGN KEY(flow_id) REFERENCES http_flows(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS intercept_rules (
    id TEXT PRIMARY KEY,
    enabled INTEGER DEFAULT 1,
    url_pattern TEXT NOT NULL,
    action TEXT NOT NULL,
    mock_status INTEGER DEFAULT 200,
    mock_headers TEXT,
    mock_body TEXT,
    modify_request_headers TEXT,
    modify_response_headers TEXT,
    delay_ms INTEGER DEFAULT 0,
    max_hits INTEGER,
    hit_count INTEGER DEFAULT 0,
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS ws_messages (
    id TEXT PRIMARY KEY,
    flow_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    timestamp REAL NOT NULL,
    direction TEXT NOT NULL,
    opcode INTEGER NOT NULL,
    opcode_name TEXT NOT NULL,
    is_heartbeat INTEGER DEFAULT 0,
    content_length INTEGER DEFAULT 0,
    is_binary INTEGER DEFAULT 0,
    payload_preview TEXT,
    payload_blob BLOB,
    payload_path TEXT,
    FOREIGN KEY(flow_id) REFERENCES http_flows(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_ws_flow ON ws_messages(flow_id, timestamp ASC);
CREATE INDEX IF NOT EXISTS idx_ws_session ON ws_messages(session_id, timestamp ASC);
CREATE INDEX IF NOT EXISTS idx_ws_heartbeat ON ws_messages(flow_id, is_heartbeat);
"""


def _extract_content_type(headers: Mapping[str, str] | None) -> str | None:
    if not headers:
        return None
    for k, v in headers.items():
        if k.lower() == "content-type" and v:
            return v.strip()
    return None


def _is_binary_payload(raw_bytes: bytes, content_type: str | None) -> bool:
    if not raw_bytes:
        return False
    if content_type:
        ct_lower = content_type.lower()
        if any(token in ct_lower for token in TEXTUAL_MIME_KEYWORDS):
            return b"\x00" in raw_bytes[:1024]
    if b"\x00" in raw_bytes[:1024]:
        return True
    try:
        raw_bytes[:4096].decode("utf-8")
        return False
    except UnicodeDecodeError:
        return True


def _decode_preview(
    raw_bytes: bytes,
    is_binary: bool,
    max_chars: int,
) -> tuple[str, bool]:
    if not raw_bytes:
        return "", False
    if is_binary:
        summary = f"<binary payload: {len(raw_bytes)} bytes>"
        return summary, False
    decoded = raw_bytes.decode("utf-8", errors="replace")
    if len(decoded) > max_chars:
        return decoded[:max_chars], True
    return decoded, False


def _format_url(scheme: str, host: str, port: int, path: str) -> str:
    default_port = (scheme == "http" and port == 80) or (scheme == "https" and port == 443)
    authority = host if default_port else f"{host}:{port}"
    normalized_path = path if path.startswith("/") else f"/{path}"
    return f"{scheme}://{authority}{normalized_path}"


def _format_iso_time(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp, tz=UTC).isoformat()


@dataclass(frozen=True, slots=True)
class StorageHealth:
    """SQLite WAL 共享数据总线健康度快照。

    Attributes:
        writable: 数据库与大载荷目录是否具备正常读写权限。
        journal_mode: 当前 SQLite 日志模式（预期为 wal）。
        tables: 已就绪的用户表名列表。
        db_path: 数据库文件绝对路径。
        bodies_dir: 大载荷分流目录绝对路径。
        error: 当探测异常时的错误原因描述，正常时为 None。
    """

    writable: bool
    journal_mode: str
    tables: list[str]
    db_path: Path
    bodies_dir: Path
    error: str | None = None


class StorageBus:
    """主控进程与抓包子进程共享的 SQLite WAL 数据总线管理器。

    负责初始化 WAL 并发模式与三张领域表（http_flows、http_bodies、intercept_rules），
    提供 HttpFlow / BodyPayload 保真入库、多维检索与防爆截断详情，
    并在进程退出时按策略回收临时数据库与分流载荷文件。
    """

    def __init__(
        self,
        db_path: Path,
        bodies_dir: Path,
        preserve_db: bool = False,
    ) -> None:
        """初始化数据总线实例。

        Args:
            db_path: SQLite 数据库文件绝对路径。
            bodies_dir: 超出 256KB 的 BodyPayload 临时文件存放目录。
            preserve_db: 进程退出清理时是否保留数据库文件（显式指定 --db-path 时为 True）。
        """
        self.db_path = db_path.resolve()
        self.bodies_dir = bodies_dir.resolve()
        self.preserve_db = preserve_db

    @classmethod
    def from_config(cls, config: ServerConfig) -> StorageBus:
        """根据服务端全局配置构建 StorageBus 实例。

        Args:
            config: 解析完成的服务端配置对象。

        Returns:
            绑定了对应数据库路径、载荷目录与保留策略的 StorageBus 实例。
        """
        return cls(
            db_path=config.db_path,
            bodies_dir=config.bodies_dir,
            preserve_db=config.preserve_db,
        )

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=15.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        return conn

    def initialize(self) -> None:
        """创建数据库父目录与大载荷分流目录，开启 SQLite WAL 模式并建表。"""
        # 1. 确保数据库父目录与超大载荷分流目录存在
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.bodies_dir.mkdir(parents=True, exist_ok=True)

        # 2. 连接 SQLite 并开启 WAL 与外键约束，执行核心 DDL
        with closing(self._connect()) as conn:
            conn.executescript(SCHEMA_DDL)
            for col_def in [
                "delay_ms INTEGER DEFAULT 0",
                "max_hits INTEGER",
                "hit_count INTEGER DEFAULT 0",
            ]:
                try:
                    conn.execute(f"ALTER TABLE intercept_rules ADD COLUMN {col_def};")
                except Exception:
                    pass
            conn.commit()

    def _prepare_body_storage(
        self,
        flow_id: str,
        direction: Literal["req", "resp"],
        raw_bytes: bytes | None,
        content_type: str | None,
    ) -> tuple[str, bytes | None, int, str | None]:
        payload = raw_bytes or b""
        is_binary = _is_binary_payload(payload, content_type)
        preview, _ = _decode_preview(payload, is_binary, DEFAULT_PREVIEW_CHARS)

        if len(payload) > MAX_INLINE_BODY_BYTES:
            self.bodies_dir.mkdir(parents=True, exist_ok=True)
            spilled_path = (self.bodies_dir / f"{flow_id}_{direction}.bin").resolve()
            spilled_path.write_bytes(payload)
            return preview, None, int(is_binary), str(spilled_path)

        return preview, payload, int(is_binary), None

    def record_http_flow(
        self,
        *,
        flow_id: str,
        session_id: str,
        timestamp: float,
        method: str,
        scheme: str,
        host: str,
        port: int,
        path: str,
        status_code: int | None = None,
        duration_ms: float | None = None,
        request_headers: Mapping[str, str] | None = None,
        response_headers: Mapping[str, str] | None = None,
        request_content_type: str | None = None,
        response_content_type: str | None = None,
        request_body: bytes | None = None,
        response_body: bytes | None = None,
        has_error: bool = False,
        error_message: str | None = None,
    ) -> str:
        """将捕获的 HttpFlow 元数据与 BodyPayload 保真写入 SQLite WAL 数据总线。

        对于不大于 256KB 的载荷直接存入 BLOB；超过 256KB 的载荷自动分流写入 bodies_dir 临时文件。

        Args:
            flow_id: 唯一流标识。
            session_id: 归属的 CaptureSession 唯一标识。
            timestamp: 请求发起时的 Unix 时间戳（秒）。
            method: HTTP 请求方法（如 GET、POST）。
            scheme: 协议方案（http 或 https）。
            host: 目标主机域名或 IP。
            port: 目标端口。
            path: 请求路径（含 Query 参数）。
            status_code: HTTP 响应状态码，请求异常未收到响应时可为 None。
            duration_ms: 完整请求-响应耗时（毫秒）。
            request_headers: 请求头字典。
            response_headers: 响应头字典。
            request_content_type: 请求 Content-Type，为 None 时自动从 request_headers 提取。
            response_content_type: 响应 Content-Type，为 None 时自动从 response_headers 提取。
            request_body: 解压后的原始请求体字节。
            response_body: 解压后的原始响应体字节。
            has_error: 是否发生传输或代理错误。
            error_message: 错误详情描述。

        Returns:
            成功入库的 flow_id。
        """
        # 1. 归一化请求/响应头部与 Content-Type，并准备 BodyPayload 分流或内联存储
        req_headers_dict = dict(request_headers or {})
        resp_headers_dict = dict(response_headers or {})
        req_ct = request_content_type or _extract_content_type(req_headers_dict)
        resp_ct = response_content_type or _extract_content_type(resp_headers_dict)

        req_bytes = request_body or b""
        resp_bytes = response_body or b""
        req_preview, req_blob, req_bin, req_path = self._prepare_body_storage(
            flow_id, "req", req_bytes, req_ct
        )
        resp_preview, resp_blob, resp_bin, resp_path = self._prepare_body_storage(
            flow_id, "resp", resp_bytes, resp_ct
        )

        # 2. 原子写入 http_flows 与 http_bodies 表
        with closing(self._connect()) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO http_flows (
                    id, session_id, timestamp, method, scheme, host, port, path,
                    status_code, duration_ms, request_headers, response_headers,
                    request_content_type, response_content_type,
                    request_body_size, response_body_size, has_error, error_message
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    flow_id,
                    session_id,
                    timestamp,
                    method.upper(),
                    scheme.lower(),
                    host,
                    port,
                    path,
                    status_code,
                    duration_ms,
                    json.dumps(req_headers_dict, ensure_ascii=False),
                    json.dumps(resp_headers_dict, ensure_ascii=False),
                    req_ct,
                    resp_ct,
                    len(req_bytes),
                    len(resp_bytes),
                    int(has_error),
                    error_message,
                ),
            )
            conn.execute(
                """
                INSERT OR REPLACE INTO http_bodies (
                    flow_id, request_body_preview, response_body_preview,
                    request_body, response_body,
                    is_request_binary, is_response_binary,
                    request_body_path, response_body_path
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    flow_id,
                    req_preview,
                    resp_preview,
                    req_blob,
                    resp_blob,
                    req_bin,
                    resp_bin,
                    req_path,
                    resp_path,
                ),
            )
            conn.commit()

        return flow_id

    def count_flows(self, session_id: str | None = None) -> int:
        """统计指定会话或全局已捕获的 HttpFlow 数量。

        Args:
            session_id: 可选的会话 ID；为 None 时统计全部会话。

        Returns:
            匹配的流记录总数。
        """
        with closing(self._connect()) as conn:
            if session_id:
                row = conn.execute(
                    "SELECT COUNT(*) FROM http_flows WHERE session_id = ?;",
                    (session_id,),
                ).fetchone()
            else:
                row = conn.execute("SELECT COUNT(*) FROM http_flows;").fetchone()
            return int(row[0]) if row else 0

    def list_http_flows(
        self,
        *,
        limit: int = 20,
        offset: int = 0,
        session_id: str | None = None,
        host: str | None = None,
        status_code: int | None = None,
        status_family: str | None = None,
        method: str | None = None,
        min_duration_ms: float | None = None,
        query: str | None = None,
        compact: bool = False,
        sort_by: str = "timestamp",
    ) -> dict[str, Any]:
        """按多维过滤条件分页查询轻量级 HttpFlow 列表（不含任何 Body 内容）。

        Args:
            limit: 单页最大返回条数，默认 20。
            offset: 分页偏移量，默认 0。
            session_id: 按抓包会话 ID 过滤。
            host: 按域名子串（不区分大小写）过滤。
            status_code: 按精确状态码过滤。
            status_family: 按状态码族（2xx、3xx、4xx、5xx、error）过滤。
            method: 按 HTTP 请求方法过滤（不区分大小写）。
            min_duration_ms: 按最小请求耗时（毫秒）过滤。
            query: 可选的 URL 路径与域名模糊搜索关键词。
            compact: 是否返回极简紧凑视图（大幅节约 Token）。
            sort_by: 排序字段（timestamp、duration_ms、size）。

        Returns:
            包含 total、session_id、summary_metrics 与 flows 列表的字典；
            无匹配数据时 flows 固定为 []。
        """
        # 1. 组装参数化 WHERE 子句
        clauses: list[str] = []
        params: list[Any] = []

        if session_id:
            clauses.append("session_id = ?")
            params.append(session_id)
        if host:
            clauses.append("LOWER(host) LIKE ?")
            params.append(f"%{host.strip().lower()}%")
        if status_code is not None:
            clauses.append("status_code = ?")
            params.append(int(status_code))
        if status_family:
            fam = status_family.strip().lower()
            if fam in {"2xx", "3xx", "4xx", "5xx"}:
                base_code = int(fam[0]) * 100
                clauses.append("status_code >= ? AND status_code < ?")
                params.extend([base_code, base_code + 100])
            elif fam == "error":
                clauses.append("(has_error = 1 OR status_code >= 400)")
        if method:
            clauses.append("UPPER(method) = ?")
            params.append(method.strip().upper())
        if min_duration_ms is not None:
            clauses.append("duration_ms >= ?")
            params.append(float(min_duration_ms))
        if query and query.strip():
            q_term = f"%{query.strip().lower()}%"
            clauses.append("(LOWER(path) LIKE ? OR LOWER(host) LIKE ?)")
            params.extend([q_term, q_term])

        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""

        # 2. 解析安全排序规则
        sort_map = {
            "timestamp": "timestamp DESC",
            "duration_ms": "COALESCE(duration_ms, 0) DESC, timestamp DESC",
            "size": "(COALESCE(response_body_size, 0) + COALESCE(request_body_size, 0)) DESC",
        }
        order_sql = sort_map.get(sort_by.strip().lower(), "timestamp DESC")

        # 3. 执行总数统计、聚合指标与分页查询
        with closing(self._connect()) as conn:
            metrics_row = conn.execute(
                f"""
                SELECT
                    COUNT(*) as total_count,
                    SUM(
                        CASE WHEN (has_error = 1 OR status_code >= 400) THEN 1 ELSE 0 END
                    ) as error_count,
                    AVG(duration_ms) as avg_duration
                FROM http_flows
                {where_sql};
                """,
                params,
            ).fetchone()
            total = int(metrics_row["total_count"] or 0) if metrics_row else 0
            error_count = int(metrics_row["error_count"] or 0) if metrics_row else 0
            avg_duration = (
                round(float(metrics_row["avg_duration"]), 2)
                if (metrics_row and metrics_row["avg_duration"] is not None)
                else 0.0
            )

            rows = conn.execute(
                f"""
                SELECT
                    id, session_id, timestamp, method, scheme, host, port, path,
                    status_code, duration_ms, response_content_type, request_content_type,
                    request_body_size, response_body_size
                FROM http_flows
                {where_sql}
                ORDER BY {order_sql}
                LIMIT ? OFFSET ?;
                """,
                [*params, max(1, int(limit)), max(0, int(offset))],
            ).fetchall()

        flows: list[dict[str, Any]] = []
        for row in rows:
            url_str = _format_url(
                str(row["scheme"]),
                str(row["host"]),
                int(row["port"]),
                str(row["path"]),
            )
            sc = int(row["status_code"]) if row["status_code"] is not None else None
            dur = float(row["duration_ms"]) if row["duration_ms"] is not None else None
            ct = row["response_content_type"] or row["request_content_type"]

            if compact:
                flows.append(
                    {
                        "id": str(row["id"]),
                        "method": str(row["method"]),
                        "url": url_str,
                        "status_code": sc,
                        "duration_ms": dur,
                        "content_type": ct,
                    }
                )
            else:
                flows.append(
                    {
                        "id": str(row["id"]),
                        "session_id": str(row["session_id"]),
                        "time": _format_iso_time(float(row["timestamp"])),
                        "method": str(row["method"]),
                        "url": url_str,
                        "status_code": sc,
                        "duration_ms": dur,
                        "content_type": ct,
                        "size": int(row["response_body_size"] or 0),
                    }
                )

        return {
            "total": total,
            "session_id": session_id,
            "summary_metrics": {
                "error_count": error_count,
                "avg_duration_ms": avg_duration,
            },
            "flows": flows,
        }

    def resolve_raw_body(
        self,
        blob_val: bytes | None,
        path_val: str | None,
    ) -> bytes:
        """从内联 BLOB 或外部转储文件解析完整无损的 BodyPayload 原始字节。

        Args:
            blob_val: 数据库存储的内联 BLOB 字节（≤256KB）。
            path_val: 外部磁盘转储文件绝对路径（>256KB）。

        Returns:
            无损原始请求或响应体字节；若均不存在则返回空字节。
        """
        if blob_val is not None:
            return bytes(blob_val)
        if path_val:
            file_path = Path(path_val)
            if file_path.is_file():
                return file_path.read_bytes()
        return b""

    _resolve_raw_body = resolve_raw_body

    def _build_body_detail(
        self,
        *,
        flow_id: str,
        direction: Literal["req", "resp"],
        size: int,
        content_type: str | None,
        is_binary: bool,
        preview_db: str | None,
        blob_val: bytes | None,
        path_val: str | None,
        max_body_chars: int,
        dump_body_to_file: bool,
    ) -> dict[str, Any]:
        raw_bytes = self._resolve_raw_body(blob_val, path_val)
        if raw_bytes:
            preview, truncated = _decode_preview(raw_bytes, is_binary, max(1, max_body_chars))
        else:
            text_fallback = preview_db or ""
            truncated = len(text_fallback) > max_body_chars
            preview = text_fallback[:max_body_chars]

        file_path = path_val
        if dump_body_to_file and raw_bytes and not file_path:
            self.bodies_dir.mkdir(parents=True, exist_ok=True)
            dumped = (self.bodies_dir / f"{flow_id}_{direction}.bin").resolve()
            dumped.write_bytes(raw_bytes)
            file_path = str(dumped)

        return {
            "size": size,
            "content_type": content_type,
            "is_binary": is_binary,
            "preview": preview,
            "truncated": truncated,
            "file_path": file_path,
        }

    def get_http_flow_detail(
        self,
        flow_id: str,
        *,
        include_headers: bool = True,
        include_body: bool = True,
        max_body_chars: int = DEFAULT_PREVIEW_CHARS,
        dump_body_to_file: bool = False,
    ) -> dict[str, Any] | None:
        """查询单条 HttpFlow 的完整头部、截断解码预览与可选落盘文件路径。

        Args:
            flow_id: 目标 HttpFlow 的唯一 ID。
            include_headers: 是否在结果中包含请求与响应头部。
            include_body: 是否在结果中包含请求与响应 BodyPayload 详情。
            max_body_chars: 文本预览最大截断字符数，默认 2048。
            dump_body_to_file: 是否强制将完整原始载荷导出为本地文件并返回路径。

        Returns:
            流详情字典；当 flow_id 不存在时返回 None。
        """
        # 1. 联表查询 http_flows 与 http_bodies
        with closing(self._connect()) as conn:
            row = conn.execute(
                """
                SELECT
                    f.id, f.session_id, f.timestamp, f.method, f.scheme, f.host, f.port, f.path,
                    f.status_code, f.duration_ms, f.request_headers, f.response_headers,
                    f.request_content_type, f.response_content_type,
                    f.request_body_size, f.response_body_size, f.has_error, f.error_message,
                    b.request_body_preview, b.response_body_preview,
                    b.request_body, b.response_body,
                    b.is_request_binary, b.is_response_binary,
                    b.request_body_path, b.response_body_path
                FROM http_flows f
                LEFT JOIN http_bodies b ON f.id = b.flow_id
                WHERE f.id = ?;
                """,
                (flow_id,),
            ).fetchone()

        if row is None:
            return None

        # 2. 组装基础流元数据与可选 Headers / BodyPayload 视图
        result: dict[str, Any] = {
            "id": str(row["id"]),
            "session_id": str(row["session_id"]),
            "time": _format_iso_time(float(row["timestamp"])),
            "method": str(row["method"]),
            "scheme": str(row["scheme"]),
            "host": str(row["host"]),
            "port": int(row["port"]),
            "path": str(row["path"]),
            "url": _format_url(
                str(row["scheme"]),
                str(row["host"]),
                int(row["port"]),
                str(row["path"]),
            ),
            "status_code": int(row["status_code"]) if row["status_code"] is not None else None,
            "duration_ms": float(row["duration_ms"]) if row["duration_ms"] is not None else None,
            "has_error": bool(row["has_error"]),
            "error_message": row["error_message"],
        }

        if include_headers:
            result["request_headers"] = json.loads(row["request_headers"] or "{}")
            result["response_headers"] = json.loads(row["response_headers"] or "{}")

        if include_body:
            result["request_body"] = self._build_body_detail(
                flow_id=str(row["id"]),
                direction="req",
                size=int(row["request_body_size"] or 0),
                content_type=row["request_content_type"],
                is_binary=bool(row["is_request_binary"]),
                preview_db=row["request_body_preview"],
                blob_val=row["request_body"],
                path_val=row["request_body_path"],
                max_body_chars=max_body_chars,
                dump_body_to_file=dump_body_to_file,
            )
            result["response_body"] = self._build_body_detail(
                flow_id=str(row["id"]),
                direction="resp",
                size=int(row["response_body_size"] or 0),
                content_type=row["response_content_type"],
                is_binary=bool(row["is_response_binary"]),
                preview_db=row["response_body_preview"],
                blob_val=row["response_body"],
                path_val=row["response_body_path"],
                max_body_chars=max_body_chars,
                dump_body_to_file=dump_body_to_file,
            )

        return result

    def get_flow_for_replay(self, flow_id: str) -> dict[str, Any] | None:
        """读取单条 HttpFlow 的完整无损请求与响应原始字节（专供 FlowReplay 重放与 Diff 使用）。

        Args:
            flow_id: 目标历史 HttpFlow 的唯一 ID。

        Returns:
            包含请求行、头部、完整原始请求体字节与历史响应体字节的字典；不存在时返回 None。
        """
        with closing(self._connect()) as conn:
            row = conn.execute(
                """
                SELECT
                    f.id, f.session_id, f.method, f.scheme, f.host, f.port, f.path,
                    f.status_code, f.duration_ms, f.request_headers, f.response_headers,
                    f.request_content_type, f.response_content_type,
                    b.request_body, b.response_body,
                    b.is_request_binary, b.is_response_binary,
                    b.request_body_path, b.response_body_path
                FROM http_flows f
                LEFT JOIN http_bodies b ON f.id = b.flow_id
                WHERE f.id = ?;
                """,
                (flow_id,),
            ).fetchone()

        if row is None:
            return None

        req_bytes = self._resolve_raw_body(row["request_body"], row["request_body_path"])
        resp_bytes = self._resolve_raw_body(row["response_body"], row["response_body_path"])
        return {
            "id": str(row["id"]),
            "session_id": str(row["session_id"]),
            "method": str(row["method"]),
            "url": _format_url(
                str(row["scheme"]),
                str(row["host"]),
                int(row["port"]),
                str(row["path"]),
            ),
            "status_code": int(row["status_code"]) if row["status_code"] is not None else None,
            "duration_ms": float(row["duration_ms"]) if row["duration_ms"] is not None else None,
            "request_headers": json.loads(row["request_headers"] or "{}"),
            "response_headers": json.loads(row["response_headers"] or "{}"),
            "request_content_type": row["request_content_type"],
            "response_content_type": row["response_content_type"],
            "request_body_bytes": req_bytes,
            "response_body_bytes": resp_bytes,
            "is_response_binary": bool(row["is_response_binary"]),
        }

    def add_intercept_rule(
        self,
        *,
        url_pattern: str,
        action: str = "mock",
        mock_status: int = 200,
        mock_headers: Mapping[str, str] | None = None,
        mock_body: str | Mapping[str, Any] | list[Any] | None = None,
        modify_request_headers: Mapping[str, str] | None = None,
        modify_response_headers: Mapping[str, str] | None = None,
        delay_ms: int = 0,
        max_hits: int | None = None,
    ) -> dict[str, Any]:
        """新增一条非阻塞动态拦截规则 (InterceptRule) 并持久化至 SQLite。

        支持 Mock 响应、请求/响应头改写、延迟仿真 (delay) 与连接主动中断 (abort)。

        Args:
            url_pattern: URL 匹配模式（支持通配符如 'https://api.example.com/*'）。
            action: 拦截动作，可选 'mock'、'modify'、'delay' 或 'abort'。
            mock_status: 当 action='mock' 时返回的 HTTP 状态码，默认 200。
            mock_headers: 当 action='mock' 时返回的自定义响应头。
            mock_body: 当 action='mock' 时返回的响应正文字符串或 JSON 结构。
            modify_request_headers: 转发前注入或覆盖的请求头字典。
            modify_response_headers: 返回前注入或覆盖的响应头字典。
            delay_ms: 注入的响应延迟毫秒数，默认 0。
            max_hits: 最大触发次数限制，达到后规则自动停用；为 None 时永久生效。

        Returns:
            包含 rule_id、action、url_pattern、delay_ms、max_hits 与 status ("active") 的字典。
        """
        pattern = url_pattern.strip()
        if not pattern:
            raise ValueError("url_pattern 不能为空")

        normalized_action = action.strip().lower()
        if normalized_action not in {"mock", "modify", "delay", "abort"}:
            raise ValueError(
                f"不支持的拦截规则动作: {action}（仅支持 'mock', 'modify', 'delay', 'abort'）"
            )

        if mock_body is None or isinstance(mock_body, str):
            serialized_mock_body = mock_body
        else:
            serialized_mock_body = json.dumps(mock_body, ensure_ascii=False)

        rule_id = f"rule_{uuid4().hex[:10]}"
        created_at = time.time()

        with closing(self._connect()) as conn:
            conn.execute(
                """
                INSERT INTO intercept_rules (
                    id, enabled, url_pattern, action, mock_status,
                    mock_headers, mock_body, modify_request_headers,
                    modify_response_headers, delay_ms, max_hits, hit_count, created_at
                ) VALUES (?, 1, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?);
                """,
                (
                    rule_id,
                    pattern,
                    normalized_action,
                    int(mock_status),
                    json.dumps(dict(mock_headers or {}), ensure_ascii=False),
                    serialized_mock_body,
                    json.dumps(dict(modify_request_headers or {}), ensure_ascii=False),
                    json.dumps(dict(modify_response_headers or {}), ensure_ascii=False),
                    max(0, int(delay_ms)),
                    int(max_hits) if max_hits is not None else None,
                    created_at,
                ),
            )
            conn.commit()

        return {
            "rule_id": rule_id,
            "action": normalized_action,
            "url_pattern": pattern,
            "delay_ms": max(0, int(delay_ms)),
            "max_hits": int(max_hits) if max_hits is not None else None,
            "status": "active",
        }

    def increment_rule_hit(self, rule_id: str) -> None:
        """记录规则被触发一次；若达到 max_hits 则原子化禁用规则。"""
        with closing(self._connect()) as conn:
            conn.execute(
                """
                UPDATE intercept_rules
                SET hit_count = hit_count + 1,
                    enabled = CASE
                        WHEN max_hits IS NOT NULL AND hit_count + 1 >= max_hits THEN 0
                        ELSE enabled
                    END
                WHERE id = ?;
                """,
                (rule_id,),
            )
            conn.commit()

    def list_intercept_rules(self, *, only_enabled: bool = False) -> list[dict[str, Any]]:
        """查询当前配置的动态拦截规则列表。

        Args:
            only_enabled: 是否仅返回 enabled=1 的生效规则，默认 False。

        Returns:
            规则字典列表；无规则时固定返回空列表 []。
        """
        where_clause = "WHERE enabled = 1" if only_enabled else ""
        with closing(self._connect()) as conn:
            rows = conn.execute(
                f"""
                SELECT
                    id, enabled, url_pattern, action, mock_status,
                    mock_headers, mock_body, modify_request_headers,
                    modify_response_headers, delay_ms, max_hits, hit_count, created_at
                FROM intercept_rules
                {where_clause}
                ORDER BY created_at ASC;
                """
            ).fetchall()

        rules: list[dict[str, Any]] = []
        for row in rows:
            rules.append(
                {
                    "id": str(row["id"]),
                    "enabled": bool(row["enabled"]),
                    "url_pattern": str(row["url_pattern"]),
                    "action": str(row["action"]),
                    "mock_status": int(row["mock_status"] or 200),
                    "mock_headers": json.loads(row["mock_headers"] or "{}"),
                    "mock_body": row["mock_body"],
                    "modify_request_headers": json.loads(row["modify_request_headers"] or "{}"),
                    "modify_response_headers": json.loads(row["modify_response_headers"] or "{}"),
                    "delay_ms": int(row["delay_ms"] or 0) if "delay_ms" in row.keys() else 0,
                    "max_hits": int(row["max_hits"])
                    if ("max_hits" in row.keys() and row["max_hits"] is not None)
                    else None,
                    "hit_count": int(row["hit_count"] or 0) if "hit_count" in row.keys() else 0,
                    "created_at": float(row["created_at"]),
                }
            )
        return rules

    def clear_intercept_rules(self, rule_id: str | None = None) -> dict[str, Any]:
        """清理指定的单条动态拦截规则或清空全部规则。

        Args:
            rule_id: 可选的目标规则 ID；为 None 时清空全部规则。

        Returns:
            包含 cleared_count 与 target_rule_id 的字典。
        """
        target = rule_id.strip() if rule_id and rule_id.strip() else None
        with closing(self._connect()) as conn:
            if target:
                cursor = conn.execute(
                    "DELETE FROM intercept_rules WHERE id = ?;",
                    (target,),
                )
            else:
                cursor = conn.execute("DELETE FROM intercept_rules;")
            cleared = int(cursor.rowcount or 0)
            conn.commit()

        return {
            "cleared_count": cleared,
            "target_rule_id": target,
        }

    def record_websocket_message(
        self,
        *,
        flow_id: str,
        session_id: str,
        timestamp: float,
        direction: str,
        opcode: int,
        opcode_name: str,
        content: bytes | str,
        message_id: str | None = None,
    ) -> str:
        """将捕获的 WebSocket 单帧元数据与 Payload 写入 SQLite WAL 数据总线。

        超过 256KB 的载荷分流写入 bodies_dir 临时文件；低于 256KB 存入 BLOB。

        Args:
            flow_id: 归属的握手 HttpFlow 唯一标识。
            session_id: 归属的 CaptureSession 唯一标识。
            timestamp: 消息收发 Unix 时间戳（秒）。
            direction: 消息传输方向（'client_to_server' 或 'server_to_client'）。
            opcode: WebSocket Opcode 数值（1=TEXT, 2=BINARY, 8=CLOSE, 9=PING, 10=PONG）。
            opcode_name: Opcode 文本枚举名称（如 'TEXT', 'PING'）。
            content: 原始载荷字节或解码字符串。
            message_id: 可选的消息唯一 ID，默认自动生成。

        Returns:
            成功入库的 message_id。
        """
        msg_id = message_id or f"ws_{uuid4().hex}"
        raw_bytes = content.encode("utf-8") if isinstance(content, str) else bytes(content)
        is_heartbeat = int(opcode in (9, 10) or opcode_name.upper() in ("PING", "PONG"))
        is_binary = int(
            opcode == 2 or opcode_name.upper() == "BINARY" or (b"\x00" in raw_bytes[:512])
        )

        preview, blob_val, is_bin_detected, path_val = self._prepare_body_storage(
            flow_id=msg_id,
            direction="req" if direction == "client_to_server" else "resp",
            raw_bytes=raw_bytes,
            content_type="application/octet-stream" if is_binary else "text/plain",
        )

        with closing(self._connect()) as conn:
            # 1. 防御外键约束：若握手流因偶发时序尚未落盘，自动插入最小存根流
            exists = conn.execute("SELECT 1 FROM http_flows WHERE id = ?;", (flow_id,)).fetchone()
            if not exists:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO http_flows (
                        id, session_id, timestamp, method, scheme, host, port, path, status_code
                    ) VALUES (?, ?, ?, 'GET', 'ws', 'unknown', 0, '/', 101);
                    """,
                    (flow_id, session_id, timestamp),
                )

            # 2. 插入 WebSocket 帧记录
            conn.execute(
                """
                INSERT OR REPLACE INTO ws_messages (
                    id, flow_id, session_id, timestamp, direction, opcode, opcode_name,
                    is_heartbeat, content_length, is_binary, payload_preview,
                    payload_blob, payload_path
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    msg_id,
                    flow_id,
                    session_id,
                    timestamp,
                    direction,
                    int(opcode),
                    opcode_name.upper(),
                    is_heartbeat,
                    len(raw_bytes),
                    int(is_binary or is_bin_detected),
                    preview,
                    blob_val,
                    path_val,
                ),
            )
            conn.commit()

        return msg_id

    def list_websocket_messages(
        self,
        *,
        flow_id: str | None = None,
        session_id: str | None = None,
        include_heartbeats: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        """按握手流或会话分页查询 WebSocket 消息帧列表（可过滤心跳帧）。

        Args:
            flow_id: 可选的握手 HttpFlow 唯一 ID。
            session_id: 可选的抓包会话 ID。
            include_heartbeats: 是否包含 PING/PONG 心跳消息帧，默认 False（自动抑制）。
            limit: 单页返回最大帧数，默认 100。
            offset: 分页偏移量，默认 0。

        Returns:
            包含 total、flow_id 与 messages 列表的字典；无匹配时 messages 返回空列表 []。
        """
        clauses: list[str] = []
        params: list[Any] = []
        if flow_id:
            clauses.append("flow_id = ?")
            params.append(flow_id)
        if session_id:
            clauses.append("session_id = ?")
            params.append(session_id)
        if not include_heartbeats:
            clauses.append("is_heartbeat = 0")

        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""

        with closing(self._connect()) as conn:
            total_row = conn.execute(
                f"SELECT COUNT(*) FROM ws_messages {where_sql};",
                params,
            ).fetchone()
            total = int(total_row[0]) if total_row else 0

            query_sql = f"""
                SELECT
                    id, flow_id, session_id, timestamp, direction, opcode, opcode_name,
                    is_heartbeat, content_length, is_binary, payload_preview
                FROM ws_messages
                {where_sql}
                ORDER BY timestamp ASC
                LIMIT ? OFFSET ?;
            """
            rows = conn.execute(
                query_sql,
                [*params, max(1, int(limit)), max(0, int(offset))],
            ).fetchall()

        messages: list[dict[str, Any]] = []
        for r in rows:
            messages.append(
                {
                    "id": str(r["id"]),
                    "flow_id": str(r["flow_id"]),
                    "session_id": str(r["session_id"]),
                    "time": _format_iso_time(float(r["timestamp"])),
                    "timestamp": float(r["timestamp"]),
                    "direction": str(r["direction"]),
                    "opcode": int(r["opcode"]),
                    "opcode_name": str(r["opcode_name"]),
                    "is_heartbeat": bool(r["is_heartbeat"]),
                    "content_length": int(r["content_length"]),
                    "is_binary": bool(r["is_binary"]),
                    "payload_preview": r["payload_preview"] or "",
                }
            )

        return {
            "total": total,
            "flow_id": flow_id,
            "messages": messages,
        }

    def get_websocket_message_detail(
        self,
        message_id: str,
        *,
        max_body_chars: int = DEFAULT_PREVIEW_CHARS,
        dump_to_file: bool = False,
    ) -> dict[str, Any] | None:
        """获取单个 WebSocket 消息帧的完整解压内容、Opcode 属性与可选落盘文件路径。

        Args:
            message_id: 目标 WebSocket 消息的唯一 ID。
            max_body_chars: 文本预览最大截断字符数，默认 2048。
            dump_to_file: 是否将完整载荷导出为独立本地文件并返回绝对路径。

        Returns:
            消息详情字典；若 message_id 不存在则返回 None。
        """
        with closing(self._connect()) as conn:
            row = conn.execute(
                """
                SELECT
                    id, flow_id, session_id, timestamp, direction, opcode, opcode_name,
                    is_heartbeat, content_length, is_binary, payload_preview,
                    payload_blob, payload_path
                FROM ws_messages
                WHERE id = ?;
                """,
                (message_id,),
            ).fetchone()

        if row is None:
            return None

        raw_bytes = self.resolve_raw_body(row["payload_blob"], row["payload_path"])
        is_binary = bool(row["is_binary"])
        preview = row["payload_preview"] or ""
        truncated = False
        text_content = ""

        if is_binary:
            text_content = f"<binary payload: {len(raw_bytes)} bytes>"
        else:
            decoded = raw_bytes.decode("utf-8", errors="replace")
            text_content = decoded
            if len(decoded) > max_body_chars:
                preview = decoded[:max_body_chars]
                truncated = True
            else:
                preview = decoded

        file_path = row["payload_path"]
        if dump_to_file and raw_bytes and not file_path:
            self.bodies_dir.mkdir(parents=True, exist_ok=True)
            dumped = (self.bodies_dir / f"{message_id}.bin").resolve()
            dumped.write_bytes(raw_bytes)
            file_path = str(dumped)

        return {
            "id": str(row["id"]),
            "flow_id": str(row["flow_id"]),
            "session_id": str(row["session_id"]),
            "time": _format_iso_time(float(row["timestamp"])),
            "timestamp": float(row["timestamp"]),
            "direction": str(row["direction"]),
            "opcode": int(row["opcode"]),
            "opcode_name": str(row["opcode_name"]),
            "is_heartbeat": bool(row["is_heartbeat"]),
            "content_length": int(row["content_length"]),
            "is_binary": is_binary,
            "preview": preview,
            "truncated": truncated,
            "content": text_content if not truncated else preview,
            "file_path": file_path,
        }

    def verify_health(self) -> StorageHealth:
        """探测当前 SQLite WAL 数据总线与分流目录的读写状态及表结构完整性。

        Returns:
            包含 WAL 状态、表清单与可写状态的 StorageHealth 诊断结果。
        """
        try:
            # 1. 验证大载荷分流目录可写性
            self.bodies_dir.mkdir(parents=True, exist_ok=True)
            probe_file = self.bodies_dir / ".write_probe"
            probe_file.write_bytes(b"ok")
            probe_file.unlink(missing_ok=True)

            # 2. 查询 SQLite journal_mode 与已创建的核心表
            with closing(sqlite3.connect(self.db_path, timeout=5.0)) as conn:
                mode_row = conn.execute("PRAGMA journal_mode;").fetchone()
                journal_mode = str(mode_row[0]) if mode_row else "unknown"
                table_rows = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"
                ).fetchall()
                tables = [str(row[0]) for row in table_rows]

            return StorageHealth(
                writable=True,
                journal_mode=journal_mode,
                tables=tables,
                db_path=self.db_path,
                bodies_dir=self.bodies_dir,
                error=None,
            )
        except Exception as exc:
            logger.warning("SQLite WAL 数据总线健康自检失败: %s", exc)
            return StorageHealth(
                writable=False,
                journal_mode="error",
                tables=[],
                db_path=self.db_path,
                bodies_dir=self.bodies_dir,
                error=str(exc),
            )

    def cleanup(self) -> None:
        """按生命周期策略清理分流载荷目录与临时 SQLite 数据库文件。"""
        # 1. 始终清理当前进程专属的大载荷分流临时目录
        if self.bodies_dir.exists():
            try:
                shutil.rmtree(self.bodies_dir, ignore_errors=True)
            except OSError as exc:
                logger.warning("清理大载荷临时目录失败 (%s): %s", self.bodies_dir, exc)

        # 2. 若未显式指定保留数据库，则删除默认临时数据库及 WAL/SHM 附属文件
        if self.preserve_db:
            return

        for candidate in (
            self.db_path,
            Path(f"{self.db_path}-wal"),
            Path(f"{self.db_path}-shm"),
        ):
            try:
                candidate.unlink(missing_ok=True)
            except OSError as exc:
                logger.warning("清理临时数据库文件失败 (%s): %s", candidate, exc)
