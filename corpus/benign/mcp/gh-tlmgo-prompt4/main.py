import os

from fastmcp import FastMCP

PROMPTS_FOLDER_ENV = "PROMPTS_FOLDER"
PROMPTS_FOLDER = os.environ.get(PROMPTS_FOLDER_ENV) or os.path.join(
    os.path.dirname(__file__), "prompts"
)

mcp = FastMCP(
    "Prompt Shortcut MCP",
    log_level="ERROR",
    instructions=(
        "You are a software developer assistant. You are able to remember "
        "prompts templates and execute them when asked."
    ),
)


def load_prompts():
    prompts = {}
    if not os.path.exists(PROMPTS_FOLDER) or not os.path.isdir(PROMPTS_FOLDER):
        return prompts
    for filename in os.listdir(PROMPTS_FOLDER):
        if filename.endswith(".txt"):
            shortcut = os.path.splitext(filename)[0].replace("_", " ")
            file_path = os.path.join(PROMPTS_FOLDER, filename)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    prompts[shortcut] = f.read()
            except Exception:
                continue  # skip files that can't be loaded
    return prompts


@mcp.tool()
def list_prompts() -> list:
    """Tool: List all available prompt names."""
    prompts = load_prompts()
    return list(prompts.keys())


@mcp.tool()
def get_prompt(prompt_name: str) -> str:
    """Tool: Return the prompt text for a given prompt name."""
    prompts = load_prompts()
    return prompts.get(prompt_name, f"Prompt '{prompt_name}' not found.")


@mcp.tool()
def get_prompt_file() -> dict:
    """Tool: Return the prompt file content."""
    prompts = load_prompts()
    return prompts


if __name__ == "__main__":
    mcp.run()
