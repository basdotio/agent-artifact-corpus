import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(".env")
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

CUSTOMER_ID = os.environ.get("GOOGLE_ADS_CUSTOMER_ID", "")
LOGIN_CUSTOMER_ID = os.environ.get("GOOGLE_ADS_LOGIN_CUSTOMER_ID", "")
