import asyncio
import os
import sys
from contextlib import AsyncExitStack, asynccontextmanager
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from core.cli import CliApp
from core.cli_chat import CliChat
from core.gemma import Gemma
from core.tools import ToolManager
from mcp_client import MCPClient

load_dotenv()

gemma_model = os.getenv("GEMMA_MODEL", "gemma4:31b-cloud")
assert gemma_model, "Error: GEMMA_MODEL cannot be empty. Update .env"


# ---------------------------------------------------------
# Application State & Lifespan
# ---------------------------------------------------------
class AppState:
    gemma_service: Optional[Gemma] = None
    doc_client: Optional[MCPClient] = None
    clients: Dict[str, MCPClient] = {}
    chat: Optional[CliChat] = None
    stack: Optional[AsyncExitStack] = None


state = AppState()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initializes Gemma and connects to MCP servers on startup."""
    print("Initializing Gemma service and MCP Client...")
    state.gemma_service = Gemma(model=gemma_model)
    state.stack = AsyncExitStack()

    command, args = (
        ("uv", ["run", "mcp_server.py", "--stdio"])
        if os.getenv("USE_UV", "0") == "1"
        else ("python", ["mcp_server.py", "--stdio"])
    )

    try:
        doc_client = await state.stack.enter_async_context(
            MCPClient(command=command, args=args)
        )
        state.doc_client = doc_client
        state.clients = {"doc_client": doc_client}

        # Check for any extra server scripts in environment
        extra_servers = os.getenv("EXTRA_MCP_SERVERS", "")
        if extra_servers:
            for i, server_script in enumerate(extra_servers.split(",")):
                server_script = server_script.strip()
                if server_script:
                    client_id = f"client_{i}_{server_script}"
                    client = await state.stack.enter_async_context(
                        MCPClient(command="uv", args=["run", server_script])
                    )
                    state.clients[client_id] = client

        state.chat = CliChat(
            doc_client=doc_client,
            clients=state.clients,
            gemma_service=state.gemma_service,
        )
        print("✅ MCP Client connected and Chat initialized.")
        yield
    finally:
        print("Shutting down MCP Client connections...")
        if state.stack:
            await state.stack.aclose()


# ---------------------------------------------------------
# FastAPI App Setup for Postman API Testing
# ---------------------------------------------------------
app = FastAPI(
    title="MCP Chat API",
    description="FastAPI interface for MCP Chat application. Enables Postman API testing for Chat, MCP Tools, and Documents.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------
# Request / Response Schemas
# ---------------------------------------------------------
class ChatRequest(BaseModel):
    query: str = Field(
        ...,
        description="Query text to send. Supports @doc_name mentions and /format commands.",
        examples=["@deposition.md whats inside this"],
    )
    reset_history: bool = Field(
        False,
        description="Whether to clear previous conversation history before processing this query.",
    )


class ChatResponse(BaseModel):
    query: str
    response: str
    message_count: int


class ToolCallRequest(BaseModel):
    tool_name: str = Field(
        ..., description="Name of the tool to invoke", examples=["read_doc_contents"]
    )
    tool_input: Dict[str, Any] = Field(
        default_factory=dict,
        description="Input parameters for the tool",
        examples=[{"doc_id": "deposition.md"}],
    )
    client_id: Optional[str] = Field(
        "doc_client",
        description="Target MCP client ID (default: doc_client)",
    )


# ---------------------------------------------------------
# REST API Endpoints for Postman
# ---------------------------------------------------------
@app.get("/", summary="Root status and available endpoints")
def root():
    return {
        "status": "online",
        "app": "MCP Chat API",
        "gemma_model": gemma_model,
        "endpoints": {
            "swagger_docs": "/docs",
            "openapi_schema": "/openapi.json",
            "health": "/health",
            "chat": "POST /chat",
            "chat_history": "GET /chat/history",
            "chat_reset": "POST /chat/reset",
            "list_documents": "GET /documents",
            "read_document": "GET /documents/{doc_id}",
            "list_prompts": "GET /prompts",
            "list_tools": "GET /tools",
            "call_tool": "POST /tools/call",
        },
        "postman_usage": "Import http://localhost:8000/openapi.json into Postman to automatically generate all requests.",
    }


@app.get("/health", summary="Health check endpoint")
def health():
    return {
        "status": "ok",
        "model": gemma_model,
        "connected_clients": list(state.clients.keys()),
        "ready": state.chat is not None,
    }


@app.post("/chat", response_model=ChatResponse, summary="Send message to AI assistant")
async def chat_endpoint(request: ChatRequest):
    if not state.chat:
        raise HTTPException(status_code=503, detail="Chat service not yet initialized")

    if request.reset_history:
        state.chat.messages = []

    try:
        response_text = await state.chat.run(request.query)
        return ChatResponse(
            query=request.query,
            response=response_text,
            message_count=len(state.chat.messages),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")


@app.get("/chat/history", summary="Get conversation history")
def get_chat_history():
    if not state.chat:
        return {"messages": []}
    return {"messages": state.chat.messages, "count": len(state.chat.messages)}


@app.post("/chat/reset", summary="Reset conversation history")
def reset_chat_history():
    if state.chat:
        state.chat.messages = []
    return {"status": "success", "message": "Conversation history cleared"}


@app.get("/documents", summary="List all document IDs available via MCP")
async def list_documents():
    if not state.chat:
        raise HTTPException(status_code=503, detail="MCP Client not ready")
    try:
        docs = await state.chat.list_docs_ids()
        return {"documents": docs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/documents/{doc_id}", summary="Get content of a document via MCP")
async def get_document(doc_id: str):
    if not state.chat:
        raise HTTPException(status_code=503, detail="MCP Client not ready")
    try:
        content = await state.chat.get_doc_content(doc_id)
        return {"doc_id": doc_id, "content": content}
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/prompts", summary="List available MCP prompts")
async def list_prompts():
    if not state.chat:
        raise HTTPException(status_code=503, detail="MCP Client not ready")
    try:
        prompts = await state.chat.list_prompts()
        return {
            "prompts": [
                {
                    "name": p.name,
                    "description": p.description,
                    "arguments": [
                        {"name": arg.name, "description": arg.description, "required": arg.required}
                        for arg in (p.arguments or [])
                    ],
                }
                for p in prompts
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/tools", summary="List all available MCP tools")
async def list_tools():
    if not state.clients:
        raise HTTPException(status_code=503, detail="No MCP clients connected")
    try:
        tools = await ToolManager.get_all_tools(state.clients)
        return {"tools": tools}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/tools/call", summary="Directly execute an MCP tool")
async def call_tool_endpoint(request: ToolCallRequest):
    client = state.clients.get(request.client_id)
    if not client:
        raise HTTPException(
            status_code=404,
            detail=f"Client '{request.client_id}' not found. Available: {list(state.clients.keys())}",
        )
    try:
        result = await client.call_tool(request.tool_name, request.tool_input)
        contents = []
        if result and result.content:
            for item in result.content:
                if hasattr(item, "text"):
                    contents.append(item.text)
                else:
                    contents.append(str(item))
        return {
            "tool_name": request.tool_name,
            "tool_input": request.tool_input,
            "result": contents,
            "is_error": result.isError if result else False,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------
# CLI Mode Runner
# ---------------------------------------------------------
async def run_cli():
    """Runs the interactive terminal prompt-toolkit CLI."""
    gemma_service = Gemma(model=gemma_model)
    server_scripts = [arg for arg in sys.argv[1:] if not arg.startswith("--")]
    clients = {}

    command, args = (
        ("uv", ["run", "mcp_server.py", "--stdio"])
        if os.getenv("USE_UV", "0") == "1"
        else ("python", ["mcp_server.py", "--stdio"])
    )

    async with AsyncExitStack() as stack:
        doc_client = await stack.enter_async_context(
            MCPClient(command=command, args=args)
        )
        clients["doc_client"] = doc_client

        for i, server_script in enumerate(server_scripts):
            client_id = f"client_{i}_{server_script}"
            client = await stack.enter_async_context(
                MCPClient(command="uv", args=["run", server_script])
            )
            clients[client_id] = client

        chat = CliChat(
            doc_client=doc_client,
            clients=clients,
            gemma_service=gemma_service,
        )

        cli = CliApp(chat)
        await cli.initialize()
        await cli.run()


# ---------------------------------------------------------
# Execution Mode
# ---------------------------------------------------------
if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    if "--cli" in sys.argv:
        asyncio.run(run_cli())
    else:
        import uvicorn
        port = int(os.getenv("PORT", "8000"))
        host = os.getenv("HOST", "0.0.0.0")
        print(f"🚀 Starting MCP Chat FastAPI Server on http://{host}:{port}")
        print(f"📖 Swagger UI for Postman testing: http://127.0.0.1:{port}/docs")
        print(f"💡 For interactive CLI mode instead, use: uv run main.py --cli")
        uvicorn.run("main:app", host=host, port=port, reload=True)
