"""Complete stdio MCP server composition for local applications."""

from __future__ import annotations

import os
import sys
from collections.abc import AsyncIterator, Callable, Mapping, Sequence
from contextlib import asynccontextmanager
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Protocol, cast

from fastmcp import FastMCP

from localmcp.config import ConfigDocument, ConfigError, LocalMCPPaths, ServerConfig
from localmcp.llm import (
    DEFAULT_MODEL_REGISTRY,
    ConfiguredModelFactory,
    LLMBackend,
    LLMBackendConfig,
    ModelConfigurationError,
    ModelFactory,
    ModelRegistry,
    ModelSpec,
    infer_model_spec,
)
from localmcp.observability.logging import configure_logging, get_logger, resolve_log_level
from localmcp.observability.telemetry import (
    LangfuseTelemetry,
    LangfuseToolMiddleware,
    install_telemetry,
    telemetry,
)
from localmcp.secrets import SecretCatalog, SecretResolver

log = get_logger(__name__)


class RuntimeLifecycle(Protocol):
    async def start(self) -> None: ...

    async def close(self) -> None: ...


class RuntimeFactory[ConfigT, RuntimeT: RuntimeLifecycle](Protocol):
    def __call__(
        self,
        config: ConfigT,
        state_root: Path,
        model_factory: ModelFactory,
        *,
        telemetry: LangfuseTelemetry,
    ) -> RuntimeT: ...


class RuntimeUnavailableError(RuntimeError):
    """Raised when a tool resolves its runtime outside the server lifespan."""


_runtime: RuntimeLifecycle | None = None


@dataclass(frozen=True)
class _ObservabilitySettings:
    """Library-owned logging settings for a stdio server."""

    log_level: str = "WARNING"


@dataclass(frozen=True)
class _ServerSettings:
    """Validated localmcplib settings for one effective server view."""

    llm: LLMBackendConfig
    registry: ModelRegistry
    observability: _ObservabilitySettings


def current_runtime[RuntimeT: RuntimeLifecycle](expected_type: type[RuntimeT]) -> RuntimeT:
    """Return the lifespan-owned application runtime with a checked type."""
    runtime = _runtime
    if runtime is None:
        raise RuntimeUnavailableError("application runtime is not initialized")
    if not isinstance(runtime, expected_type):
        raise RuntimeUnavailableError("a different application runtime is initialized")
    return runtime


