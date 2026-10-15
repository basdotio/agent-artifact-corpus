"""
Simple SSE MCP Server for Headless PM
"""

import asyncio
import json
import logging
from typing import Any, Dict, Optional
from datetime import datetime
import uuid

from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse
import httpx

logging.basicConfig(level=logging.INFO, format='[MCP-SSE] %(message)s')
logger = logging.getLogger("headless-pm-mcp-sse")


class SimpleMCPSSEServer:
    def __init__(self, base_url: str = "http://localhost:6969"):
        self.base_url = base_url.rstrip('/')
        self.app = FastAPI(title="Headless PM MCP SSE Server")
        self.client = httpx.AsyncClient(timeout=30.0)
        self.sessions = {}
        
        # Set up routes
        self._setup_routes()
    
    def _setup_routes(self):
        @self.app.get("/")
        async def root():
            """SSE endpoint - this is where Claude Code connects"""
            async def event_generator():
                session_id = str(uuid.uuid4())
                session = {
                    "id": session_id,
                    "agent_id": None,
                    "agent_role": None,
                    "agent_skill_level": None
                }
                self.sessions[session_id] = session
                
                try:
                    # Send initial message
                    yield f"data: {json.dumps({'type': 'connection', 'sessionId': session_id})}\n\n"
                    
                    # Keep connection alive
                    while True:
                        await asyncio.sleep(30)
                        yield f"data: {json.dumps({'type': 'ping'})}\n\n"
                        
                except asyncio.CancelledError:
                    # Cleanup on disconnect
                    if session_id in self.sessions:
                        del self.sessions[session_id]
                    raise
            
            return StreamingResponse(
                event_generator(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no"
                }
            )
        
        @self.app.post("/")
        async def handle_message(request: Request):
            """Handle JSON-RPC messages from Claude Code"""
            try:
                body = await request.json()
                logger.info(f"Received message: {json.dumps(body, indent=2)}")
                
                method = body.get("method", "")
                params = body.get("params", {})
                request_id = body.get("id")
                
                # Handle different methods
                if method == "initialize":
                    result = {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {
                            "tools": {},
                            "resources": {}
                        },
                        "serverInfo": {
                            "name": "headless-pm",
                            "version": "1.0.0"
                        }
                    }
                
                elif method == "tools/list":
                    result = {
                        "tools": [
                            {
                                "name": "register_agent",
                                "description": "Register agent with Headless PM",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "agent_id": {"type": "string"},
                                        "role": {
                                            "type": "string",
                                            "enum": ["frontend_dev", "backend_dev", "architect", "pm", "qa"]
                                        },
                                        "skill_level": {
                                            "type": "string",
                                            "enum": ["junior", "senior", "principal"],
                                            "default": "senior"
                                        }
                                    },
                                    "required": ["agent_id", "role"]
                                }
                            },
                            {
                                "name": "get_project_context",
                                "description": "Get project context"
                            },
                            {
                                "name": "get_next_task",
                                "description": "Get next available task"
                            }
                        ]
                    }
                
                elif method == "tools/call":
                    tool_name = params.get("name")
                    arguments = params.get("arguments", {})
                    
                    if tool_name == "register_agent":
                        # Register with backend
                        agent_data = {
                            "agent_id": arguments["agent_id"],
                            "role": arguments["role"],
                            "level": arguments.get("skill_level", "senior"),
                            "connection_type": "mcp_sse"
                        }
                        
                        response = await self.client.post(
                            f"{self.base_url}/api/v1/register",
                            json=agent_data
                        )
                        
                        result = {
                            "content": [
                                {
                                    "type": "text",
                                    "text": f"Registered as {arguments['role']} agent: {arguments['agent_id']}"
                                }
                            ]
                        }
                    
                    elif tool_name == "get_project_context":
                        response = await self.client.get(f"{self.base_url}/api/v1/context")
                        context = response.json()
                        
                        result = {
                            "content": [
                                {
                                    "type": "text",
                                    "text": json.dumps(context, indent=2)
                                }
                            ]
                        }
                    
                    else:
                        result = {
                            "content": [
                                {
                                    "type": "text",
                                    "text": f"Tool {tool_name} not implemented yet"
                                }
                            ]
                        }
                
                else:
                    # Unknown method
                    return {
                        "jsonrpc": "2.0",
                        "error": {
                            "code": -32601,
                            "message": f"Method not found: {method}"
                        },
                        "id": request_id
                    }
                
                # Return JSON-RPC response
                return {
                    "jsonrpc": "2.0",
                    "result": result,
                    "id": request_id
                }
                
            except Exception as e:
                logger.error(f"Error processing request: {e}")
                return {
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32603,
                        "message": str(e)
                    },
                    "id": body.get("id") if "body" in locals() else None
                }
        
        @self.app.on_event("shutdown")
        async def shutdown():
            await self.client.aclose()


def create_app(base_url: str = None) -> FastAPI:
    """Create FastAPI app."""
    import os
    
    if base_url is None:
        base_url = os.getenv('HEADLESS_PM_URL', 'http://localhost:6969')
    
    server = SimpleMCPSSEServer(base_url)
    return server.app


# For running with uvicorn
app = create_app()