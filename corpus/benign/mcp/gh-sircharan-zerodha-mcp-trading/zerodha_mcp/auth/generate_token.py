"""
Generate authentication token for Zerodha API access.

This module handles the complete authentication flow for the Zerodha MCP trading
system. It provides functionality to:
1. Generate the login URL for user authentication
2. Process the authentication callback
3. Generate and store access tokens
4. Handle error conditions gracefully

The authentication flow follows these steps:
1. User visits the login URL
2. User authenticates with Zerodha credentials
3. Zerodha redirects with a request token
4. System generates an access token using the request token
5. Access token is stored for future use

Environment Variables Required:
-----------------------------
- ZERODHA_API_KEY: Your Zerodha API key
- ZERODHA_API_SECRET: Your Zerodha API secret

Example Usage:
-------------
$ python -m zerodha_mcp.auth.generate_token

Security Notes:
--------------
- Never share or commit your API credentials
- Store credentials only in .env file
- Rotate access tokens periodically
- Monitor authentication logs for suspicious activity
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from kiteconnect import KiteConnect
from loguru import logger

def setup_logging():
    """
    Configure logging for the authentication process.
    
    Sets up logging to both console and file with appropriate formats:
    - Console: Real-time feedback during authentication
    - File: Persistent log for audit and debugging
    
    The log file (mcp.log) is automatically rotated when it reaches 10MB.
    """
    logger.remove()
    logger.add(sys.stderr, format="{time} | {level} | {message}")
    logger.add("mcp.log", rotation="10 MB")

def load_environment():
    """
    Load and validate environment variables from .env file.
    
    This function:
    1. Checks for the existence of .env file
    2. Loads environment variables
    3. Validates required API credentials
    
    Returns:
        tuple: (api_key, api_secret) if both are found
        
    Raises:
        SystemExit: If .env file is missing or credentials are not found
    """
    env_path = Path(".env")
    if not env_path.exists():
        logger.error(".env file not found. Please create one with your API credentials.")
        sys.exit(1)
    
    load_dotenv()
    
    api_key = os.getenv("ZERODHA_API_KEY")
    api_secret = os.getenv("ZERODHA_API_SECRET")
    
    if not api_key or not api_secret:
        logger.error("API credentials not found in .env file.")
        sys.exit(1)
    
    return api_key, api_secret

def generate_login_url():
    """
    Generate the Zerodha login URL for user authentication.
    
    This function:
    1. Loads API credentials
    2. Initializes KiteConnect client
    3. Generates the login URL
    
    Returns:
        str: The URL where users should authenticate
        
    Example:
        >>> url = generate_login_url()
        >>> print(f"Please visit: {url}")
    """
    api_key, _ = load_environment()
    kite = KiteConnect(api_key=api_key)
    return kite.login_url()

def generate_access_token(request_token):
    """
    Generate and store an access token using the request token.
    
    This function:
    1. Initializes KiteConnect with API credentials
    2. Generates a session using the request token
    3. Extracts the access token
    4. Stores the token in .tokens file
    
    Args:
        request_token (str): The request token from Zerodha's callback
        
    Returns:
        str: The generated access token
        
    Raises:
        SystemExit: If token generation fails
        
    Example:
        >>> token = generate_access_token("your_request_token")
        >>> print(f"Access token: {token}")
    """
    api_key, api_secret = load_environment()
    kite = KiteConnect(api_key=api_key)
    
    try:
        data = kite.generate_session(request_token, api_secret=api_secret)
        access_token = data["access_token"]
        
        # Save the access token
        token_path = Path(".tokens")
        token_path.write_text(access_token)
        
        logger.info("Access token generated and saved successfully!")
        return access_token
    
    except Exception as e:
        logger.error(f"Failed to generate access token: {str(e)}")
        sys.exit(1)

def main():
    """
    Main function to orchestrate the token generation process.
    
    This function:
    1. Sets up logging
    2. Generates and displays the login URL
    3. Waits for user input (request token)
    4. Generates and saves the access token
    
    The process requires user interaction to:
    1. Visit the login URL
    2. Authenticate with Zerodha
    3. Copy and paste the request token
    """
    setup_logging()
    logger.info("Starting authentication process...")
    
    # Generate and display login URL
    login_url = generate_login_url()
    logger.info(f"Please visit this URL to login: {login_url}")
    
    # Get request token from user
    request_token = input("Enter the request token from the redirect URL: ")
    
    # Generate and save access token
    access_token = generate_access_token(request_token)
    logger.info("Authentication completed successfully!")

if __name__ == "__main__":
    main() 