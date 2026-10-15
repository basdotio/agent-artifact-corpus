"""Optional Langfuse tracing with private-by-default MCP instrumentation."""

from __future__ import annotations

import asyncio
import importlib
from collections.abc import Mapping
from contextlib import AbstractContextManager
from dataclasses import dataclass
from types import TracebackType
from typing import Any, Literal, Protocol
from urllib.parse import urlsplit

from fastmcp.server.middleware import CallNext, Middleware, MiddlewareContext
from fastmcp.tools.base import ToolResult
from mcp.types import CallToolRequestParams

from localmcp.observability.logging import get_logger

log = get_logger(__name__)

_ENABLED_VALUES = frozenset({"1", "true", "yes", "on"})
_REQUIRED_ENV = ("LANGFUSE_BASE_URL", "LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY")
_CAPTURE_PAYLOADS_ENV = "LOCALMCP_LANGFUSE_CAPTURE_PAYLOADS"
_PAYLOAD_ATTRIBUTE_NAMES = frozenset(
    {
        "langfuse.trace.input",
        "langfuse.trace.output",
        "langfuse.observation.input",
        "langfuse.observation.output",
    }
)
_PAYLOAD_ATTRIBUTE_PREFIXES = (
    "gen_ai.prompt.",
    "gen_ai.completion.",
    "gen_ai.input.",
    "gen_ai.output.",
)


class Observation(Protocol):
    def update(self, **kwargs: Any) -> Any: ...


class _SafeObservation:
    def __init__(self, name: str, metadata: Mapping[str, Any], observation: Observation | None = None):
        self._name = name
        self._metadata = dict(metadata)
        self._observation = observation

    def update(self, **kwargs: Any) -> None:
        metadata = kwargs.pop("metadata", None)
        if isinstance(metadata, Mapping):
            self._metadata.update(metadata)
        if self._observation is None:
            return
        try:
            self._observation.update(metadata=self._metadata, **kwargs)
        except Exception as exc:
            log.warning("langfuse.span_update_failed", span=self._name, error_type=type(exc).__name__)


class _Span(AbstractContextManager[Observation]):
    def __init__(
        self,
        service: LangfuseTelemetry,
        name: str,
        *,
        observation_type: str,
        metadata: Mapping[str, Any] | None,
        trace_seed: str | None,
        model: str | None,
    ):
        self._service = service
        self._name = name
        self._observation_type = observation_type
        self._metadata = dict(metadata or {})
        self._trace_seed = trace_seed
        self._model = model
        self._context: AbstractContextManager[Any] | None = None
        self._observation = _SafeObservation(name, self._metadata)

    def __enter__(self) -> Observation:
        client = self._service._client
        if client is None:
            return self._observation
        kwargs: dict[str, Any] = {
            "as_type": self._observation_type,
            "name": self._name,
            "metadata": self._metadata,
        }
        if self._model is not None:
            kwargs["model"] = self._model
        try:
            if self._trace_seed is not None:
                kwargs["trace_context"] = {"trace_id": client.create_trace_id(seed=self._trace_seed)}
            self._context = client.start_as_current_observation(**kwargs)
            raw = self._context.__enter__()
            self._observation = _SafeObservation(self._name, self._metadata, raw)
        except Exception as exc:
            self._context = None
            self._observation = _SafeObservation(self._name, self._metadata)
            log.warning("langfuse.span_start_failed", span=self._name, error_type=type(exc).__name__)
        return self._observation

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> Literal[False]:
        if self._context is None:
            return False
        try:
            self._observation.update(
                metadata={**self._metadata, "outcome": "error" if exc_type is not None else "success"}
            )
            self._context.__exit__(exc_type, exc, traceback)
        except Exception as telemetry_error:
            log.warning("langfuse.span_finish_failed", span=self._name, error_type=type(telemetry_error).__name__)
        return False


@dataclass(frozen=True)
class LangfuseStatus:
    status: Literal["disabled", "ready", "configuration_error", "dependency_missing", "initialization_error"]
    enabled: bool
    base_url: str | None
    message: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "enabled": self.enabled,
            "base_url": self.base_url,
            "message": self.message,
        }


