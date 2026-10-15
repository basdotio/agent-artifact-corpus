"""
Configuration module for API MCP Server
Created by D. Theoden
Date: June 12, 2025
"""

import os
from dotenv import load_dotenv

load_dotenv()

URL = os.getenv('API_URL')
USERNAME = os.getenv('API_USERNAME')
PASSWORD = os.getenv('API_PASSWORD')
DATABASE = os.getenv('ARAS_DATABASE')
TIMEOUT = int(os.getenv('API_TIMEOUT', '30'))
RETRY_COUNT = int(os.getenv('API_RETRY_COUNT', '3'))
RETRY_DELAY = int(os.getenv('API_RETRY_DELAY', '1'))
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FILE = os.getenv('LOG_FILE', 'api_client.log') 