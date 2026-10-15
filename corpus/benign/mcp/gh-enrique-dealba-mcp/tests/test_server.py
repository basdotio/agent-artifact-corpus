import sys
from types import SimpleNamespace

import pytest


# Provide a minimal stub for the fastmcp package so that server can be imported
class DummyMCP(SimpleNamespace):
    def tool(self, func=None):
        def decorator(f):
            return f

        # Allow use as @mcp.tool() or direct call
        if func is None:
            return decorator
        return decorator(func)


sys.modules["fastmcp"] = SimpleNamespace(FastMCP=lambda name: DummyMCP())

import server


def test_add():
    assert server.add(2, 3) == 5


def test_multiply():
    assert server.multiply(2, 3) == 6


def test_divide():
    assert server.divide(6, 3) == 2


def test_divide_by_zero():
    with pytest.raises(ValueError):
        server.divide(1, 0)
