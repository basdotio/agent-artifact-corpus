"""Shared logic, reused by every episode: connect to the AgentCore Gateway over
MCP and run a Strands + Claude agent against whatever tools the Gateway exposes.

Used by:
  • app.py        — deployed to AgentCore Runtime
  • run_local.py  — quick local dev run

The agent declares NO tools of its own. It discovers them from the Gateway, so
the same code works for every episode — the tools change, the agent doesn't.

Override the system prompt per episode with the AGENT_SYSTEM_PROMPT env var.
"""

import os

from mcp.client.streamable_http import streamablehttp_client
from strands import Agent
from strands.tools.mcp.mcp_client import MCPClient

from cognito_auth import get_bearer_token

# Switch between Anthropic direct API and AWS Bedrock by setting MODEL_PROVIDER.
MODEL_PROVIDER     = os.environ.get("MODEL_PROVIDER", "anthropic")
ANTHROPIC_MODEL_ID = os.environ.get("ANTHROPIC_MODEL_ID", "claude-sonnet-4-5-20250929")
BEDROCK_MODEL_ID   = os.environ.get("BEDROCK_MODEL_ID", "eu.amazon.nova-pro-v1:0")

DEFAULT_SYSTEM_PROMPT = (
    "You are a helpful assistant. Use the available tools to look up real "
    "information before answering. Be concise and never invent data."
)


def _model():
    if MODEL_PROVIDER == "bedrock":
        from strands.models.bedrock import BedrockModel
        return BedrockModel(
            model_id=BEDROCK_MODEL_ID,
            region_name=os.environ.get("AWS_REGION", "us-east-1"),
        )
    from strands.models.anthropic import AnthropicModel
    return AnthropicModel(
        client_args={"api_key": os.environ["ANTHROPIC_API_KEY"]},
        model_id=ANTHROPIC_MODEL_ID,
        max_tokens=1024,
    )


def _mcp_client() -> MCPClient:
    """MCP client pointed at the Gateway, authenticated with a fresh Cognito JWT."""
    token = get_bearer_token()
    gateway_url = os.environ["GATEWAY_URL"]
    return MCPClient(
        lambda: streamablehttp_client(
            gateway_url, headers={"Authorization": f"Bearer {token}"}
        )
    )


def list_tools() -> list[str]:
    """Return the names of the tools the Gateway currently exposes."""
    with _mcp_client() as mcp_client:
        return [t.tool_name for t in mcp_client.list_tools_sync()]


def run_agent(prompt: str, verbose: bool = False) -> str:
    """Run one prompt end-to-end and return the agent's final text."""
    system_prompt = os.environ.get("AGENT_SYSTEM_PROMPT", DEFAULT_SYSTEM_PROMPT)
    with _mcp_client() as mcp_client:
        tools = mcp_client.list_tools_sync()
        if verbose:
            print(f"Gateway exposed {len(tools)} tool(s): "
                  + ", ".join(t.tool_name for t in tools))
        agent = Agent(model=_model(), tools=tools, system_prompt=system_prompt)
        return str(agent(prompt))
