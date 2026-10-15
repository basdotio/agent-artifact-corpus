"""
Generic API Client for RESTful operations
Created by D. Theoden
Date: June 12, 2025
"""

import requests
import json
from .auth import get_bearer_token
from .config import URL

class APIClient:
    def __init__(self):
        self.token = None
        self.url = URL
        self.odata_url = f"{URL}/Server/Odata"  # Aras OData endpoint

    def authenticate(self):
        """Authenticate with the API and store the token."""
        try:
            self.token = get_bearer_token()
            return True
        except Exception as error:
            import sys
            print(f"Authentication error: {error}", file=sys.stderr)
            return False

    def get_items(self, endpoint, expand=None, filter_param=None, select=None):
        """Get items from Aras OData API."""
        try:
            if not self.token:
                self.authenticate()

            # Build OData URL - endpoint should be an ItemType like 'Part', 'Document', etc.
            api_url = f"{self.odata_url}/{endpoint}"
            params = []
            
            if expand:
                params.append(f"$expand={expand}")
            if filter_param:
                params.append(f"$filter={filter_param}")
            if select:
                params.append(f"$select={select}")
            
            if params:
                api_url += "?" + "&".join(params)

            response = requests.get(
                api_url,
                headers={
                    'Accept': 'application/json',
                    'Authorization': f'Bearer {self.token}'
                }
            )
            response.raise_for_status()

            return response.json()
        except Exception as error:
            import sys
            print(f"Error getting items: {error}", file=sys.stderr)
            raise error

    def create_item(self, endpoint, data):
        """Create a new item using Aras OData API."""
        try:
            if not self.token:
                self.authenticate()

            response = requests.post(
                f"{self.odata_url}/{endpoint}",
                json=data,
                headers={
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                    'Authorization': f'Bearer {self.token}'
                }
            )
            response.raise_for_status()

            return response.json()
        except Exception as error:
            import sys
            print(f"Error creating item: {error}", file=sys.stderr)
            raise error

    def call_method(self, method_name, data):
        """Call an Aras server method."""
        try:
            if not self.token:
                self.authenticate()

            # Aras methods are typically called via OData actions
            response = requests.post(
                f"{self.odata_url}/Method('{method_name}')",
                json=data,
                headers={
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                    'Authorization': f'Bearer {self.token}'
                }
            )
            response.raise_for_status()

            return response.json()
        except Exception as error:
            import sys
            print(f"Error calling method {method_name}: {error}", file=sys.stderr)
            raise error

    def get_list(self, list_id, expand=None):
        """Get list data from Aras API."""
        try:
            if not self.token:
                self.authenticate()

            # Aras lists are accessed via List ItemType
            list_url = f"{self.odata_url}/List('{list_id}')"
            if expand:
                list_url += f"?$expand={expand}"

            response = requests.get(
                list_url,
                headers={
                    'Accept': 'application/json',
                    'Authorization': f'Bearer {self.token}'
                }
            )
            response.raise_for_status()

            return response.json()
        except Exception as error:
            import sys
            print(f"Error getting list {list_id}: {error}", file=sys.stderr)
            raise error 