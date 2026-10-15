from dotenv import load_dotenv

from fastmcp import FastMCP
from fastmcp.server.dependencies import get_access_token
from fastmcp.server.context import Context

from msgraph import GraphServiceClient
from msgraph.generated.users.item.messages.messages_request_builder import (
    MessagesRequestBuilder,
)
from kiota_abstractions.base_request_configuration import RequestConfiguration

from utils.config import load_config
from utils.auth import PatchedAzureProvider, get_graph_client

from resources.mail import setup_mail_resources
from resources.calendar import setup_calendar_resources
from tools.mail import setup_mail_tools
from tools.calendar import setup_calendar_tools


load_dotenv()


def main():
    config = load_config()

    # initialize oidc proxy
    auth = PatchedAzureProvider(
        client_id=config.get("azure_client_id"),
        tenant_id=config.get("azure_tenant_id"),
        client_secret=config.get("azure_client_secret"),
        base_url=config.get("base_url"),
        redirect_path=config.get("azure_redirect_url"),
        required_scopes=[
            "User.Read",
            "email",
            "openid",
            "profile",
            "Calendars.ReadWrite",
            "Mail.Read",
            "MailboxFolder.Read",
        ],
    )

    # initialize server
    mcp = FastMCP(name="Outlook MCP", auth=auth, stateless_http=True)

    @mcp.resource(
        "config://whoami",
        title="Who Am I",
        description="Information about the logged in user",
    )
    def get_who_am_i(ctx: Context) -> dict:
        token = get_access_token()

        return {
            "azure_id": token.claims.get("sub"),
            "email": token.claims.get("email"),
            "name": token.claims.get("name"),
        }

    # * RESOURCES
    # register all resources

    setup_mail_resources(mcp=mcp)
    setup_calendar_resources(mcp=mcp)

    # * TOOLS
    # register all tools
    setup_mail_tools(mcp=mcp)
    setup_calendar_tools(mcp=mcp)

    # start the server
    mcp.run(
        transport="streamable-http",
        host=config.get("host"),
        port=int(config.get("port")),
    )


if __name__ == "__main__":
    main()
