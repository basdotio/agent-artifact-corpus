# Basic imports
from mcp.server.fastmcp import FastMCP
from mcp.types import TextContent
import sys
import os
# from dotenv import load_dotenv
from email.message import EmailMessage
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import base64
from googleapiclient.errors import HttpError
import json
from url_scrape import scrape_url
import time
import asyncio

# Load environment variables
# load_dotenv()

# Gmail and Google Drive API setup
SCOPES = [
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive.file'
]
gmail_service = None
sheets_service = None
drive_service = None

def initialize_google_services():
    global gmail_service, sheets_service, drive_service
    creds = None
    token_path = 'token.json'
    creds_path = 'credentials.json'

    print("\nInitializing Google services...")
    
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, 'w') as token:
            token.write(creds.to_json())
    
    gmail_service = build('gmail', 'v1', credentials=creds)
    sheets_service = build('sheets', 'v4', credentials=creds)
    drive_service = build('drive', 'v3', credentials=creds)

    print("Google services initialized successfully")

# Initialize Google services
try:
    initialize_google_services()
except Exception as e:
    print(f"Failed to initialize Google services: {e}")

# Instantiate an MCP server client
mcp = FastMCP("Cortex-R Agent")

# DEFINE TOOLS

# Fetch F1 standings tool
@mcp.tool()
async def fetch_f1_standings() -> dict:
    """Fetch the current F1 standings"""
    print("CALLED: fetch_f1_standings() -> dict:")
    try:
        # Scrape the F1 standings page
        URL = "https://www.formula1.com/en/results/2025/drivers"
        content = scrape_url(URL, "f1_standings")

        # Handle table formatting
        content = content.replace("|", ",")
        
        return {
            "content": [
                TextContent(
                    type="text",
                    text=content
                )
            ]
        }
    except Exception as e:
        return {
            "content": [
                TextContent(
                    type="text",
                    text=f"Failed to fetch F1 standings: {str(e)}"
                )
            ]
        }

# Send email tool
@mcp.tool()
async def send_email(recipient_id: str, subject: str, message: str) -> dict:
    """Send an email using Gmail API"""
    print("CALLED: send_email(recipient_id: str, subject: str, message: str) -> dict:")
    try:
        if not gmail_service:
            return {
                "content": [
                    TextContent(
                        type="text",
                        text="Gmail service not initialized"
                    )
                ]
            }
            
        message_obj = EmailMessage()
        message_obj.set_content(message)
        
        # Get user's email address
        user_profile = gmail_service.users().getProfile(userId='me').execute()
        sender_email = user_profile.get('emailAddress', '')
        
        message_obj['To'] = recipient_id
        message_obj['From'] = sender_email
        message_obj['Subject'] = subject

        encoded_message = base64.urlsafe_b64encode(message_obj.as_bytes()).decode()
        create_message = {'raw': encoded_message}
        
        send_message = gmail_service.users().messages().send(userId="me", body=create_message).execute()
        
        return {
            "content": [
                TextContent(
                    type="text",
                    text=f"Email sent successfully. Message ID: {send_message['id']}"
                )
            ]
        }
    except Exception as e:
        return {
            "content": [
                TextContent(
                    type="text",
                    text=f"Failed to send email: {str(e)}"
                )
            ]
        }

# Get unread emails tool
@mcp.tool()
async def get_unread_emails() -> dict:
    """Get unread emails from Gmail"""
    print("CALLED: get_unread_emails() -> dict:")
    try:
        if not gmail_service:
            return {
                "content": [
                    TextContent(
                        type="text",
                        text="Gmail service not initialized"
                    )
                ]
            }
            
        results = gmail_service.users().messages().list(
            userId='me',
            labelIds=['UNREAD', 'INBOX']
        ).execute()
        
        messages = results.get('messages', [])
        
        if not messages:
            return {
                "content": [
                    TextContent(
                        type="text",
                        text="No unread messages found."
                    )
                ]
            }
            
        unread_emails = []
        for msg in messages[:5]:  # Get details of first 5 unread messages
            message = gmail_service.users().messages().get(
                userId='me',
                id=msg['id']
            ).execute()
            
            headers = message['payload']['headers']
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No subject')
            sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown sender')
            
            unread_emails.append({
                'id': msg['id'],
                'subject': subject,
                'from': sender
            })
            
        return {
            "content": [
                TextContent(
                    type="text",
                    text=f"Found {len(unread_emails)} unread emails: {unread_emails}"
                )
            ]
        }
    except Exception as e:
        return {
            "content": [
                TextContent(
                    type="text",
                    text=f"Failed to get unread emails: {str(e)}"
                )
            ]
        }

@mcp.tool()
async def create_google_sheet(title: str, content: str) -> dict:
    """Create a Google Sheet with the given content and return its link"""
    print("CALLED: create_google_sheet(title: str, content: str) -> dict:")
    try:
        if not sheets_service or not drive_service:
            return {
                "content": [
                    TextContent(
                        type="text",
                        text="Google services not initialized"
                    )
                ]
            }

        # Create a new spreadsheet
        spreadsheet = {
            'properties': {
                'title': title
            }
        }
        spreadsheet = sheets_service.spreadsheets().create(body=spreadsheet).execute()
        spreadsheet_id = spreadsheet.get('spreadsheetId')

        try:
            # Parse content as JSON if it's a JSON string
            data = json.loads(content)
            if isinstance(data, list):
                values = data
            elif isinstance(data, dict):
                # Convert dict to 2D array with keys as headers
                headers = list(data.keys())
                values = [headers, list(data.values())]
            else:
                values = [[str(content)]]
        except json.JSONDecodeError:
            # If not JSON, split by newlines and commas
            values = [
                row.split(',')
                for row in content.split('\n')
                if row.strip()
            ]

        # Update the values in the spreadsheet
        body = {
            'values': values
        }
        sheets_service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range='A1',
            valueInputOption='RAW',
            body=body
        ).execute()

        # Make the file readable by anyone with the link
        drive_service.permissions().create(
            fileId=spreadsheet_id,
            body={'type': 'anyone', 'role': 'reader'},
            fields='id'
        ).execute()

        # Get the spreadsheet URL
        spreadsheet_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"

        return {
            "content": [
                TextContent(
                    type="text",
                    text=f"Google Sheet created successfully. URL: {spreadsheet_url}"
                )
            ]
        }
    except Exception as e:
        return {
            "content": [
                TextContent(
                    type="text",
                    text=f"Failed to create Google Sheet: {str(e)}"
                )
            ]
        }


if __name__ == "__main__":
    print("STARTING THE SERVER")

    if len(sys.argv) > 1 and sys.argv[1] == "dev":
        mcp.run() # Run without transport for dev server
    else:
        # Start the server in a separate thread
        import threading
        server_thread = threading.Thread(target=lambda: mcp.run(transport="stdio"))
        # server_thread = threading.Thread(target=lambda: mcp.run(transport="sse"))
        server_thread.daemon = True
        server_thread.start()
        
        # Wait a moment for the server to start
        time.sleep(2)
        
        # # Initialize Google services
        # try:
        #     initialize_google_services()
        # except Exception as e:
        #     print(f"Failed to initialize Google services: {e}")
        
        # Test the tools
        # print("\nTesting the tools...")
        # asyncio.run(fetch_f1_standings())
        # asyncio.run(create_google_sheet("F1 Standings", "TBD,TBD\nTBD,TBD"))
        # asyncio.run(send_email("thegame.banerjee3@gmail.com", "F1 Standings", "TBD"))

        # Keep the main thread alive
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nShutting down...")