class STDIOServer[ConfigT, RuntimeT: RuntimeLifecycle]:
    """Own all generic bootstrap and serving behavior for one stdio MCP server."""

    def __init__(
        self,
        *,
        name: str,
        tools: Sequence[Any],
        runtime_factory: RuntimeFactory[ConfigT, RuntimeT],
        config_parser: Callable[[ServerConfig], ConfigT] | None = None,
        llm_secret_name: str = "llm_api_key",
        openai_secret_name: str = "openai_api_key",
        anthropic_secret_name: str = "anthropic_api_key",
        log_level_env: str = "LOCALMCP_LOG_LEVEL",
    ) -> None:
        self.name = name
        self.tools = tuple(tools)
        self.config_parser = config_parser
        self.runtime_factory = runtime_factory
        self.llm_secret_name = llm_secret_name
        self.openai_secret_name = openai_secret_name
        self.anthropic_secret_name = anthropic_secret_name
        self.log_level_env = log_level_env
        # Replaced by the configured catalog in start_runtime; kept off the
        # _model_factory signature so subclass overrides remain compatible.
        self._model_registry = DEFAULT_MODEL_REGISTRY

        @asynccontextmanager
        async def lifespan(_server: FastMCP) -> AsyncIterator[ConfigT]:
            config = await self.start_runtime(env=os.environ, home=Path.home())
            try:
                yield config
            finally:
                try:
                    await self.stop_runtime()
                except Exception as exc:
                    log.warning("server.shutdown_close_failed", error_type=type(exc).__name__)

        self.mcp = FastMCP(name, lifespan=lifespan)
        self.mcp.add_middleware(LangfuseToolMiddleware())
        for tool in self.tools:
            self.mcp.add_tool(tool)

    def load_config(
        self,
        *,
        env: Mapping[str, str],
        home: Path,
    ) -> ConfigT:
        """Load the effective application-owned configuration."""
        _document, _settings, config = self._load_config(env=env, home=home)
        return config

    def _load_config(
        self,
        *,
        env: Mapping[str, str],
        home: Path,
    ) -> tuple[ConfigDocument, _ServerSettings, ConfigT]:
        document = ConfigDocument.load(env=env, home=home)
        effective = document.for_server(self.name)
        shared = _parse_shared_config(effective)
        application = _application_config(effective)
        if self.config_parser is None:
            config = cast(ConfigT, application)
        else:
            config = self.config_parser(application)
        return document, shared, config

    async def start_runtime(self, *, env: Mapping[str, str], home: Path) -> ConfigT:
        """Build and transactionally start the shared application runtime."""
        global _runtime
        if _runtime is not None:
            await self.stop_runtime()

        document, shared, config = self._load_config(env=env, home=home)
        catalog = SecretCatalog.from_config(document, server=self.name)
        resolver = SecretResolver(env, tolerate_keyring_errors=True)
        self._model_registry = shared.registry
        model_factory = self._model_factory(shared.llm, catalog, resolver)
        telemetry_service = LangfuseTelemetry(env)
        install_telemetry(telemetry_service)
        paths = LocalMCPPaths.from_environment(env, home=home)
        runtime = self.runtime_factory(
            config,
            paths.server_state_dir(self.name),
            model_factory,
            telemetry=telemetry_service,
        )
        try:
            await runtime.start()
        except BaseException:
            await telemetry_service.close()
            install_telemetry(LangfuseTelemetry({}))
            raise
        _runtime = runtime
        return config

    def _model_factory(
        self,
        config: LLMBackendConfig,
        catalog: SecretCatalog,
        resolver: SecretResolver,
    ) -> ConfiguredModelFactory:
        if config.backend == "openai_compatible":
            gateway_api_key = _secret_provider(catalog, resolver, self.llm_secret_name, required=True)
            return ConfiguredModelFactory(
                self._model_registry,
                config,
                gateway_api_key=gateway_api_key,
            )
        return ConfiguredModelFactory(
            self._model_registry,
            config,
            openai_api_key=_secret_provider(catalog, resolver, self.openai_secret_name),
            anthropic_api_key=_secret_provider(catalog, resolver, self.anthropic_secret_name),
        )

    async def stop_runtime(self) -> None:
        """Close and forget the application runtime and telemetry service."""
        global _runtime
        runtime, _runtime = _runtime, None
        close_error: BaseException | None = None
        if runtime is not None:
            try:
                await runtime.close()
            except BaseException as exc:
                close_error = exc
        await telemetry().close()
        install_telemetry(LangfuseTelemetry({}))
        if close_error is not None:
            raise close_error

    def run(self) -> None:
        """Configure file-only logging and serve MCP over stdio."""
        env = os.environ
        try:
            home = Path.home()
            _document, shared, _config = self._load_config(env=env, home=home)
            level = resolve_log_level(
                env,
                env_var=self.log_level_env,
                file_level=shared.observability.log_level,
            )
            log_file = LocalMCPPaths.from_environment(env, home=home).server_log_file(self.name)
            configure_logging(log_file=log_file, level=level)
        except ConfigError as exc:
            print(f"{self.name}: configuration error: {exc}", file=sys.stderr)
            raise SystemExit(1) from exc
        except Exception as exc:
            raise SystemExit(1) from exc

        log.info("server.starting", server=self.name, transport="stdio", tool_count=len(self.tools))
        try:
            self.mcp.run(transport="stdio", show_banner=False)
        except Exception as exc:
            log.error("server.crashed", server=self.name, error_type=type(exc).__name__)
            raise SystemExit(1) from exc


def main[ConfigT, RuntimeT: RuntimeLifecycle](server: STDIOServer[ConfigT, RuntimeT]) -> None:
    """Run a configured :class:`STDIOServer`."""
    server.run()


def _parse_shared_config(config: ServerConfig) -> _ServerSettings:
    llm = _table(config.values.get("llm"), field="llm")
    supported_llm_fields = {"backend", "base_url", "default_headers", "verify", "keepalive_expiry", "models"}
    unsupported = set(llm) - supported_llm_fields
    if unsupported:
        raise ConfigError(f"llm has unsupported fields: {', '.join(sorted(unsupported))}")

    backend = llm.get("backend")
    if not isinstance(backend, str):
        raise ConfigError("llm.backend must be a string")
    if backend not in ("openai_compatible", "native"):
        raise ConfigError(f"unsupported llm.backend: {backend!r}")
    selected_backend = cast(LLMBackend, backend)
    base_url = llm.get("base_url")
    if base_url is not None and not isinstance(base_url, str):
        raise ConfigError("llm.base_url must be a string")
    headers = llm.get("default_headers")
    if headers is not None:
        if not isinstance(headers, Mapping) or not all(
            isinstance(key, str) and isinstance(value, str) for key, value in headers.items()
        ):
            raise ConfigError("llm.default_headers must be a table of strings")
        headers = dict(headers)
    verify = llm.get("verify", True)
    if not isinstance(verify, bool | str):
        raise ConfigError("llm.verify must be a boolean or string")
    keepalive_expiry = llm.get("keepalive_expiry", 5.0)
    if isinstance(keepalive_expiry, bool) or not isinstance(keepalive_expiry, int | float):
        raise ConfigError("llm.keepalive_expiry must be a number")
    registry = _parse_model_specs(_table(llm.get("models", {}), field="llm.models"))

    observability = _table(config.values.get("observability", {}), field="observability")
    unsupported = set(observability) - {"log_level"}
    if unsupported:
        raise ConfigError(f"observability has unsupported fields: {', '.join(sorted(unsupported))}")
    log_level = observability.get("log_level", "WARNING")
    if not isinstance(log_level, str):
        raise ConfigError("observability.log_level must be a string")

    return _ServerSettings(
        llm=LLMBackendConfig(
            backend=selected_backend,
            base_url=base_url,
            default_headers=headers,
            verify=verify,
            keepalive_expiry=float(keepalive_expiry),
        ),
        registry=registry,
        observability=_ObservabilitySettings(log_level=log_level),
    )


