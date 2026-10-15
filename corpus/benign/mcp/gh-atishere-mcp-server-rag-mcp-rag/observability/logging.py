"""Structured JSON logging with context vars."""

import logging
import sys
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Generator

import structlog

from mcp_rag.config import settings

# ============================================================
# CONTEXT VARIABLES (async-safe, thread-safe)
# ============================================================
request_id_var: ContextVar[str] = ContextVar("request_id", default="")
user_id_var: ContextVar[str] = ContextVar("user_id", default="")
workspace_id_var: ContextVar[str] = ContextVar("workspace_id", default="")


def new_request_id() -> str:
    """Tạo request ID mới (UUID ngắn 16 ký tự)."""
    return uuid.uuid4().hex[:16]


# ============================================================
# CUSTOM PROCESSORS
# ============================================================
def add_context_vars(
    logger: Any, method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Tự động thêm context vars vào mỗi log."""
    if request_id := request_id_var.get():
        event_dict["request_id"] = request_id
    if user_id := user_id_var.get():
        event_dict["user_id"] = user_id
    if workspace_id := workspace_id_var.get():
        event_dict["workspace_id"] = workspace_id
    return event_dict


def add_app_info(
    logger: Any, method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Thêm app name + version + env vào mỗi log."""
    event_dict["app"] = settings.app_name
    event_dict["version"] = settings.app_version
    event_dict["env"] = settings.environment
    return event_dict


SENSITIVE_KEYS = {
    "token",
    "password",
    "api_key",
    "secret",
    "authorization",
    "jwt",
    "credit_card",
}


def censor_sensitive_data(
    logger: Any, method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Che dữ liệu nhạy cảm (token, password) trước khi log."""

    def censor(obj: Any) -> Any:
        if isinstance(obj, dict):
            return {
                k: "***" if k.lower() in SENSITIVE_KEYS else censor(v)
                for k, v in obj.items()
            }
        if isinstance(obj, list):
            return [censor(item) for item in obj]
        return obj

    return censor(event_dict)


# ============================================================
# SETUP
# ============================================================
def setup_logging() -> None:
    """Cấu hình structlog + stdlib logging.

    QUAN TRỌNG: Logging đi vào STDERR, không phải STDOUT.
    Vì MCP protocol dùng STDOUT để giao tiếp JSON-RPC.
    Nếu log vào STDOUT → làm hỏng protocol.
    """
    # Bước 1: Cấu hình stdlib logging → STDERR (không phải stdout!)
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stderr,          # ← QUAN TRỌNG: stderr, không phải stdout
        level=getattr(logging, settings.log_level),
    )

    # Bước 2: Chọn renderer
    if settings.is_production:
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    # Bước 3: Cấu hình structlog
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            add_context_vars,
            add_app_info,
            censor_sensitive_data,
            structlog.processors.format_exc_info,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, settings.log_level)
        ),
        # PrintLoggerFactory → stderr
        logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = __name__) -> structlog.stdlib.BoundLogger:
    """Lấy logger instance."""
    return structlog.get_logger(name)  # type: ignore[no-any-return]


# ============================================================
# CONTEXT MANAGER
# ============================================================
@contextmanager
def log_context(
    request_id: str | None = None,
    user_id: str | None = None,
    workspace_id: str | None = None,
) -> Generator[None, None, None]:
    """Context manager set context vars tạm thời."""
    tokens: list[tuple[str, Any]] = []
    if request_id:
        tokens.append(("request_id", request_id_var.set(request_id)))
    if user_id:
        tokens.append(("user_id", user_id_var.set(user_id)))
    if workspace_id:
        tokens.append(("workspace_id", workspace_id_var.set(workspace_id)))

    try:
        yield
    finally:
        for name, token in tokens:
            if name == "request_id":
                request_id_var.reset(token)
            elif name == "user_id":
                user_id_var.reset(token)
            elif name == "workspace_id":
                workspace_id_var.reset(token)
