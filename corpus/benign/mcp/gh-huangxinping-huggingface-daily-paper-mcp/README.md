# HuggingFace Daily Papers MCP Server

A MCP (Model Context Protocol) server for fetching HuggingFace daily papers.

## Features

- Fetch today's, yesterday's or specific date HuggingFace papers
- Provides paper title, authors, abstract, tags, votes, and submitted by info
- Includes paper links and PDF download links  
- Supports MCP tools and resource interfaces
- ArXiv integration for complete author lists
- Complete error handling and logging
- Comprehensive test coverage

## Installation & Usage

### Option 1: Direct execution with uvx (Recommended)

Install and run directly using uvx:

```bash
uvx huggingface-daily-paper-mcp
```

This will automatically install the package and its dependencies, then start the MCP server.

### Option 2: Local development

For local development, clone the repository and install dependencies:

```bash
git clone https://github.com/huangxinping/huggingface-daily-paper-mcp.git
cd huggingface-daily-paper-mcp
uv sync
```

### Local usage commands

**Run as MCP Server (for development)**:
```bash
python main.py
```

**Test Scraper Function**:
```bash
python scraper.py
```

**Run Tests**:
```bash
uv run -m pytest test_mcp_server.py -v
```

**Build Package**:
```bash
uv build
```

## MCP Interface

### Tools

1. **get_papers_by_date**
   - Description: Get HuggingFace papers for a specific date
   - Parameters: `date` (YYYY-MM-DD format)

2. **get_today_papers**
   - Description: Get today's HuggingFace papers
   - Parameters: None

3. **get_yesterday_papers**
   - Description: Get yesterday's HuggingFace papers
   - Parameters: None

### Resources

1. **papers://today**
   - Today's papers JSON data

2. **papers://yesterday**
   - Yesterday's papers JSON data

## Project Structure

```
huggingface-daily-paper-mcp/
├── main.py                    # MCP server main program
├── scraper.py                 # HuggingFace papers scraper module
├── test_mcp_server.py         # MCP server test cases
├── README.md                  # Project documentation
├── .gitignore                 # Git ignore file
├── pyproject.toml             # Project configuration file
└── uv.lock                    # Dependency lock file
```

## Tech Stack

- **Python 3.10+**: Programming language
- **MCP**: Model Context Protocol framework
- **Requests**: HTTP request library
- **BeautifulSoup4**: HTML parsing library
- **pytest**: Testing framework
- **uv**: Python package manager

## Development Standards

- Use uv native commands for package management
- Follow Python PEP 8 coding standards
- Include type hints and docstrings
- Complete error handling and logging
- Write unit tests to ensure code quality

## Example Output

Single paper data structure:

```json
{
  "title": "CMPhysBench: A Benchmark for Evaluating Large Language Models in Condensed Matter Physics",
  "authors": ["Weida Wang", "Dongchen Huang", "Jiatong Li", "..."],
  "abstract": "CMPhysBench evaluates LLMs in condensed matter physics using calculation problems...",
  "url": "https://huggingface.co/papers/2508.18124",
  "pdf_url": "https://arxiv.org/pdf/2508.18124.pdf",
  "votes": 15,
  "submitted_by": "researcher123",
  "scraped_at": "2025-08-27T10:30:00.123456"
}
```

MCP Tool output format:
```
Title: CMPhysBench: A Benchmark for Evaluating Large Language Models in Condensed Matter Physics
Authors: Weida Wang, Dongchen Huang, Jiatong Li, Tengchao Yang, Ziyang Zheng...
Abstract: CMPhysBench evaluates LLMs in condensed matter physics using calculation problems...
URL: https://huggingface.co/papers/2508.18124
PDF: https://arxiv.org/pdf/2508.18124.pdf
Votes: 15
Submitted by: researcher123
--------------------------------------------------
```

## AI IDE/CLI Configuration

### Claude Code (CLI)

Add to your MCP configuration:

```json
{
  "mcpServers": {
    "huggingface-papers": {
      "command": "uvx",
      "args": ["huggingface-daily-paper-mcp"]
    }
  }
}
```

### Cursor IDE

Add to your `.cursorrules` or MCP settings:

```json
{
  "mcp": {
    "servers": {
      "huggingface-papers": {
        "command": "uvx",
        "args": ["huggingface-daily-paper-mcp"],
        "env": {}
      }
    }
  }
}
```

### Windsurf IDE

Add to your Windsurf MCP configuration:

```json
{
  "mcpServers": {
    "huggingface-papers": {
      "command": "uvx",
      "args": ["huggingface-daily-paper-mcp"]
    }
  }
}
```

### VS Code with Continue Extension

Add to your `continue` configuration:

```json
{
  "mcp": {
    "servers": {
      "huggingface-papers": {
        "command": "uvx",
        "args": ["huggingface-daily-paper-mcp"]
      }
    }
  }
}
```

### Other MCP-Compatible Tools

For any MCP-compatible client, use:

```bash
# Command
uvx huggingface-daily-paper-mcp

# Or with Python path
python -m main
```

## License

MIT License