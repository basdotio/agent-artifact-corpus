import os
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request


def create_service(client_secret_file, api_name, api_version, *scopes, prefix=''):
    """
    Create a Google API service instance.

    Args:
        client_secret_file: Path to the client secret JSON file
        api_name: Name of the API service
        api_version: Version of the API
        scopes: Authorization scopes required by the API
        prefix: Optional prefix for token filename

    Returns:
        Google API service instance or None if creation failed
    """
    CLIENT_SECRET_FILE = client_secret_file
    API_SERVICE_NAME = api_name
    API_VERSION = api_version
    SCOPES = [scope for scope in scopes[0]]

    creds = None

    working_dir = os.path.dirname(os.path.abspath(client_secret_file))
    
    token_dir = 'token files'
    token_file = f'token_{API_SERVICE_NAME}_{API_VERSION}{prefix}.json'

    if not os.path.exists(os.path.join(working_dir, token_dir)):
        os.mkdir(os.path.join(working_dir, token_dir))

    if os.path.exists(os.path.join(working_dir, token_dir, token_file)):
        creds = Credentials.from_authorized_user_file(
            os.path.join(working_dir, token_dir, token_file),
            SCOPES
        )

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CLIENT_SECRET_FILE,
                SCOPES
            )
            creds = flow.run_local_server(port=0)

        with open(
            os.path.join(working_dir, token_dir, token_file),
            'w'
        ) as token:
            token.write(creds.to_json())

    try:
        service = build(
            API_SERVICE_NAME,
            API_VERSION,
            credentials=creds,
            static_discovery=False
        )
        return service

    except Exception as e:
        os.remove(os.path.join(working_dir, token_dir, token_file))
        return None