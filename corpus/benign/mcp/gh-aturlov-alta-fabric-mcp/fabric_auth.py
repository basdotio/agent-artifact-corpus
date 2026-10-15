"""
Authentication providers for Microsoft Fabric API access.

This module provides different authentication strategies for accessing Microsoft Fabric:
- InteractiveAuthProvider: User-based authentication via device code flow (recommended for individuals)
- ServicePrincipalAuthProvider: Service principal authentication (for automation/services)
"""

import os
import sys
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional
import msal


class BaseAuthProvider(ABC):
    """Base class for authentication providers."""
    
    @abstractmethod
    def get_access_token(self, scope: List[str]) -> str:
        """
        Get an access token for the specified scope.
        
        Args:
            scope: List of OAuth scopes to request
            
        Returns:
            str: Access token
            
        Raises:
            Exception: If authentication fails
        """
        pass


class InteractiveAuthProvider(BaseAuthProvider):
    """
    Interactive authentication provider using device code flow.
    
    This provider is ideal for individual users and development scenarios.
    It prompts users to authenticate via browser and caches tokens for reuse.
    """
    
    def __init__(
        self,
        client_id: str = "ea0616ba-638b-4df5-95b9-636659ae5121",  # Power BI default
        tenant_id: str = "common",
        token_cache_file: Optional[Path] = None
    ):
        """
        Initialize interactive authentication provider.
        
        Args:
            client_id: Azure AD application (client) ID (default: Power BI client ID)
            tenant_id: Azure AD tenant ID or 'common' for multi-tenant
            token_cache_file: Path to token cache file (default: ~/.fabric_mcp_token_cache.json)
        """
        self.client_id = client_id
        self.tenant_id = tenant_id
        self.authority = f"https://login.microsoftonline.com/{tenant_id}"
        
        if token_cache_file is None:
            token_cache_file = Path.home() / ".fabric_mcp_token_cache.json"
        self.token_cache_file = token_cache_file
        
        self._token_cache = self._load_token_cache()
        self._app = None
    
    def clear_token_cache(self) -> bool:
        """
        Clear the cached authentication tokens (sign out).
        
        Returns:
            bool: True if cache was deleted, False if no cache existed
        """
        if self.token_cache_file.exists():
            self.token_cache_file.unlink()
            self._token_cache = msal.SerializableTokenCache()
            self._app = None  # Reset app to force re-initialization
            return True
        return False
    
    def _load_token_cache(self) -> msal.SerializableTokenCache:
        """Load token cache from file or create new one."""
        cache = msal.SerializableTokenCache()
        if self.token_cache_file.exists():
            try:
                cache.deserialize(self.token_cache_file.read_text())
            except Exception as e:
                print(f"Warning: Could not load token cache: {e}")
        return cache
    
    def _save_token_cache(self):
        """Save token cache to file."""
        if self._token_cache.has_state_changed:
            try:
                self.token_cache_file.parent.mkdir(parents=True, exist_ok=True)
                self.token_cache_file.write_text(self._token_cache.serialize())
            except Exception as e:
                print(f"Warning: Could not save token cache: {e}")
    
    def _get_msal_app(self) -> msal.PublicClientApplication:
        """Get or create MSAL public client application."""
        if not self._app:
            self._app = msal.PublicClientApplication(
                self.client_id,
                authority=self.authority,
                token_cache=self._token_cache
            )
        return self._app
    
    def get_access_token(self, scope: List[str]) -> str:
        """
        Get access token using interactive authentication with device code flow.
        
        Args:
            scope: List of OAuth scopes to request
            
        Returns:
            str: Access token
        """
        app = self._get_msal_app()
        
        # Try to get token silently from cache first
        accounts = app.get_accounts()
        if accounts:
            result = app.acquire_token_silent(scope, account=accounts[0])
            if result and "access_token" in result:
                return result["access_token"]
        
        # If silent acquisition fails, use device code flow
        print("\n" + "=" * 70, file=sys.stderr)
        print("AUTHENTICATION REQUIRED FOR MICROSOFT FABRIC", file=sys.stderr)
        print("=" * 70, file=sys.stderr)
        
        flow = app.initiate_device_flow(scopes=scope)
        if "user_code" not in flow:
            raise Exception(f"Failed to create device flow: {flow.get('error_description', 'Unknown error')}")
        
        print(flow["message"], file=sys.stderr)
        print("=" * 70, file=sys.stderr)
        print("Please complete authentication within 5 minutes.", file=sys.stderr)
        print("=" * 70 + "\n", file=sys.stderr)
        
        # Wait for user to authenticate
        result = app.acquire_token_by_device_flow(flow)
        
        if "access_token" in result:
            self._save_token_cache()
            print("=" * 70, file=sys.stderr)
            print("Authentication successful!", file=sys.stderr)
            print("=" * 70 + "\n", file=sys.stderr)
            return result["access_token"]
        else:
            error_msg = result.get('error_description', 'Unknown error')
            print(f"\nAuthentication failed: {error_msg}", file=sys.stderr)
            raise Exception(f"Could not acquire token: {error_msg}")


