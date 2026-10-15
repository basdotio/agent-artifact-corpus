import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Sequence

import mcp.types as types
from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
from pydantic import AnyUrl
from scraper import HuggingFacePapersScraper

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

server = Server("huggingface-daily-papers")
scraper = HuggingFacePapersScraper()

@server.list_resources()
async def handle_list_resources() -> list[types.Resource]:
    return [
        types.Resource(
            uri=AnyUrl("papers://today"),
            name="Today's Papers",
            description="HuggingFace daily papers for today",
            mimeType="application/json",
        ),
        types.Resource(
            uri=AnyUrl("papers://yesterday"),
            name="Yesterday's Papers", 
            description="HuggingFace daily papers for yesterday",
            mimeType="application/json",
        ),
    ]

@server.read_resource()
async def handle_read_resource(uri: AnyUrl) -> str:
    try:
        logger.info(f"Reading resource: {uri}")
        
        if uri.scheme != "papers":
            raise ValueError(f"Unsupported URI scheme: {uri.scheme}")
        
        if uri.host == "today":
            papers = scraper.get_today_papers()
            return json.dumps(papers, ensure_ascii=False, indent=2)
        elif uri.host == "yesterday": 
            papers = scraper.get_yesterday_papers()
            return json.dumps(papers, ensure_ascii=False, indent=2)
        else:
            raise ValueError(f"Unknown resource: {uri.host}")
    except Exception as e:
        logger.error(f"Error reading resource {uri}: {e}")
        raise

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="get_papers_by_date",
            description="Get HuggingFace daily papers for a specific date",
            inputSchema={
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Date in YYYY-MM-DD format",
                        "pattern": r"^\d{4}-\d{2}-\d{2}$"
                    }
                },
                "required": ["date"]
            },
        ),
        types.Tool(
            name="get_today_papers", 
            description="Get today's HuggingFace daily papers",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        types.Tool(
            name="get_yesterday_papers",
            description="Get yesterday's HuggingFace daily papers", 
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
    ]

@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict[str, Any] | None
) -> list[types.TextContent]:
    try:
        logger.info(f"Calling tool: {name} with arguments: {arguments}")
        
        if name == "get_papers_by_date":
            if not arguments or "date" not in arguments:
                raise ValueError("Date is required")
            
            date = arguments["date"]
            papers = scraper.get_papers_by_date(date)
            
            if not papers:
                return [
                    types.TextContent(
                        type="text",
                        text=f"No papers found for {date}. Please check if the date is correct and has published papers."
                    )
                ]
            
            return [
                types.TextContent(
                    type="text",
                    text=f"Found {len(papers)} papers for {date}:\n\n" + 
                         "\n".join([
                             f"Title: {paper['title']}\n"
                             f"Authors: {', '.join(paper['authors'])}\n" 
                             f"Abstract: {paper['abstract']}\n"
                             f"URL: {paper['url']}\n"
                             f"PDF: {paper['pdf_url']}\n"
                             f"Votes: {paper['votes']}\n"
                             f"Submitted by: {paper['submitted_by']}\n"
                             + "-" * 50
                             for paper in papers
                         ])
                )
            ]
        
        elif name == "get_today_papers":
            papers = scraper.get_today_papers()
            today = datetime.now().strftime("%Y-%m-%d")
            
            if not papers:
                return [
                    types.TextContent(
                        type="text",
                        text=f"No papers found for today ({today}). Papers might not be published yet or there could be a network issue."
                    )
                ]
            
            return [
                types.TextContent(
                    type="text", 
                    text=f"Today's Papers ({today}) - Found {len(papers)} papers:\n\n" +
                         "\n".join([
                             f"Title: {paper['title']}\n"
                             f"Authors: {', '.join(paper['authors'])}\n"
                             f"Abstract: {paper['abstract']}\n" 
                             f"URL: {paper['url']}\n"
                             f"PDF: {paper['pdf_url']}\n"
                             f"Votes: {paper['votes']}\n"
                             f"Submitted by: {paper['submitted_by']}\n"
                             + "-" * 50
                             for paper in papers
                         ])
                )
            ]
        
        elif name == "get_yesterday_papers":
            papers = scraper.get_yesterday_papers()
            yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
            
            if not papers:
                return [
                    types.TextContent(
                        type="text",
                        text=f"No papers found for yesterday ({yesterday}). There might be no papers published that day or a network issue."
                    )
                ]
            
            return [
                types.TextContent(
                    type="text",
                    text=f"Yesterday's Papers ({yesterday}) - Found {len(papers)} papers:\n\n" +
                         "\n".join([
                             f"Title: {paper['title']}\n"
                             f"Authors: {', '.join(paper['authors'])}\n"
                             f"Abstract: {paper['abstract']}\n"
                             f"URL: {paper['url']}\n" 
                             f"PDF: {paper['pdf_url']}\n"
                             f"Votes: {paper['votes']}\n"
                             f"Submitted by: {paper['submitted_by']}\n"
                             + "-" * 50
                             for paper in papers
                         ])
                )
            ]
        
        else:
            raise ValueError(f"Unknown tool: {name}")
            
    except Exception as e:
        logger.error(f"Error calling tool {name}: {e}")
        return [
            types.TextContent(
                type="text",
                text=f"Error: {str(e)}"
            )
        ]


async def main():
    from mcp.server.stdio import stdio_server
    
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream, 
            InitializationOptions(
                server_name="huggingface-daily-papers",
                server_version="0.1.4",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


def cli():
    """Command line interface entry point for uvx."""
    asyncio.run(main())


if __name__ == "__main__":
    cli()
