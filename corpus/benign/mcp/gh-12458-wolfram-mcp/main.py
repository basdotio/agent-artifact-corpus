from fastmcp import FastMCP
from wolframclient.evaluation import WolframLanguageSession
from wolframclient.language import wlexpr
from wolframclient.exception import (
    WolframLanguageException,
    WolframKernelException,
    WolframEvaluationException,
    RequestException,
    SocketException
)

# Initialize FastMCP server
eval_mcp = FastMCP("Wolfram REPL MCP")

# Start a persistent Wolfram Language session
session = WolframLanguageSession()

@eval_mcp.tool
def eval_wolfram(code: str) -> str:
    """
    Evaluate a Wolfram Language expression and return its result as a string.
    Args:
        code (str): A string representing a Wolfram Language expression.
    Returns:
        A string representing the result of the Wolfram Language expression.
    Raises:
        WolframClientException: If there is an error in the Wolfram Language expression.
        Exception: If there is an unexpected error.
    """
    try:
        expr = wlexpr(code)
        result = session.evaluate(expr)
        return repr(result)
    except WolframKernelException as e:
        return f"Wolfram Kernel Error: {e}"
    except WolframEvaluationException as e:
        return f"Wolfram Evaluation Error: {e}"
    except RequestException as e:
        return f"Wolfram Request Error: {e}"
    except SocketException as e:
        return f"Wolfram Socket Error: {e}"
    except WolframLanguageException as e:
        return f"Wolfram Language Error: {e}"
    except Exception as e:
        return f"Unexpected Error: {e}"

@eval_mcp.tool
def terminate_session() -> str:
    """Terminate the Wolfram Language session and free resources."""
    try:
        session.terminate()
        return "Wolfram session terminated successfully."
    except Exception as e:
        return f"Error terminating session: {e}"

if __name__ == "__main__":
    # Run the MCP server (default STDIO transport)
    eval_mcp.run()
