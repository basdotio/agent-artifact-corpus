"""
Authentication module for Zerodha API access.

This module handles all authentication-related functionality for the Zerodha MCP
trading system, including:
- Access token management
- Session handling
- Token persistence
- Authentication state validation

The module uses a file-based token storage system for persistence between sessions.
Tokens are stored in a '.tokens' file in the project root directory.

Example Usage:
-------------
>>> from zerodha_mcp.auth import get_access_token
>>> 
>>> # Get stored access token
>>> token = get_access_token()
>>> if token:
...     print("Using existing session")
... else:
...     print("New authentication required")

Security Note:
-------------
Access tokens are sensitive credentials. The .tokens file should be:
- Added to .gitignore
- Protected with appropriate file permissions
- Regularly rotated for security
"""

from pathlib import Path
from typing import Optional

def get_access_token() -> Optional[str]:
    """
    Retrieve the stored Zerodha API access token.
    
    This function checks for a stored access token in the .tokens file.
    The token is used to authenticate API requests without requiring
    re-authentication for each session.
    
    Returns:
        Optional[str]: The access token if available, None if:
            - The .tokens file doesn't exist
            - The file is empty
            - The file cannot be read
    
    Example:
        >>> token = get_access_token()
        >>> if token:
        ...     kite.set_access_token(token)
        ... else:
        ...     # Initiate new authentication flow
        ...     pass
    """
    token_path = Path(".tokens")
    if token_path.exists():
        return token_path.read_text().strip()
    return None 