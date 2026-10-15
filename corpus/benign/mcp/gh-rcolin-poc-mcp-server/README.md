# Pokémon Name Generator MCP Server

This project is a simple Model Context Protocol (MCP) server that generates the names of main Pokémon characters. It is designed to be used with GitHub Copilot MCP in VS Code, but can also be run and tested independently.

## Features
- MCP server using [fastmcp](https://github.com/ai-ctx/fastmcp)
- Tool to generate the main Pokémon character names
- Ready for integration with Copilot MCP
- Unit tests included

## Installation

1. **Clone the repository** (if needed):
   ```sh
   git clone <your-repo-url>
   cd poc-mcp-server
   ```

2. **Install dependencies using [uv](https://github.com/astral-sh/uv):**
   ```sh
   uv pip install -r uv.lock
   # or, if you use pyproject.toml:
   uv pip install -r pyproject.toml
   ```
   > If you don't have `uv`, install it with: `pip install uv`

3. **(Optional) Install test dependencies:**
   ```sh
   uv pip install pytest
   ```

## Running the MCP Server

To start the MCP server (stdio transport):
```sh
uv python main.py
```

## Running the Tests

To run the unit tests:
```sh
uv pytest
```

If you have import issues, try:
```sh
PYTHONPATH=. uv pytest
```

## Project Structure
```
├── main.py                  # MCP server and tool definition
├── tests/
│   ├── __init__.py          # Makes tests a package
│   └── test_main.py         # Unit tests
├── .vscode/
│   └── settings.json        # VS Code settings
│   └── mcp.json             # MCP config for VS Code
├── .gitignore               # Git ignore rules
├── pyproject.toml           # Project metadata
├── uv.lock                  # uv lock file
└── README.md
```

## License
MIT
