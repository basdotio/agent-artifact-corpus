"""
Authentication module for API access
Created by D. Theoden
Date: June 12, 2025
"""

import requests
from requests_oauthlib import OAuth2Session
from oauthlib.oauth2 import LegacyApplicationClient
import os
from dotenv import load_dotenv
from .config import URL, USERNAME, PASSWORD, DATABASE

# Load environment variables
load_dotenv()

def get_bearer_token():
    """Get bearer token using OAuth 2.0 Resource Owner Password Credentials Grant."""
    try:
        # Create OAuth2 session with Resource Owner Password Credentials Grant
        client = LegacyApplicationClient(client_id='IOMApp')
        oauth = OAuth2Session(client=client)
        
        # Token endpoint for Aras
        token_url = f"{URL}/oauthserver/connect/token"
        
        # Get token using username/password (with database parameter)
        token = oauth.fetch_token(
            token_url=token_url,
            username=USERNAME,
            password=PASSWORD,
            client_id='IOMApp',
            scope='openid Innovator offline_access',
            database=DATABASE  # Aras requires database parameter
        )
        
        return token['access_token']
        
    except Exception as err:
        import sys
        print(f"Error in get_bearer_token: {err}", file=sys.stderr)
        # Fallback to manual OAuth if the library approach fails
        return get_bearer_token_manual()

def get_bearer_token_manual():
    """Fallback manual OAuth 2.0 implementation."""
    try:
        token_url = f"{URL}/oauthserver/connect/token"
        
        # Prepare OAuth 2.0 token request with database parameter
        token_data = {
            "grant_type": "password",
            "username": USERNAME,
            "password": PASSWORD,
            "database": DATABASE,  # Aras requires this
            "scope": "openid Innovator offline_access",
            "client_id": "IOMApp"
        }

        # Make token request
        token_response = requests.post(
            token_url,
            data=token_data,
            headers={
                'Content-Type': 'application/x-www-form-urlencoded'
            }
        )
        
        token_response.raise_for_status()
        token_json = token_response.json()
        
        return token_json["access_token"]
        
    except requests.exceptions.HTTPError as http_err:
        import sys
        print(f"HTTP error in get_bearer_token_manual: {http_err}", file=sys.stderr)
        print(f"Response content: {http_err.response.text}", file=sys.stderr)
        raise http_err
    except Exception as err:
        import sys
        print(f"Error in get_bearer_token_manual: {err}", file=sys.stderr)
        raise err 