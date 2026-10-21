"""Base utilities for Grafana MCP tools to eliminate code duplication."""

import functools
import threading
from typing import Callable, TypeVar, ParamSpec

from ..client import create_client
from ..config import config

P = ParamSpec('P')
T = TypeVar('T')

# Thread-local storage for the current Grafana client
_thread_local = threading.local()


def with_validated_client(func: Callable[P, T]) -> Callable[P, T]:
    """Decorator to handle cluster validation and client creation.
    
    This decorator automatically:
    1. Validates the cluster parameter
    2. Creates and manages the HTTP client
    3. Makes the client available via get_current_client()
    
    The decorated function should access the client via get_current_client().
    """

    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        # Extract cluster from first argument or keyword arguments
        if args:
            cluster = args[0]
        elif 'cluster' in kwargs:
            cluster = kwargs['cluster']
        else:
            raise ValueError("Cluster parameter is required as first argument")

        if not isinstance(cluster, str):
            raise ValueError("Cluster parameter must be a string")

        # Validate cluster configuration
        config.validate_cluster(cluster)

        # Create client and call function
        with create_client(cluster) as client:
            # Store client in thread-local storage
            _thread_local.client = client
            try:
                return func(*args, **kwargs)
            finally:
                # Clean up
                if hasattr(_thread_local, 'client'):
                    delattr(_thread_local, 'client')

    return wrapper


def get_current_client():
    """Get the current Grafana client from the decorator context.
    
    This function should only be called from within a function decorated with @grafana_tool.
    """
    if not hasattr(_thread_local, 'client'):
        raise RuntimeError("get_current_client() called outside of @grafana_tool decorated function")
    return _thread_local.client


def validate_cluster_only(func: Callable[P, T]) -> Callable[P, T]:
    """Decorator to only validate cluster parameter without creating client.
    
    Used for functions that don't need HTTP client but still need cluster validation.
    """

    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        # Extract cluster from first argument if present
        if args:
            cluster = args[0]
            if isinstance(cluster, str):
                config.validate_cluster(cluster)

        return func(*args, **kwargs)

    return wrapper


def handle_grafana_errors(func: Callable[P, T]) -> Callable[P, T]:
    """Decorator to provide consistent error handling for Grafana API calls."""

    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # Convert httpx errors to more user-friendly messages
            error_msg = str(e)
            if "401" in error_msg:
                raise ValueError("Authentication failed. Check your API token.")
            elif "403" in error_msg:
                raise ValueError("Permission denied. Check your API token permissions.")
            elif "404" in error_msg:
                raise ValueError("Resource not found.")
            elif "500" in error_msg:
                raise ValueError("Grafana server error. Please try again later.")
            else:
                # Re-raise original error for other cases
                raise

    return wrapper


def grafana_tool(func: Callable[P, T]) -> Callable[P, T]:
    """Convenience decorator that combines client validation and error handling."""
    return handle_grafana_errors(with_validated_client(func))
