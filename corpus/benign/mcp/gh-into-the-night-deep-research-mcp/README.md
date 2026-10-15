# Deep Research MCP

This is a sample MCP server used to showcase MCP's integrative capabilites. It includes two tools: `generate_plan` and `execute_plan`.

## Built with 🛠

- FastMCP
- LangChain
- Groq

## How to run 🏃🏻‍♂️

1. Clone the repository:
   ```
   git clone https://github.com/into-the-night/deep-research-mcp.git
   cd deep-research-mcp
   ```

2. Install uv:

    For Windows-
    ```
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    ```

    For MacOS/Linux-
    ```
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```

2. Create a virtual environment and activate it:
    ```
    uv venv
    source .venv/bin/activate  # On Windows: .venv\Scripts\activate
    ```

3. Install dependencies:
    ```
    uv pip install -e .
    ```

4. Create a .env file and populate it with:
    ```
    TAVILY_API_KEY=<YOUR_TAVILY_API_KEY>
    GROQ_API_KEY=<YOUR_GROQ_API_KEY>
    ```

5. Run the app:
    ```
    uv run app.py
    ```

## Use with Claude Desktop 💻

1. Download Claue Desktop: https://claude.ai/download

2. Copy and paste this into `claude_desktop_config.json`:
    ```
    {
        "mcpServers": {
            "deep_research": {
                "command": "uv",
                "args": [
                    "--directory",
                    "ABSOLUTE\PATH\TO\REPO",
                    "run",
                    "app.py"
                ]
            }
        }
    }
    ```

3. Restart Claude Desktop

Note: If you still can't see the server inside the app, make sure Claude gets completely restarted as it might still be running in system tray.

## Author ✍

Made with ♥ by [Abhay Shukla](https://github.com/into-the-night)

## License 📜

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details.