# EIPs MCP

An MCP server for providing semantically related Ethereum Improvement Proposals (EIPs) to AI agents.

![GitHub License](https://img.shields.io/github/license/kukapay/eips-mcp) 
![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)
![Status](https://img.shields.io/badge/status-active-brightgreen.svg)

## Features

- **Semantic Search**: Utilizes vector embeddings for accurate, context-aware search across EIP documents.
- **Markdown Support**: Processes EIP markdown files with chunking for efficient storage and retrieval.

## Installation

### Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip for dependency management

### Setup

1. **Clone the Repository**:
   ```bash
   git clone --recursive-submodules https://github.com/kukapay/eips-mcp.git
   cd eips-mcp
   ```

2. **Install the Dependencies** (recommended):
   ```bash
   uv sync
   ```

3. **Load EIP Documents**:
   Use the provided `load_eips.py` script to automatically fetch and process EIPs:
   ```bash
   uv run load_eips.py
   ```

4. **Installing to Claude Desktop**:

    Install the server as a Claude Desktop application:
    ```bash
    uv run mcp install main.py --name "EIPs"
    ```

    Configuration file as a reference:

    ```json
    {
       "mcpServers": {
           "EIPs": {
               "command": "uv",
               "args": [ "--directory", "/path/to/eips-mcp", "run", "main.py" ]
           }
       }
    }
    ```
    Replace `/path/to/eips-mcp` with your actual installation path.


## Usage

The server exposes a single MCP tool, `search`, which accepts a query string and returns relevant EIP content. Example usage in an MCP-compatible client:

You can use natural language prompts such as:

- "Search for EIPs related to CREATE2"
- "Find EIPs about contract deployment opcodes"
- "EIPs discussing CREATE2 implementation details"

The tool processes these queries and returns up to 5 relevant EIP document chunks, formatted with separators for clarity.

When searching for "CREATE2" using the `search` tool, the output might look like:

```
--------------------eip-1014.md--------------------
# EIP-1014: Skinny CREATE2
**Abstract**: This EIP adds a new opcode at 0xf5, CREATE2, which allows for deterministic address generation...
...
--------------------eip-1014.md--------------------
**Motivation**: The CREATE2 opcode enables predictable contract addresses, which is useful for...
...
```

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

