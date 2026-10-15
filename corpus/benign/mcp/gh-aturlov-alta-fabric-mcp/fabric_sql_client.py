"""
Microsoft Fabric SQL client for lakehouse queries.

Provides SQL query capabilities for Microsoft Fabric lakehouses using
ODBC connection with Azure AD authentication.
"""

from typing import Any, Dict, List
import pyodbc
from fabric_auth import BaseAuthProvider
from fabric_api_client import FabricAPIClient, FABRIC_SCOPE


class FabricSQLClient:
    """
    SQL client for querying Fabric lakehouse data via SQL endpoint.
    
    This client uses ODBC Driver 17 for SQL Server with Azure AD authentication
    to execute queries against Fabric lakehouse SQL endpoints.
    """
    
    def __init__(self, auth_provider: BaseAuthProvider, api_client: FabricAPIClient):
        """
        Initialize Fabric SQL client.
        
        Args:
            auth_provider: Authentication provider for token acquisition
            api_client: Fabric API client for retrieving lakehouse metadata
        """
        self.auth_provider = auth_provider
        self.api_client = api_client
    
    def _get_connection_string(self, sql_endpoint: str, lakehouse_name: str) -> str:
        """
        Build ODBC connection string for Fabric lakehouse with Azure AD auth.
        
        Args:
            sql_endpoint: SQL endpoint server address
            lakehouse_name: Name of the lakehouse (database)
            
        Returns:
            str: ODBC connection string
        """
        return (
            f"Driver={{ODBC Driver 17 for SQL Server}};"
            f"Server={sql_endpoint};"
            f"Database={lakehouse_name};"
            f"Encrypt=yes;"
            f"TrustServerCertificate=no;"
        )
    
    async def _get_lakehouse_info(
        self,
        workspace_id: str,
        lakehouse_id: str
    ) -> tuple[str, str]:
        """
        Get SQL endpoint and lakehouse name from Fabric API.
        
        Args:
            workspace_id: Workspace containing the lakehouse
            lakehouse_id: Lakehouse ID
            
        Returns:
            tuple: (sql_endpoint, lakehouse_name)
            
        Raises:
            Exception: If lakehouse has no SQL endpoint
        """
        data = await self.api_client.get(
            f"/workspaces/{workspace_id}/lakehouses/{lakehouse_id}"
        )
        
        sql_properties = data.get("properties", {}).get("sqlEndpointProperties", {})
        connection_string = sql_properties.get("connectionString")
        lakehouse_name = data.get("displayName", lakehouse_id)
        
        if not connection_string:
            raise Exception(f"No SQL endpoint found for lakehouse {lakehouse_id}")
        
        # Extract server address from connection string (format: "Server=xyz.datawarehouse.fabric.microsoft.com")
        sql_endpoint = connection_string
        if "Server=" in connection_string:
            # Parse out just the server address
            parts = connection_string.split(";")
            for part in parts:
                if part.startswith("Server="):
                    sql_endpoint = part.replace("Server=", "")
                    break
        
        return sql_endpoint, lakehouse_name
    
    async def execute_query(
        self,
        workspace_id: str,
        lakehouse_id: str,
        query: str
    ) -> List[Dict[str, Any]]:
        """
        Execute SQL query against lakehouse and return results.
        
        Args:
            workspace_id: Workspace containing the lakehouse
            lakehouse_id: Lakehouse to query
            query: SQL query to execute
            
        Returns:
            list: List of dictionaries representing query results
            
        Raises:
            Exception: If query execution fails
        """
        sql_endpoint, lakehouse_name = await self._get_lakehouse_info(
            workspace_id, lakehouse_id
        )
        connection_string = self._get_connection_string(sql_endpoint, lakehouse_name)
        
        try:
            # Get access token for SQL authentication
            token = self.auth_provider.get_access_token(FABRIC_SCOPE)
            
            # Convert token to bytes for SQL authentication
            # SQL_COPT_SS_ACCESS_TOKEN = 1256
            token_bytes = token.encode('utf-16-le')
            # Correct format: length (4 bytes, little-endian) + token bytes
            token_length = len(token_bytes)
            token_struct = token_length.to_bytes(4, byteorder='little') + token_bytes
            
            # Connect with access token
            with pyodbc.connect(
                connection_string,
                attrs_before={1256: token_struct}
            ) as conn:
                cursor = conn.cursor()
                cursor.execute(query)
                
                # Get column names
                columns = [column[0] for column in cursor.description]
                
                # Get all rows
                rows = cursor.fetchall()
                
                # Convert to list of dictionaries
                results = [dict(zip(columns, row)) for row in rows]
                
                return results
                
        except Exception as e:
            raise Exception(f"SQL query failed: {str(e)}")
