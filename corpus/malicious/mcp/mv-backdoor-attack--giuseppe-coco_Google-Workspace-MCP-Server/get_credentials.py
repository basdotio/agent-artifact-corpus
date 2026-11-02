import os
import google.oauth2.credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from config import TOKEN_PATH, SCOPES, CLIENT_SECRETS_PATH

def main():
    creds = None
    if os.path.exists(TOKEN_PATH):
        print(f"Token file '{TOKEN_PATH}' already exists. Loading credentials.")
        creds = google.oauth2.credentials.Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Credentials have expired. Refreshing...")
            creds.refresh(Request())
        else:
            print("No valid credentials found. Starting authorization flow...")
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_PATH, SCOPES)
            creds = flow.run_local_server(port=0, prompt='consent')
        
        with open(TOKEN_PATH, 'w') as token_file:
            token_file.write(creds.to_json())
        print(f"Credentials successfully saved to '{TOKEN_PATH}'")
    else:
        print("Credentials are valid and ready to use.")

if __name__ == '__main__':
    main()