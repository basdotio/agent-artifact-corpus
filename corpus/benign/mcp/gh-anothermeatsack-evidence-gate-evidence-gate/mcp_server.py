"""Optional MCP tools. Lazy model loading keeps protocol startup lightweight."""
import contextlib
import sys
import threading
from .core import Engine, MLXBackend


def run(model=None, revision=None, device=None):
    from mcp.server.fastmcp import FastMCP
    mcp = FastMCP("Evidence Gate")
    engine = None
    lock = threading.Lock()

    def get_engine():
        nonlocal engine
        with lock:
            if engine is None:
                with contextlib.redirect_stdout(sys.stderr):
                    engine = Engine(MLXBackend(model, revision, device))
        return engine

    @mcp.tool()
    def local_decide(state: str, question: str, choices: dict[str, str], threshold: float = 0.8) -> dict:
        """Classify short input locally. Returns a proposal and review status; does not execute actions. Probabilities are unvalidated for your task."""
        return get_engine().decide({"state": state, "question": question, "choices": choices, "threshold": threshold})

    @mcp.tool()
    def check_evidence(claim: str, sources: list[dict[str, str]], threshold: float = 0.8) -> dict:
        """Assess claim support in supplied short source passages. Each source needs text; title/url/locator are optional attribution. Does not fetch papers or prove scientific validity."""
        return get_engine().evidence({"claim": claim, "sources": sources, "threshold": threshold})

    mcp.run(transport="stdio")
