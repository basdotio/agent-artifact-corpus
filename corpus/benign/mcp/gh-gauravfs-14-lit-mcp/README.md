# lit-mcp (Literature Review Assistant MCP Server)

<!-- mcp-name: io.github.gauravfs-14/lit-mcp -->

[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://python.org)
[![MCP](https://img.shields.io/badge/MCP-Compatible-green.svg)](https://modelcontextprotocol.io)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![arXiv](https://img.shields.io/badge/arXiv-API-orange.svg)](https://arxiv.org)
[![DBLP](https://img.shields.io/badge/DBLP-API-red.svg)](https://dblp.org)
[![uv](https://img.shields.io/badge/uv-Package%20Manager-purple.svg)](https://github.com/astral-sh/uv)

A powerful Model Context Protocol (MCP) server that provides seamless access to academic literature databases, helping researchers accelerate their literature review process using LLMs and MCP clients like Claude, Cursor, and others.

## 🚀 Features

- **arXiv Integration**: Search and retrieve academic papers from arXiv
- **DBLP Integration**: Search computer science publications from DBLP database
- **AI-Powered Prompts**: Generate comprehensive research summaries and insights (usable as "/" commands)
- **MCP Compatible**: Works with any MCP client (Claude, Cursor, etc.)
- **Structured Data**: Returns well-formatted paper metadata
- **Fast & Reliable**: Built on FastMCP for optimal performance
- **Extensible**: Easy to add new academic databases

## 🚀 Quick Start

### 1. Install UV (one-time setup)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Add to MCP Client

Simply add lit-mcp to your MCP client configuration - `uvx` will handle the rest automatically!

## 🔌 MCP Client Integration

### Cursor IDE

Add to your MCP configuration (usually in `~/.cursor/mcp.json`):

```json
{
  "mcpServers": {
    "lit-mcp": {
      "command": "uvx",
      "args": ["lit-mcp"]
    }
  }
}
```

### Codex CLI

Use this single-line command to use it with codex.

```bash
codex mcp add lit-mcp -- uvx lit-mcp
```

<details>
<summary><strong>Other MCP Clients (Claude Desktop, etc.)</strong></summary>

Any MCP-compatible client can use lit-mcp with the same configuration pattern:

```json
{
  "mcpServers": {
    "lit-mcp": {
      "command": "uvx",
      "args": ["lit-mcp"]
    }
  }
}
```

**Example Usage:**

Once configured, you can use the available tools in your MCP client:

```text
# Search tools
Search for 5 papers on "machine learning transformers" using arXiv.
Search for computer science papers on "GPS trajectory" using DBLP.

# AI-powered prompts (as "/" commands in Cursor)
/latest_info small language models
/related_topics transformer architectures  
/author_spotlight computer vision
```

</details>

## 📖 Available Tools

### Search Tools

<details>
<summary><strong>arxiv_search</strong></summary>

Search for academic papers on arXiv with advanced query capabilities.

**Parameters:**

- `query` (string): Search query (supports arXiv syntax like `au:Author_Name`, `ti:Title`, etc.)
- `max_results` (integer, optional): Maximum number of results (default: 10)

**Returns:**

- List of paper objects with title, authors, publication date, summary, PDF URL, categories, and DOI

**Example Queries:**

```python
# Search by author
"au:Gaurab_Chhetri"

# Search by title keywords
"ti:machine learning"

# Search by category
"cat:cs.AI"

# Combined search
"au:Chhetri AND ti:transport"
```

</details>

<details>
<summary><strong>dblp_search</strong></summary>

Search for computer science publications in the DBLP database.

**Parameters:**

- `query` (string): Search query for computer science papers
- `max_results` (integer, optional): Maximum number of results (default: 10)

**Returns:**

- List of publication objects with title, authors, venue, volume, number, pages, publisher, year, type, access, key, DOI, electronic edition link, and DBLP URL

**Example Queries:**

```python
# Search for specific topics
"machine learning"
"computer vision"
"natural language processing"
"GPS trajectory"
"blockchain technology"
```

</details>

### AI-Powered Research Prompts

<details>
<summary><strong>latest_info</strong></summary>

Generate comprehensive summaries of the most recent innovations, trends, and papers in a research field.

**Parameters:**

- `topic` (string): Research field or topic to analyze

**Returns:**

- Well-structured Markdown document with recent papers, key trends, and insights

**Features:**

- Identifies latest papers (preferably within last 12 months)
- Focuses on highly cited, emerging, or novel works
- Provides structured summaries with PDF links
- Includes "Key Trends & Insights" section
- Beautifully formatted for easy reading

**Example Usage:**

```text
# As MCP prompt
Generate latest information about "small language models"
Analyze recent trends in "quantum machine learning"

# As "/" command in Cursor
/latest_info small language models
/latest_info quantum machine learning
```

</details>

<details>
<summary><strong>related_topics</strong></summary>

Discover related and emerging research areas connected to a given topic.

**Parameters:**

- `topic` (string): Research topic to explore connections for

**Returns:**

- Structured Markdown document with related topics, representative papers, and emerging intersections

**Features:**

- Identifies 3-6 distinct related topics or subfields
- Shows connections between topics
- Provides representative papers with summaries
- Highlights emerging interdisciplinary areas
- Reveals novel applications and fusion trends

**Example Usage:**

```text
# As MCP prompt
Find related topics for "transformer architectures"
Explore connections around "federated learning"

# As "/" command in Cursor
/related_topics transformer architectures
/related_topics federated learning
```

</details>

<details>
<summary><strong>author_spotlight</strong></summary>

Identify leading authors, labs, and research groups advancing innovation in a field.

**Parameters:**

- `topic` (string): Research field to analyze for key contributors

**Returns:**

- Structured Markdown document with top authors, their affiliations, notable papers, and collaborative networks

**Features:**

- Ranks authors by publication frequency and impact
- Shows affiliations and research themes
- Lists notable papers with summaries
- Identifies collaborative networks and research groups
- Highlights cross-institution projects

**Example Usage:**

```text
# As MCP prompt
Find leading authors in "computer vision"
Identify key researchers in "natural language processing"

# As "/" command in Cursor
/author_spotlight computer vision
/author_spotlight natural language processing
```

</details>

## 📊 Example Output

### arXiv Search Result

```json
{
  "title": "Model Context Protocols in Adaptive Transport Systems: A Survey",
  "authors": ["Gaurab Chhetri", "Shriyank Somvanshi", "..."],
  "published": "2025-08-26T17:58:56+00:00",
  "summary": "The rapid expansion of interconnected devices...",
  "entry_id": "http://arxiv.org/abs/2508.19239v1",
  "pdf_url": "http://arxiv.org/pdf/2508.19239v1",
  "categories": ["cs.AI"],
  "doi": null
}
```

### DBLP Search Result

```json
{
  "title": "GPS Trajectory Data Mining: A Survey",
  "authors": ["John Doe", "Jane Smith"],
  "venue": "IEEE Transactions on Knowledge and Data Engineering",
  "volume": "35",
  "number": "3",
  "pages": "1234-1250",
  "publisher": "IEEE",
  "year": "2023",
  "type": "Journal Articles",
  "access": "open",
  "key": "journals/tkde/DoeS23",
  "doi": "10.1109/TKDE.2023.1234567",
  "ee": "https://doi.org/10.1109/TKDE.2023.1234567",
  "url": "https://dblp.org/rec/journals/tkde/DoeS23.html"
}
```

## 🎯 Real-World Example

We tested this MCP by adding to Cursor. The [output](./example/small-lang-models.md) was generated using the new AI-powered prompts and search tools. This comprehensive survey demonstrates the capabilities of lit-mcp:

**Generated using:**

- `latest_info` prompt for recent trends and innovations
- `related_topics` prompt for connected research areas  
- `author_spotlight` prompt for key researchers and collaborations
- `arxiv_search` tool for paper discovery and citations

**Original prompt:**
> I want to write a comprehensive survey paper on small language models. Can you create me a template along with fully detailed analysis of the contents? The writeup should be narrative (paragraph) style with minimal use of bullet points. Update to the file named small-lang-models.md and put the detailed contents there. Make sure to add accurate in-text citations as well to the content using markdown citation format, and also make sure to give the PDF links to all the papers. Use the arxiv tool.

## 🛠️ Development Installation

### Prerequisites

- Python 3.12
- uv package manager

<details>
<summary><strong>Setup & Development Configuration</strong></summary>

1. **Clone the repository**

   ```bash
   git clone https://github.com/gauravfs-14/lit-mcp.git
   cd lit-mcp
   ```

2. **Install dependencies**

   ```bash
   # Install UV if not already installed
   curl -LsSf https://astral.sh/uv/install.sh | sh
   
   # Install project dependencies
   uv sync
   ```

3. **Run the MCP server**

   ```bash
   uv run lit-mcp
   ```

### Development Setup for MCP Clients

If you're developing locally, you can use the development setup:

```json
{
  "mcpServers": {
    "lit-mcp": {
      "command": "uv",
      "args": [
        "--directory",
        "<absolute_path_to_the_cloned_repo>",
        "run",
        "lit-mcp"
      ]
    }
  }
}
```

</details>

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for detailed information on how to contribute to this project.

<details>
<summary><strong>Quick Start for Contributors</strong></summary>

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests (`uv run python tests/test_basic.py`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

**New contributors can help with:**

- Adding new academic database integrations (PubMed, IEEE Xplore, ACM Digital Library)
- Creating new AI-powered research prompts
- Improving existing prompt templates
- Adding new evaluation metrics and benchmarks
- Enhancing documentation and examples

For detailed guidelines, see [CONTRIBUTING.md](CONTRIBUTING.md).

</details>

This project follows a [Code of Conduct](CODE_OF_CONDUCT.md) to ensure a welcoming environment for all contributors.

## 🙏 Acknowledgments

- [arXiv](https://arxiv.org/) for providing free access to academic papers
- [DBLP](https://dblp.org/) for the comprehensive computer science bibliography
- [arxiv-py](https://pypi.org/project/arxiv/) developers for the excellent Python wrapper
- [DBLP API](https://dblp.org/faq/How+to+use+the+dblp+search+API) for providing direct access to computer science publications
- [FastMCP](https://github.com/modelcontextprotocol/fastmcp) for the MCP server framework

## 🆘 Support

If you encounter any issues or have questions:

1. Check the [Issues](https://github.com/gauravfs-14/lit-mcp/issues) page
2. Create a new issue with detailed information
3. Join our community discussions

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
