"""DesignPatternServer — FastMCP entry point with lifespan management and tool registration.

Startup order (docs/implementation-guide.md §2.2/§2.3/§2.4): configuration → catalog load, join and
integrity gate (fail-fast ``ERR_CATALOG_INVALID``) → variant resource materialization behind that
gate → retrieval index warm-up (a failed embedder refuses the start) → job store → tool, prompt and
resource registration (each idempotency-guarded, because the lifespan re-enters per client session).

Error handling:
- ERR_011 — catalog or configuration integrity failure at startup (critical)
- ERR_013 — server initialization failure (critical)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import warnings
from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, ClassVar

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.server.transforms import GetToolNext, PromptsAsTools, ResourcesAsTools, VersionSpec
from fastmcp.tools import Tool
from mcp.shared.exceptions import MCPDeprecationWarning
from mcp.types import ToolAnnotations

from src.anti_scope import AntiScopeGuard
from src.patterns.embedder import OfflineHashEmbedder, build_embedder, embedder_identity
from src.patterns.loader import (
    PatternLoader,
    load_catalog,
    parse_locally_implementable_names,
    parse_out_of_scope_terms,
)
from src.config import ConfigManager, ServerConfig
from src.tools.jobs import JobsStore
from src.agent import LLMClientProtocol, build_llm_client
from src.pipeline import DesignPipeline
from src.resources.variants import VariantsResource
from src.patterns.retriever import RetrievalIndex
from src.patterns.safe_tei_rerank import LexicalReranker, build_reranker
from src.tools import create_all_tools
from src.reasoning import ReasoningConfig
from src.reasoning.client import ReasoningClient

ERROR_SERVER_INIT = "ERR_013"

logger = logging.getLogger(__name__)


def configure_logging(log_level: str = "INFO", log_format: str = "json") -> None:
    """Redirect logs to stderr; stdout stays clean for the MCP stdio protocol.

    Also silences the SDK's per-call notice for the MCP logging capability (SEP-2577, deprecated
    2026-07-28): fastmcp 4.x deliberately keeps routing ``Context.info``/``log`` through it, and the
    unruled ``UserWarning`` would print raw text into the JSON stderr stream. The test surface is
    covered by the matching message-scoped filter in ``pyproject.toml``.
    """
    import json as _json

    # Message-scoped: other MCPDeprecationWarnings (roots, elicitation) still surface.
    warnings.filterwarnings(
        "ignore",
        message=r"The logging capability is deprecated",
        category=MCPDeprecationWarning,
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    stderr_handler = logging.StreamHandler(sys.stderr)

    if log_format.lower() == "json":

        class JSONFormatter(logging.Formatter):
            _STANDARD_ATTRS: ClassVar[frozenset[str]] = frozenset(
                {
                    "name", "msg", "args", "levelname", "levelno", "pathname", "filename", "module",
                    "exc_info", "exc_text", "stack_info", "lineno", "funcName", "created", "msecs",
                    "relativeCreated", "thread", "threadName", "processName", "process", "taskName",
                    "message", "asctime",
                }
            )

            def format(self, record: logging.LogRecord) -> str:
                log_entry: dict[str, Any] = {
                    "timestamp": datetime.now(UTC).isoformat(),
                    "level": record.levelname,
                    "logger": record.name,
                    "message": record.getMessage(),
                }
                for key, value in record.__dict__.items():
                    if key not in self._STANDARD_ATTRS and not key.startswith("_"):
                        log_entry[key] = value
                if record.exc_info:
                    log_entry["exception"] = self.formatException(record.exc_info)
                return _json.dumps(log_entry, default=str)

        stderr_handler.setFormatter(JSONFormatter())
    else:
        stderr_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )

    root_logger.addHandler(stderr_handler)


_PROMPTS_AS_TOOLS_HINTS: dict[str, ToolAnnotations] = {
    "list_prompts": ToolAnnotations(
        title="List Prompts", read_only_hint=True, destructive_hint=False,
        idempotent_hint=True, open_world_hint=False,
    ),
    "get_prompt": ToolAnnotations(
        title="Get Prompt", read_only_hint=True, destructive_hint=False,
        idempotent_hint=True, open_world_hint=False,
    ),
}


class AnnotatedPromptsAsTools(PromptsAsTools):
    """PromptsAsTools that injects ToolAnnotations on the generated tools (#3459 workaround).

    Upstream emits ``list_prompts`` / ``get_prompt`` with ``annotations=None``, so clients must
    assume worst-case. Idempotent: once upstream adds annotations, the injection is a no-op.
    """

    async def list_tools(self, tools: Sequence[Tool]) -> Sequence[Tool]:
        result = await super().list_tools(tools)
        return [_with_prompts_as_tools_annotations(tool) for tool in result]

    async def get_tool(
        self, name: str, call_next: GetToolNext, *, version: VersionSpec | None = None
    ) -> Tool | None:
        tool = await super().get_tool(name, call_next, version=version)
        return _with_prompts_as_tools_annotations(tool) if tool else None


def _with_prompts_as_tools_annotations(tool: Tool) -> Tool:
    """Copy ``tool`` with injected annotations when it matches a known transform tool name."""
    hints = _PROMPTS_AS_TOOLS_HINTS.get(tool.name)
    if hints is None or tool.annotations is not None:
        return tool
    return tool.model_copy(update={"annotations": hints})


class DesignPatternServer:
    """FastMCP server exposing the design-pattern selection tools, prompts and resources."""

    _TOOL_METHOD_MAP: dict[str, str] = {
        "select_design_patterns": "select",
        "analyze_design": "analyze",
        "generate_design": "generate",
        "evaluate_design": "evaluate",
        "list_design_patterns": "list_patterns",
        "get_design_pattern": "get_pattern",
        "submit_design_job": "submit_job",
        "get_design_status": "get_status",
        "cancel_design": "cancel",
    }

    def __init__(
        self,
        config_path: str | None = None,
        *,
        transport: str | None = None,
        host: str | None = None,
        port: int | None = None,
        offline: bool = False,
    ) -> None:
        self._config_path = config_path
        self._offline = offline

        config_dict = ConfigManager.load_config(self._config_path)
        if transport is not None:
            config_dict["transport"] = transport
        if host is not None:
            config_dict["host"] = host
        if port is not None:
            config_dict["port"] = port
        self._config = ServerConfig.model_validate(config_dict)

        configure_logging(log_level=self._config.logging_level, log_format=self._config.logging_format)

        self._mcp = FastMCP(
            "design-pattern-mcp",
            lifespan=self.lifespan,
            on_duplicate="error",
        )
        # add_transform is once-per-instance; do NOT move into lifespan without an
        # idempotency guard - add_transform appends, it does not replace.
        self._mcp.add_transform(AnnotatedPromptsAsTools(self._mcp))
        self._mcp.add_transform(ResourcesAsTools(self._mcp))

        self._catalog: PatternLoader | None = None
        self._variants: VariantsResource | None = None
        self._index: RetrievalIndex | None = None
        self._llm: LLMClientProtocol | None = None
        self._pipeline: DesignPipeline | None = None
        self._tools: dict[str, Any] = {}
        self._tools_registered: set[str] = set()
        self._prompts_registered_count: int = 0
        self._resources_registered: bool = False
        self._prompts_registered: bool = False
        self._job_tasks: dict[str, tuple[asyncio.Task[None], Any]] = {}
        # The reasoning client/health map are also read by the lifespan yield and by
        # _cleanup; with reasoning disabled the health check is skipped, so both must
        # exist from construction (otherwise startup dies with AttributeError).
        self._reasoning_client: ReasoningClient | None = None
        self._reasoning_health: dict[str, str] = {}

    # -- startup ------------------------------------------------------------------

    async def _initialize(self) -> None:
        """Load catalog, build the retrieval index and construct every tool instance."""
        try:
            pattern_dir = Path(self._config.paths.pattern_directory)
            docs_dir = Path(self._config.paths.docs_directory)

            self._catalog = load_catalog(pattern_dir, docs_dir)
            self._variants = VariantsResource(self._catalog)

            embedder = (
                OfflineHashEmbedder()
                if self._offline
                else build_embedder(self._config.embedder)
            )
            reranker = (
                LexicalReranker()
                if self._offline
                else build_reranker(self._config.reranker)
            )
            self._index = await RetrievalIndex.build(
                self._catalog,
                embedder,
                reranker,
                self._config.retrieval,
                self._config.reranker.rerank_top_n,
                rerank_text=self._config.reranker.rerank_text,
                dense_cache=None if self._offline else self._config.dense_cache,
                identity=None if self._offline else embedder_identity(self._config.embedder),
            )
            logger.info(
                "Retrieval index warmed up",
                extra={
                    "documents": len(self._catalog.records),
                    "offline": self._offline,
                    "embedder": type(embedder).__name__,
                    "reranker": type(reranker).__name__,
                },
            )
            self._llm = build_llm_client(self._config)
            if not self._config.generator.config.api_key:
                logger.warning(
                    "No generator api_key configured; pipeline runs will fall back to the "
                    "documented degraded paths (E3/E4/E12)"
                )

            self._pipeline = DesignPipeline(
                config=self._config,
                catalog=self._catalog,
                index=self._index,
                llm=self._llm,
                guard=AntiScopeGuard(
                    parse_out_of_scope_terms(docs_dir / "design-patterns.md"),
                    self._catalog,
                    parse_locally_implementable_names(docs_dir / "design-patterns.md"),
                ),
                reasoning=None,  # populated below after health-check
            )
            await self._pipeline.warmup()
            self._pipeline.validate()

            self._reasoning_client = self._build_reasoning_client()
            if self._reasoning_client is not None and self._reasoning_client.enabled:
                await self._check_reasoning_health(
                    self._reasoning_client,
                    self._config.reasoning.fail_fast,
                )
                self._pipeline._reasoning = self._reasoning_client

            JobsStore.configure(str(Path(self._config.jobs.db_path).expanduser()))
            await JobsStore.get_instance()

            self._tools = create_all_tools(
                self._pipeline,
                self._catalog,
                tasks_config=self._config.tasks,
                job_tasks=self._job_tasks,
            )
            logger.info("All tools initialized", extra={"tool_count": len(self._tools)})
        except Exception as exc:
            logger.error(
                "Server initialization failed",
                extra={"error": ERROR_SERVER_INIT, "details": str(exc)},
            )
            raise


    def _build_reasoning_client(self) -> ReasoningClient | None:
        """Build the ReasoningClient from config (None when disabled).

        Thoughts are authored with the generator's own LLM (the same
        LiteLLM instance behind DESIGN_PATTERN_GENERATOR_*); there is no
        separate reasoning model.
        """
        reasoning_config: ReasoningConfig = self._config.reasoning
        if not reasoning_config.enabled:
            logger.info("Reasoning MCP integration disabled (REASONING_ENABLED=false)")
            return None
        if self._llm is None:
            raise RuntimeError("DesignAgent not initialized — cannot build ReasoningClient")
        return ReasoningClient(reasoning_config, self._llm)  # type: ignore[arg-type]  # runtime is DesignAgent

    async def _check_reasoning_health(
        self, client: ReasoningClient, fail_fast: bool
    ) -> None:
        """LOUD startup health check for the reasoning MCP tools.

        Per-call behaviour stays silently degrading, but startup must not:
        an unreachable tool is logged at ERROR so a broken embedding is visible
        immediately.
        """
        self._reasoning_health = await client.health_check()
        for tool_name, status in self._reasoning_health.items():
            if status == "ok":
                logger.info(f"Reasoning MCP '{tool_name}' reachable")
            else:
                logger.error(
                    f"Reasoning MCP '{tool_name}' NOT reachable: {status}",
                    extra={
                        "reasoning_mcps": self._reasoning_health,
                        "hint": (
                            "Traces degrade to the in-prompt scaffold. Check the "
                            "embedded entry points (/usr/local/lib/node_modules/...) "
                            "or override REASONING_SHANNONTHINKING_CMD / "
                            "REASONING_CODE_REASONING_CMD."
                        ),
                    },
                )
        if fail_fast and any(
            s != "ok" for s in self._reasoning_health.values()
        ):
            raise RuntimeError(
                f"Reasoning MCP failed its health check (fail_fast=true): {self._reasoning_health}"
            )

    async def _cleanup(self) -> None:
        """Tear down resources; always called from the lifespan finally block."""
        try:
            for job_id, (task, _token) in list(self._job_tasks.items()):
                task.cancel()
                logger.debug("Cancelled background task: %s", job_id)
            if self._job_tasks:
                await asyncio.gather(*(task for task, _ in self._job_tasks.values()), return_exceptions=True)
                self._job_tasks.clear()
            try:
                store = await JobsStore.get_instance()
                await store.close()
            except Exception as exc:
                logger.debug("JobsStore cleanup", extra={"error": str(exc)})
            if self._reasoning_client:
                await self._reasoning_client.close()
                logger.debug("Cleaned up ReasoningClient")
            self._tools.clear()
            logger.info("Server resources cleanup completed")
        except Exception as exc:
            logger.warning("Error during cleanup", extra={"details": str(exc)})

    @asynccontextmanager
    async def lifespan(self, server: FastMCP) -> AsyncIterator[dict[str, Any]]:
        """Initialize before yielding the context dict; clean up in finally."""
        logger.info("Starting DesignPatternServer lifespan")
        try:
            await self._initialize()
            self._register_tools(server)
            self._register_resources(server)
            self._register_prompts(server)
            logger.info(
                "MCP surface registered",
                extra={
                    "tools": len(self._tools_registered),
                    "resources": [
                        "design-patterns://variants",
                        "design-patterns://variants/{pattern}",
                    ],
                    "prompts": self._prompts_registered_count,
                },
            )
            yield {
                "pipeline": self._pipeline,
                "agent": self._llm,
                "tools": self._tools,
                "config": self._config,
                "catalog": self._catalog,
                "pattern_loader": self._catalog,
                "variants": self._variants,
                "reasoning_client": self._reasoning_client,
                "reasoning_health": self._reasoning_health,
            }
        finally:
            logger.info("Shutting down DesignPatternServer lifespan")
            await self._cleanup()

    # -- registration -------------------------------------------------------------

    def _register_tools(self, server: FastMCP) -> None:
        """Idempotent: skips tools already registered (lifespan re-enters on client connect)."""
        for tool_key, method_name in self._TOOL_METHOD_MAP.items():
            if tool_key in self._tools_registered:
                continue
            server.add_tool(getattr(self._tools[tool_key], method_name))
            self._tools_registered.add(tool_key)
            logger.debug("Registered tool: %s", tool_key)

    def _register_resources(self, server: FastMCP) -> None:
        """Register the §2.4 variant resource and its per-pattern template (idempotent)."""
        if self._resources_registered:
            return

        def _provider(ctx: Context) -> VariantsResource:
            provider: VariantsResource | None = ctx.lifespan_context.get("variants")
            if provider is None:
                raise ToolError("ERR_013: variant catalog is not available in this session")
            return provider

        @server.resource(
            "design-patterns://variants",
            name="design-pattern-variants",
            mime_type="application/json",
        )
        async def _variants_catalog(ctx: Context) -> str:
            return json.dumps(_provider(ctx).payload(), indent=2)

        @server.resource(
            "design-patterns://variants/{pattern}",
            name="design-pattern-variants-pattern",
            mime_type="application/json",
        )
        async def _variants_for_pattern(pattern: str, ctx: Context) -> str:
            data = _provider(ctx).load(pattern)
            if data is None:
                raise ToolError(f"Design pattern not found: {pattern}")
            return json.dumps(data, indent=2)

        self._resources_registered = True
        logger.info("MCP resources registered", extra={"resources": ["design-patterns://variants"]})

    def _register_prompts(self, server: FastMCP) -> None:
        """Register the workflow prompts (idempotent; mirrors ``_register_resources``)."""
        if self._prompts_registered:
            return
        from src.mcp_prompts import register_prompts

        catalog = self._catalog
        if catalog is None:
            raise ToolError("ERR_013: catalog is not loaded; prompts cannot be registered")
        count = register_prompts(server, catalog)
        self._prompts_registered_count = count
        logger.info("MCP prompts registered", extra={"prompt_count": count})
        self._prompts_registered = True

    async def run(self) -> None:
        """Run via FastMCP's dispatcher: stdio for subprocess clients, streamable-http else."""
        logger.info("Starting DesignPatternServer", extra={"transport": self._config.transport})
        transport = self._config.transport
        if transport == "stdio":
            await self._mcp.run_async(transport="stdio")
        elif transport == "streamable-http":
            await self._mcp.run_async(
                transport="streamable-http", host=self._config.host, port=self._config.port
            )
        else:
            raise ValueError(
                f"Invalid transport value: {transport!r}. Must be one of: 'stdio', 'streamable-http'."
            )


