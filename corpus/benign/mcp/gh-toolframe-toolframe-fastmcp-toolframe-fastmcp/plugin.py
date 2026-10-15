"""Toolframe's standalone FastMCP provider."""

from __future__ import annotations

from collections.abc import Sequence
from copy import deepcopy
from hashlib import sha256
from re import compile as compile_regex
from typing import Any

from fastmcp import FastMCP
from fastmcp.server.auth import AccessToken, TokenVerifier
from fastmcp.server.dependencies import get_access_token
from fastmcp.server.providers import Provider
from fastmcp.tools import Tool, ToolResult
from jsonschema.exceptions import ValidationError
from pydantic import PrivateAttr
from toolframe_sdk import (
    AuthorizationSpec,
    OwnedResource,
    Plugin,
    PluginDefinition,
    PluginError,
    RuntimeContext,
    validate,
)
from toolframe_sdk.http import HttpServer

_OWNER = compile_regex(r"[a-z][a-z0-9-]{0,63}\Z")
_RESOURCE_ID = compile_regex(r"[a-z][a-z0-9_-]{0,63}\Z")
_DEFAULT_INPUT_SCHEMA = {"type": "object"}


class _McpTool(Tool):
    """A FastMCP tool backed by one immutable Toolframe resource binding."""

    _owned_key: str = PrivateAttr()
    _method: str = PrivateAttr()
    _prepared_epoch: str = PrivateAttr()
    _context: RuntimeContext = PrivateAttr()
    _validation_schema: dict = PrivateAttr()

    def __init__(
        self,
        *,
        name: str,
        title: str | None,
        description: str | None,
        parameters: dict[str, Any],
        output_schema: dict[str, Any] | None,
        owned_key: str,
        method: str,
        prepared_epoch: str,
        context: RuntimeContext,
        validation_schema: dict,
    ) -> None:
        super().__init__(
            name=name,
            title=title,
            description=description,
            parameters=parameters,
            output_schema=output_schema,
        )
        self._owned_key = owned_key
        self._method = method
        self._prepared_epoch = prepared_epoch
        self._context = context
        self._validation_schema = validation_schema

    async def run(self, arguments: dict[str, Any]) -> ToolResult:
        arguments = dict(arguments)
        for key, schema in self.parameters.get("properties", {}).items():
            if key not in arguments and "default" in schema:
                arguments[key] = deepcopy(schema["default"])
        try:
            validate(self.parameters, arguments)
        except (ValidationError, TypeError, ValueError) as error:
            return _error_result("invalid_input", str(error))

        try:
            token = get_access_token()
            if token is None:
                raise PluginError(
                    "authentication_required", "MCP request authentication is required"
                )
            result = await self._context.resource_call(
                self._owned_key,
                self._method,
                arguments,
                epoch=self._prepared_epoch,
                access_context=token.token,
            )
        except PluginError as error:
            return _error_result(error.code, error.message)
        except Exception:  # noqa: BLE001 - keep implementation details off the wire
            return _error_result("internal_error", "Tool execution failed")

        if self._validation_schema:
            try:
                validate(self._validation_schema, result)
            except ValidationError, TypeError, ValueError:
                return _error_result(
                    "invalid_output", "Tool result does not match its declared schema"
                )

        try:
            if isinstance(result, dict):
                return ToolResult(structured_content=result)
            return ToolResult(content=result)
        except Exception:  # noqa: BLE001 - keep implementation details off the wire
            return _error_result("internal_error", "Tool result serialization failed")

    def to_mcp_tool(self, **overrides: Any):
        """Keep the resource title unchanged on the MCP wire."""
        overrides.setdefault("title", self.title)
        return super().to_mcp_tool(**overrides)


class _CatalogProvider(Provider):
    """Expose the provider's current immutable tool tuple to FastMCP."""

    def __init__(self) -> None:
        super().__init__()
        self._tools: tuple[_McpTool, ...] = ()

    def replace(self, tools: tuple[_McpTool, ...]) -> None:
        self._tools = tools

    async def _list_tools(self) -> Sequence[_McpTool]:
        token = get_access_token()
        permitted = set(token.claims.get("resources", ())) if token else set()
        return tuple(tool for tool in self._tools if tool._owned_key in permitted)


class _GatewayVerifier(TokenVerifier):
    """Accept only live request credentials minted by this provider's core."""

    def __init__(self, context: RuntimeContext):
        super().__init__()
        self.context = context

    async def verify_token(self, token: str) -> AccessToken | None:
        try:
            result = await self.context.mcp_access(token)
        except PluginError:
            return None
        actor = result["principal"]
        identity = actor.get("credential_id") or "public"
        return AccessToken(
            token=token,
            client_id=identity,
            subject=identity,
            scopes=list(actor["scopes"]),
            claims={"iss": result["issuer"], "resources": result["resources"]},
        )


