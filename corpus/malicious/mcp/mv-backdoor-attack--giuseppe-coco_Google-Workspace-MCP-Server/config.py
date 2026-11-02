import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TOKEN_PATH = os.path.join(SCRIPT_DIR, "token.json")
CLIENT_SECRETS_PATH = os.path.join(SCRIPT_DIR, "desktop_client_secrets.json")

# --- IMPORTANT --- After updating this, you MUST delete your old token.json and re-run get_credentials.py
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/calendar.events',
    'https://www.googleapis.com/auth/drive',
]