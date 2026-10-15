#!/usr/bin/env python3

import logging
import os
import asyncio
import sys
from typing import Any

# --- Start of Logging Setup ---
# THIS MUST BE THE FIRST THING TO RUN
log_file_path = os.path.join(os.path.dirname(__file__), 'mcp_server.log')
logging.basicConfig(
    filename=log_file_path,
    filemode='w',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(funcName)s] - %(message)s'
)
logging.info("--- Log system initialised, server starting up... ---")
# --- End of Logging Setup ---

try:
    # --- Windows-specific Policies ---
    if sys.platform == "win32":
        try:
            # Set the asyncio policy for stdio stability on Windows
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
            logging.info("Successfully set asyncio policy to WindowsSelectorEventLoopPolicy")
        except Exception as e:
            logging.error(f"Failed to set asyncio policy: {e}", exc_info=True)
            raise  # Re-raise the exception to halt execution if this critical step fails
    # --------------------------------

    logging.info("Importing libraries... (This may take a moment)")
    from mcp.server import Server
    from mcp.server.models import InitializationOptions
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent, ServerCapabilities, ToolsCapability
    # --- The import is now here, at startup! ---
    from youtube_tool import get_youtube_transcript

    logging.info("Libraries imported successfully.")

    # Create the server instance
    server = Server("MCP-YouTube-Transcribe")
    logging.info("Server instance created.")


    @server.list_tools()
    async def handle_list_tools() -> list[Tool]:
        """List available tools."""
        logging.info("handle_list_tools called.")
        return [
            Tool(
                name="get_youtube_transcript",
                description="Search for a YouTube video and get its transcript. If no official transcript exists, generates one using Whisper.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query for the YouTube video (e.g., 'What is an API? by MuleSoft')"
                        },
                        "force_whisper": {
                            "type": "boolean",
                            "description": "Force the use of Whisper for transcription, even if an official transcript is available",
                            "default": False
                        }
                    },
                    "required": ["query"]
                }
            )
        ]


    @server.call_tool()
    async def handle_call_tool(name: str, arguments: dict[str, Any] | None) -> list[TextContent]:
        """Handle tool calls."""
        logging.info(f"handle_call_tool called for tool: {name}")
        if name != "get_youtube_transcript":
            logging.error(f"Unknown tool called: {name}")
            raise ValueError(f"Unknown tool: {name}")

        if not arguments:
            logging.error("Tool call missing arguments.")
            raise ValueError("Missing arguments")

        query = arguments.get("query")
        if not query:
            logging.error("Tool call missing required argument: query")
            raise ValueError("Missing required argument: query")

        force_whisper = arguments.get("force_whisper", False)

        try:
            # The import is no longer here. We just call the function directly.
            result = get_youtube_transcript(query=query, force_whisper=force_whisper)
            logging.info(f"youtube_tool returned with status: {result.get('status')}")

            if result.get("status") == "success":
                content = f"**Title:** {result['title']}\n**URL:** {result['url']}\n**Source:** {result['source']}\n\n**Transcript:**\n{result['transcript']}"
            else:
                content = f"**Error:** {result.get('message', 'Unknown error occurred')}"

            return [TextContent(type="text", text=content)]
        except Exception as e:
            logging.error(f"An exception occurred during tool execution: {str(e)}", exc_info=True)
            return [TextContent(type="text", text=f"**Error:** An unexpected error occurred: {str(e)}")]


    async def main():
        logging.info("Main function started.")
        # --- Add this for Windows stdio encoding ---
        if sys.platform == "win32":
            try:
                # Reconfigure stdin and stdout to use UTF-8
                sys.stdin.reconfigure(encoding='utf-8')
                sys.stdout.reconfigure(encoding='utf-8')
                logging.info("Successfully reconfigured stdin and stdout to use UTF-8 on Windows.")
            except Exception as e:
                logging.error(f"Failed to reconfigure stdio encoding: {e}", exc_info=True)
                raise  # Re-raise to halt if this fails
        # -------------------------------------------
        async with stdio_server() as (read_stream, write_stream):
            logging.info("Stdio server context entered.")

            capabilities = ServerCapabilities(tools=ToolsCapability(listChanged=False))

            logging.info("About to call server.run(). This should block and wait for requests.")
            await server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="MCP-YouTube-Transcribe",
                    server_version="1.0.0",
                    capabilities=capabilities
                ),
            )
            logging.warning("server.run() returned. This means the server loop has exited, which is unexpected.")
        logging.info("Stdio server context exited.")


    if __name__ == "__main__":
        logging.info("Executing main block.")
        try:
            asyncio.run(main())
        except Exception as e:
            # This will now catch errors from the main() function itself
            logging.error(f"A critical error occurred in main execution: {e}", exc_info=True)
            raise
        finally:
            logging.info("--- Server script finished ---")
            logging.shutdown()  # Ensure all logs are flushed

except Exception as e:
    # This will now catch errors from startup (imports, etc.)
    logging.error(f"A critical error occurred during initial setup: {e}", exc_info=True)
    logging.shutdown()
    raise
