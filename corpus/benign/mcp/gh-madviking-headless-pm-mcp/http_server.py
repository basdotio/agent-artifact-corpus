"""
HTTP-based MCP Server for network connections
Provides a REST API wrapper around MCP functionality
"""

import json
import logging
from typing import Any, Dict, Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import httpx

from .token_tracker import TokenTracker

logging.basicConfig(level=logging.INFO, format='[MCP-HTTP] %(message)s')
logger = logging.getLogger("headless-pm-mcp-http")


class MCPRequest(BaseModel):
    """Generic MCP request model."""
    method: str
    params: Optional[Dict[str, Any]] = {}
    id: Optional[str] = None


class MCPResponse(BaseModel):
    """Generic MCP response model."""
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None
    id: Optional[str] = None


class HTTPMCPServer:
    """HTTP-based MCP Server for network connections."""
    
    def __init__(self, base_url: str = "http://localhost:6969"):
        self.base_url = base_url.rstrip('/')
        self.app = FastAPI(title="Headless PM MCP Server", version="1.0.0")
        self.client = httpx.AsyncClient(timeout=30.0)
        self.token_tracker = TokenTracker()
        self.sessions: Dict[str, Dict[str, Any]] = {}
        
        # Register routes
        self._register_routes()
    
    def _register_routes(self):
        """Register HTTP routes."""
        
        @self.app.get("/")
        async def root():
            return {
                "name": "headless-pm-mcp",
                "version": "1.0.0",
                "description": "MCP server for Headless PM",
                "endpoints": {
                    "initialize": "POST /mcp/initialize",
                    "list_tools": "GET /mcp/tools",
                    "call_tool": "POST /mcp/tools/call",
                    "list_resources": "GET /mcp/resources",
                    "read_resource": "POST /mcp/resources/read"
                }
            }
        
        @self.app.post("/mcp/initialize")
        async def initialize(request: Request):
            """Initialize MCP session."""
            session_id = request.headers.get("X-Session-ID", "default")
            client_info = await request.json() if request.headers.get("content-type") == "application/json" else {}
            
            self.sessions[session_id] = {
                "initialized_at": datetime.now().isoformat(),
                "client_info": client_info,
                "agent_id": None,
                "agent_role": None,
                "agent_skill_level": None
            }
            
            return {
                "protocolVersion": "0.1.0",
                "capabilities": {
                    "tools": {
                        "register_agent": True,
                        "task_management": True,
                        "document_creation": True,
                        "service_registry": True
                    },
                    "resources": {
                        "tasks": True,
                        "agents": True,
                        "documents": True,
                        "services": True
                    }
                },
                "serverInfo": {
                    "name": "headless-pm-mcp",
                    "version": "1.0.0",
                    "apiUrl": self.base_url
                }
            }
        
        @self.app.get("/mcp/tools")
        async def list_tools():
            """List available tools."""
            return {
                "tools": [
                    {
                        "name": "register_agent",
                        "description": "Register agent with Headless PM system",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "agent_id": {"type": "string"},
                                "role": {"type": "string", "enum": ["frontend_dev", "backend_dev", "architect", "pm", "qa"]},
                                "skill_level": {"type": "string", "enum": ["junior", "senior", "principal"]}
                            },
                            "required": ["agent_id", "role"]
                        }
                    },
                    {
                        "name": "get_project_context",
                        "description": "Get project configuration and context"
                    },
                    {
                        "name": "get_next_task",
                        "description": "Get next available task"
                    },
                    {
                        "name": "create_task",
                        "description": "Create a new task"
                    },
                    {
                        "name": "lock_task",
                        "description": "Lock a task"
                    },
                    {
                        "name": "update_task_status",
                        "description": "Update task status"
                    },
                    {
                        "name": "create_document",
                        "description": "Create a document"
                    },
                    {
                        "name": "get_mentions",
                        "description": "Get mentions for agent"
                    },
                    {
                        "name": "register_service",
                        "description": "Register a service"
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
            }
        
        @self.app.post("/mcp/tools/call")
        async def call_tool(request: Request, mcp_request: MCPRequest):
            """Call a tool."""
            session_id = request.headers.get("X-Session-ID", "default")
            session = self.sessions.get(session_id, {})
            
            try:
                tool_name = mcp_request.method
                params = mcp_request.params or {}
                
                # Track request
                self.token_tracker.track_request({"tool": tool_name, "params": params})
                
                # Route to appropriate handler
                if tool_name == "register_agent":
                    result = await self._register_agent(params, session_id)
                elif tool_name == "get_project_context":
                    result = await self._get_project_context()
                elif tool_name == "get_next_task":
                    result = await self._get_next_task(params, session)
                elif tool_name == "create_task":
                    result = await self._create_task(params, session)
                elif tool_name == "lock_task":
                    result = await self._lock_task(params, session)
                elif tool_name == "update_task_status":
                    result = await self._update_task_status(params, session)
                elif tool_name == "create_document":
                    result = await self._create_document(params, session)
                elif tool_name == "get_mentions":
                    result = await self._get_mentions(session)
                elif tool_name == "register_service":
                    result = await self._register_service(params, session)
                elif tool_name == "send_heartbeat":
                    result = await self._send_heartbeat(params)
                elif tool_name == "poll_changes":
                    result = await self._poll_changes(params)
                else:
                    raise ValueError(f"Unknown tool: {tool_name}")
                
                # Track response
                self.token_tracker.track_response(result)
                
                return MCPResponse(result=result, id=mcp_request.id)
            
            except Exception as e:
                logger.error(f"Error calling tool {mcp_request.method}: {e}")
                return MCPResponse(
                    error={"code": -32603, "message": str(e)},
                    id=mcp_request.id
                )
        
        @self.app.get("/mcp/resources")
        async def list_resources():
            """List available resources."""
            return {
                "resources": [
                    {"uri": "headless-pm://tasks/list", "name": "Current Tasks"},
                    {"uri": "headless-pm://agents/list", "name": "Active Agents"},
                    {"uri": "headless-pm://documents/recent", "name": "Recent Documents"},
                    {"uri": "headless-pm://services/status", "name": "Service Status"},
                    {"uri": "headless-pm://changelog/recent", "name": "Recent Activity"},
                    {"uri": "headless-pm://context/project", "name": "Project Context"}
                ]
            }
        
        @self.app.post("/mcp/resources/read")
        async def read_resource(resource_request: Dict[str, str]):
            """Read a resource."""
            uri = resource_request.get("uri", "")
            
            try:
                if uri == "headless-pm://tasks/list":
                    response = await self.client.get(f"{self.base_url}/api/v1/tasks")
                    return {"content": response.json()}
                
                elif uri == "headless-pm://agents/list":
                    response = await self.client.get(f"{self.base_url}/api/v1/agents")
                    return {"content": response.json()}
                
                elif uri == "headless-pm://documents/recent":
                    response = await self.client.get(f"{self.base_url}/api/v1/documents?limit=20")
                    return {"content": response.json()}
                
                elif uri == "headless-pm://services/status":
                    response = await self.client.get(f"{self.base_url}/api/v1/services")
                    return {"content": response.json()}
                
                elif uri == "headless-pm://changelog/recent":
                    response = await self.client.get(f"{self.base_url}/api/v1/changelog?limit=50")
                    return {"content": response.json()}
                
                elif uri == "headless-pm://context/project":
                    response = await self.client.get(f"{self.base_url}/api/v1/context")
                    return {"content": response.json()}
                
                else:
                    raise ValueError(f"Unknown resource URI: {uri}")
            
            except Exception as e:
                logger.error(f"Error reading resource {uri}: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.on_event("shutdown")
        async def shutdown():
            await self.client.aclose()
    
    async def _register_agent(self, params: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """Register agent."""
        agent_id = params["agent_id"]
        role = params["role"]
        skill_level = params.get("skill_level", "senior")
        
        # Update session
        self.sessions[session_id].update({
            "agent_id": agent_id,
            "agent_role": role,
            "agent_skill_level": skill_level
        })
        
        # Register with API
        data = {
            "agent_id": agent_id,
            "role": role,
            "level": skill_level,
            "connection_type": "mcp_http"
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
    
    async def _get_next_task(self, params: Dict[str, Any], session: Dict[str, Any]) -> Dict[str, Any]:
        """Get next task."""
        query_params = {
            "role": params.get("role", session.get("agent_role")),
            "skill_level": params.get("skill_level", session.get("agent_skill_level"))
        }
        
        response = await self.client.get(f"{self.base_url}/api/v1/tasks/next", params=query_params)
        return response.json() if response.status_code == 200 else {"message": "No tasks available"}
    
    async def _create_task(self, params: Dict[str, Any], session: Dict[str, Any]) -> Dict[str, Any]:
        """Create task."""
        data = {
            "title": params["title"],
            "description": params["description"],
            "complexity": params["complexity"],
            "role": params.get("role", session.get("agent_role")),
            "skill_level": params.get("skill_level", session.get("agent_skill_level"))
        }
        
        response = await self.client.post(f"{self.base_url}/api/v1/tasks/create", json=data)
        return response.json()
    
    async def _lock_task(self, params: Dict[str, Any], session: Dict[str, Any]) -> Dict[str, Any]:
        """Lock task."""
        task_id = params["task_id"]
        agent_id = session.get("agent_id")
        
        if not agent_id:
            raise ValueError("Agent not registered")
        
        response = await self.client.post(
            f"{self.base_url}/api/v1/tasks/{task_id}/lock",
            json={"agent_id": agent_id}
        )
        
        return {"success": True, "task_id": task_id, "locked_by": agent_id}
    
    async def _update_task_status(self, params: Dict[str, Any], session: Dict[str, Any]) -> Dict[str, Any]:
        """Update task status."""
        task_id = params["task_id"]
        agent_id = session.get("agent_id")
        
        if not agent_id:
            raise ValueError("Agent not registered")
        
        data = {
            "status": params["status"],
            "agent_id": agent_id
        }
        
        if "notes" in params:
            data["notes"] = params["notes"]
        
        response = await self.client.put(
            f"{self.base_url}/api/v1/tasks/{task_id}/status",
            json=data
        )
        
        return {"success": True, "task_id": task_id, "status": params["status"]}
    
    async def _create_document(self, params: Dict[str, Any], session: Dict[str, Any]) -> Dict[str, Any]:
        """Create document."""
        agent_id = session.get("agent_id")
        
        if not agent_id:
            raise ValueError("Agent not registered")
        
        data = {
            "title": params["title"],
            "content": params["content"],
            "type": params.get("doc_type", "note"),
            "author": agent_id
        }
        
        if "mentions" in params:
            data["mentions"] = params["mentions"]
        
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
    
    async def _register_service(self, params: Dict[str, Any], session: Dict[str, Any]) -> Dict[str, Any]:
        """Register service."""
        agent_id = session.get("agent_id", "system")
        
        data = {
            "name": params["service_name"],
            "url": params["service_url"],
            "registered_by": agent_id
        }
        
        if "health_check_url" in params:
            data["health_check_url"] = params["health_check_url"]
        
        response = await self.client.post(f"{self.base_url}/api/v1/services/register", json=data)
        return {"success": True, "service_name": params["service_name"]}
    
    async def _send_heartbeat(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Send heartbeat."""
        service_name = params["service_name"]
        data = {"status": params.get("status", "healthy")}
        
        response = await self.client.post(
            f"{self.base_url}/api/v1/services/{service_name}/heartbeat",
            json=data
        )
        
        return {"success": True, "service_name": service_name, "status": data["status"]}
    
    async def _poll_changes(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Poll changes."""
        query_params = {}
        if "since_timestamp" in params:
            query_params["since"] = params["since_timestamp"]
        
        response = await self.client.get(f"{self.base_url}/api/v1/changes", params=query_params)
        return response.json()


def create_app(base_url: str = None) -> FastAPI:
    """Create FastAPI app."""
    import os
    
    if base_url is None:
        base_url = os.getenv('HEADLESS_PM_URL', 'http://localhost:6969')
    
    server = HTTPMCPServer(base_url)
    return server.app


# For running with uvicorn
app = create_app()