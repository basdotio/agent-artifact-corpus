from typing import Optional, List
from datetime import datetime

from fastmcp import FastMCP
from fastmcp.server.dependencies import get_access_token

from msgraph.generated.users.item.messages.messages_request_builder import (
    MessagesRequestBuilder,
)
from kiota_abstractions.base_request_configuration import RequestConfiguration

from utils.auth import get_graph_client
from utils.parser import parse_email_html


def setup_mail_tools(mcp: FastMCP):
    """Register all mail-related tools"""

    @mcp.tool()
    async def search_emails(
        sender: Optional[str] = None,
        subject: Optional[str] = None,
        body: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        max_results: int = 20,
    ) -> List[dict]:
        """
        Search for emails in your mailbox based on various criteria.

        Args:
            sender: Email address or name of the sender to search for (e.g., "john@example.com" or "John Doe")
            subject: Text to search for in email subjects
            body: Text to search for in email body
            start_date: Search for emails received on or after this date (ISO format: YYYY-MM-DD)
            end_date: Search for emails received on or before this date (ISO format: YYYY-MM-DD)
            max_results: Maximum number of results to return (default: 20, max: 100)

        Returns:
            List of emails matching the search criteria, including subject, sender, delivery time, and body
        """
        token = get_access_token()
        client = get_graph_client(token.token)

        # Build the filter query using OData syntax
        filter_terms = []

        if sender:
            # Search in the from field - exact match on email address
            filter_terms.append(f"from/emailAddress/address eq '{sender}'")

        if start_date:
            # Search for emails received on or after the start date
            filter_terms.append(f"receivedDateTime ge {start_date}T00:00:00Z")

        if end_date:
            # Search for emails received on or before the end date
            filter_terms.append(f"receivedDateTime le {end_date}T23:59:59Z")

        # Combine all filter terms with AND operator
        filter_query = " and ".join(filter_terms) if filter_terms else None

        # For subject and body, use search instead of filter (more flexible text matching)
        search_terms = []
        if subject:
            search_terms.append(subject)
        if body:
            search_terms.append(body)

        search_query = " ".join(search_terms) if search_terms else None

        # If no search criteria provided, return an error
        if not filter_query and not search_query:
            return {
                "error": "Please provide at least one search criterion (sender, subject, body, start_date, or end_date)"
            }

        # Limit max_results to 100
        if max_results > 100:
            max_results = 100

        # Build the query parameters
        query_params = MessagesRequestBuilder.MessagesRequestBuilderGetQueryParameters(
            filter=filter_query,
            search=search_query,
            select=["sender", "subject", "receivedDateTime", "body"],
            top=max_results,
        )

        request_configuration = RequestConfiguration(
            query_parameters=query_params,
        )

        # Execute the search
        message_resp = await client.me.messages.get(
            request_configuration=request_configuration
        )

        # Process the results
        messages = []
        if message_resp and message_resp.value:
            for msg in message_resp.value:
                messages.append(
                    {
                        "subject": msg.subject,
                        "delivery_time": (
                            msg.received_date_time.isoformat()
                            if msg.received_date_time
                            else None
                        ),
                        "from_address": {
                            "name": (
                                msg.sender.email_address.name
                                if msg.sender and msg.sender.email_address
                                else None
                            ),
                            "address": (
                                msg.sender.email_address.address
                                if msg.sender and msg.sender.email_address
                                else None
                            ),
                        },
                        "body": (
                            parse_email_html(msg.body.content)
                            if msg.body and msg.body.content
                            else ""
                        ),
                    }
                )

        return messages
