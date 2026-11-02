"""Deployment management tools."""
import httpx
from typing import Dict, Any, Optional
from .platforms import get_client


async def list_all_services() -> Dict[str, Any]:
    """List all services across all platforms."""
    platforms = ["vercel", "render", "railway", "fly"]
    all_services = []
    errors = []
    
    for platform in platforms:
        try:
            client = get_client(platform)
            result = await client.list_services()
            if result.get("success"):
                all_services.extend(result.get("services", []))
            else:
                errors.append({
                    "platform": platform,
                    "error": result.get("error", "Unknown error")
                })
        except Exception as e:
            errors.append({
                "platform": platform,
                "error": str(e)
            })
    
    return {
        "success": True,
        "services": all_services,
        "count": len(all_services),
        "errors": errors if errors else None
    }


async def get_deploy_status(platform: str, service_id: str) -> Dict[str, Any]:
    """Get deployment status for a specific service."""
    try:
        client = get_client(platform)
        return await client.get_deploy_status(service_id)
    except Exception as e:
        return {
            "success": False,
            "platform": platform,
            "service_id": service_id,
            "error": str(e)
        }


async def tail_logs(platform: str, service_id: str, lines: int = 100) -> Dict[str, Any]:
    """Get recent logs from a service."""
    try:
        client = get_client(platform)
        return await client.tail_logs(service_id, lines)
    except Exception as e:
        return {
            "success": False,
            "platform": platform,
            "service_id": service_id,
            "error": str(e)
        }


async def get_env_vars(platform: str, service_id: str) -> Dict[str, Any]:
    """Get environment variables for a service."""
    try:
        client = get_client(platform)
        return await client.get_env_vars(service_id)
    except Exception as e:
        return {
            "success": False,
            "platform": platform,
            "service_id": service_id,
            "error": str(e)
        }


async def set_env_var(platform: str, service_id: str, key: str, value: str) -> Dict[str, Any]:
    """Set an environment variable for a service."""
    try:
        client = get_client(platform)
        return await client.set_env_var(service_id, key, value)
    except Exception as e:
        return {
            "success": False,
            "platform": platform,
            "service_id": service_id,
            "key": key,
            "error": str(e)
        }


async def trigger_redeploy(platform: str, service_id: str) -> Dict[str, Any]:
    """Trigger a redeploy for a service."""
    try:
        client = get_client(platform)
        return await client.trigger_redeploy(service_id)
    except Exception as e:
        return {
            "success": False,
            "platform": platform,
            "service_id": service_id,
            "error": str(e)
        }


async def get_build_logs(platform: str, deploy_id: str) -> Dict[str, Any]:
    """Get build logs for a deployment."""
    try:
        client = get_client(platform)
        return await client.get_build_logs(deploy_id)
    except Exception as e:
        return {
            "success": False,
            "platform": platform,
            "deployment_id": deploy_id,
            "error": str(e)
        }


async def check_health(url: str) -> Dict[str, Any]:
    """Ping a health endpoint."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10.0, follow_redirects=True)
            
            return {
                "success": True,
                "url": url,
                "status_code": response.status_code,
                "healthy": 200 <= response.status_code < 300,
                "response_time_ms": int(response.elapsed.total_seconds() * 1000),
                "headers": dict(response.headers)
            }
    except httpx.TimeoutException:
        return {
            "success": False,
            "url": url,
            "error": "Request timeout",
            "healthy": False
        }
    except Exception as e:
        return {
            "success": False,
            "url": url,
            "error": str(e),
            "healthy": False
        }


async def rollback_deploy(platform: str, service_id: str, version: str) -> Dict[str, Any]:
    """Rollback to a previous deployment version."""
    # This is platform-specific and would require different implementations
    # For now, return a placeholder
    return {
        "success": False,
        "platform": platform,
        "service_id": service_id,
        "version": version,
        "error": "Rollback not yet implemented for this platform"
    }
