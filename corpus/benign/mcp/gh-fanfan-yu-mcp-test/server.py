import asyncio
import logging
import yaml
import os

import redis

from mcp import stdio_server
from mcp.server import Server
from mcp.types import Tool, TextContent

def load_config():
    # read config.yaml
    config_path = os.path.join(os.path.dirname(__file__), "config.yaml")
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # extract redis config
    redis_config = config.get("redis", {})
    return redis_config

# build redis client
def build_redis_client():
    conf = load_config()
    redisClient = redis.Redis(
        host=conf.get("host", "localhost"),
        port=conf.get("port", 6379),
        password=conf.get("password", ''),
        decode_responses=conf.get("decode_responses", True)
    )
    if not redisClient.ping():
        raise ConnectionError("Failed to connect to Redis")

    return redisClient

logger = logging.getLogger(__name__)

app = Server("mcp_demo")

# singleton pattern
client = build_redis_client()

@app.list_tools()
async def list_tools() -> list[Tool]:
    logger.info("start to list tools.")
    return [
        Tool(
            name="redis_execution",
            description="Execute the redis command.",
            inputSchema={
                "type": "object",
                "properties": {
                    "input": {
                        "type": "string",
                        "description": "The input is the redis command to be executed."}
                },
                "required": ["input"]
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    logger.info("start to call tool.")

    if name != "redis_execution":
        raise ValueError("Tool not found")

    redis_execution_sql = arguments.get("input")
    if not redis_execution_sql:
        raise ValueError("Execution sql is required")

    parts = redis_execution_sql.split()
    if len(parts) < 2:
        raise ValueError("Invalid redis command")
    command = parts[0].upper()
    args = parts[1:]

    try:
        client.execute_command(command, *args)
        return [TextContent(type="text", text=f"Execute sql successfully.")]
    except redis.exceptions.ResponseError as e:
        return [TextContent(type="text", text=f"Error executing sql: {str(e)}")]


async def main():
    logger.info("Start mcp server.")
    async with stdio_server() as (read_stream, write_stream):
        try:
            await app.run(
                read_stream,
                write_stream,
                app.create_initialization_options()
            )
        except Exception as e:
            logger.error(f"Server error: {str(e)}", exc_info=True)
            raise

if __name__ == "__main__":
    asyncio.run(main())
