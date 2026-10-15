"""
MCP Streamable HTTP Server for Headless PM
Implements the MCP protocol over HTTP transport for network connections
"""

import json
import logging
from typing import Any, Dict, Optional, List
from datetime import datetime
import uuid

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
import httpx

from .token_tracker import TokenTracker

logging.basicConfig(level=logging.INFO, format='[MCP-HTTP] %(message)s')
logger = logging.getLogger("headless-pm-mcp-http")


class JSONRPCRequest(BaseModel):
    """JSON-RPC 2.0 Request"""
    jsonrpc: str = "2.0"
    method: str
    params: Optional[Dict[str, Any]] = None
    id: Optional[Any] = None


class JSONRPCResponse(BaseModel):
    """JSON-RPC 2.0 Response"""
    jsonrpc: str = "2.0"
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None
    id: Optional[Any] = None


class StreamableHTTPMCPServer:
    """MCP Server implementing Streamable HTTP transport."""
    
    def __init__(self, base_url: str = "http://localhost:6969"):
        self.base_url = base_url.rstrip('/')
        self.app = FastAPI(
            title="Headless PM MCP Server",
            version="1.0.0",
            description="MCP server with Streamable HTTP transport"
        )
        self.client = httpx.AsyncClient(timeout=30.0)
        self.token_tracker = TokenTracker()
        self.sessions: Dict[str, Dict[str, Any]] = {}
        
        # Register routes
        self._register_routes()
    
    def _register_routes(self):
        """Register HTTP routes for MCP protocol."""
        
        @self.app.post("/")
        async def handle_jsonrpc(request: Request) -> JSONResponse:
            """Handle JSON-RPC requests for MCP protocol."""
            try:
                # Parse request body
                body = await request.body()
                data = json.loads(body)
                
                # Handle batch requests
                if isinstance(data, list):
                    responses = []
                    for req in data:
                        response = await self._handle_single_request(req, request)
                        if response:  # Don't include responses for notifications
                            responses.append(response)
                    return JSONResponse(content=responses)
                else:
                    # Single request
                    response = await self._handle_single_request(data, request)
                    if response:
                        return JSONResponse(content=response)
                    else:
                        # Notification - no response
                        return Response(status_code=204)
            
            except json.JSONDecodeError:
                return JSONResponse(
                    content={
                        "jsonrpc": "2.0",
                        "error": {
                            "code": -32700,
                            "message": "Parse error"
                        },
                        "id": None
                    },
                    status_code=400
                )
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                return JSONResponse(
                    content={
                        "jsonrpc": "2.0",
                        "error": {
                            "code": -32603,
                            "message": "Internal error",
                            "data": str(e)
                        },
                        "id": None
                    },
                    status_code=500
                )
        
        @self.app.on_event("shutdown")
        async def shutdown():
            await self.client.aclose()
    
    async def _handle_single_request(self, data: Dict[str, Any], request: Request) -> Optional[Dict[str, Any]]:
        """Handle a single JSON-RPC request."""
        method = data.get("method", "")
        params = data.get("params", {})
        request_id = data.get("id")
        
        # Get or create session
        session_id = request.headers.get("X-Session-ID", str(uuid.uuid4()))
        if session_id not in self.sessions:
            self.sessions[session_id] = {
                "id": session_id,
                "created_at": datetime.now().isoformat(),
                "agent_id": None,
                "agent_role": None,
                "agent_skill_level": None
            }
        
        session = self.sessions[session_id]
        
        try:
            # Route to appropriate handler
            if method == "initialize":
                result = await self._handle_initialize(params, session)
            elif method == "notifications/initialized":
                # This is a notification, no response needed
                return None
            elif method == "tools/list":
                result = await self._handle_list_tools()
            elif method == "tools/call":
                result = await self._handle_call_tool(params, session)
            elif method == "resources/list":
                result = await self._handle_list_resources()
            elif method == "resources/read":
                result = await self._handle_read_resource(params)
            elif method == "ping":
                result = {"status": "pong"}
            else:
                raise ValueError(f"Method not found: {method}")
            
            # Return response only if request has an ID (not a notification)
            if request_id is not None:
                return {
                    "jsonrpc": "2.0",
                    "result": result,
                    "id": request_id
                }
            else:
                return None
        
        except Exception as e:
            logger.error(f"Error handling method {method}: {e}")
            if request_id is not None:
                return {
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32603,
                        "message": str(e)
                    },
                    "id": request_id
                }
            else:
                return None
    
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
                "description": "Get project configuration and context information",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "get_next_task",
                "description": "Get next available task for the registered agent",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "role": {
                            "type": "string",
                            "description": "Override agent role for task search"
                        },
                        "skill_level": {
                            "type": "string",
                            "description": "Override skill level for task search"
                        }
                    }
                }
            },
            {
                "name": "create_task",
                "description": "Create a new task",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "description": {"type": "string"},
                        "complexity": {
                            "type": "string",
                            "enum": ["minor", "major"]
                        },
                        "role": {"type": "string"},
                        "skill_level": {
                            "type": "string",
                            "enum": ["junior", "senior", "principal"]
                        }
                    },
                    "required": ["title", "description", "complexity"]
                }
            },
            {
                "name": "lock_task",
                "description": "Lock a task to prevent other agents from picking it up",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "task_id": {
                            "type": "integer",
                            "description": "ID of the task to lock"
                        }
                    },
                    "required": ["task_id"]
                }
            },
            {
                "name": "update_task_status",
                "description": "Update task status and progress",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "integer"},
                        "status": {
                            "type": "string",
                            "enum": ["created", "assigned", "under_work", "dev_done", "testing", "completed", "blocked"]
                        },
                        "notes": {"type": "string"}
                    },
                    "required": ["task_id", "status"]
                }
            },
            {
                "name": "create_document",
                "description": "Create a document with optional @mentions",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "content": {"type": "string"},
                        "doc_type": {
                            "type": "string",
                            "default": "note"
                        },
                        "mentions": {
                            "type": "array",
                            "items": {"type": "string"}
                        }
                    },
                    "required": ["title", "content"]
                }
            },
            {
                "name": "get_mentions",
                "description": "Get notifications and mentions for the registered agent",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "register_service",
                "description": "Register a microservice with the system",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "service_name": {"type": "string"},
                        "service_url": {"type": "string"},
                        "health_check_url": {"type": "string"}
                    },
                    "required": ["service_name", "service_url"]
                }
            },
            {
                "name": "send_heartbeat",
                "description": "Send heartbeat for a registered service",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "service_name": {"type": "string"},
                        "status": {
                            "type": "string",
                            "default": "healthy"
                        }
                    },
                    "required": ["service_name"]
                }
            },
            {
                "name": "poll_changes",
                "description": "Poll for system changes since a given timestamp",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "since_timestamp": {"type": "string"}
                    }
                }
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
            if tool_name == "register_agent":
                result = await self._register_agent(arguments, session)
            elif tool_name == "get_project_context":
                result = await self._get_project_context()
            elif tool_name == "get_next_task":
                result = await self._get_next_task(arguments, session)
            elif tool_name == "create_task":
                result = await self._create_task(arguments, session)
            elif tool_name == "lock_task":
                result = await self._lock_task(arguments, session)
            elif tool_name == "update_task_status":
                result = await self._update_task_status(arguments, session)
            elif tool_name == "create_document":
                result = await self._create_document(arguments, session)
            elif tool_name == "get_mentions":
                result = await self._get_mentions(session)
            elif tool_name == "register_service":
                result = await self._register_service(arguments, session)
            elif tool_name == "send_heartbeat":
                result = await self._send_heartbeat(arguments)
            elif tool_name == "poll_changes":
                result = await self._poll_changes(arguments)
            else:
                raise ValueError(f"Unknown tool: {tool_name}")
            
            # Track response
            self.token_tracker.track_response(result)
            
            # Return in MCP format
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(result, indent=2) if isinstance(result, dict) else str(result)
                    }
                ]
            }
        
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
                "description": "List of all current tasks in the system",
                "mimeType": "application/json"
            },
            {
                "uri": "headless-pm://agents/list",
                "name": "Active Agents",
                "description": "List of all registered agents",
                "mimeType": "application/json"
            },
            {
                "uri": "headless-pm://documents/recent",
                "name": "Recent Documents",
                "description": "Recently created documents",
                "mimeType": "application/json"
            },
            {
                "uri": "headless-pm://services/status",
                "name": "Service Status",
                "description": "Status of all registered services",
                "mimeType": "application/json"
            },
            {
                "uri": "headless-pm://changelog/recent",
                "name": "Recent Activity",
                "description": "Recent system activity",
                "mimeType": "application/json"
            },
            {
                "uri": "headless-pm://context/project",
                "name": "Project Context",
                "description": "Current project configuration",
                "mimeType": "application/json"
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
            elif uri == "headless-pm://documents/recent":
                response = await self.client.get(f"{self.base_url}/api/v1/documents?limit=20")
                content = response.json()
            elif uri == "headless-pm://services/status":
                response = await self.client.get(f"{self.base_url}/api/v1/services")
                content = response.json()
            elif uri == "headless-pm://changelog/recent":
                response = await self.client.get(f"{self.base_url}/api/v1/changelog?limit=50")
                content = response.json()
            elif uri == "headless-pm://context/project":
                response = await self.client.get(f"{self.base_url}/api/v1/context")
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
    
    # Tool implementation methods (same as before)
    async def _register_agent(self, args: Dict[str, Any], session: Dict[str, Any]) -> Dict[str, Any]:
        """Register agent."""
        agent_id = args["agent_id"]
        role = args["role"]
        skill_level = args.get("skill_level", "senior")
        
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
            "connection_type": "mcp_streamable_http"
        }
        
        response = await self.client.post(f"{self.base_url}/api/v1/register", json=data)
        result = response.json()
        
        return {
            "success": True,
            "agent_id": agent_id,
            "role": role,
            "skill_level": skill_level,
            "message": f"Agent {agent_id} registered as {role} ({skill_level})"
        }
    
    async def _get_project_context(self) -> Dict[str, Any]:
        """Get project context."""
        response = await self.client.get(f"{self.base_url}/api/v1/context")
        return response.json()
    
    async def _get_next_task(self, args: Dict[str, Any], session: Dict[str, Any]) -> Dict[str, Any]:
        """Get next task."""
        query_params = {
            "role": args.get("role", session.get("agent_role")),
            "skill_level": args.get("skill_level", session.get("agent_skill_level"))
        }
        
        response = await self.client.get(f"{self.base_url}/api/v1/tasks/next", params=query_params)
        if response.status_code == 200:
            return response.json()
        else:
            return {"message": "No tasks available"}
    
    async def _create_task(self, args: Dict[str, Any], session: Dict[str, Any]) -> Dict[str, Any]:
        """Create task."""
        data = {
            "title": args["title"],
            "description": args["description"],
            "complexity": args["complexity"],
            "role": args.get("role", session.get("agent_role")),
            "skill_level": args.get("skill_level", session.get("agent_skill_level"))
        }
        
        response = await self.client.post(f"{self.base_url}/api/v1/tasks/create", json=data)
        return response.json()
    
    async def _lock_task(self, args: Dict[str, Any], session: Dict[str, Any]) -> Dict[str, Any]:
        """Lock task."""
        task_id = args["task_id"]
        agent_id = session.get("agent_id")
        
        if not agent_id:
            raise ValueError("Agent not registered")
        
        response = await self.client.post(
            f"{self.base_url}/api/v1/tasks/{task_id}/lock",
            json={"agent_id": agent_id}
        )
        
        return {"success": True, "task_id": task_id, "locked_by": agent_id}
    
    async def _update_task_status(self, args: Dict[str, Any], session: Dict[str, Any]) -> Dict[str, Any]:
        """Update task status."""
        task_id = args["task_id"]
        agent_id = session.get("agent_id")
        
        if not agent_id:
            raise ValueError("Agent not registered")
        
        data = {
            "status": args["status"],
            "agent_id": agent_id
        }
        
        if "notes" in args:
            data["notes"] = args["notes"]
        
        response = await self.client.put(
            f"{self.base_url}/api/v1/tasks/{task_id}/status",
            json=data
        )
        
        return {"success": True, "task_id": task_id, "status": args["status"]}
    
    async def _create_document(self, args: Dict[str, Any], session: Dict[str, Any]) -> Dict[str, Any]:
        """Create document."""
        agent_id = session.get("agent_id")
        
        if not agent_id:
            raise ValueError("Agent not registered")
        
        data = {
            "title": args["title"],
            "content": args["content"],
            "type": args.get("doc_type", "note"),
            "author": agent_id
        }
        
        if "mentions" in args:
            data["mentions"] = args["mentions"]
        
        response = await self.client.post(f"{self.base_url}/api/v1/documents", json=data)
        return response.json()
    
    async def _get_mentions(self, session: Dict[str, Any]) -> Dict[str, Any]:
        """Get mentions."""
        agent_id = session.get("agent_id")
        
        if not agent_id:
            raise ValueError("Agent not registered")
        
        response = await self.client.get(
            f"{self.base_url}/api/v1/mentions",
            params={"agent_id": agent_id}
        )
        
        mentions = response.json() if response.status_code == 200 else []
        return {"mentions": mentions, "count": len(mentions)}
    
    async def _register_service(self, args: Dict[str, Any], session: Dict[str, Any]) -> Dict[str, Any]:
        """Register service."""
        agent_id = session.get("agent_id", "system")
        
        data = {
            "name": args["service_name"],
            "url": args["service_url"],
            "registered_by": agent_id
        }
        
        if "health_check_url" in args:
            data["health_check_url"] = args["health_check_url"]
        
        response = await self.client.post(f"{self.base_url}/api/v1/services/register", json=data)
        return {"success": True, "service_name": args["service_name"]}
    
    async def _send_heartbeat(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Send heartbeat."""
        service_name = args["service_name"]
        data = {"status": args.get("status", "healthy")}
        
        response = await self.client.post(
            f"{self.base_url}/api/v1/services/{service_name}/heartbeat",
            json=data
        )
        
        return {"success": True, "service_name": service_name, "status": data["status"]}
    
    async def _poll_changes(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Poll changes."""
        query_params = {}
        if "since_timestamp" in args:
            query_params["since"] = args["since_timestamp"]
        
        response = await self.client.get(f"{self.base_url}/api/v1/changes", params=query_params)
        return response.json()


def create_app(base_url: str = None) -> FastAPI:
    """Create FastAPI app."""
    import os
    
    if base_url is None:
        base_url = os.getenv('HEADLESS_PM_URL', 'http://localhost:6969')
    
    server = StreamableHTTPMCPServer(base_url)
    return server.app


# For running with uvicorn
app = create_app()