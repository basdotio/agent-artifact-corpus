from os import getenv


def load_config():
    """
    loads configuration for this application from environment
    variables in the application's environment.
    """
    host = getenv("HOST") if getenv("HOST") else "127.0.0.1"
    port = getenv("PORT") if getenv("PORT") else "8080"
    base_url = getenv("BASE_URL") if getenv("BASE_URL") else f"http://{host}:{port}"

    return {
        "host": host,
        "port": port,
        "base_url": base_url,
        "azure_config_url": getenv("AZURE_CONFIG_URL"),
        "azure_tenant_id": getenv("AZURE_TENANT_ID"),
        "azure_client_id": getenv("AZURE_CLIENT_ID"),
        "azure_redirect_url": (
            getenv("AZURE_REDIRECT_URL")
            if getenv("AZURE_REDIRECT_URL")
            else f"/auth/callback"
        ),
        "azure_client_secret": getenv("AZURE_CLIENT_SECRET"),
    }
