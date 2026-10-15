from azure.core.credentials import AccessToken

from fastmcp.server.auth.providers.azure import AzureProvider
from fastmcp.server.context import Context

from msgraph import GraphServiceClient

from kiota_authentication_azure.azure_identity_authentication_provider import (
    AzureIdentityAuthenticationProvider,
)

import time

# Graph API utilities


class GraphTokenCredentials:
    def __init__(self, access_token: str, expires_on: int = None):
        """
        A custom class that enables you to use pass tokens
        directly into the Microsoft Graph API as a credentials
        object
        """
        self.access_token = access_token
        # Set expiration to 1 hour from now if not provided
        self.expires_on = expires_on or int(time.time()) + 3600

    def get_token(self, *scopes, **kwargs):
        return AccessToken(self.access_token, self.expires_on)


def get_graph_client(token: str) -> GraphServiceClient:
    """get a microsoft graph API client
    from the access token acquired during
    authentication with the MCP server
    """
    credentials = GraphTokenCredentials(token)
    graph_client = GraphServiceClient(credentials=credentials)
    return graph_client


# Azure Authentication Provider for FastMCP


class PatchedAzureProvider(AzureProvider):
    def _get_resource_url(self, mcp_path):
        return None  # Force v2.0 behavior

    def authorize(self, *args, **kwargs):
        kwargs.pop("resource", None)
        return super().authorize(*args, **kwargs)
