import os
import sys
from typing import Any, List
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.prompts import base

# ---------------------------------------------------------
# MCP Server Instance
# ---------------------------------------------------------
mcp = FastMCP("DocumentMCP", log_level="ERROR")

docs = {
    "deposition.md": "This deposition covers the testimony of Angela Smith, P.E.",
    "report.pdf": "The report details the state of a 20m condenser tower.",
    "financials.docx": "These financials outline the project's budget and expenditures.",
    "outlook.pdf": "This document presents the projected future performance of the system.",
    "plan.md": "The plan outlines the steps for the project's implementation.",
    "spec.txt": "These specifications define the technical requirements for the equipment.",
}


# ---------------------------------------------------------
# MCP Tools, Resources, and Prompts
# ---------------------------------------------------------
@mcp.tool(
    name="read_doc_contents",
    description="Read the contents of a document and return it as a string.",
)
def read_document(
    doc_id: str = Field(description="Id of the document to read"),
) -> str:
    if doc_id not in docs:
        raise ValueError(f"Doc with id '{doc_id}' not found")
    return docs[doc_id]


@mcp.tool(
    name="edit_document",
    description="Edit a document by replacing a string in the documents content with a new string",
)
def edit_document(
    doc_id: str = Field(description="Id of the document that will be edited"),
    old_str: str = Field(
        description="The text to replace. Must match exactly, including whitespace"
    ),
    new_str: str = Field(
        description="The new text to insert in place of the old text"
    ),
) -> str:
    if doc_id not in docs:
        raise ValueError(f"Doc with id '{doc_id}' not found")
    docs[doc_id] = docs[doc_id].replace(old_str, new_str)
    return docs[doc_id]


@mcp.resource("docs://documents", mime_type="application/json")
def list_docs() -> list[str]:
    return list(docs.keys())


@mcp.resource("docs://documents/{doc_id}", mime_type="text/plain")
def fetch_doc(doc_id: str) -> str:
    if doc_id not in docs:
        raise ValueError(f"Doc with id '{doc_id}' not found")
    return docs[doc_id]


@mcp.prompt(
    name="format",
    description="Rewrites the contents of the document in Markdown format.",
)
def format_document(
    doc_id: str = Field(description="Id of the document to format"),
) -> list[base.Message]:
    prompt = f"""
    Your goal is to reformat a document to be written with markdown syntax.

    The id of the document you need to reformat is:
    <document_id>
    {doc_id}
    </document_id>

    Add in headers, bullet points, tables, etc as necessary. Feel free to add in extra text, but don't change the meaning of the report.
    Use the 'edit_document' tool to edit the document. After the document has been edited, respond with the final version of the doc. Don't explain your changes.
    """
    return [base.UserMessage(prompt)]