class ServicePrincipalAuthProvider(BaseAuthProvider):
    """
    Service principal authentication provider.
    
    This provider is ideal for automation, CI/CD pipelines, and service scenarios.
    Requires Azure AD app registration with client secret.
    """
    
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        tenant_id: str
    ):
        """
        Initialize service principal authentication provider.
        
        Args:
            client_id: Azure AD application (client) ID
            client_secret: Azure AD application client secret
            tenant_id: Azure AD tenant ID
        """
        if not all([client_id, client_secret, tenant_id]):
            raise ValueError("client_id, client_secret, and tenant_id are required for service principal auth")
        
        self.client_id = client_id
        self.client_secret = client_secret
        self.tenant_id = tenant_id
        self.authority = f"https://login.microsoftonline.com/{tenant_id}"
        self._app = None
    
    def _get_msal_app(self) -> msal.ConfidentialClientApplication:
        """Get or create MSAL confidential client application."""
        if not self._app:
            self._app = msal.ConfidentialClientApplication(
                self.client_id,
                authority=self.authority,
                client_credential=self.client_secret
            )
        return self._app
    
    def get_access_token(self, scope: List[str]) -> str:
        """
        Get access token using service principal credentials.
        
        Args:
            scope: List of OAuth scopes to request
            
        Returns:
            str: Access token
        """
        app = self._get_msal_app()
        result = app.acquire_token_for_client(scopes=scope)
        
        if "access_token" in result:
            return result["access_token"]
        else:
            error_msg = result.get('error_description', 'Unknown error')
            raise Exception(f"Could not acquire token: {error_msg}")


def create_auth_provider_from_env() -> BaseAuthProvider:
    """
    Create an authentication provider based on environment variables.
    
    If FABRIC_CLIENT_SECRET is set, creates ServicePrincipalAuthProvider.
    Otherwise, creates InteractiveAuthProvider.
    
    Environment variables:
        FABRIC_CLIENT_ID: Azure AD application (client) ID (optional for interactive)
        FABRIC_CLIENT_SECRET: Azure AD client secret (triggers service principal auth)
        FABRIC_TENANT_ID: Azure AD tenant ID (optional for interactive)
    
    Returns:
        BaseAuthProvider: Configured authentication provider
    """
    client_id = os.getenv("FABRIC_CLIENT_ID")
    client_secret = os.getenv("FABRIC_CLIENT_SECRET")
    tenant_id = os.getenv("FABRIC_TENANT_ID")
    
    if client_secret:
        # Service principal authentication
        if not client_id or not tenant_id:
            raise ValueError("FABRIC_CLIENT_ID and FABRIC_TENANT_ID are required for service principal auth")
        return ServicePrincipalAuthProvider(client_id, client_secret, tenant_id)
    else:
        # Interactive authentication (uses defaults if not provided)
        kwargs = {}
        if client_id:
            kwargs["client_id"] = client_id
        if tenant_id:
            kwargs["tenant_id"] = tenant_id
        return InteractiveAuthProvider(**kwargs)
