"""Interactive Terminal CLI and Agent Loop for ArXivLens MCP."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from arxivlens.client import ArXivLensClient

load_dotenv()
console = Console()


# ============================================================================
# FORMATTING HELPERS
# ============================================================================

def print_banner() -> None:
    """Print ArXivLens brand banner."""
    console.print(
        Panel.fit(
            "[bold cyan]🔍 ArXivLens MCP[/bold cyan] [bold white]— Autonomous Academic & Research Intelligence[/bold white]\n"
            "[dim]Powered by FastMCP 2.0 | Real-Time arXiv Discovery | GitHub Code Mapping[/dim]",
            border_style="cyan",
        )
    )


def format_papers_table(papers: List[Dict[str, Any]], title: str = "Search Results") -> Table:
    """Format paper list into a rich terminal table."""
    table = Table(title=title, show_lines=True, header_style="bold magenta")
    table.add_column("arXiv ID", style="cyan", width=14)
    table.add_column("Title", style="bold white", min_width=30)
    table.add_column("Primary Cat", style="green", width=12)
    table.add_column("Published", style="dim", width=12)
    table.add_column("Authors", style="yellow", width=25)

    for p in papers:
        arxiv_id = p.get("arxiv_id", "")
        title_text = p.get("title", "")
        category = p.get("primary_category", "")
        published = p.get("published", "")[:10]
        authors = ", ".join(p.get("authors", []))
        if len(authors) > 24:
            authors = authors[:21] + "..."
        table.add_row(arxiv_id, title_text, category, published, authors)

    return table


def format_repos_table(repos: List[Dict[str, Any]], arxiv_id: str) -> Table:
    """Format GitHub repository list into a rich table."""
    table = Table(
        title=f"Matched Code Repositories for arXiv:{arxiv_id}",
        show_lines=True,
        header_style="bold green",
    )
    table.add_column("Repository", style="bold cyan", min_width=25)
    table.add_column("Stars", style="yellow", width=10, justify="right")
    table.add_column("Forks", style="dim", width=8, justify="right")
    table.add_column("Language", style="magenta", width=12)
    table.add_column("Description", style="white", min_width=30)

    for r in repos:
        name = r.get("full_name", "")
        stars = f"⭐ {r.get('stars', 0):,}"
        forks = str(r.get("forks", 0))
        lang = r.get("language") or "N/A"
        desc = r.get("description") or "No description provided."
        if len(desc) > 60:
            desc = desc[:57] + "..."
        table.add_row(name, stars, forks, lang, desc)

    return table


# ============================================================================
# SUBCOMMAND HANDLERS
# ============================================================================

async def handle_inspect(target: Optional[str] = None) -> None:
    """Inspect all tools, resources, and prompts exposed by the server."""
    print_banner()
    with console.status("[bold green]Connecting to ArXivLens MCP Server..."):
        async with ArXivLensClient(target) as client:
            tools = await client.list_tools()
            resources = await client.list_resources()
            prompts = await client.list_prompts()

    # Tools Table
    tools_table = Table(title="Registered MCP Tools", header_style="bold cyan", show_lines=True)
    tools_table.add_column("Tool Name", style="bold yellow", width=25)
    tools_table.add_column("Description", style="white")

    for t in tools:
        # Check both object attribute and dict format
        name = getattr(t, "name", None) or (t.get("name") if isinstance(t, dict) else str(t))
        desc = getattr(t, "description", None) or (t.get("description") if isinstance(t, dict) else "")
        tools_table.add_row(name, desc or "[dim]No description[/dim]")

    console.print(tools_table)
    console.print()

    # Resources Table
    res_table = Table(title="Exposed MCP Resources", header_style="bold green", show_lines=True)
    res_table.add_column("URI / Pattern", style="bold cyan", width=30)
    res_table.add_column("Name / Description", style="white")

    for r in resources:
        uri = getattr(r, "uri", None) or (r.get("uri") if isinstance(r, dict) else str(r))
        name = getattr(r, "name", None) or (r.get("name") if isinstance(r, dict) else "")
        res_table.add_row(str(uri), name or "[dim]Resource endpoint[/dim]")

    console.print(res_table)
    console.print()

    # Prompts Table
    prompts_table = Table(title="MCP Prompt Templates", header_style="bold magenta", show_lines=True)
    prompts_table.add_column("Prompt Name", style="bold yellow", width=25)
    prompts_table.add_column("Description", style="white")

    for p in prompts:
        name = getattr(p, "name", None) or (p.get("name") if isinstance(p, dict) else str(p))
        desc = getattr(p, "description", None) or (p.get("description") if isinstance(p, dict) else "")
        prompts_table.add_row(name, desc or "[dim]Prompt template[/dim]")

    console.print(prompts_table)


async def handle_search(query: str, max_results: int, sort_by: str, target: Optional[str] = None) -> None:
    """Execute real-time paper search on arXiv."""
    print_banner()
    with console.status(f"[bold green]Searching arXiv for: '{query}'..."):
        async with ArXivLensClient(target) as client:
            result = await client.search(query=query, max_results=max_results, sort_by=sort_by)

    # Handle result content
    papers = []
    if hasattr(result, "content") and result.content:
        # FastMCP tool result
        text = result.content[0].text if hasattr(result.content[0], "text") else str(result.content[0])
        try:
            papers = json.loads(text)
        except Exception:
            papers = []
    elif isinstance(result, list):
        papers = result

    if not papers:
        console.print(f"[yellow]No papers found matching query: '{query}'[/yellow]")
        return

    table = format_papers_table(papers, title=f"arXiv Results for: '{query}' ({len(papers)} found)")
    console.print(table)


async def handle_brief(arxiv_id: str, target: Optional[str] = None) -> None:
    """Generate and display structured research brief."""
    print_banner()
    with console.status(f"[bold green]Synthesizing research brief for arXiv:{arxiv_id}..."):
        async with ArXivLensClient(target) as client:
            result = await client.get_brief(arxiv_id=arxiv_id)

    brief_data = {}
    if hasattr(result, "content") and result.content:
        text = result.content[0].text if hasattr(result.content[0], "text") else str(result.content[0])
        try:
            brief_data = json.loads(text)
        except Exception:
            brief_data = {"markdown": text}
    elif isinstance(result, dict):
        brief_data = result

    markdown_text = brief_data.get("markdown")
    if markdown_text:
        console.print(Markdown(markdown_text))
    else:
        console.print(Panel(json.dumps(brief_data, indent=2), title=f"Brief for {arxiv_id}"))


async def handle_code(arxiv_id: str, title: str, max_results: int, target: Optional[str] = None) -> None:
    """Discover GitHub repositories matching an arXiv paper."""
    print_banner()
    with console.status(f"[bold green]Scanning GitHub for implementations of arXiv:{arxiv_id}..."):
        async with ArXivLensClient(target) as client:
            result = await client.find_code(arxiv_id=arxiv_id, title=title, max_results=max_results)

    repos = []
    if hasattr(result, "content") and result.content:
        text = result.content[0].text if hasattr(result.content[0], "text") else str(result.content[0])
        try:
            repos = json.loads(text)
        except Exception:
            repos = []
    elif isinstance(result, list):
        repos = result

    if not repos:
        console.print(f"[yellow]No code repositories found for arXiv:{arxiv_id}[/yellow]")
        return

    table = format_repos_table(repos, arxiv_id=arxiv_id)
    console.print(table)


async def handle_agent_loop(target: Optional[str] = None) -> None:
    """Interactive Agent Loop with autonomous tool dispatch and synthesis."""
    print_banner()
    console.print(
        Panel(
            "[bold white]Welcome to the ArXivLens Autonomous Research Agent![/bold white]\n\n"
            "You can ask natural language questions such as:\n"
            "  • [cyan]'Find recent papers on speculative decoding and find their code'[/cyan]\n"
            "  • [cyan]'Generate a brief for 1706.03762'[/cyan]\n"
            "  • [cyan]'What are the latest breakthroughs in cs.CL?'[/cyan]\n"
            "  • [cyan]'Critique paper 2310.06825'[/cyan]\n\n"
            "[dim]Type 'exit' or 'quit' to exit the session.[/dim]",
            border_style="green",
        )
    )

    async with ArXivLensClient(target) as client:
        while True:
            try:
                user_input = console.input("\n[bold cyan]ArXivLens ❯ [/bold cyan]").strip()
                if not user_input:
                    continue
                if user_input.lower() in ["exit", "quit", "q"]:
                    console.print("[dim]Goodbye![/dim]")
                    break

                # Autonomous Agent Reasoning & Dispatch
                with console.status("[bold green]Agent reasoning and coordinating MCP tools..."):
                    # Check for explicit brief request
                    if "brief" in user_input.lower() or "summary" in user_input.lower():
                        import re
                        match = re.search(r"(\d{4}\.\d{4,5})", user_input)
                        if match:
                            paper_id = match.group(1)
                            console.print(f"[dim]➔ Calling MCP Tool: generate_research_brief(arxiv_id='{paper_id}')[/dim]")
                            res = await client.get_brief(arxiv_id=paper_id)
                            content = res.content[0].text if hasattr(res, "content") else str(res)
                            data = json.loads(content) if isinstance(content, str) and content.startswith("{") else {}
                            if "markdown" in data:
                                console.print(Markdown(data["markdown"]))
                            else:
                                console.print(content)
                            continue

                    # Check for code discovery request
                    if "code" in user_input.lower() or "repo" in user_input.lower() or "github" in user_input.lower():
                        import re
                        match = re.search(r"(\d{4}\.\d{4,5})", user_input)
                        paper_id = match.group(1) if match else ""
                        if paper_id:
                            console.print(f"[dim]➔ Calling MCP Tool: find_code_repositories(arxiv_id='{paper_id}')[/dim]")
                            res = await client.find_code(arxiv_id=paper_id)
                            content = res.content[0].text if hasattr(res, "content") else str(res)
                            repos = json.loads(content) if isinstance(content, str) and content.startswith("[") else []
                            console.print(format_repos_table(repos, arxiv_id=paper_id))
                            continue

                    # Default: Search papers on arXiv
                    clean_query = user_input
                    for prefix in ["find papers on", "search for", "search", "papers about", "look up"]:
                        if user_input.lower().startswith(prefix):
                            clean_query = user_input[len(prefix):].strip()
                            break

                    console.print(f"[dim]➔ Calling MCP Tool: search_arxiv(query='{clean_query}', max_results=4)[/dim]")
                    res = await client.search(query=clean_query, max_results=4)
                    content = res.content[0].text if hasattr(res, "content") else str(res)
                    papers = json.loads(content) if isinstance(content, str) and content.startswith("[") else []

                    if papers:
                        console.print(format_papers_table(papers, title=f"Agent Found {len(papers)} Papers"))
                        # Follow up: check code for top paper
                        top_paper = papers[0]
                        top_id = top_paper.get("arxiv_id", "")
                        if top_id:
                            console.print(f"[dim]➔ Auto-scouting GitHub code for top paper ({top_id})...[/dim]")
                            code_res = await client.find_code(arxiv_id=top_id, title=top_paper.get("title", ""), max_results=2)
                            code_content = code_res.content[0].text if hasattr(code_res, "content") else str(code_res)
                            repos = json.loads(code_content) if isinstance(code_content, str) and code_content.startswith("[") else []
                            if repos:
                                console.print(format_repos_table(repos, arxiv_id=top_id))
                            else:
                                console.print(f"[dim]No open repositories indexed yet for arXiv:{top_id}[/dim]")
                    else:
                        console.print(f"[yellow]No papers found for '{clean_query}'. Try refining your search terms.[/yellow]")

            except KeyboardInterrupt:
                console.print("\n[dim]Session interrupted. Exiting.[/dim]")
                break
            except Exception as err:
                console.print(f"[red]Error during agent execution: {err}[/red]")


# ============================================================================
# MAIN ENTRYPOINT
# ============================================================================

def main():
    """Parse arguments and dispatch CLI commands."""
    parser = argparse.ArgumentParser(
        prog="arxivlens-client",
        description="CLI and Interactive Client for ArXivLens FastMCP 2.0 Server",
    )
    parser.add_argument("--server", help="Server script path, URL, or empty for local in-memory", default=None)

    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # inspect
    subparsers.add_parser("inspect", help="Inspect all tools, resources, and prompts on the server")

    # search
    search_p = subparsers.add_parser("search", help="Search papers on arXiv in real time")
    search_p.add_argument("query", help="Search query string")
    search_p.add_argument("--max", type=int, default=5, help="Max results (default: 5)")
    search_p.add_argument("--sort", default="relevance", choices=["relevance", "submittedDate", "lastUpdatedDate"])

    # brief
    brief_p = subparsers.add_parser("brief", help="Generate a structured research brief for a paper")
    brief_p.add_argument("arxiv_id", help="arXiv paper ID (e.g., 1706.03762)")

    # code
    code_p = subparsers.add_parser("code", help="Find GitHub repositories matching an arXiv paper")
    code_p.add_argument("arxiv_id", help="arXiv paper ID")
    code_p.add_argument("--title", default="", help="Optional paper title")
    code_p.add_argument("--max", type=int, default=5, help="Max repositories to return")

    # agent
    subparsers.add_parser("agent", help="Launch interactive agent terminal loop")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    if args.command == "inspect":
        asyncio.run(handle_inspect(args.server))
    elif args.command == "search":
        asyncio.run(handle_search(args.query, args.max, args.sort, args.server))
    elif args.command == "brief":
        asyncio.run(handle_brief(args.arxiv_id, args.server))
    elif args.command == "code":
        asyncio.run(handle_code(args.arxiv_id, args.title, args.max, args.server))
    elif args.command == "agent":
        asyncio.run(handle_agent_loop(args.server))


if __name__ == "__main__":
    main()
