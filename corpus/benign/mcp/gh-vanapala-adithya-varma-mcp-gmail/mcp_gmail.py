import os
from typing import Any
from mcp.server.fastmcp import FastMCP
from tools.google_api import GmailTool


work_dir = os.path.dirname(__file__)
gmail_tool = GmailTool(os.path.join(work_dir, 'client-secret.json'))

mcp = FastMCP(
    'Gmail',
    dependencies=[
        'google-api-python-client',
        'google-auth-httplib2',
        'google-auth-oauthlib'
    ],
)

mcp.add_tool(
    gmail_tool.send_email,
    name='Gmail-Send-Email',
    description='Send an email message in Gmail.'
)

mcp.add_tool(
    gmail_tool.get_email_message_details,
    name='Gmail-Get-Email-Message-Details',
    description='Get details of an email message in Gmail.'
)

mcp.add_tool(
    gmail_tool.get_email_message_body,
    name='Get-Email-Message-Body',
    description='Get the body of an email message (Gmail).'
)

mcp.add_tool(
    gmail_tool.search_emails,
    name='Gmail-Search-Emails',
    description='Search or return emails in Gmail. Default is None, which returns all emails.'
)

mcp.add_tool(
    gmail_tool.delete_email_message,
    name='Gmail-Delete-Email-Message',
    description='Delete an email message in Gmail.'
)


if __name__ == "__main__":
    mcp.run()