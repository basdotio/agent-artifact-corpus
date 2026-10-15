from mcp.server.fastmcp import FastMCP

from app.tool.run_kubectx import tool_run_kubectx
from app.tool.run_kubectl import tool_run_kubectl

mcp = FastMCP("mcp-k8s-manager", "0.1.0")

@mcp.tool(
    description="Run a kubectx command. Make sure kubectx is installed and configured.",
    name="run_kubectx",
)
def run_kubectx(command: str) -> str:
    return tool_run_kubectx(command)

@mcp.tool(
    description="Run a kubectl command. Make sure kubectl is installed and configured. In case, you can use the run_kubectx tool to switch context before running this command.",
    name="run_kubectl",
)
def run_kubectl(command: str) -> str:
    return tool_run_kubectl(command)

@mcp.tool(
    description="Run a kubectl auth can i command to make sure if user can use some k8s verb on resources."
                "Make sure kubectl is installed and configured. In case, you can use the run_kubectx tool to switch context before running this command."
                "Before execute kubectl command make sure user has auth on that verb for the resource provided",
    name="run_kubectl_auth_can_i",
)
def run_kubectl_auth_can_i(command: str) -> str:
    return tool_run_kubectl(command)