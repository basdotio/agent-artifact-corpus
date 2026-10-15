# Prompt4

Prompt4 is a lightweight server for managing and retrieving reusable text prompts, designed to work seamlessly with the FastMCP 2 protocol and tools like Cursor. It allows you to organize prompts as individual text files, making it easy to maintain, update, and share prompt templates for code review, automation, and other developer workflows.

Why is this useful?
- **Centralized Prompt Management:** Store all your prompt templates in one place, version-controlled with your codebase.
- **Easy Integration:** Works out-of-the-box with Cursor and any MCP-compatible client, enabling fast access to prompts directly from your editor or automation scripts.
- **Reusability:** Avoid copy-pasting or rewriting common instructions—just trigger the right prompt by name.
- **Collaboration:** Teams can standardize and improve their prompt templates over time, ensuring consistency and best practices.
- **Automation:** Prompts can be used to automate repetitive tasks, code reviews, or documentation requests, saving time and reducing errors.

## Features
- List all available prompt names (via MCP tool)
- Retrieve the text for a specific prompt (via MCP tool)

## Example prompt folder structure

Prompts are stored as individual text files in a folder (e.g., `prompts/`). Each file name (without the extension) is the prompt name. For example, a prompt named `feedback` would be stored as `prompts/feedback.txt`:

```
prompts/
  feedback.txt
  ...
```

Contents of `prompts/feedback.txt`:

```
Please review the codebase and provide feedback on the following aspects:

- General Issues: Identify any problems and suggest improvements.
- Good Practices: Highlight any best practices found.
- Areas for Improvement: Suggest specific improvements.
- Refactoring: Point out code that could be refactored.
- Optimization: Recommend ways to optimize the code.
- Security: Identify security concerns and suggest mitigations.
- Performance: Suggest ways to improve performance.
- Readability: Recommend changes to improve code readability.
- Maintainability: Suggest how to make the code easier to maintain.
- Scalability: Advise on making the code more scalable.
- Testability: Suggest improvements for easier or better testing.
- Documentation: Point out missing or unclear documentation.
- Error Handling: Recommend better error handling practices.
- Logging: Suggest improvements to logging.
- Debugging: Recommend ways to make debugging easier.

For each point, provide concrete suggestions or examples where possible.
```

## Using the MCP in Cursor

To use the MCP server in Cursor, you can trigger a prompt with the following instruction in the Cursor command bar:

```
run [prompt name]. use prompt4
```

Replace `[prompt name]` with the name of the prompt you want to use (e.g., `feedback`).

- Most of the time, Cursor will execute the prompt immediately.
- Sometimes, Cursor will only retrieve the prompt text and display it without executing. In this case, simply type:

```
do it.
```

This will instruct Cursor to execute the retrieved instructions.

> **Tip:** For an even faster workflow, add the following rule to your user instructions in Cursor:
>
> "When the chat message starts with '!', use prompt4 to get the prompt and execute it. Example: '!PROMPT_NAME'."
>
> With this rule, you only need to start your chat message with `!` followed by the name of the shortcut to instantly trigger the corresponding prompt.

## Installation

1. Clone the repository:
   ```bash
   git clone <repo-url>
   cd prompt-shortcut-mcp
   ```
2. Install dependencies (recommended: use Python 3.12+):
   ```bash
   poetry install
   ```

## Usage

Run the MCP server:
```bash
fastmcp run my_server.py:mcp
```

This will launch a FastMCP 2 server exposing two tools:
- `list_prompts`: Lists all available prompt names
- `get_prompt`: Returns the text for a given prompt name

You can connect to this server using any MCP-compatible client (such as [fastmcp.Client](https://github.com/jlowin/fastmcp)).

### Example: Listing tools from a client
```python
import asyncio
from fastmcp import Client

client = Client("main.py")

async def main():
    async with client:
        tools = await client.list_tools()
        print([tool.name for tool in tools])

asyncio.run(main())
```

## Docker Integration and Cursor Configuration

### Build the Docker Image

Run the following command in your project root to build the Docker image:

```bash
docker build -t prompt4-mcp .
```

### Using with Cursor (MCP Integration)

To use this server with Cursor via Docker, add the following to your Cursor config file (typically `mcp.json`):

```json
{
  "mcpServers": {
    "Prompt4": {
      "autoApprove": [],
      "disabled": false,
      "timeout": 60,
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "-e",
        "PROMPTS_FOLDER=/prompts",
        "-v",
        "[FOLDER CONTAINING THE PROMPTS ON YOUR MACHINE]:/prompts",
        "prompt4-mcp"
      ],
      "transportType": "stdio"
    }
  }
}
```

This setup allows Cursor to launch the MCP server in a Docker container automatically.

## Author
Jean-Pierre Bluteau <jean-pierre.bluteau@tlmgo.com>

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details. 