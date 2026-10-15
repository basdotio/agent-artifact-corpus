from bs4 import BeautifulSoup

from fastmcp import FastMCP
from fastmcp.server.dependencies import get_access_token

from msgraph.generated.users.item.messages.messages_request_builder import (
    MessagesRequestBuilder,
)
from kiota_abstractions.base_request_configuration import RequestConfiguration

from utils.auth import get_graph_client
from utils.parser import parse_email_html

from typing import List, TypedDict


class FromAddress(TypedDict):
    name: str
    address: str


class Email(TypedDict):
    subject: str
    delivery_time: str
    from_address: FromAddress
    body: str


MailList = List[Email]


def setup_mail_resources(mcp: FastMCP):
    """Register all mail-related resources"""

    @mcp.resource("outlook://mail/recent/{count}", name="Get Recent Mail")
    async def get_recent_mail(count: int = 20) -> MailList:
        """get <count> (default of 20) most recent emails from your inbox.
        returns: email subject, delivery time, from address, and body
        """
        token = get_access_token()
        client = get_graph_client(token.token)

        # get recent emails
        query_params = MessagesRequestBuilder.MessagesRequestBuilderGetQueryParameters(
            select=["sender", "subject", "receivedDateTime", "body"], top=count
        )

        request_configuration = RequestConfiguration(
            query_parameters=query_params,
        )
        message_resp = await client.me.messages.get(
            request_configuration=request_configuration
        )

        messages = []
        if message_resp and message_resp.value:
            for msg in message_resp.value:
                messages.append(
                    {
                        "subject": msg.subject,
                        "delivery_time": msg.received_date_time,
                        "from_address": {
                            "name": msg.sender.email_address.name,
                            "address": msg.sender.email_address.address,
                        },
                        "body": parse_email_html(msg.body.content),
                    }
                )

        return messages

    @mcp.resource("outlook://mail/unread/{count}", name="Get Unread Emails")
    async def get_unread_mail(count=20) -> MailList:
        """get <count> (default of 20) most recent unread emails from your inbox.
        returns: email subject, delivery time, from address, and body
        """
        token = get_access_token()
        client = get_graph_client(token.token)

        # get the number of unread emails
        query_params = MessagesRequestBuilder.MessagesRequestBuilderGetQueryParameters(
            filter="isRead eq false",
            select=["sender", "subject", "receivedDateTime", "body"],
            top=count,
        )

        request_configuration = RequestConfiguration(
            query_parameters=query_params,
        )

        request_configuration = RequestConfiguration(
            query_parameters=query_params,
        )
        message_resp = await client.me.messages.get(
            request_configuration=request_configuration
        )

        messages = []
        if message_resp and message_resp.value:
            for msg in message_resp.value:
                messages.append(
                    {
                        "subject": msg.subject,
                        "delivery_time": msg.received_date_time,
                        "from_address": {
                            "name": msg.sender.email_address.name,
                            "address": msg.sender.email_address.address,
                        },
                        "body": parse_email_html(msg.body.content),
                    }
                )

        return messages

    @mcp.resource("outlook://mail/folders", name="Get Folders In Mailbox")
    async def get_mail_folders() -> list:
        """gets folders in your mailbox
        returns: folder name, path, and ID
        """
        token = get_access_token()
        client = get_graph_client(token.token)

        # Fetch mail folders
        folders_resp = await client.me.mail_folders.get()

        folders = []
        if folders_resp and folders_resp.value:
            for folder in folders_resp.value:
                folders.append(
                    {
                        "name": folder.display_name,
                        "id": folder.id,
                        "path": getattr(folder, "parent_folder_id", None),
                    }
                )

        return folders
