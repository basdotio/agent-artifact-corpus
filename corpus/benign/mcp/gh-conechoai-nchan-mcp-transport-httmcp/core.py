import base64
import logging
import json
import uuid
from typing import Any
from fastapi import FastAPI, Header, Response
from mcp.types import *
from mcp.server.fastmcp import FastMCP, Context
from mcp.server.fastmcp.server import _convert_to_content
from mcp.server.lowlevel.server import request_ctx, RequestContext
import httpx
from fastapi.routing import APIRouter
from openapiclient import OpenAPIClient


logger = logging.getLogger(__name__)



class HTTMCP(FastMCP):

    def __init__(
        self, name: str | None = None,
        instructions: str | None = None,
        publish_server: str | None = None,
        api_prefix: str = "",
        **settings: Any
    ):
        self._publish_server = publish_server
        self.api_prefix = api_prefix
        super().__init__(name, instructions, **settings)

    async def publish_to_channel(self, channel_id: str, message: dict, event: str = "message") -> bool:
        """Publish a message to an nchan channel."""
        async with httpx.AsyncClient() as client:
            # In a real scenario, you'd need the actual URL of your nchan server
            headers = {
                "Content-Type": "application/json",
                "X-EventSource-Event": event,
            }
            try:
                data = message
                if isinstance(message, dict):
                    data = json.dumps(message)
                elif isinstance(message, BaseModel):
                    data = message.model_dump_json()
                response = await client.post(
                    f"{self._publish_server}/mcp/{self.name}/{channel_id}", 
                    data=data,
                    headers=headers
                )
                return response.status_code == 200
            except Exception as e:
                logger.error(f"Error publishing to channel: {str(e)}")
                return False

    @property
    def router(self) -> APIRouter:
        router = APIRouter(prefix=self.api_prefix if self.api_prefix else f"/mcp/{self.name}")
        router.add_api_route("/", self.start_session, methods=["GET"])
        router.add_api_route("/endpoint", self.send_endpoint, methods=["GET"])
        router.add_api_route("/initialize", self.handle_request, methods=["POST"])
        for path in [
            "/",  # for streamable http transport
            "/resources/list", "/resources/read", "/resources/templates/list",
            "/prompts/list", "/prompts/get",
            "/tools/list", "/tools/call",
            "/ping", "/notifications/initialized", "/notifications/cancelled",
        ]:
            router.add_api_route(path, self.handle_request, methods=["POST"])
        return router
    
    async def handle_request(
        self,
        message: JSONRPCMessage,
        x_mcp_session_id: Annotated[str | None, Header()] = None,
        mcp_session_id: Annotated[str | None, Header()] = None,  # streamable http transport using this header
    ):
        token = None
        jsonrpc_response = None

        try:
            requst_id = message.root.id if hasattr(message.root, "id") else None
            validated_request = ClientRequest.model_validate(
                message.root.model_dump(
                    by_alias=True, mode="json", exclude_none=True
                )
            )
            # Set our global state that can be retrieved via
            # app.get_request_context()
            meta = validated_request.root.params.meta if validated_request.root.params else None
            # store session_id in meta
            if meta:
                meta.session_id = x_mcp_session_id or mcp_session_id
            token = request_ctx.set(
                RequestContext(
                    message.root.id,
                    meta,
                    None,
                    None,
                )
            )

            response = None
            typ = type(validated_request.root)
            if typ == InitializeRequest:
                options = self._mcp_server.create_initialization_options()
                response = InitializeResult(
                    protocolVersion=LATEST_PROTOCOL_VERSION,
                    capabilities=options.capabilities,
                    serverInfo=Implementation(
                        name=options.server_name,
                        version=options.server_version,
                    ),
                    instructions=options.instructions,
                )
            else:
                handler = self._mcp_server.request_handlers.get(typ, None) or self._mcp_server.notification_handlers.get(None)
                if not handler:
                    raise Exception(f"Handler not found for request of type {typ.__name__}")
                response = await handler(validated_request.root)

            if response is not None:
                jsonrpc_response = JSONRPCResponse(
                    jsonrpc="2.0",
                    id=requst_id,
                    result=response.model_dump(
                        by_alias=True, mode="json", exclude_none=True
                    ),
                )
        except Exception as err:
            error = ErrorData(code=0, message=str(err), data=None)
            jsonrpc_response = JSONRPCResponse(
                jsonrpc="2.0",
                id=requst_id,
                error=error.model_dump(
                    by_alias=True, mode="json", exclude_none=True
                ),
            )
        finally:
            # Reset the global state after we are done
            if token is not None:
                request_ctx.reset(token)
            if jsonrpc_response:
                logger.debug(f"Response: {jsonrpc_response.model_dump_json()}")
                return Response(
                    content=jsonrpc_response.model_dump_json(),
                    media_type="application/json",
                    status_code=200,
                )
            else:
                return Response(status_code=204)

    async def start_session(self):
        session_id = str(uuid.uuid4())
        return Response(
            status_code=200,
            headers={
                "X-Accel-Redirect": f"/internal/{self.name}/{session_id}",
                "X-Accel-Buffering": "no"
            }
        )

    async def send_endpoint(
        self, x_mcp_session_id: Annotated[str | None, Header()] = None,
        x_mcp_transport: Annotated[str | None, Header()] = None,
    ):
        if x_mcp_transport == "sse":
            await self.publish_to_channel(x_mcp_session_id, f"/mcp/{self.name}/{x_mcp_session_id}", "endpoint")


