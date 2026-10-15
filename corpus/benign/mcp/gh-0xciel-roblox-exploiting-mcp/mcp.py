from mcp.server.fastmcp import FastMCP
import requests
mcp = FastMCP("Roblox")
@mcp.tool()
def execute(code: str) -> str:
    """
    Executes Luau code in the live Roblox game and returns the result.
    IMPORTANT: The code MUST end with a `return <string>` statement to capture the output.
    """
    try:
        response = requests.post("http://localhost:8080/execute", data=code)
        return response.text
    except Exception as e:
        return f"Error connecting to server: {e}"

if __name__ == "__main__":
    mcp.run()
