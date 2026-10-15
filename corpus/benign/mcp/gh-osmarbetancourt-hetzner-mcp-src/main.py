import os
import importlib
import inspect
from dotenv import load_dotenv
from hcloud import Client
from hcloud.images import Image
from hcloud.server_types import ServerType
from fastmcp import FastMCP
import traceback

# Load .env and get Hetzner API token
load_dotenv()
HETZNER_API_TOKEN = os.getenv("HETZNER_API_TOKEN")
if not HETZNER_API_TOKEN:
    raise Exception("HETZNER_API_TOKEN not set in .env")

client = Client(token=HETZNER_API_TOKEN)

def main():

    mcp = FastMCP(name="Hetzner MCP Server")
    print("[MCP SERVER] Starting Hetzner MCP Server...")

    @mcp.tool
    def echo(text: str) -> str:
        """Echoes back the input text."""
        return text

    @mcp.tool
    def call_hetzner(code: str) -> dict:
        """
        Executes any Python code using the Hetzner SDK client. WARNING: This is highly flexible but unsafe—use only in trusted, isolated environments (e.g., Docker)!
        Example: client.servers.create(name="myserver", server_type="cx11", image="ubuntu-20.04")
        Returns result or error.
        """
        try:
            code_stripped = code.strip()
            allowed_globals = {"client": client}
            result = eval(code_stripped, allowed_globals, {})
            if hasattr(result, "to_dict"):
                return {"ok": True, "result": result.to_dict()}
            return {"ok": True, "result": str(result)}
        except Exception as e:
            return {"ok": False, "error": str(e), "traceback": traceback.format_exc()}

    @mcp.tool
    def mcp_health() -> dict:
        """MCP health check endpoint."""
        return {"status": "ok"}

    @mcp.tool
    def hetzner_help() -> dict:
        """
        Returns a detailed list of all available Hetzner SDK resources, their public methods, signatures, and docstrings.
        Useful for LLMs and users to discover what actions are possible with the SDK.
        """
        help_info = {}
        for attr in dir(client):
            if attr.startswith("_"):
                continue
            resource = getattr(client, attr)
            # Only include resource clients (skip methods, primitives)
            if not hasattr(resource, "__class__") or not resource.__class__.__name__.endswith("Client"):
                continue
            methods = {}
            for meth_name in dir(resource):
                if meth_name.startswith("_"):
                    continue
                meth = getattr(resource, meth_name)
                if not callable(meth):
                    continue
                try:
                    sig = str(inspect.signature(meth))
                except Exception:
                    sig = "(unknown signature)"
                doc = inspect.getdoc(meth) or ""
                methods[meth_name] = {
                    "signature": sig,
                    "doc": doc[:200] + ("..." if doc and len(doc) > 200 else "")
                }
            if methods:
                help_info[attr] = {
                    "client_class": resource.__class__.__name__,
                    "methods": methods
                }
        return help_info

    if __name__ == "__main__":
        mcp.run()

main()
