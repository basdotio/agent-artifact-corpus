from typing import Any, cast, Generator
import tempfile
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from mini_agent import agentic_loop, Env
from typedefs import AssistantMessage, SystemMessage, UserMessage, TextMessageContent, UserTranscriptItem
import pydantic
import mcp
import mcp.types


class MockMcp:
    tool1 = mcp.types.Tool(name="Tool1", description="Tool1.desc", inputSchema={})
    resource1 = "resource://resource1/{input}"

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> mcp.types.CallToolResult:
        if name != MockMcp.tool1.name:
            raise ValueError("tool name")
        return mcp.types.CallToolResult(content=[mcp.types.TextContent(type="text", text="Tool1.result")], isError=False)

    async def list_resource_templates(self, cursor: str | None = None) -> mcp.types.ListResourceTemplatesResult:
        return mcp.types.ListResourceTemplatesResult(resourceTemplates=[
                mcp.types.ResourceTemplate(name="Resource1", uriTemplate=MockMcp.resource1),
            ])

    async def read_resource(self, uri: pydantic.AnyUrl) -> mcp.types.ReadResourceResult:
        schema = uri.scheme
        host = uri.host
        input = uri.path
        if schema == "resource" and host == "resource1":
            return mcp.types.ReadResourceResult(
                contents=[mcp.types.TextResourceContents(uri=uri, text=f"resource1.content:{input}")]
            )
        raise ValueError(f"Unknown resource: {str(uri)}")



@pytest.fixture
def env() -> Generator[Env, None, None]:
    mcp1 = cast(mcp.ClientSession, MockMcp())
    with tempfile.NamedTemporaryFile(mode='w') as f:
        yield Env(
            execute_tools=True,
            interactive=False,
            system_message=SystemMessage(content=[]),
            resources=[(MockMcp.resource1, mcp1)],
            tools=[(MockMcp.tool1, mcp1)],
            models={"model": "test_model", "digest-model": "test_digest_model"},
            model="model",
            transcript=[UserTranscriptItem(message=UserMessage(role="user", content=[TextMessageContent(text="Hello")]))],
            transcript_file=Path(f.name)
        )


class TestAgent:

    @pytest.mark.asyncio
    @patch("mini_agent.adapter.acompletion")
    async def test_basic(self, acompletion: MagicMock, env: Env) -> None:
        acompletion.return_value = AssistantMessage(id="id1", content=[
            TextMessageContent(text="world")], model="test")
        r = await agentic_loop(env)
        assert r[0].text == "world"
        acompletion.assert_called_once()

