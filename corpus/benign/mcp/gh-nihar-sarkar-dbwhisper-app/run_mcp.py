import logging
from app.server import create_mcp_server
from app.util.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

mcp = create_mcp_server()

if __name__ == "__main__":
    mcp.run(transport="http", host=settings.MCP_SERVER_HOST, port=settings.MCP_SERVER_PORT)
