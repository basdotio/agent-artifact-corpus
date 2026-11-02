"""Platform API clients for Vercel, Render, Railway, and Fly.io."""
import os
import httpx
from typing import Dict, List, Optional, Any


class VercelClient:
    """Vercel API client."""
    
    def __init__(self, token: str = None):
        self.token = token or os.getenv("VERCEL_TOKEN", "")
        self.base_url = "https://api.vercel.com"
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    async def list_services(self) -> Dict[str, Any]:
        """List all Vercel projects."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/v9/projects",
                headers=self.headers,
                timeout=30.0
            )
            response.raise_for_status()
            data = response.json()
            
            projects = data.get("projects", [])
            return {
                "success": True,
                "platform": "vercel",
                "services": [
                    {
                        "id": p["id"],
                        "name": p["name"],
                        "framework": p.get("framework"),
                        "url": f"https://{p['name']}.vercel.app",
                        "created_at": p.get("createdAt"),
                        "updated_at": p.get("updatedAt")
                    }
                    for p in projects
                ],
                "count": len(projects)
            }
    
    async def get_deploy_status(self, service_id: str) -> Dict[str, Any]:
        """Get deployment status for a Vercel project."""
        async with httpx.AsyncClient() as client:
            # Get latest deployment
            response = await client.get(
                f"{self.base_url}/v6/deployments",
                headers=self.headers,
                params={"projectId": service_id, "limit": 1},
                timeout=30.0
            )
            response.raise_for_status()
            data = response.json()
            
            deployments = data.get("deployments", [])
            if not deployments:
                return {
                    "success": True,
                    "platform": "vercel",
                    "service_id": service_id,
                    "status": "no_deployments",
                    "message": "No deployments found"
                }
            
            deployment = deployments[0]
            return {
                "success": True,
                "platform": "vercel",
                "service_id": service_id,
                "deployment_id": deployment["uid"],
                "status": deployment.get("readyState", "UNKNOWN"),
                "url": deployment.get("url"),
                "created_at": deployment.get("createdAt"),
                "ready_at": deployment.get("ready")
            }
    
    async def tail_logs(self, service_id: str, lines: int = 100) -> Dict[str, Any]:
        """Get recent logs (Vercel doesn't have a direct log API, returns build logs)."""
        return {
            "success": False,
            "platform": "vercel",
            "error": "Vercel does not provide a runtime logs API. Use get_build_logs instead."
        }
    
    async def get_env_vars(self, service_id: str) -> Dict[str, Any]:
        """Get environment variables for a Vercel project."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/v9/projects/{service_id}/env",
                headers=self.headers,
                timeout=30.0
            )
            response.raise_for_status()
            data = response.json()
            
            env_vars = data.get("envs", [])
            return {
                "success": True,
                "platform": "vercel",
                "service_id": service_id,
                "env_vars": {
                    env["key"]: {
                        "value": env.get("value", "[ENCRYPTED]"),
                        "target": env.get("target", []),
                        "type": env.get("type", "plain")
                    }
                    for env in env_vars
                },
                "count": len(env_vars)
            }
    
    async def set_env_var(self, service_id: str, key: str, value: str) -> Dict[str, Any]:
        """Set an environment variable for a Vercel project."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/v10/projects/{service_id}/env",
                headers=self.headers,
                json={
                    "key": key,
                    "value": value,
                    "type": "plain",
                    "target": ["production", "preview", "development"]
                },
                timeout=30.0
            )
            response.raise_for_status()
            
            return {
                "success": True,
                "platform": "vercel",
                "service_id": service_id,
                "key": key,
                "message": "Environment variable set successfully"
            }
    
    async def trigger_redeploy(self, service_id: str) -> Dict[str, Any]:
        """Trigger a redeploy for a Vercel project."""
        async with httpx.AsyncClient() as client:
            # Get latest deployment first
            response = await client.get(
                f"{self.base_url}/v6/deployments",
                headers=self.headers,
                params={"projectId": service_id, "limit": 1},
                timeout=30.0
            )
            response.raise_for_status()
            data = response.json()
            
            deployments = data.get("deployments", [])
            if not deployments:
                return {
                    "success": False,
                    "platform": "vercel",
                    "error": "No deployments found to redeploy"
                }
            
            # Trigger redeploy
            deployment_id = deployments[0]["uid"]
            response = await client.post(
                f"{self.base_url}/v13/deployments/{deployment_id}/redeploy",
                headers=self.headers,
                timeout=30.0
            )
            response.raise_for_status()
            result = response.json()
            
            return {
                "success": True,
                "platform": "vercel",
                "service_id": service_id,
                "deployment_id": result.get("id"),
                "url": result.get("url"),
                "message": "Redeploy triggered successfully"
            }
    
    async def get_build_logs(self, deploy_id: str) -> Dict[str, Any]:
        """Get build logs for a Vercel deployment."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/v2/deployments/{deploy_id}/events",
                headers=self.headers,
                timeout=30.0
            )
            response.raise_for_status()
            logs = response.json()
            
            return {
                "success": True,
                "platform": "vercel",
                "deployment_id": deploy_id,
                "logs": [
                    {"timestamp": log.get("created"), "message": log.get("text", "")}
                    for log in logs
                ],
                "count": len(logs)
            }


class RenderClient:
    """Render API client."""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("RENDER_API_KEY", "")
        self.base_url = "https://api.render.com/v1"
        self.headers = {"Authorization": f"Bearer {self.api_key}"}
    
    async def list_services(self) -> Dict[str, Any]:
        """List all Render services."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/services",
                headers=self.headers,
                timeout=30.0
            )
            response.raise_for_status()
            services = response.json()
            
            return {
                "success": True,
                "platform": "render",
                "services": [
                    {
                        "id": s["service"]["id"],
                        "name": s["service"]["name"],
                        "type": s["service"]["type"],
                        "url": s["service"].get("serviceDetails", {}).get("url"),
                        "region": s["service"].get("serviceDetails", {}).get("region"),
                        "created_at": s["service"].get("createdAt"),
                        "updated_at": s["service"].get("updatedAt")
                    }
                    for s in services
                ],
                "count": len(services)
            }
    
    async def get_deploy_status(self, service_id: str) -> Dict[str, Any]:
        """Get deployment status for a Render service."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/services/{service_id}",
                headers=self.headers,
                timeout=30.0
            )
            response.raise_for_status()
            service = response.json()
            
            return {
                "success": True,
                "platform": "render",
                "service_id": service_id,
                "status": service.get("service", {}).get("serviceDetails", {}).get("deployStatus"),
                "url": service.get("service", {}).get("serviceDetails", {}).get("url"),
                "suspended": service.get("service", {}).get("suspended", "NOT_SUSPENDED")
            }
    
    async def tail_logs(self, service_id: str, lines: int = 100) -> Dict[str, Any]:
        """Get recent logs from a Render service."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/services/{service_id}/logs",
                headers=self.headers,
                params={"limit": lines},
                timeout=30.0
            )
            response.raise_for_status()
            logs = response.json()
            
            return {
                "success": True,
                "platform": "render",
                "service_id": service_id,
                "logs": logs,
                "count": len(logs)
            }
    
    async def get_env_vars(self, service_id: str) -> Dict[str, Any]:
        """Get environment variables for a Render service."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/services/{service_id}/env-vars",
                headers=self.headers,
                timeout=30.0
            )
            response.raise_for_status()
            env_vars = response.json()
            
            return {
                "success": True,
                "platform": "render",
                "service_id": service_id,
                "env_vars": {
                    env["envVar"]["key"]: env["envVar"]["value"]
                    for env in env_vars
                },
                "count": len(env_vars)
            }
    
    async def set_env_var(self, service_id: str, key: str, value: str) -> Dict[str, Any]:
        """Set an environment variable for a Render service."""
        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"{self.base_url}/services/{service_id}/env-vars/{key}",
                headers=self.headers,
                json={"value": value},
                timeout=30.0
            )
            response.raise_for_status()
            
            return {
                "success": True,
                "platform": "render",
                "service_id": service_id,
                "key": key,
                "message": "Environment variable set successfully"
            }
    
    async def trigger_redeploy(self, service_id: str) -> Dict[str, Any]:
        """Trigger a redeploy for a Render service."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/services/{service_id}/deploys",
                headers=self.headers,
                json={"clearCache": "do_not_clear"},
                timeout=30.0
            )
            response.raise_for_status()
            result = response.json()
            
            return {
                "success": True,
                "platform": "render",
                "service_id": service_id,
                "deployment_id": result.get("deploy", {}).get("id"),
                "status": result.get("deploy", {}).get("status"),
                "message": "Redeploy triggered successfully"
            }
    
    async def get_build_logs(self, deploy_id: str) -> Dict[str, Any]:
        """Get build logs for a Render deployment."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/deploys/{deploy_id}/logs",
                headers=self.headers,
                timeout=30.0
            )
            response.raise_for_status()
            logs = response.json()
            
            return {
                "success": True,
                "platform": "render",
                "deployment_id": deploy_id,
                "logs": logs,
                "count": len(logs)
            }


class RailwayClient:
    """Railway API client (GraphQL-based - basic implementation)."""
    
    def __init__(self, token: str = None):
        self.token = token or os.getenv("RAILWAY_TOKEN", "")
        self.base_url = "https://backboard.railway.app/graphql/v2"
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    async def list_services(self) -> Dict[str, Any]:
        """List all Railway services."""
        query = """
        query {
          projects {
            edges {
              node {
                id
                name
                services {
                  edges {
                    node {
                      id
                      name
                      serviceInstances {
                        edges {
                          node {
                            id
                            domains {
                              serviceDomains {
                                domain
                              }
                            }
                          }
                        }
                      }
                    }
                  }
                }
              }
            }
          }
        }
        """
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    self.base_url,
                    headers=self.headers,
                    json={"query": query},
                    timeout=30.0
                )
                response.raise_for_status()
                data = response.json()
                
                services = []
                for project_edge in data.get("data", {}).get("projects", {}).get("edges", []):
                    project = project_edge["node"]
                    for service_edge in project.get("services", {}).get("edges", []):
                        service = service_edge["node"]
                        services.append({
                            "id": service["id"],
                            "name": service["name"],
                            "project": project["name"]
                        })
                
                return {
                    "success": True,
                    "platform": "railway",
                    "services": services,
                    "count": len(services)
                }
            except Exception as e:
                return {
                    "success": False,
                    "platform": "railway",
                    "error": f"Railway API error: {str(e)}"
                }
    
    async def get_deploy_status(self, service_id: str) -> Dict[str, Any]:
        """Get deployment status for a Railway service."""
        return {
            "success": False,
            "platform": "railway",
            "error": "Railway deploy status not yet implemented (GraphQL required)"
        }
    
    async def tail_logs(self, service_id: str, lines: int = 100) -> Dict[str, Any]:
        """Get recent logs from a Railway service."""
        return {
            "success": False,
            "platform": "railway",
            "error": "Railway logs not yet implemented (requires websocket)"
        }
    
    async def get_env_vars(self, service_id: str) -> Dict[str, Any]:
        """Get environment variables for a Railway service."""
        return {
            "success": False,
            "platform": "railway",
            "error": "Railway env vars not yet implemented (GraphQL required)"
        }
    
    async def set_env_var(self, service_id: str, key: str, value: str) -> Dict[str, Any]:
        """Set an environment variable for a Railway service."""
        return {
            "success": False,
            "platform": "railway",
            "error": "Railway set env var not yet implemented (GraphQL required)"
        }
    
    async def trigger_redeploy(self, service_id: str) -> Dict[str, Any]:
        """Trigger a redeploy for a Railway service."""
        return {
            "success": False,
            "platform": "railway",
            "error": "Railway redeploy not yet implemented (GraphQL required)"
        }
    
    async def get_build_logs(self, deploy_id: str) -> Dict[str, Any]:
        """Get build logs for a Railway deployment."""
        return {
            "success": False,
            "platform": "railway",
            "error": "Railway build logs not yet implemented"
        }


class FlyClient:
    """Fly.io API client (basic implementation)."""
    
    def __init__(self, token: str = None):
        self.token = token or os.getenv("FLY_API_TOKEN", "")
        self.base_url = "https://api.fly.io/graphql"
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    async def list_services(self) -> Dict[str, Any]:
        """List all Fly.io apps."""
        query = """
        query {
          apps {
            nodes {
              id
              name
              status
              hostname
              organization {
                name
              }
            }
          }
        }
        """
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    self.base_url,
                    headers=self.headers,
                    json={"query": query},
                    timeout=30.0
                )
                response.raise_for_status()
                data = response.json()
                
                apps = data.get("data", {}).get("apps", {}).get("nodes", [])
                return {
                    "success": True,
                    "platform": "fly",
                    "services": [
                        {
                            "id": app["id"],
                            "name": app["name"],
                            "status": app.get("status"),
                            "url": f"https://{app.get('hostname')}" if app.get("hostname") else None,
                            "organization": app.get("organization", {}).get("name")
                        }
                        for app in apps
                    ],
                    "count": len(apps)
                }
            except Exception as e:
                return {
                    "success": False,
                    "platform": "fly",
                    "error": f"Fly.io API error: {str(e)}"
                }
    
    async def get_deploy_status(self, service_id: str) -> Dict[str, Any]:
        """Get deployment status for a Fly.io app."""
        return {
            "success": False,
            "platform": "fly",
            "error": "Fly.io deploy status not yet implemented"
        }
    
    async def tail_logs(self, service_id: str, lines: int = 100) -> Dict[str, Any]:
        """Get recent logs from a Fly.io app."""
        return {
            "success": False,
            "platform": "fly",
            "error": "Fly.io logs not yet implemented (use flyctl CLI)"
        }
    
    async def get_env_vars(self, service_id: str) -> Dict[str, Any]:
        """Get environment variables for a Fly.io app."""
        return {
            "success": False,
            "platform": "fly",
            "error": "Fly.io env vars not yet implemented"
        }
    
    async def set_env_var(self, service_id: str, key: str, value: str) -> Dict[str, Any]:
        """Set an environment variable for a Fly.io app."""
        return {
            "success": False,
            "platform": "fly",
            "error": "Fly.io set env var not yet implemented"
        }
    
    async def trigger_redeploy(self, service_id: str) -> Dict[str, Any]:
        """Trigger a redeploy for a Fly.io app."""
        return {
            "success": False,
            "platform": "fly",
            "error": "Fly.io redeploy not yet implemented"
        }
    
    async def get_build_logs(self, deploy_id: str) -> Dict[str, Any]:
        """Get build logs for a Fly.io deployment."""
        return {
            "success": False,
            "platform": "fly",
            "error": "Fly.io build logs not yet implemented"
        }


# Platform client factory
def get_client(platform: str):
    """Get the appropriate platform client."""
    clients = {
        "vercel": VercelClient,
        "render": RenderClient,
        "railway": RailwayClient,
        "fly": FlyClient
    }
    
    client_class = clients.get(platform.lower())
    if not client_class:
        raise ValueError(f"Unknown platform: {platform}. Supported: {list(clients.keys())}")
    
    return client_class()
