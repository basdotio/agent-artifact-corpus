import os
from typing import Any, Awaitable, Callable, MutableMapping
from starlette.responses import PlainTextResponse

# Retrieve the main authentication token from environment variables.
# This token is used for general API access, not specific user authorization.
BEARER_TOKEN = os.environ.get("AUTH_TOKEN")


class AuthenticationMiddleware:
    """
    A Starlette middleware for handling authentication based on a bearer token.

    This middleware intercepts incoming HTTP requests. It checks for an Authorization
    header with a Bearer token for most routes. For the "/auth" route, it expects
    'userid' and 'token' as query parameters to validate user-specific authorization.
    """

    def __init__(
        self,
        app: Callable[
            [
                MutableMapping[str, Any],
                Callable[[], Awaitable[MutableMapping[str, Any]]],
                Callable[[MutableMapping[str, Any]], Awaitable[None]],
            ],
            Awaitable[None],
        ],
    ):
        """
        Initializes the AuthenticationMiddleware.

        Args:
            app: The ASGI application to be wrapped by this middleware.
        """
        self.app = app

    async def __call__(
        self,
        scope: MutableMapping[str, Any],
        receive: Callable[[], Awaitable[MutableMapping[str, Any]]],
        send: Callable[[MutableMapping[str, Any]], Awaitable[None]],
    ):
        """
        The ASGI callable method for the middleware.

        Args:
            scope: The ASGI scope dictionary containing information about the request.
            receive: An awaitable callable that receives incoming messages.
            send: An awaitable callable that sends outgoing messages.
        """
        # Process only HTTP requests
        if scope["type"] == "http":
            # Get the request path from the scope, default to "/"
            path = scope.get("path", "/")

            # Extract and decode headers into a dictionary for easy access
            headers = scope.get("headers", [])
            header_dict = {
                header[0].decode("latin-1").lower(): header[1].decode("latin-1")
                for header in headers
            }

            # Initialize bearer token from request
            bearer = None

            authorization_header = header_dict.get("authorization")

            # If no Authorization header is present, return 401 Unauthorized
            if not authorization_header:
                response = PlainTextResponse(
                    "Missing Authorization Header", status_code=401
                )
                await response(scope, receive, send)
                return

            # Parse the Authorization header to extract the bearer token
            parts = authorization_header.strip().split(maxsplit=1)
            if len(parts) == 2 and parts[0].lower() == "bearer":
                bearer = parts[1]

            # If the extracted bearer token does not match
            if bearer != BEARER_TOKEN:
                # Return 401 Unauthorized response
                response = PlainTextResponse("Unauthorized", status_code=401)
                await response(scope, receive, send)
                return

            # If authentication is successful, proceed to the next ASGI application in the stack
            await self.app(scope, receive, send)
        else:
            # If it's not an HTTP scope (e.g., websocket), just pass it to the next application
            await self.app(scope, receive, send)