_MODEL_SPEC_CHOICES: Mapping[str, tuple[str, ...]] = {
    "temperature": ("zero", "omit"),
    "native_provider": ("anthropic", "openai"),
    "dialect": ("anthropic", "openai"),
}


def _parse_model_specs(models: Mapping[str, object]) -> ModelRegistry:
    """Overlay ``[llm.models]`` entries on the built-in catalog.

    Each entry updates only the fields it names, starting from the built-in
    spec when the ID is catalogued and from the inferred spec otherwise.
    """
    catalog = DEFAULT_MODEL_REGISTRY.as_mapping()
    overrides: dict[str, ModelSpec] = {}
    for model_id, raw in models.items():
        field = f"llm.models.{model_id}"
        entry = _table(raw, field=field)
        unsupported = set(entry) - {*_MODEL_SPEC_CHOICES, "supports_reasoning_effort", "default_reasoning_effort"}
        if unsupported:
            raise ConfigError(f"{field} has unsupported fields: {', '.join(sorted(unsupported))}")
        updates: dict[str, Any] = {}
        for name, choices in _MODEL_SPEC_CHOICES.items():
            if name in entry:
                value = entry[name]
                if value not in choices:
                    raise ConfigError(f"{field}.{name} must be one of: {', '.join(choices)}")
                updates[name] = value
        if "supports_reasoning_effort" in entry:
            if not isinstance(entry["supports_reasoning_effort"], bool):
                raise ConfigError(f"{field}.supports_reasoning_effort must be a boolean")
            updates["supports_reasoning_effort"] = entry["supports_reasoning_effort"]
        if "default_reasoning_effort" in entry:
            if not isinstance(entry["default_reasoning_effort"], str):
                raise ConfigError(f"{field}.default_reasoning_effort must be a string")
            updates["default_reasoning_effort"] = entry["default_reasoning_effort"]
        base = catalog.get(model_id) or infer_model_spec(model_id)
        if "supports_reasoning_effort" not in updates and ("dialect" in updates or "native_provider" in updates):
            # A dialect change can invalidate an inherited reasoning capability;
            # only an explicit setting keeps it.
            dialect = (
                updates.get("dialect", base.dialect) or updates.get("native_provider", base.native_provider) or "openai"
            )
            if dialect != "openai":
                updates.setdefault("supports_reasoning_effort", False)
                updates.setdefault("default_reasoning_effort", None)
        try:
            overrides[model_id] = replace(base, **updates)
        except ModelConfigurationError as exc:
            raise ConfigError(f"{field}: {exc}") from exc
    try:
        return DEFAULT_MODEL_REGISTRY.overlay(overrides)
    except ModelConfigurationError as exc:
        raise ConfigError(f"llm.models: {exc}") from exc


def _application_config(config: ServerConfig) -> ServerConfig:
    library_fields = {"schema_version", "llm", "observability", "secrets"}
    return ServerConfig(
        name=config.name,
        values={key: value for key, value in config.values.items() if key not in library_fields},
    )


def _table(value: object, *, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ConfigError(f"{field} must be a TOML table")
    if not all(isinstance(key, str) for key in value):
        raise ConfigError(f"{field} keys must be strings")
    return cast(Mapping[str, object], value)


def _secret_provider(
    catalog: SecretCatalog,
    resolver: SecretResolver,
    logical_name: str,
    *,
    required: bool = False,
) -> Callable[[], str] | None:
    reference = catalog.require(logical_name) if required else catalog.get(logical_name)
    if reference is None:
        return None

    def resolve() -> str:
        return resolver.require(reference).reveal()

    return resolve
