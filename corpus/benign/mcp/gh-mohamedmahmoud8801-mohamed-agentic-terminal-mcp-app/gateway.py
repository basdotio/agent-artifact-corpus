from fastmcp import FastMCP
from fastmcp.server import create_proxy
mcp = FastMCP()


@mcp.tool()
async def fetch():
    '''Use this tool to fetch data from a source.'''

    # Simulate fetching data from a source
    ''' You can make some API calls here or fetch data from a database '''
    return {"data": "Hello, MCP!"}

@mcp.tool()
async def process(path:str):
    '''Use this tool to process the fetched data.'''

    # Simulate processing the fetched data
    ''' You can perform some data transformations here '''
    return {"processed_data": "Data has been processed! at path: " + path}


# Mount the tools to the MCP instance
mcp.mount(
    create_proxy({
        "mcpServers": {
            "ddg_mcp": {
                "command": "uvx",
                "args": ["duckduckgo-mcp-server"],
            }
        }
    })
)

mcp.mount(
    create_proxy({
        "mcpServers": {
            "agentic_terminal": {
                "command": "uvx",
                "args": [
                    "--from",
                    "mohamed-agentic-terminal==0.1.0",
                    "agentic_terminal",
                ],
            }
        }
    })
)


if __name__ == "__main__":
    # Run the MCP server
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8001)