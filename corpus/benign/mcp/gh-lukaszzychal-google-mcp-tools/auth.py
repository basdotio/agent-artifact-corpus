"""
auth.py – Moduł autoryzacji OAuth2 dla wielu kont Google.

Każde konto identyfikowane jest przez account_id (np. 'praca', 'prywatne').
Token dla każdego konta jest przechowywany w osobnym pliku:
    credentials/token_{account_id}.json

Pierwsze logowanie dla nowego konta otwiera przeglądarkę z ekranem Google.
Kolejne uruchomienia używają zapisanego tokenu (automatyczne odświeżanie).
"""

from pathlib import Path
from typing import Optional
import logging

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from config import SCOPES, CREDENTIALS_FILE, CREDENTIALS_DIR

logger = logging.getLogger(__name__)


def _token_path(account_id: str) -> Path:
    """Zwraca ścieżkę do pliku tokenu dla danego konta."""
    return CREDENTIALS_DIR / f"token_{account_id}.json"


def get_google_service(account_id: str, service_name: str, version: str):
    """
    Zwraca autoryzowany klient Google API dla danego konta.

    Przy pierwszym wywołaniu dla nowego account_id:
      - otwiera przeglądarkę z ekranem logowania Google
      - zapisuje token do credentials/token_{account_id}.json

    Przy kolejnych wywołaniach:
      - wczytuje token z pliku
      - odświeża go automatycznie jeśli wygasł

    Args:
        account_id:   Identyfikator konta (np. 'praca', 'prywatne')
        service_name: Nazwa serwisu Google (np. 'gmail', 'drive', 'calendar')
        version:      Wersja API (np. 'v1', 'v3', 'v4')

    Returns:
        Autoryzowany obiekt serwisu Google API

    Raises:
        FileNotFoundError: Jeśli brak pliku credentials.json
        Exception:         Przy błędzie autoryzacji lub API
    """
    if not CREDENTIALS_FILE.exists():
        raise FileNotFoundError(
            f"Brak pliku credentials.json w: {CREDENTIALS_FILE}\n"
            "Pobierz go z Google Cloud Console → APIs & Services → Credentials."
        )

    token_file = _token_path(account_id)
    creds: Optional[Credentials] = None

    # 1. Załaduj istniejący token
    if token_file.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)
            logger.debug(f"Token wczytany dla konta '{account_id}'")
        except Exception as e:
            logger.warning(f"Błąd wczytywania tokenu dla '{account_id}': {e}")
            creds = None

    # 2. Odśwież lub zaloguj się od nowa
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                logger.info(f"Token odświeżony dla konta '{account_id}'")
            except Exception as e:
                logger.warning(f"Odświeżanie tokenu nieudane dla '{account_id}': {e}")
                creds = None

        if not creds or not creds.valid:
            logger.info(
                f"Otwieram przeglądarkę – logowanie dla konta '{account_id}'..."
            )
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_FILE), SCOPES
            )
            creds = flow.run_local_server(port=0)
            logger.info(f"Logowanie udane dla konta '{account_id}'")

        # 3. Zapisz (lub zaktualizuj) token
        token_file.parent.mkdir(parents=True, exist_ok=True)
        with open(token_file, "w") as f:
            f.write(creds.to_json())
        logger.debug(f"Token zapisany: {token_file}")

    return build(service_name, version, credentials=creds)


def list_available_accounts() -> list[str]:
    """
    Zwraca posortowaną listę account_id z zapisanymi tokenami.

    Returns:
        Lista stringów, np. ['praca', 'prywatne']
    """
    if not CREDENTIALS_DIR.exists():
        return []
    return sorted(
        f.stem.replace("token_", "") for f in CREDENTIALS_DIR.glob("token_*.json")
    )


def revoke_account(account_id: str) -> bool:
    """
    Usuwa token dla danego konta (wylogowanie).

    Args:
        account_id: Identyfikator konta do wylogowania

    Returns:
        True jeśli token istniał i został usunięty, False jeśli nie istniał
    """
    token_file = _token_path(account_id)
    if token_file.exists():
        token_file.unlink()
        logger.info(f"Token usunięty dla konta '{account_id}'")
        return True
    return False


if __name__ == "__main__":
    import sys

    args = sys.argv[1:]
    cmd = args[0] if args else "list"

    if cmd == "list":
        accounts = list_available_accounts()
        if not accounts:
            print("ℹ️  Brak zalogowanych kont Google w katalogu credentials/.")
            print("   Aby dodać konto, uruchom: python auth.py add <nazwa_konta>")
        else:
            print(f"✅ Zalogowane konta ({len(accounts)}):")
            for acc in accounts:
                print(f"  👤 {acc}")
    elif cmd == "add" and len(args) > 1:
        acc_id = args[1]
        print(f"🚀 Rozpoczynam logowanie dla konta '{acc_id}'...")
        print("   W przeglądarce otworzy się okno autoryzacji Google...")
        try:
            get_google_service(acc_id, "gmail", "v1")
            print(f"✅ Konto '{acc_id}' zostało pomyślnie zalogowane i zapisane!")
        except Exception as e:
            print(f"❌ Błąd logowania konta '{acc_id}': {e}")
    elif cmd == "revoke" and len(args) > 1:
        acc_id = args[1]
        if revoke_account(acc_id):
            print(f"✅ Konto '{acc_id}' zostało wylogowane (usunięto token).")
        else:
            print(f"ℹ️  Konto '{acc_id}' nie było zalogowane.")
    else:
        print("Użycie:")
        print("  python auth.py list              - lista kont")
        print("  python auth.py add <nazwa_konta>  - dodanie/zalogowanie konta")
        print("  python auth.py revoke <nazwa_konta> - wylogowanie konta")
