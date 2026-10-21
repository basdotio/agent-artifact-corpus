import asyncio
import json

from ollama import chat, list as ollama_list
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

MCP_SERVER = r"D:\Gmail-MCP-Local\mcp_gmail.py"

PYTHON_EXECUTABLE = (
    r"C:\Users\adith\AppData\Local\Programs\Python\Python312\python.exe"
)


# ---------------------------------------------------------
# Detect Local Ollama Models
# ---------------------------------------------------------

def get_local_models():

    try:
        response = ollama_list()

        models = []

        for model in response.models:

            model_name = model.model

            # Ollama cloud models generally have "-cloud"
            # in their model name and are not stored locally.
            if "-cloud" in model_name:
                continue

            # Only include models that actually have local size.
            if hasattr(model, "size") and model.size:

                models.append({
                    "name": model_name,
                    "size": model.size
                })

        return models

    except Exception as e:

        print("\nERROR: Could not connect to Ollama.")
        print(f"Details: {e}")

        return []


# ---------------------------------------------------------
# Format model size
# ---------------------------------------------------------

def format_size(size):

    if size >= 1024 ** 3:
        return f"{size / (1024 ** 3):.1f} GB"

    if size >= 1024 ** 2:
        return f"{size / (1024 ** 2):.1f} MB"

    return f"{size} bytes"


# ---------------------------------------------------------
# Model Selection
# ---------------------------------------------------------

def select_model():

    models = get_local_models()

    if not models:

        print("\nNo local Ollama models were found.")

        print(
            "\nMake sure Ollama is running and that you have "
            "at least one local model installed."
        )

        print("\nExample:")
        print("ollama pull qwen3:8b")

        return None

    print("\n========================================")
    print("       LOCAL OLLAMA MODELS")
    print("========================================\n")

    for index, model in enumerate(models, start=1):

        print(
            f"{index}. {model['name']}"
            f" ({format_size(model['size'])})"
        )

    print("\n========================================")

    while True:

        selection = input(
            f"\nSelect a model [1-{len(models)}]: "
        ).strip()

        try:

            selection = int(selection)

            if 1 <= selection <= len(models):

                selected_model = models[selection - 1]["name"]

                print(
                    f"\nSelected model: {selected_model}\n"
                )

                return selected_model

            print(
                f"Please enter a number between 1 and {len(models)}."
            )

        except ValueError:

            print("Please enter a valid number.")


# ---------------------------------------------------------
# MCP Server Configuration
# ---------------------------------------------------------

server_params = StdioServerParameters(
    command=PYTHON_EXECUTABLE,
    args=[
        MCP_SERVER
    ],
)


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------