class LangfuseTelemetry:
    """Lifespan-owned optional Langfuse client with a no-op disabled state."""

    def __init__(
        self,
        env: Mapping[str, str],
        *,
        enabled_env_var: str = "LOCALMCP_LANGFUSE_ENABLED",
    ):
        self._client: Any | None = None
        self._public_key: str | None = None
        self.capture_payloads = env.get(_CAPTURE_PAYLOADS_ENV, "").strip().lower() in _ENABLED_VALUES
        enabled = env.get(enabled_env_var, "").strip().lower() in _ENABLED_VALUES
        base_url = env.get("LANGFUSE_BASE_URL", "").strip() or None
        reported_base_url = _safe_endpoint(base_url)
        if not enabled:
            self.status = LangfuseStatus("disabled", False, reported_base_url, "Langfuse tracing is disabled.")
            return
        missing = [name for name in _REQUIRED_ENV if not env.get(name, "").strip()]
        if missing:
            self.status = LangfuseStatus(
                "configuration_error",
                True,
                reported_base_url,
                f"Missing required environment variable(s): {', '.join(missing)}.",
            )
            log.warning("langfuse.configuration_invalid", missing=missing)
            return
        try:
            module = importlib.import_module("langfuse")
            types_module = importlib.import_module("langfuse.types")
        except ImportError:
            self.status = LangfuseStatus(
                "dependency_missing",
                True,
                reported_base_url,
                "The langfuse package could not be imported.",
            )
            log.warning("langfuse.dependency_missing")
            return
        try:
            self._public_key = env["LANGFUSE_PUBLIC_KEY"].strip()
            self._client = module.Langfuse(
                public_key=self._public_key,
                secret_key=env["LANGFUSE_SECRET_KEY"].strip(),
                base_url=base_url,
                tracing_enabled=True,
                mask_otel_spans=None if self.capture_payloads else _payload_suppressor(types_module),
            )
        except Exception as exc:
            self.status = LangfuseStatus(
                "initialization_error",
                True,
                reported_base_url,
                f"Langfuse SDK initialization failed ({type(exc).__name__}).",
            )
            log.warning("langfuse.initialization_failed", error_type=type(exc).__name__)
            return
        self.status = LangfuseStatus("ready", True, reported_base_url, "Langfuse is initialized.")
        log.info("langfuse.initialized", base_url=reported_base_url)

    def langchain_callback(self) -> Any | None:
        if self._client is None or self._public_key is None:
            return None
        try:
            callback = importlib.import_module("langfuse.langchain").CallbackHandler(public_key=self._public_key)
            callback._langfuse_client = self._client
            return callback
        except Exception as exc:
            log.warning("langfuse.langchain_callback_failed", error_type=type(exc).__name__)
            return None

    def span(
        self,
        name: str,
        *,
        observation_type: str = "span",
        metadata: Mapping[str, Any] | None = None,
        trace_seed: str | None = None,
        model: str | None = None,
    ) -> AbstractContextManager[Observation]:
        return _Span(
            self,
            name,
            observation_type=observation_type,
            metadata=metadata,
            trace_seed=trace_seed,
            model=model,
        )

    async def check(self) -> dict[str, Any]:
        result = self.status.as_dict()
        if self._client is None:
            result["authenticated"] = False
            return result
        try:
            authenticated = bool(await asyncio.to_thread(self._client.auth_check))
        except Exception as exc:
            result.update(
                status="connection_error",
                authenticated=False,
                message=f"Langfuse connectivity check failed ({type(exc).__name__}).",
            )
            return result
        result.update(
            status="ready" if authenticated else "authentication_error",
            authenticated=authenticated,
            message=(
                "Langfuse credentials and endpoint are ready." if authenticated else "Langfuse rejected the key pair."
            ),
        )
        return result

    async def close(self) -> None:
        client, self._client = self._client, None
        if client is None:
            return
        try:
            await asyncio.to_thread(client.shutdown)
        except Exception as exc:
            log.warning("langfuse.shutdown_failed", error_type=type(exc).__name__)


def _safe_endpoint(value: str | None) -> str | None:
    if value is None:
        return None
    try:
        parsed = urlsplit(value)
        if parsed.scheme not in {"http", "https"} or parsed.hostname is None:
            return "<configured>"
        port = f":{parsed.port}" if parsed.port is not None else ""
        return f"{parsed.scheme}://{parsed.hostname}{port}"
    except ValueError:
        return "<configured>"


def _payload_suppressor(types_module: Any) -> Any:
    def suppress(*, params: Any) -> Any:
        patches = {}
        for identifier, span in params.spans.items():
            payload_attributes = tuple(
                name
                for name in span.attributes
                if name in _PAYLOAD_ATTRIBUTE_NAMES or name.startswith(_PAYLOAD_ATTRIBUTE_PREFIXES)
            )
            if payload_attributes:
                patches[identifier] = types_module.OtelSpanPatch(delete_attributes=payload_attributes)
        if not patches:
            return None
        return types_module.MaskOtelSpansResult(span_patches=patches)

    return suppress


_telemetry = LangfuseTelemetry({})


def install_telemetry(service: LangfuseTelemetry) -> None:
    global _telemetry
    _telemetry = service


def telemetry() -> LangfuseTelemetry:
    return _telemetry


class LangfuseToolMiddleware(Middleware):
    """Trace top-level MCP calls, capturing payloads only by explicit opt-in."""

    async def on_call_tool(
        self,
        context: MiddlewareContext[CallToolRequestParams],
        call_next: CallNext[CallToolRequestParams, ToolResult],
    ) -> ToolResult:
        name = getattr(context.message, "name", "unknown")
        service = telemetry()
        with service.span(
            f"mcp.tool.{name}",
            observation_type="tool",
            metadata={"tool": name, "source": context.source},
        ) as observation:
            if service.capture_payloads:
                observation.update(input=context.message.arguments or {})
            result = await call_next(context)
            if service.capture_payloads:
                try:
                    output = result.model_dump(mode="json", by_alias=True, exclude_none=True)
                except Exception as exc:
                    log.warning("langfuse.tool_output_serialization_failed", error_type=type(exc).__name__)
                else:
                    observation.update(output=output)
            return result
