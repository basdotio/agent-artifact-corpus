"""
Microsoft Fabric API client.

Provides a clean interface for interacting with Microsoft Fabric REST APIs,
including workspaces, lakehouses, and other Fabric resources.
"""

from typing import Any, Dict
import httpx
from fabric_auth import BaseAuthProvider


FABRIC_API_BASE = "https://api.fabric.microsoft.com/v1"
FABRIC_SCOPE = ["https://analysis.windows.net/powerbi/api/.default"]


class FabricAPIClient:
    """
    Client for Microsoft Fabric REST API operations.
    
    This client handles authentication and provides methods for common
    API operations like GET, POST, PUT, and DELETE requests.
    """
    
    def __init__(self, auth_provider: BaseAuthProvider):
        """
        Initialize Fabric API client.
        
        Args:
            auth_provider: Authentication provider to use for API requests
        """
        self.auth_provider = auth_provider
        self._base_url = FABRIC_API_BASE
    
    def _get_access_token(self) -> str:
        """Get access token from auth provider."""
        return self.auth_provider.get_access_token(FABRIC_SCOPE)
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Make authenticated request to Fabric API.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint path
            **kwargs: Additional arguments to pass to httpx request
            
        Returns:
            dict: JSON response from API
            
        Raises:
            Exception: If API request fails
        """
        token = self._get_access_token()
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {token}"
        
        url = f"{self._base_url}/{endpoint.lstrip('/')}"
        
        async with httpx.AsyncClient() as client:
            response = await client.request(method, url, headers=headers, **kwargs)
            
            if response.status_code == 200:
                return response.json()
            else:
                raise Exception(
                    f"Fabric API Error {response.status_code}: {response.text}"
                )
    
    async def get(self, endpoint: str, **kwargs) -> Dict[str, Any]:
        """
        Make GET request to Fabric API.
        
        Args:
            endpoint: API endpoint path
            **kwargs: Additional arguments (params, headers, etc.)
            
        Returns:
            dict: JSON response
        """
        return await self._make_request("GET", endpoint, **kwargs)
    
    async def post(self, endpoint: str, **kwargs) -> Dict[str, Any]:
        """
        Make POST request to Fabric API.
        
        Args:
            endpoint: API endpoint path
            **kwargs: Additional arguments (json, data, headers, etc.)
            
        Returns:
            dict: JSON response
        """
        return await self._make_request("POST", endpoint, **kwargs)
    
    async def put(self, endpoint: str, **kwargs) -> Dict[str, Any]:
        """
        Make PUT request to Fabric API.
        
        Args:
            endpoint: API endpoint path
            **kwargs: Additional arguments (json, data, headers, etc.)
            
        Returns:
            dict: JSON response
        """
        return await self._make_request("PUT", endpoint, **kwargs)
    
    async def delete(self, endpoint: str, **kwargs) -> Dict[str, Any]:
        """
        Make DELETE request to Fabric API.
        
        Args:
            endpoint: API endpoint path
            **kwargs: Additional arguments (headers, etc.)
            
        Returns:
            dict: JSON response
        """
        return await self._make_request("DELETE", endpoint, **kwargs)