async def health_check(config_path: str | None = None) -> dict[str, Any]:
    """Offline readiness check: config, catalog integrity, variant catalog and index warm-up.

    Uses the deterministic offline embedder/reranker, so the check never touches the network.
    """
    server = DesignPatternServer(config_path, offline=True)
    report: dict[str, Any] = {"config": "ok", "catalog": "ok", "variants": "ok", "index": "ok"}
    catalog = load_catalog(
        Path(server._config.paths.pattern_directory), Path(server._config.paths.docs_directory)
    )
    variants = VariantsResource(catalog)
    index = await RetrievalIndex.build(
        catalog,
        OfflineHashEmbedder(),
        LexicalReranker(),
        server._config.retrieval,
        server._config.reranker.rerank_top_n,
        rerank_text=server._config.reranker.rerank_text,
    )
    hits = await index.retrieve(statement="bound the latency of a synchronous call", constraints=[], scope="object")
    report.update(
        {
            "records": len(catalog.records),
            "ordered_records": len(catalog.order),
            "language_files": sum(len(record.language_implementations) for record in catalog.records.values()),
            "variant_languages": len(variants.payload()),
            "index_documents": len(catalog.records),
            "index_probe_hits": len(hits),
        }
    )
    return report


async def server_main(
    config_path: str | None = None,
    *,
    transport: str | None = None,
    host: str | None = None,
    port: int | None = None,
    offline: bool = False,
) -> None:
    """Entry point: resolve config, construct the server, run it; exit(1) on startup failure."""
    resolved_config = (
        os.environ.get("DESIGN_PATTERN_CONFIG_PATH") or config_path or ConfigManager.DEFAULT_CONFIG_PATH
    )
    resolved_config = os.path.abspath(os.path.expanduser(resolved_config))

    try:
        logger.info(f"Starting DesignPatternServer, using config: {resolved_config}")
        server = DesignPatternServer(
            config_path=resolved_config, transport=transport, host=host, port=port, offline=offline
        )
        await server.run()
    except ValueError as exc:
        logger.critical(f"Invalid configuration: {exc}")
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        logger.critical(f"Failed to start MCP server: {exc}")
        print(f"Error: Failed to start MCP server: {exc}", file=sys.stderr)
        sys.exit(1)
