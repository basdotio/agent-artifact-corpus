"""
Configuration module for ElectreeFi CMS RCA MCP Server.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env if present
load_dotenv()

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Portal URLs
BASE_URL = os.getenv("ELECTREEFI_BASE_URL", "https://cms.ev-charge-network.com").rstrip("/")
LOGIN_URL = os.getenv("ELECTREEFI_LOGIN_URL", f"{BASE_URL}/Account/Login")
BOOKINGS_URL = f"{BASE_URL}/ChargingStationManagement/AdminBookingDetails"
OCPP_DASHBOARD_URL = f"{BASE_URL}/OCPPManagement/OCPP/LoadOCPPDashboard"
ALL_CHARGERS_URL = f"{BASE_URL}/OCPPManagement/OCPP/LoadAllChargerDashboard"

# Session storage
SESSION_STORAGE_PATH = Path(os.getenv("SESSION_STORAGE_PATH", str(DATA_DIR / "session_state.json")))
if not SESSION_STORAGE_PATH.is_absolute():
    SESSION_STORAGE_PATH = BASE_DIR / SESSION_STORAGE_PATH

# Browser settings
BROWSER_HEADLESS = os.getenv("BROWSER_HEADLESS", "true").lower() in ("true", "1", "yes")
BROWSER_TIMEOUT_MS = int(os.getenv("BROWSER_TIMEOUT_MS", "30000"))

# RCA parameters
RCA_LOG_TIME_WINDOW_MINUTES = int(os.getenv("RCA_LOG_TIME_WINDOW_MINUTES", "10"))
RCA_LOW_CONSUMPTION_THRESHOLD_KW = float(os.getenv("RCA_LOW_CONSUMPTION_THRESHOLD_KW", "1.0"))

# Optional credentials
ELECTREEFI_USERNAME = os.getenv("ELECTREEFI_USERNAME", "")
ELECTREEFI_PASSWORD = os.getenv("ELECTREEFI_PASSWORD", "")
