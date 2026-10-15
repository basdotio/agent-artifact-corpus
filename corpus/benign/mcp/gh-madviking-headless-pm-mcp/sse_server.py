"""
MCP SSE (Server-Sent Events) Server for Headless PM
Implements MCP protocol over SSE transport for Claude Code
"""

import asyncio
import json
import logging
import uuid
from typing import Any, Dict, Optional, AsyncGenerator
from datetime import datetime

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import httpx

from .token_tracker import TokenTracker

logging.basicConfig(level=logging.INFO, format='[MCP-SSE] %(message)s')
logger = logging.getLogger("headless-pm-mcp-sse")


class SSEMCPServer:
    """MCP Server implementing SSE transport."""
    
    def __init__(self, base_url: str = "http://localhost:6969"):
        self.base_url = base_url.rstrip('/')
        self.app = FastAPI(
            title="Headless PM MCP SSE Server",
            version="1.0.0",
            description="MCP server with SSE transport for Claude Code"
        )
        self.client = httpx.AsyncClient(timeout=30.0)
        self.token_tracker = TokenTracker()
        self.sessions: Dict[str, Dict[str, Any]] = {}
        
        # Register routes
        self._register_routes()
    
    def _register_routes(self):
        """Register SSE routes."""
        
        @self.app.get("/")
        async def sse_endpoint(request: Request):
            """SSE endpoint for MCP communication."""
            session_id = str(uuid.uuid4())
            self.sessions[session_id] = {
                "id": session_id,
                "created_at": datetime.now().isoformat(),
                "agent_id": None,
                "agent_role": None,
                "agent_skill_level": None,
                "message_queue": asyncio.Queue()
            }
            
            return StreamingResponse(
                self._sse_stream(session_id, request),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "X-Accel-Buffering": "no",
                    "Connection": "keep-alive"
                }
            )
        
        @self.app.post("/messages")
        async def handle_message_endpoint(request: Request):
            """Handle incoming messages from the client."""
            try:
                body = await request.json()
                session_id = request.headers.get("X-Session-ID")
                
                if not session_id or session_id not in self.sessions:
                    raise HTTPException(status_code=400, detail="Invalid session")
                
                session = self.sessions[session_id]
                await self._handle_message(body, session)
                
                return {"status": "ok"}
            
            except Exception as e:
                logger.error(f"Error handling message: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.on_event("shutdown")
        async def shutdown():
            await self.client.aclose()
    
    async def _sse_stream(self, session_id: str, request: Request) -> AsyncGenerator[str, None]:
        """Generate SSE stream for the session."""
        session = self.sessions[session_id]
        
        try:
            # Send initial connection event
            yield f"event: connected\ndata: {json.dumps({'session_id': session_id})}\n\n"
            
            # Create a background task to read messages from the client
            # SSE is one-way, so we'll need a separate endpoint for client messages
            
            # Main message loop
            while True:
                try:
                    # Check for messages to send
                    message = await asyncio.wait_for(
                        session["message_queue"].get(),
                        timeout=30.0  # 30 second timeout for keepalive
                    )
                    
                    # Send message as SSE event
                    yield f"event: message\ndata: {json.dumps(message)}\n\n"
                    
                except asyncio.TimeoutError:
                    # Send keepalive
                    yield f"event: ping\ndata: {json.dumps({'timestamp': datetime.now().isoformat()})}\n\n"
                
                except asyncio.CancelledError:
                    break
                
        except Exception as e:
            logger.error(f"Error in SSE stream: {e}")
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
        
        finally:
            # Cleanup session
            del self.sessions[session_id]
    
    async def _handle_message(self, message: Dict[str, Any], session: Dict[str, Any]) -> None:
        """Handle incoming message and queue response."""
        method = message.get("method", "")
        params = message.get("params", {})
        request_id = message.get("id")
        
        try:
            # Route to appropriate handler
            if method == "initialize":
                result = await self._handle_initialize(params, session)
            elif method == "tools/list":
                result = await self._handle_list_tools()
            elif method == "tools/call":
                result = await self._handle_call_tool(params, session)
            elif method == "resources/list":
                result = await self._handle_list_resources()
            elif method == "resources/read":
                result = await self._handle_read_resource(params)
            else:
                raise ValueError(f"Unknown method: {method}")
            
            # Queue response
            response = {
                "jsonrpc": "2.0",
                "result": result,
                "id": request_id
            }
            await session["message_queue"].put(response)
            
        except Exception as e:
            logger.error(f"Error handling method {method}: {e}")
            error_response = {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,
                    "message": str(e)
                },
                "id": request_id
            }
            await session["message_queue"].put(error_response)
    
    async def _handle_initialize(self, params: Dict[str, Any], session: Dict[str, Any]) -> Dict[str, Any]:
        """Handle initialize request."""
        return {
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
    
    async def _handle_list_tools(self) -> Dict[str, Any]:
        """Handle tools/list request."""
        tools = [
            {
                "name": "register_agent",
                "description": "Register agent with Headless PM system",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "agent_id": {
                            "type": "string",
                            "description": "Unique identifier for the agent"
                        },
                        "role": {
                            "type": "string",
                            "description": "Agent role",
                            "enum": ["frontend_dev", "backend_dev", "architect", "pm", "qa"]
                        },
                        "skill_level": {
                            "type": "string",
                            "description": "Agent skill level",
                            "enum": ["junior", "senior", "principal"],
                            "default": "senior"
                        }
                    },
                    "required": ["agent_id", "role"]
                }
            },
            {
                "name": "get_project_context",
                "description": "Get project configuration and context information"
            },
            {
                "name": "get_next_task",
                "description": "Get next available task for the registered agent"
            },
            {
                "name": "create_task",
                "description": "Create a new task"
            },
            {
                "name": "lock_task",
                "description": "Lock a task to prevent other agents from picking it up"
            },
            {
                "name": "update_task_status",
                "description": "Update task status and progress"
            },
            {
                "name": "create_document",
                "description": "Create a document with optional @mentions"
            },
            {
                "name": "get_mentions",
                "description": "Get notifications and mentions"
            },
            {
                "name": "register_service",
                "description": "Register a microservice"
            },
            {
                "name": "send_heartbeat",
                "description": "Send service heartbeat"
            },
            {
                "name": "poll_changes",
                "description": "Poll for system changes"
            }
        ]
        
        return {"tools": tools}
    
    async def _handle_call_tool(self, params: Dict[str, Any], session: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools/call request."""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        # Track request
        self.token_tracker.track_request({"tool": tool_name, "args": arguments})
        
        try:
            # Tool implementations (simplified for brevity)
            if tool_name == "register_agent":
                agent_id = arguments["agent_id"]
                role = arguments["role"]
                skill_level = arguments.get("skill_level", "senior")
                
                # Update session
                session.update({
                    "agent_id": agent_id,
                    "agent_role": role,
                    "agent_skill_level": skill_level
                })
                
                # Register with API
                data = {
                    "agent_id": agent_id,
                    "role": role,
                    "level": skill_level,
                    "connection_type": "mcp_sse"
                }
                
                response = await self.client.post(f"{self.base_url}/api/v1/register", json=data)
                result = response.json()
                
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Agent {agent_id} registered as {role} ({skill_level})"
                        }
                    ]
                }
            
            elif tool_name == "get_project_context":
                response = await self.client.get(f"{self.base_url}/api/v1/context")
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(response.json(), indent=2)
                        }
                    ]
                }
            
            # Add other tool implementations...
            else:
                raise ValueError(f"Unknown tool: {tool_name}")
            
        except Exception as e:
            logger.error(f"Error calling tool {tool_name}: {e}")
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Error: {str(e)}"
                    }
                ],
                "isError": True
            }
    
    async def _handle_list_resources(self) -> Dict[str, Any]:
        """Handle resources/list request."""
        resources = [
            {
                "uri": "headless-pm://tasks/list",
                "name": "Current Tasks",
                "description": "List of all current tasks"
            },
            {
                "uri": "headless-pm://agents/list",
                "name": "Active Agents",
                "description": "List of all registered agents"
            }
        ]
        
        return {"resources": resources}
    
    async def _handle_read_resource(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle resources/read request."""
        uri = params.get("uri", "")
        
        try:
            if uri == "headless-pm://tasks/list":
                response = await self.client.get(f"{self.base_url}/api/v1/tasks")
                content = response.json()
            elif uri == "headless-pm://agents/list":
                response = await self.client.get(f"{self.base_url}/api/v1/agents")
                content = response.json()
            else:
                raise ValueError(f"Unknown resource URI: {uri}")
            
            return {
                "contents": [
                    {
                        "uri": uri,
                        "mimeType": "application/json",
                        "text": json.dumps(content, indent=2)
                    }
                ]
            }
        
        except Exception as e:
            logger.error(f"Error reading resource {uri}: {e}")
            raise


def create_app(base_url: str = None) -> FastAPI:
    """Create FastAPI app."""
    import os
    
    if base_url is None:
        base_url = os.getenv('HEADLESS_PM_URL', 'http://localhost:6969')
    
    server = SSEMCPServer(base_url)
    return server.app


# For running with uvicorn
app = create_app()