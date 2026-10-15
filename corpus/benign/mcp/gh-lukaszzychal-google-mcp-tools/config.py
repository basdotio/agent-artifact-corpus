"""
config.py – Centralna konfiguracja serwera Google MCP.

Aby dodać/usunąć uprawnienia:
1. Odkomentuj lub zakomentuj odpowiedni scope
2. Skasuj pliki token_*.json z katalogu credentials/
3. Przy kolejnym użyciu przeglądarka poprosi o nowe uprawnienia
"""

import os
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────────
# Ścieżki plików
# ─────────────────────────────────────────────────────────────────────────────

BASE_DIR = Path(__file__).parent
CREDENTIALS_DIR = BASE_DIR / "credentials"
CREDENTIALS_FILE = CREDENTIALS_DIR / "credentials.json"

# ─────────────────────────────────────────────────────────────────────────────
# Uprawnienia OAuth2 (SCOPES)
#
# UWAGA: Po każdej zmianie tej listy skasuj token_*.json
#        i zaloguj się ponownie!
# ─────────────────────────────────────────────────────────────────────────────

SCOPES = [
    # ── Gmail ────────────────────────────────────────────────────────────────
    "https://www.googleapis.com/auth/gmail.readonly",  # Odczyt maili
    "https://www.googleapis.com/auth/gmail.send",  # Wysyłanie maili
    "https://www.googleapis.com/auth/gmail.modify",  # Oznaczanie, archiwizacja
    # ── Google Drive ─────────────────────────────────────────────────────────
    "https://www.googleapis.com/auth/drive",  # Pełny dostęp (odczyt, tworzenie, edycja, usuwanie)
    # ── Google Calendar ──────────────────────────────────────────────────────
    "https://www.googleapis.com/auth/calendar",  # Pełny dostęp (odczyt, tworzenie, edycja, usuwanie)
    # ── YouTube ──────────────────────────────────────────────────────────────
    "https://www.googleapis.com/auth/youtube.readonly",  # Dane kanału i filmów
    "https://www.googleapis.com/auth/yt-analytics.readonly",  # Analytics YouTube
    # ── Google Sheets ────────────────────────────────────────────────────────
    "https://www.googleapis.com/auth/spreadsheets",  # Odczyt + zapis arkuszy
    # ── Google Analytics ─────────────────────────────────────────────────────
    "https://www.googleapis.com/auth/analytics.readonly",  # Statystyki stron
    # ── Google AdSense ───────────────────────────────────────────────────────
    "https://www.googleapis.com/auth/adsense.readonly",  # Przychody reklam
    # ── Google Fitness ───────────────────────────────────────────────────────
    "https://www.googleapis.com/auth/fitness.activity.read",  # Aktywność fizyczna
    "https://www.googleapis.com/auth/fitness.sleep.read",  # Dane snu
]

# ─────────────────────────────────────────────────────────────────────────────
# Ustawienia serwera MCP
# ─────────────────────────────────────────────────────────────────────────────

MCP_SERVER_NAME = "Google-Multi-Account-MCP"
MCP_SERVER_VERSION = "1.0.0"

# ─────────────────────────────────────────────────────────────────────────────
# Mapowanie alias -> nazwa serwisu Google (do użycia w get_google_service)
# ─────────────────────────────────────────────────────────────────────────────

SERVICE_MAP = {
    "gmail": ("gmail", "v1"),
    "drive": ("drive", "v3"),
    "calendar": ("calendar", "v3"),
    "youtube": ("youtube", "v3"),
    "sheets": ("sheets", "v4"),
    "analytics": ("analyticsdata", "v1beta"),
    "adsense": ("adsense", "v2"),
    "fitness": ("fitness", "v1"),
}