class OpenAPITool(BaseModel):
    name: str
    description: str
    parameters: dict

    @classmethod
    def from_openapi(cls, tool: dict) -> "OpenAPITool":
        return cls(
            name=tool["function"].get('name', ''),
            description=tool["function"].get('description', ''),
            parameters=tool["function"].get('parameters', {}),
        )

class OpenAPIToolManager:
    """Manages FastMCP tools."""

    def __init__(self, client: Any):
        self.client = client
        self._tools: dict[str, Tool] = {
            tool["function"].get('name', ''): OpenAPITool.from_openapi(tool)
            for tool in self.client.tools
        }

    def list_tools(self) -> list[Tool]:
        """List all registered tools."""
        print(f"Tools: {self._tools}")
        return list(self._tools.values())

    async def call_tool(
        self, name: str, arguments: dict, context: "Context | None" = None
    ) -> Any:
        """Call a tool by name with arguments."""
        return await self.client(name, **arguments)


class OpenAPIMCP(HTTMCP):
    def __init__(
        self, api: OpenAPIClient, client: Any,
        name: str | None = None,
        publish_server: str | None = None,
        api_prefix: str = "",
        **settings: Any,
    ):
        self.api = api
        self.client = client
        instructions = api.definition.get('info', {}).get('description', '')
        if not name:
            api_title = api.definition.get('info', {}).get('title', '')
            api_version = api.definition.get('info', {}).get('version', '')
            name = f"{api_title}MCP_{api_version}" if api_version else f"{api_title}"
            # Replace spaces, hyphens, dots and other special characters
            name = ''.join(c for c in name if c.isalnum())

        self._publish_server = publish_server
        self.api_prefix = api_prefix
        super().__init__(name, instructions, publish_server, api_prefix, **settings)
        self._tool_manager = OpenAPIToolManager(client)

    @classmethod
    async def from_openapi(cls, definition: str, name: str | None = None, publish_server: str | None = None, **kwargs) -> "OpenAPIMCP":
        """
        Create an MCP server from an OpenAPI definition.

        :param definition: The OpenAPI definition as a string.
        :param name: The name of the MCP server.
        :param publish_server: The URL of the Nchan server for publishing messages.
        :param kwargs: Additional settings for the MCP server (passed to httox.AsyncClient).
        :return: An instance of OpenAPIMCP.
        """
        api = OpenAPIClient(definition=definition)
        # pass the timeout, proxies, etc. to the client
        client = await api.AsyncClient(**kwargs).__aenter__()  # type: ignore
        return cls(api, client, name=name, publish_server=publish_server)