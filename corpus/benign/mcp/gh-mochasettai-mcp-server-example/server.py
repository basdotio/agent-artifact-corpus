from fastmcp import FastMCP
from sonnylabs_py import SonnyLabsClient

client = SonnyLabsClient(
    api_token="YOUR_API_KEY",
    analysis_id="YOUR_ANALYSIS_ID",
    base_url="https://sonnylabs-service.onrender.com"
)

mcp = FastMCP("My MCP Server")

@mcp.tool()
def add(a: int, b: int, sidenote: str) -> int:
    input_result = client.analyze_text(sidenote, scan_type="input")
    print(f"SonnyLabs input analysis: {input_result}")

    result = a + b

    output_result = client.analyze_text(str(result), scan_type="output", tag=input_result["tag"])
    print(f"SonnyLabs output analysis: {output_result}")

    return result

mcp.run()