# ---------------------------------------------------------
# FastAPI App Setup for Direct Postman Testing & OpenAPI Docs
# ---------------------------------------------------------
app = FastAPI(
    title="Document MCP Server API",
    description="FastAPI interface exposing Document MCP tools, resources, prompts, and SSE transport for Postman testing",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request Models
class ReadDocRequest(BaseModel):
    doc_id: str = Field(..., description="Id of the document to read", examples=["deposition.md"])


class EditDocRequest(BaseModel):
    doc_id: str = Field(..., description="Id of the document to edit", examples=["deposition.md"])
    old_str: str = Field(..., description="Exact string to replace", examples=["Angela Smith, P.E."])
    new_str: str = Field(..., description="New replacement string", examples=["Angela Smith, Ph.D."])


class FormatPromptRequest(BaseModel):
    doc_id: str = Field(..., description="Id of the document to format", examples=["deposition.md"])


# REST Endpoints for Postman
@app.get("/", summary="Server Info & Health Check")
def root():
    return {
        "status": "online",
        "server": "DocumentMCP",
        "description": "FastAPI Server for testing MCP tools, resources, and SSE in Postman",
        "endpoints": {
            "swagger_docs": "/docs",
            "openapi_schema": "/openapi.json",
            "list_documents": "/documents",
            "read_document": "/documents/{doc_id}",
            "tool_read": "/tools/read_doc_contents",
            "tool_edit": "/tools/edit_document",
            "prompt_format": "/prompts/format",
            "mcp_sse": "/sse",
            "mcp_sse_prefix": "/mcp/sse",
        },
    }


@app.get("/health", summary="Health check endpoint")
def health():
    return {"status": "ok", "documents_count": len(docs)}


@app.get("/documents", summary="List all document IDs", response_model=List[str])
def get_documents():
    return list_docs()


@app.get("/documents/{doc_id}", summary="Get contents of a specific document")
def get_document(doc_id: str):
    try:
        return {"doc_id": doc_id, "content": fetch_doc(doc_id)}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/tools/read_doc_contents", summary="Execute read_doc_contents tool")
def api_read_doc(body: ReadDocRequest):
    try:
        content = read_document(body.doc_id)
        return {"doc_id": body.doc_id, "content": content}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/tools/edit_document", summary="Execute edit_document tool")
def api_edit_doc(body: EditDocRequest):
    try:
        updated_content = edit_document(body.doc_id, body.old_str, body.new_str)
        return {"doc_id": body.doc_id, "content": updated_content, "message": "Document updated successfully"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/prompts/format", summary="Generate format prompt for a document")
def api_format_prompt(body: FormatPromptRequest):
    try:
        messages = format_document(body.doc_id)
        formatted_messages = [
            {"role": msg.role, "content": msg.content.text if hasattr(msg.content, "text") else str(msg.content)}
            for msg in messages
        ]
        return {"doc_id": body.doc_id, "messages": formatted_messages}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/tools", summary="List available MCP tools metadata")
def api_list_tools():
    return {
        "tools": [
            {
                "name": "read_doc_contents",
                "description": "Read the contents of a document and return it as a string.",
                "parameters": {"doc_id": "string"},
            },
            {
                "name": "edit_document",
                "description": "Edit a document by replacing a string in the documents content with a new string",
                "parameters": {"doc_id": "string", "old_str": "string", "new_str": "string"},
            },
        ]
    }


@app.get("/prompts", summary="List available MCP prompts metadata")
def api_list_prompts():
    return {
        "prompts": [
            {
                "name": "format",
                "description": "Rewrites the contents of the document in Markdown format.",
                "parameters": {"doc_id": "string"},
            }
        ]
    }


@app.get("/resources", summary="List available MCP resources metadata")
def api_list_resources():
    return {
        "resources": [
            {"uri": "docs://documents", "name": "Document list", "mime_type": "application/json"},
            {"uri": "docs://documents/{doc_id}", "name": "Document content", "mime_type": "text/plain"},
        ]
    }


# Mount FastMCP SSE transports so Postman's MCP client can connect
# Mount at /mcp (/mcp/sse and /mcp/messages) as well as fallback at /
app.mount("/mcp", mcp.sse_app())
app.mount("/", mcp.sse_app())


# ---------------------------------------------------------
# Execution Mode
# ---------------------------------------------------------
if __name__ == "__main__":
    if "--stdio" in sys.argv:
        mcp.run(transport="stdio")
    elif "--serve" in sys.argv or "--http" in sys.argv or sys.stdin.isatty():
        import uvicorn
        port = int(os.getenv("MCP_SERVER_PORT", "8001"))
        host = os.getenv("MCP_SERVER_HOST", "0.0.0.0")
        print(f"🚀 Starting Document MCP FastAPI Server on http://{host}:{port}")
        print(f"📖 Swagger Docs for Postman: http://127.0.0.1:{port}/docs")
        print(f"📡 MCP SSE Endpoint: http://127.0.0.1:{port}/sse")
        print(f"💡 For stdio transport (MCPClient / main.py), run with: python mcp_server.py --stdio")
        uvicorn.run("mcp_server:app", host=host, port=port, reload=True)
    else:
        mcp.run(transport="stdio")
