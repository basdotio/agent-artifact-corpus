#!/usr/bin/env python3
"""
Unified Google Workspace Authentication System
Supports Calendar and Gmail API

Reference: Auto-authentication implementation from @gongrzhe/server-gmail-autoauth-mcp
"""

import os
import sys
import json
import webbrowser
import http.server
import socketserver
from urllib.parse import urlparse, parse_qs
from pathlib import Path
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

# Global configuration directory
WORKSPACE_DIR = Path.home() / '.google-workspace'
CREDENTIALS_PATH = WORKSPACE_DIR / 'credentials.json'
TOKEN_PATH = WORKSPACE_DIR / 'token.json'

# OAuth Scopes - Calendar + Gmail
SCOPES = [
    # Calendar
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/calendar.events',
    'https://www.googleapis.com/auth/calendar.readonly',

    # Gmail
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/gmail.labels',
    'https://www.googleapis.com/auth/gmail.compose',
    'https://www.googleapis.com/auth/gmail.settings.basic'
]

# OAuth callback port
OAUTH_PORT = 3000


class OAuthCallbackHandler(http.server.SimpleHTTPRequestHandler):
    """OAuth callback HTTP handler"""

    def do_GET(self):
        """Handle GET request"""
        parsed = urlparse(self.path)

        if parsed.path == '/oauth2callback':
            # Get authorization code
            query = parse_qs(parsed.query)
            auth_code = query.get('code', [None])[0]

            if auth_code:
                # Save auth code for main program
                self.server.auth_code = auth_code

                # Return success page
                self.send_response(200)
                self.send_header('Content-type', 'text/html; charset=utf-8')
                self.end_headers()

                html = """
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="utf-8">
                    <title>Authentication Successful</title>
                    <style>
                        body {
                            font-family: Arial, sans-serif;
                            display: flex;
                            justify-content: center;
                            align-items: center;
                            height: 100vh;
                            margin: 0;
                            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        }
                        .container {
                            background: white;
                            padding: 40px;
                            border-radius: 10px;
                            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
                            text-align: center;
                        }
                        h1 { color: #4CAF50; margin-bottom: 10px; }
                        p { color: #666; font-size: 18px; }
                        .emoji { font-size: 60px; margin-bottom: 20px; }
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="emoji">✅</div>
                        <h1>Authentication Successful!</h1>
                        <p>Google Workspace Skill is now authorized</p>
                        <p style="font-size: 14px; color: #999;">You can close this page</p>
                    </div>
                </body>
                </html>
                """
                self.wfile.write(html.encode())
            else:
                # Authorization failed
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b'<h1>Authorization Failed</h1>')

        else:
            # Other paths return 404
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        """Silent logging"""
        pass


def initialize_workspace_dir():
    """Initialize workspace directory"""
    WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
    print(f"📁 Workspace directory: {WORKSPACE_DIR}")


def migrate_credentials(oauth_keys_path=None):
    """
    Migrate OAuth credentials to global directory
    Reference: Gmail MCP auto-migration mechanism
    """
    # Check parameter-specified path
    if oauth_keys_path and os.path.exists(oauth_keys_path):
        source = oauth_keys_path
    # Check current directory
    elif os.path.exists('./gcp-oauth.keys.json'):
        source = './gcp-oauth.keys.json'
    # Check environment variable
    elif os.environ.get('GOOGLE_OAUTH_CREDENTIALS'):
        source = os.environ['GOOGLE_OAUTH_CREDENTIALS']
    # Check global directory
    elif CREDENTIALS_PATH.exists():
        print(f"✅ Credentials already exist: {CREDENTIALS_PATH}")
        return CREDENTIALS_PATH
    else:
        return None

    # Copy to global directory
    import shutil
    shutil.copy2(source, CREDENTIALS_PATH)
    print(f"✅ Credentials migrated: {source} → {CREDENTIALS_PATH}")

    return CREDENTIALS_PATH


def load_credentials():
    """Load OAuth client credentials"""
    if not CREDENTIALS_PATH.exists():
        print("❌ OAuth credentials file not found")
        print("\nPlease follow these steps:")
        print("1. Visit https://console.cloud.google.com/")
        print("2. Create or select project")
        print("3. Enable Google Calendar API and Gmail API")
        print("4. Create OAuth 2.0 Client ID (Desktop application)")
        print("5. Download JSON credentials file")
        print(f"6. Save file as: {CREDENTIALS_PATH}")
        print("   Or run: python scripts/unified_auth.py <credentials_file_path>")
        sys.exit(1)

    with open(CREDENTIALS_PATH, 'r') as f:
        creds_data = json.load(f)

    # Support both formats
    if 'installed' in creds_data:
        return creds_data['installed']
    elif 'web' in creds_data:
        return creds_data['web']
    else:
        return creds_data


