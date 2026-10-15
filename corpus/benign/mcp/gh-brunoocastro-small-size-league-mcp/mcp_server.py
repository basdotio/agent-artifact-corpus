from functools import lru_cache
from logging import getLogger

import uvicorn
from fastapi.responses import PlainTextResponse
from fastmcp import FastMCP
from fastmcp.tools import Tool
from requests import Request

import config
from settings import MCP_Settings
from tools import ssl_search_tool, tdp_search_tool

logger = getLogger(__name__)


# Create MCP server
mcp = FastMCP("small-size-league-mcp")


mcp.add_tool(Tool.from_function(tdp_search_tool, name="TDP Search Engine"))
mcp.add_tool(
    Tool.from_function(ssl_search_tool, name="Small Size League Content Search")
)


# Setup the resources
@mcp.resource("full-text://urls")
@lru_cache(maxsize=128)
async def get_website_urls():
    """
    Retrieve the full list of website URLs.
    This function reads URLs from a file specified in the configuration.
    The file is expected to contain one URL per line.
    """
    with open(config.URLS_FILE_PATH, "r") as file:
        urls = file.readlines()
    urls = [url.strip() for url in urls]
    logger.info(f"Retrieved {len(urls)} URLs from file: {config.URLS_FILE_PATH}")
    return urls


@mcp.resource("full-text://website")
@lru_cache(maxsize=128)
async def get_full_website_text():
    """
    Retrieve the full text of the RoboCUP SSL website.
    This function reads the full text from a file specified in the configuration.
    The file is expected to contain the complete text of the website.
    """
    with open(config.FULL_WEBSITE_FILE_PATH, "r") as file:
        full_website_text = file.read()

    logger.info(
        f"Retrieved full website text from file: {config.FULL_WEBSITE_FILE_PATH}"
    )
    logger.info(f"Full website text length: {len(full_website_text)} characters")
    logger.info(f"Full website text preview: {full_website_text[:100]}")
    # Ensure the text is not empty
    if not full_website_text:
        logger.warning("Full website text is empty.")
        return "No website text found. The tool didn't find any website text."

    # Return the full website text
    logger.info(f"Full website text length: {len(full_website_text)} characters")
    return full_website_text


@mcp.resource("full-text://rules")
@lru_cache(maxsize=128)
async def get_full_rules_text():
    """
    Retrieve the full text of the RoboCUP SSL rules.
    This function reads the full text from a file specified in the configuration.

    Returns:
        str: The full text of the RoboCUP SSL rules.
    """
    with open(config.FULL_RULES_FILE_PATH, "r") as file:
        full_rules_text = file.read()

    if not full_rules_text:
        logger.warning("Full rules text is empty.")
        return "No rules text found. The tool didn't find any rules text."

    return full_rules_text


# @mcp.resource("full-text://repository")
# @lru_cache(maxsize=128)
# async def get_full_repository_text():
#     """
#     Retrieve the full text of the RoboCUP SSL repository.
#     This function reads the full text from a file specified in the configuration.
#     """
#     with open(config.FULL_REPOSITORY_FILE_PATH, "r") as file:
#         full_repository_text = file.read()

#     if not full_repository_text:
#         logger.warning("Full repository text is empty.")
#         return "No repository text found. The tool didn't find any repository text."

#     return full_repository_text


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> PlainTextResponse:
    return PlainTextResponse("OK")


if __name__ == "__main__":
    settings = MCP_Settings()

    http_app = mcp.http_app(transport=settings.TRANSPORT_TYPE.value)

    print(
        f"Starting MCP server on {settings.HOST}:{settings.PORT} with transport {settings.TRANSPORT_TYPE.value}"
    )
    uvicorn.run(http_app, host=settings.HOST, port=settings.PORT, log_level="trace")