async def main():

    # -----------------------------------------------------
    # Select local model
    # -----------------------------------------------------

    model = select_model()

    if not model:
        return

    # -----------------------------------------------------
    # Start MCP server
    # -----------------------------------------------------

    print("Starting Gmail MCP server...")

    async with stdio_client(server_params) as (read, write):

        async with ClientSession(read, write) as session:

            print("Initializing MCP connection...")

            await session.initialize()

            # -------------------------------------------------
            # Get MCP tools
            # -------------------------------------------------

            tools_result = await session.list_tools()

            print("\n========================================")
            print("       AVAILABLE GMAIL MCP TOOLS")
            print("========================================\n")

            for tool in tools_result.tools:

                print(f"- {tool.name}")

                if tool.description:
                    print(f"  {tool.description}")

                print()

            # -------------------------------------------------
            # Convert MCP tools to Ollama tools
            # -------------------------------------------------

            ollama_tools = []

            for tool in tools_result.tools:

                ollama_tools.append({
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description or "",
                        "parameters": tool.inputSchema,
                    }
                })

            # -------------------------------------------------
            # Ready
            # -------------------------------------------------

            print("========================================")
            print("        LOCAL GMAIL AI READY")
            print("========================================")

            print(f"\nModel: {model}")

            print("\nCommands:")
            print("  exit  - Exit the application")
            print("  model - Change the local model")

            print("\n========================================\n")

            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are a local AI assistant with access to "
                        "Gmail through MCP tools.\n\n"

                        "Use Gmail MCP tools whenever the user asks "
                        "about Gmail or emails.\n\n"

                        "Never invent email information.\n\n"

                        "When actual Gmail information is required, "
                        "always use the appropriate MCP tool."
                    )
                }
            ]

            # -------------------------------------------------
            # Chat loop
            # -------------------------------------------------

            while True:

                user_input = input("You: ").strip()

                if not user_input:
                    continue

                # ---------------------------------------------
                # Exit
                # ---------------------------------------------

                if user_input.lower() in [
                    "exit",
                    "quit"
                ]:

                    print("\nGoodbye!")

                    break

                # ---------------------------------------------
                # Change model
                # ---------------------------------------------

                if user_input.lower() == "model":

                    new_model = select_model()

                    if new_model:

                        model = new_model

                        print(
                            f"\nSwitched to: {model}\n"
                        )

                    continue

                # ---------------------------------------------
                # Add user message
                # ---------------------------------------------

                messages.append({
                    "role": "user",
                    "content": user_input
                })

                try:

                    # -----------------------------------------
                    # Ask local model
                    # -----------------------------------------

                    response = chat(
                        model=model,
                        messages=messages,
                        tools=ollama_tools
                    )

                    assistant_message = response.message

                    # -----------------------------------------
                    # Save assistant message
                    # -----------------------------------------

                    messages.append(
                        assistant_message
                    )

                    # -----------------------------------------
                    # Tool calls
                    # -----------------------------------------

                    if assistant_message.tool_calls:

                        for tool_call in assistant_message.tool_calls:

                            tool_name = (
                                tool_call.function.name
                            )

                            tool_arguments = (
                                tool_call.function.arguments
                            )

                            print(
                                f"\n[MCP TOOL CALL] "
                                f"{tool_name}"
                            )

                            print(
                                "[Arguments]"
                            )

                            print(
                                json.dumps(
                                    tool_arguments,
                                    indent=2
                                )
                            )

                            try:

                                # ---------------------------------
                                # Execute MCP tool
                                # ---------------------------------

                                result = await session.call_tool(
                                    tool_name,
                                    arguments=tool_arguments
                                )

                                result_text = ""

                                for content in result.content:

                                    if hasattr(
                                        content,
                                        "text"
                                    ):

                                        result_text += (
                                            content.text
                                        )

                                    else:

                                        result_text += str(
                                            content
                                        )

                                print(
                                    "[MCP TOOL RESULT RECEIVED]"
                                )

                                # ---------------------------------
                                # Send result to local model
                                # ---------------------------------

                                messages.append({
                                    "role": "tool",
                                    "content": result_text
                                })

                            except Exception as e:

                                error_message = (
                                    f"Error executing MCP "
                                    f"tool {tool_name}: {str(e)}"
                                )

                                print(
                                    error_message
                                )

                                messages.append({
                                    "role": "tool",
                                    "content": error_message
                                })

                        # -----------------------------------------
                        # Final model response
                        # -----------------------------------------

                        final_response = chat(
                            model=model,
                            messages=messages,
                            tools=ollama_tools
                        )

                        final_message = (
                            final_response.message
                        )

                        messages.append(
                            final_message
                        )

                        print(
                            f"\nAI: "
                            f"{final_message.content}\n"
                        )

                    else:

                        # -----------------------------------------
                        # Normal response without tool call
                        # -----------------------------------------

                        print(
                            f"\nAI: "
                            f"{assistant_message.content}\n"
                        )

                except Exception as e:

                    print(
                        f"\nERROR: {e}\n"
                    )


# ---------------------------------------------------------
# Entry Point
# ---------------------------------------------------------

if __name__ == "__main__":

    asyncio.run(main())