class McpProvider(Plugin):
    """Serve the selected epoch of explicitly owned MCP tool resources."""

    def __init__(self, context: RuntimeContext):
        super().__init__(context)
        self.app: Any | None = None
        self.server: HttpServer | None = None
        self._catalog = _CatalogProvider()
        self._staged: dict[str, tuple[_McpTool, ...]] = {}
        self._active: tuple[_McpTool, ...] = ()
        self._epoch: str | None = None

    async def activate(self) -> None:
        mcp = FastMCP(
            "Toolframe",
            auth=_GatewayVerifier(self.context),
            providers=[self._catalog],
            dereference_schemas=False,
        )
        self.app = mcp.http_app(
            path="/mcp",
            transport="streamable-http",
            stateless_http=False,
        )
        self.server = HttpServer(self.app)
        await self.server.start()

    async def health(self) -> dict[str, Any]:
        return {
            "runtime": "ready",
            "business": "not_provided",
            "http_url": self.server.url if self.server else None,
            "epoch": self._epoch,
        }

    async def dispose(self) -> None:
        try:
            if self.server:
                await self.server.close()
        finally:
            await super().dispose()

    async def prepare(self, resources: list[OwnedResource], epoch: str):
        tools: list[_McpTool] = []
        keys: set[str] = set()
        names: set[str] = set()

        for owned in resources:
            resource = owned.resource
            if resource.kind != "mcp.tool":
                raise PluginError(
                    "unsupported_resource",
                    f"Unsupported resource kind: {resource.kind}",
                )
            if _OWNER.fullmatch(owned.owner) is None:
                raise PluginError("invalid_owner", f"Invalid tool owner: {owned.owner}")
            if _RESOURCE_ID.fullmatch(resource.id) is None:
                raise PluginError(
                    "invalid_tool_id",
                    f"Invalid tool id: {resource.id}",
                )

            key = owned.key
            if key in keys:
                raise PluginError(
                    "duplicate_resource", f"Duplicate owned resource: {key}"
                )
            keys.add(key)

            fullname = f"{owned.owner}__{resource.id}"
            name = fullname
            if len(name) > 128:
                name = f"{name[:115]}_{sha256(fullname.encode()).hexdigest()[:12]}"
            if name in names:
                raise PluginError(
                    "duplicate_name", f"Duplicate public tool name: {name}"
                )
            names.add(name)

            data = resource.data
            service = data.get("service")
            if not isinstance(service, str) or not service:
                raise PluginError(
                    "invalid_resource",
                    f"Tool service is missing for {key}",
                )
            method = data.get("method")
            if not isinstance(method, str) or not method:
                raise PluginError(
                    "invalid_resource",
                    f"Tool method is missing for {key}",
                )

            input_schema = data.get("input_schema", _DEFAULT_INPUT_SCHEMA)
            if not isinstance(input_schema, dict):
                raise PluginError(
                    "invalid_schema",
                    f"Tool input schema is invalid for {key}",
                )

            output_schema = data.get("output_schema")
            if (
                not isinstance(output_schema, dict)
                or output_schema.get("type") != "object"
            ):
                output_schema = None

            try:
                tool = _McpTool(
                    name=name,
                    title=resource.title,
                    description=data.get("description", resource.title),
                    parameters=deepcopy(input_schema),
                    output_schema=deepcopy(output_schema),
                    owned_key=key,
                    method=method,
                    prepared_epoch=epoch,
                    context=self.context,
                    validation_schema=deepcopy(data.get("output_schema", {})),
                )
            except Exception as error:  # noqa: BLE001 - normalize invalid descriptors
                raise PluginError(
                    "invalid_resource",
                    f"Invalid MCP tool resource {key}: {error}",
                ) from None
            tools.append(tool)

        self._staged[epoch] = tuple(tools)
        return {"epoch": epoch}

    async def commit(self, epoch: str):
        staged = self._staged.pop(epoch, None)
        if staged is None:
            raise PluginError("unknown_epoch", f"Unknown staged epoch: {epoch}")
        self._active = staged
        self._catalog.replace(staged)
        self._epoch = epoch
        return {"epoch": epoch}

    async def abort(self, epoch: str):
        self._staged.pop(epoch, None)
        return {"epoch": epoch}


def _error_result(code: str, message: str) -> ToolResult:
    return ToolResult(content={"code": code, "message": message}, is_error=True)


plugin = PluginDefinition(
    id="fastmcp",
    kind="provider",
    provider_kind="mcp",
    factory="toolframe_fastmcp.plugin:McpProvider",
    authorization=AuthorizationSpec(),
)