def get_existing_token():
    """Get existing token (if valid)"""
    if not TOKEN_PATH.exists():
        return None

    try:
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

        # Check if expired
        if creds and creds.valid:
            return creds

        # Try to refresh
        if creds and creds.expired and creds.refresh_token:
            print("🔄 Token expired, refreshing...")
            creds.refresh(Request())
            save_token(creds)
            print("✅ Token refreshed")
            return creds

    except Exception as e:
        print(f"⚠️  Token invalid: {e}")

    return None


def save_token(credentials):
    """Save token to global directory"""
    with open(TOKEN_PATH, 'w') as f:
        f.write(credentials.to_json())

    # Set file permission to read-only (secure)
    os.chmod(TOKEN_PATH, 0o600)
    print(f"💾 Token saved: {TOKEN_PATH}")


def authenticate_with_browser():
    """
    Complete OAuth authentication using browser
    Reference: Gmail MCP auto-authentication implementation
    """
    creds_data = load_credentials()

    # Build redirect URI
    redirect_uri = f"http://localhost:{OAUTH_PORT}/oauth2callback"

    # Create Flow
    flow = Flow.from_client_config(
        {
            "installed": {
                "client_id": creds_data['client_id'],
                "client_secret": creds_data['client_secret'],
                "redirect_uris": [redirect_uri],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token"
            }
        },
        scopes=SCOPES,
        redirect_uri=redirect_uri
    )

    # Generate authorization URL
    auth_url, _ = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'  # Force authorization page display
    )

    print("\n" + "="*60)
    print("🔓 Starting OAuth authentication flow...")
    print("="*60)
    print(f"\n📍 Local server: http://localhost:{OAUTH_PORT}")
    print(f"🌐 Authorization page will open in browser...\n")

    # Start local HTTP server
    with socketserver.TCPServer(("", OAUTH_PORT), OAuthCallbackHandler) as httpd:
        httpd.auth_code = None

        # Auto-open browser
        webbrowser.open(auth_url)

        print("⏳ Waiting for authorization...")
        print("   (If browser does not open automatically, manually Visitthis URL:)")
        print(f"   {auth_url}\n")

        # Wait for one request (OAuth callback)
        httpd.handle_request()

        if httpd.auth_code:
            print("\n✅ Received authorization code, exchanging for token...")

            # Exchange token (ignore scope change warning)
            try:
                flow.fetch_token(code=httpd.auth_code)
            except Warning as w:
                # Google may add extra scopes, this is normal
                print(f"⚠️  Scope changed: {w}")
                # Token still valid despite warning, continue saving

            # Save token
            save_token(flow.credentials)

            print("\n" + "="*60)
            print("🎉 Authentication successful!")
            print("="*60)
            print(f"\n✅ Token saved to: {TOKEN_PATH}")
            print("✅ Google Calendar and Gmail are now available!\n")

            return flow.credentials
        else:
            print("\n❌ Authentication failed: No authorization code received")
            sys.exit(1)


def get_authenticated_credentials():
    """
    Get authenticated credentials
    Automatically handle refresh and re-authentication
    """
    # 1. Try to load existing token
    creds = get_existing_token()
    if creds:
        print("✅ Using existing token")
        return creds

    # 2. Token not found or invalid, re-authenticate
    print("🔐 Re-authentication required")
    return authenticate_with_browser()


def main():
    """Main function: Auto authentication setup"""
    print("\n" + "="*60)
    print("🚀 Google Workspace Skill - Unified Authentication Setup")
    print("="*60 + "\n")

    # 1. Initialize directory
    initialize_workspace_dir()

    # 2. Migrate credentials (if path provided)
    oauth_path = sys.argv[1] if len(sys.argv) > 1 else None
    creds_file = migrate_credentials(oauth_path)

    if not creds_file:
        print("\n❌ OAuth credentials file not found")
        print("\nPlease provide credentials file path:")
        print(f"   python {sys.argv[0]} /path/to/credentials.json\n")
        sys.exit(1)

    # 3. Execute authentication
    creds = get_authenticated_credentials()

    # 4. Verify token
    print("\n🧪 Testing connection...")
    from googleapiclient.discovery import build

    try:
        # Test Calendar
        calendar = build('calendar', 'v3', credentials=creds)
        cal_list = calendar.calendarList().list(maxResults=1).execute()
        print(f"✅ Calendar API: Success (found {len(cal_list.get('items', []))}  calendars)")

        # Test Gmail
        gmail = build('gmail', 'v1', credentials=creds)
        profile = gmail.users().getProfile(userId='me').execute()
        print(f"✅ Gmail API: Success ({profile['emailAddress']}）")

    except Exception as e:
        print(f"⚠️  API test failed: {e}")

    print("\n🎉 Setup complete!\n")
    print("✅ All files saved in: ~/.google-workspace/")
    print("   - venv/          (Python virtual environment)")
    print("   - token.json     (OAuth token)")
    print("   - credentials.json (OAuth credentials)\n")
    print("✅ Google Workspace Skill is now ready to use.\n")


if __name__ == '__main__':
    main()
