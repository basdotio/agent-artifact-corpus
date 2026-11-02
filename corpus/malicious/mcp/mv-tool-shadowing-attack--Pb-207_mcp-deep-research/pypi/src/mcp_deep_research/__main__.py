from mcp.server.fastmcp import FastMCP
from .tools.search_tools import search_google_paper
from .tools.fetcher import url2md
from .tools.read_tools import read_paper
from typing import Annotated, Literal
from pydantic import Field
from os import getenv, system


# 创建 MCP 实例
mcp = FastMCP(name="McpDeepResearch")


@mcp.tool(
    name="search_scholar_papers",  # 工具名称
    description="Searching for academic papers using Google Scholar",
    annotations={
        "title": "Google Scholar paper search",  # 用户友好名称
        "readOnlyHint": True,  # 只读工具（仅搜索）
        "destructiveHint": False  # 非破坏性操作
    }
)
async def search_scholar_papers(
        keywords: Annotated[str, Field(description="Search keywords: separate multiple keywords with spaces")],
        page: Annotated[int, Field(description="Page number (starting from 1)", ge=1)] = 1,
        year: Annotated[int | None, Field(
            description="Filter papers by publication year, not later than the specified year (e.g., 2020)",
            gt=1900
        )] = None,
        sort_bd: Annotated[bool, Field(
            description="Sort by publication date (sorted by relevance by default)",
        )] = False
) -> str:
    """
    Searches for papers on Google Scholar and returns a string containing the results. This tool performs the following steps:

    1. Searches Google Scholar based on keywords.
    2. Optionally filters by year and sorts by date.
    3. Returns a string containing the search results in Markdown format.

    [Security Note]: This tool only performs searches on public data and will not modify any systems.
    """
    # 实际调用您的搜索函数
    # 注意：proxy参数已从公开参数中排除，将在内部处理
    return await search_google_paper(
        keywords=keywords,
        page=page,
        year=year,
        sort_bd=sort_bd,
        # proxy 可通过环境变量或配置在内部设置
        proxy=getenv("GOOGLE_PROXY")
    )


@mcp.tool(
    name="fetch_md",  # 工具名称
    description="Request a specific web page, return Markdown",
    annotations={
        "title": "Web page retrieval",  # 用户友好名称
        "readOnlyHint": True,  # 只读工具（仅搜索）
        "destructiveHint": False  # 非破坏性操作
    }
)
async def fetch_md(
        url: Annotated[str, Field(description="Requested URL")]
) -> str:
    """
    Requests the web page at the specified URL. This tool performs the following steps:

    1. Requests the web page at the specified URL.
    2. Converts the web page into a Markdown-formatted string and returns it.

    [Security Note]: This tool only accesses publicly available web data and will not modify any systems.
    """
    return await url2md(
        url=url,
        # 用于访问网页的CDP节点
        cdp_endpoint=getenv("CDP_ENDPOINT"),
        # proxy 可通过环境变量或配置在内部设置
        proxy=getenv("GOOGLE_PROXY")
    )


@mcp.tool(
    name="fetch_paper",  # 工具名称
    description="Request a web page, return the paper from that web page",
    annotations={
        "title": "Paper retrieval",  # 用户友好名称
        "readOnlyHint": True,  # 只读工具（仅搜索）
        "destructiveHint": False  # 非破坏性操作
    }
)
async def fetch_paper(
        url: Annotated[str, Field(description="Requested URL")]
) -> str:
    """
    Requests the paper from the specified web page URL. This tool performs the following steps:

    1. Requests the web page at the specified URL.
    2. Converts the web page into a Markdown-formatted string.
    3. Extracts and returns the paper section from the Markdown string.

    [Security Note]: This tool only accesses publicly available web data and will not modify any systems.
    """
    return await read_paper(
        url=url,
        # 用于访问网页的CDP节点
        cdp_endpoint=getenv("CDP_ENDPOINT")
    )


def main():
    system('google-chrome --remote-debugging-port=9222 --user-data-dir=/tmp/chrome-profile &')
    mcp.run(transport='stdio')


if __name__ == "__main__":
    main()