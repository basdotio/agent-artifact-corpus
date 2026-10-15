"""
server.py – Główny serwer MCP dla Google Multi-Account.
Autor: Łukasz Zychal (https://lukaszzychal.dev/ | https://www.linkedin.com/in/lukaszzychal/)
Uruchomienie:
    python server.py

Podłączenie do Claude Desktop (claude_desktop_config.json):
    {
      "mcpServers": {
        "google-multi-account": {
          "command": "/sciezka/do/GoogleMCP/venv/bin/python",
          "args": ["/sciezka/do/GoogleMCP/server.py"]
        }
      }
    }

Dostępne narzędzia (po rejestracji):
  Systemowe:
    - list_accounts         Lista kont z zapisanymi tokenami
    - revoke_account        Wylogowanie konta (usunięcie tokenu)

  Gmail (5 narzędzi):
    - gmail_list_emails     Lista maili z filtrowaniem
    - gmail_get_email       Pełna treść wiadomości
    - gmail_send_email      Wysłanie maila
    - gmail_search_emails   Zaawansowane wyszukiwanie
    - gmail_mark_as_read    Oznaczanie jako przeczytane

  Google Drive (5 narzędzi):
    - drive_list_files      Lista plików
    - drive_search_files    Wyszukiwanie plików
    - drive_get_file_info   Szczegóły pliku
    - drive_read_text_file  Odczyt zawartości
    - drive_list_folders    Lista folderów

  Google Calendar (4 narzędzia):
    - calendar_list_events    Lista wydarzeń
    - calendar_get_event      Szczegóły wydarzenia
    - calendar_create_event   Tworzenie wydarzenia
    - calendar_list_calendars Lista kalendarzy

  YouTube (4 narzędzia):
    - youtube_channel_stats  Statystyki kanału
    - youtube_list_videos    Lista filmów
    - youtube_get_video_stats Statystyki wideo
    - youtube_search_videos  Wyszukiwanie

  Google Sheets (5 narzędzi):
    - sheets_read_range    Odczyt zakresu
    - sheets_write_range   Zapis zakresu
    - sheets_append_row    Dodanie wiersza
    - sheets_list_sheets   Lista zakładek
    - sheets_create        Tworzenie arkusza

  Google Analytics (3 narzędzia):
    - analytics_get_overview     Przegląd metryk
    - analytics_top_pages        Najpopularniejsze strony
    - analytics_traffic_sources  Źródła ruchu

  Google AdSense (3 narzędzia):
    - adsense_account_info  Info o koncie
    - adsense_earnings      Przychody za okres
    - adsense_top_sites     Ranking stron
"""

import logging
import sys
from mcp.server.fastmcp import FastMCP

from auth import list_available_accounts, revoke_account as _revoke_account
from config import MCP_SERVER_NAME, MCP_SERVER_VERSION

from tools.gmail_tools import register_gmail_tools
from tools.drive_tools import register_drive_tools
from tools.calendar_tools import register_calendar_tools
from tools.youtube_tools import register_youtube_tools
from tools.sheets_tools import register_sheets_tools
from tools.analytics_tools import register_analytics_tools
from tools.adsense_tools import register_adsense_tools

# ─────────────────────────────────────────────────────────────────────────────
# Konfiguracja logowania
# ─────────────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stderr,  # Claude Desktop czyta stdout – logi idą na stderr
)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Inicjalizacja serwera MCP
# ─────────────────────────────────────────────────────────────────────────────
mcp = FastMCP(MCP_SERVER_NAME)
logger.info(f"Inicjalizacja {MCP_SERVER_NAME} v{MCP_SERVER_VERSION}")

# ─────────────────────────────────────────────────────────────────────────────
# Narzędzia systemowe (zarządzanie kontami)
# ─────────────────────────────────────────────────────────────────────────────


@mcp.tool()
def list_accounts() -> str:
    """
    Wyświetla listę kont Google z zapisanymi tokenami dostępu.
    Użyj tej funkcji, aby sprawdzić jakie konta są dostępne do użycia.

    Returns:
        Lista nazw kont (account_id) lub instrukcja pierwszego logowania.
    """
    accounts = list_available_accounts()
    if not accounts:
        return (
            "ℹ️  Brak skonfigurowanych kont.\n\n"
            "Aby zalogować pierwsze konto, użyj dowolnego narzędzia\n"
            "(np. gmail_list_emails) podając wybrany account_id,\n"
            "np. 'praca' lub 'prywatne'.\n\n"
            "Przy pierwszym użyciu otworzy się przeglądarka z ekranem\n"
            "logowania Google – token zostanie zapisany automatycznie."
        )

    lines = [f"✅ Zalogowane konta ({len(accounts)}):\n"]
    for acc in accounts:
        lines.append(f"  👤 {acc}")
    lines.append("\nUżyj tych nazw jako parametru account_id w narzędziach.")
    return "\n".join(lines)


@mcp.tool()
def revoke_account_access(account_id: str) -> str:
    """
    Wylogowuje konto Google – usuwa zapisany token dostępu.
    Przy następnym użyciu tego konta konieczne będzie ponowne zalogowanie.

    Args:
        account_id: Nazwa konta do wylogowania (np. 'praca', 'prywatne')

    Returns:
        Potwierdzenie wylogowania lub informacja o braku tokenu.
    """
    removed = _revoke_account(account_id)
    if removed:
        return f"✅ Konto '{account_id}' zostało wylogowane. Token usunięty."
    return f"ℹ️  Konto '{account_id}' nie miało zapisanego tokenu."


# ─────────────────────────────────────────────────────────────────────────────
# Rejestracja wszystkich modułów narzędzi
# ─────────────────────────────────────────────────────────────────────────────
register_gmail_tools(mcp)
logger.info("✓ Zarejestrowano narzędzia Gmail")

register_drive_tools(mcp)
logger.info("✓ Zarejestrowano narzędzia Google Drive")

register_calendar_tools(mcp)
logger.info("✓ Zarejestrowano narzędzia Google Calendar")

register_youtube_tools(mcp)
logger.info("✓ Zarejestrowano narzędzia YouTube")

register_sheets_tools(mcp)
logger.info("✓ Zarejestrowano narzędzia Google Sheets")

register_analytics_tools(mcp)
logger.info("✓ Zarejestrowano narzędzia Google Analytics")

register_adsense_tools(mcp)
logger.info("✓ Zarejestrowano narzędzia Google AdSense")

# ─────────────────────────────────────────────────────────────────────────────
# Uruchomienie serwera
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logger.info(f"Uruchamianie {MCP_SERVER_NAME} v{MCP_SERVER_VERSION}...")
    logger.info("Serwer nasłuchuje na stdin/stdout (protokół MCP)")
    mcp.run()
