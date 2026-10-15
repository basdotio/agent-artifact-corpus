#!/usr/bin/env python3
"""HeadHunter OAuth Authorization Flow Example.

This script demonstrates the complete OAuth 2.0 authorization flow for HeadHunter API.
It guides the user through the process of obtaining access and refresh tokens required
for authenticated API calls to HeadHunter services.

The OAuth flow consists of the following steps:
1. Generate authorization URL with required parameters
2. User opens the URL, authorizes the application, and gets authorization code
3. Exchange the authorization code for access and refresh tokens
4. Save tokens to .env file for use by the MCP server

This script is intended to be run once to set up authentication. The obtained
tokens can then be used by the HeadHunter MCP server for authenticated operations
such as job applications and resume management.

Required environment variables:
    HH_CLIENT_ID: OAuth client ID from HeadHunter developer account
    HH_CLIENT_SECRET: OAuth client secret from HeadHunter developer account
    HH_REDIRECT_URI: Redirect URI registered in HeadHunter application settings

Usage:
    python examples/oauth_flow.py

The script will:
    - Display authorization URL for user to open in browser
    - Prompt for authorization code from the redirect URL
    - Exchange code for tokens
    - Save tokens to .env file automatically
"""

import os
import asyncio
import httpx
from dotenv import load_dotenv
from urllib.parse import urlencode

load_dotenv()

CLIENT_ID = os.getenv("HH_CLIENT_ID")
CLIENT_SECRET = os.getenv("HH_CLIENT_SECRET")
REDIRECT_URI = os.getenv("HH_REDIRECT_URI")


def get_auth_url():
    """Generate HeadHunter OAuth authorization URL.

    Constructs the authorization URL that users need to visit to grant
    permission to the application. The URL includes the client ID and
    redirect URI, and uses the authorization code grant type.

    The user should open this URL in a browser, log in to their HeadHunter
    account, and authorize the application. After authorization, they will
    be redirected to the specified redirect URI with an authorization code.

    Returns:
        str: Complete authorization URL with query parameters including:
            - response_type: Set to "code" for authorization code flow
            - client_id: OAuth client ID from environment variables
            - redirect_uri: Registered redirect URI from environment variables

    Note:
        Requires HH_CLIENT_ID and HH_REDIRECT_URI environment variables to be set.
    """
    params = {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
    }
    return f"https://hh.ru/oauth/authorize?{urlencode(params)}"


async def exchange_code(code: str):
    """Exchange authorization code for OAuth tokens.

    Makes a POST request to HeadHunter's token endpoint to exchange
    the authorization code (received from the authorization step) for
    access and refresh tokens.

    This is the second step of the OAuth 2.0 authorization code flow.
    The authorization code has a short lifetime and can only be used once.

    Args:
        code (str): Authorization code received from the HeadHunter
            authorization redirect. This code is typically found in the
            URL query parameter after user authorization.

    Returns:
        Dict[str, Any]: Token response containing:
            - access_token (str): OAuth access token for authenticated API calls
            - refresh_token (str): Token for refreshing expired access tokens
            - expires_in (int): Access token lifetime in seconds
            - token_type (str): Token type (typically "Bearer")

    Raises:
        httpx.HTTPError: If the token exchange fails due to invalid code,
            client credentials, or other OAuth errors.

    Note:
        Requires HH_CLIENT_ID, HH_CLIENT_SECRET, and HH_REDIRECT_URI
        environment variables to be set.
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://hh.ru/oauth/token",
            data={
                "grant_type": "authorization_code",
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "code": code,
                "redirect_uri": REDIRECT_URI,
            },
        )
        response.raise_for_status()
        return response.json()


async def main():
    """Main function that orchestrates the complete OAuth flow.

    This function guides the user through the entire OAuth 2.0 authorization
    process for HeadHunter API access. It provides a step-by-step interactive
    experience to obtain and save authentication tokens.

    The function performs the following steps:
    1. Display formatted instructions and authorization URL
    2. Wait for user to complete browser authorization and enter code
    3. Exchange the authorization code for tokens
    4. Display token information (partially masked for security)
    5. Automatically append tokens to .env file for future use

    The saved tokens can then be used by the HeadHunter MCP server to make
    authenticated API calls for user-specific operations like job applications
    and resume management.

    Raises:
        Exception: If required environment variables are missing or if the
            OAuth flow fails at any step.

    Note:
        This function modifies the .env file by appending the obtained tokens.
        Existing content is preserved, and tokens are added with comments
        indicating their expiration time.
    """
    print("=" * 60)
    print("HeadHunter OAuth Authorization")
    print("=" * 60)
    print("\n1. Откройте эту ссылку в браузере:\n")
    print(get_auth_url())
    print("\n2. Авторизуйтесь и разрешите доступ")
    print("3. Скопируйте код из URL (после ?code=)\n")

    code = input("Введите код авторизации: ").strip()

    print("\nОбмен кода на токены...")
    tokens = await exchange_code(code)

    print("\n✅ Успешно получены токены!")
    print(f"Access Token: {tokens['access_token'][:50]}...")
    print(f"Refresh Token: {tokens['refresh_token'][:50]}...")
    print(f"Expires in: {tokens['expires_in']} seconds")

    print("\n📝 Сохраните эти токены в .env файл:")
    print(f"\nHH_ACCESS_TOKEN={tokens['access_token']}")
    print(f"HH_REFRESH_TOKEN={tokens['refresh_token']}")

    with open(".env", "a") as f:
        f.write(f"\n\n# OAuth tokens (expires at {tokens['expires_in']} seconds)\n")
        f.write(f"HH_ACCESS_TOKEN={tokens['access_token']}\n")
        f.write(f"HH_REFRESH_TOKEN={tokens['refresh_token']}\n")

    print("\n✅ Токены сохранены в .env файл")


if __name__ == "__main__":
    asyncio.run(main())
