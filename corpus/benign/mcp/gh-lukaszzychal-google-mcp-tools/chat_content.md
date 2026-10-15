# Gemini Chat – Własny serwer MCP dla Google

**Źródło:** https://share.gemini.google/ziF8vyc8CSap  
**Model:** Gemini 3.1 Pro  
**Data:** 27 września 2026

---

## Pytanie 1

**Użytkownik:** czy mogę w Claude podłączyć connector Gmail lub Google Drive i zalogować się na kilka kont?

**Gemini:** Natywnie w Claude **nie ma możliwości** podłączenia kilku kont Google (Gmail, Google Drive, Calendar) jednocześnie. Wbudowany konektor Google Workspace w Claude pozwala na zalogowanie się tylko do jednego konta Google w danym momencie.

**Sposoby obejścia:**

1. **Użycie niestandardowych konektorów (Custom Connectors)** – zewnętrzne serwery MCP jak Composio lub Carly.
2. **Przełączanie kont w ustawieniach** – ręczne odłączanie/logowanie (~1 min).
3. **Miksowanie dostawców (Google + Microsoft)** – jedno konto Gmail + jedno Outlook/OneDrive.
4. **Przekazywanie wiadomości (Forwarding)** – automatyczne przekazywanie maili na konto główne.

---

## Pytanie 2

**Użytkownik:** lepiej użyć gotowego konektora (np. Composio) czy napisać własny MCP connector?

**Gemini:**

### 1. Gotowe usługi (np. Composio)
- ✅ Błyskawiczna konfiguracja (15 minut, bez kodowania)
- ❌ Prywatność – firma trzecia widzi Twoje maile i pliki
- ❌ Koszty abonamentowe po przekroczeniu limitu

### 2. Własny serwer MCP
- ✅ Maksymalna prywatność (Zero-Trust)
- ✅ Pełna kontrola nad uprawnieniami
- ✅ Brak opłat abonamentowych
- ❌ Bariera technologiczna (OAuth2, zarządzanie tokenami)

**Wniosek:** Własny konektor MCP = najlepsza inwestycja dla danych firmowych.

---

## Pytanie 3

**Użytkownik:** Jak zacząć pisać własny serwer MCP dla Google Drive i Gmaila? Jakie biblioteki będą potrzebne?

**Gemini:**

### Krok 1: Konfiguracja Google Cloud Console
1. Utwórz nowy projekt na [console.cloud.google.com](https://console.cloud.google.com/)
2. Włącz Google Drive API oraz Gmail API
3. Skonfiguruj OAuth consent screen (External + test users)
4. Utwórz OAuth client ID (typ: Desktop app)
5. Pobierz i zapisz plik jako `credentials.json`

### Krok 2: Instalacja bibliotek
```bash
pip install mcp google-api-python-client google-auth-httplib2 google-auth-oauthlib
```

### Krok 3: Logika autoryzacji wielu kont

```python
import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = [
    'https://www.googleapis.com/auth/drive.readonly',
    'https://www.googleapis.com/auth/gmail.readonly'
]

def get_google_service(account_id: str, service_name: str, version: str):
    token_path = f'token_{account_id}.json'
    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
        creds = flow.run_local_server(port=0)
        with open(token_path, 'w') as token:
            token.write(creds.to_json())
    return build(service_name, version, credentials=creds)
```

### Krok 4: Serwer MCP

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("MultiAccountGoogle")

@mcp.tool()
def list_drive_files(account_id: str, limit: int = 10) -> str:
    """Pobiera listę plików z Google Drive dla danego konta."""
    try:
        service = get_google_service(account_id, 'drive', 'v3')
        results = service.files().list(pageSize=limit, fields="files(id, name)").execute()
        files = results.get('files', [])
        if not files:
            return f"Brak plików na koncie {account_id}."
        return "\n".join([f"- {f['name']} (ID: {f['id']})" for f in files])
    except Exception as e:
        return f"Błąd: {str(e)}"

@mcp.tool()
def get_latest_emails(account_id: str, limit: int = 5) -> str:
    """Pobiera najnowsze maile z Gmaila dla wskazanego konta."""
    pass  # analogiczna logika

if __name__ == "__main__":
    mcp.run_stdio()
```

### Krok 5: Podłączenie do Claude Desktop

```json
{
  "mcpServers": {
    "google-multi-account": {
      "command": "python",
      "args": ["/pełna/ścieżka/do/projektu/server.py"]
    }
  }
}
```

---

## Pytania 4-7 (Wyjaśnienia OAuth2)

- `credentials.json` = identyfikator aplikacji (kto pyta Google)
- `token_*.json` = klucz dostępu użytkownika do konkretnego konta
- Konfiguracja Google Cloud = jednorazowa, darmowa
- Tryb "Testing" = tylko białe listy e-maili, bez audytu
- **Całkowicie darmowe** – Google oferuje milion zapytań dziennie do Gmail API

---

## Pytanie 8

**Użytkownik:** a gdybym chciał zrobić wersję opensource, komercyjną, lub remote?

**Gemini:**

| Wersja | Wymogi | Koszty |
|--------|--------|--------|
| **Lokalnie (prywatnie)** | Tylko credentials.json | 0 zł |
| **Open-Source** | README + instrukcja, nie commituj credentials.json | 0 zł |
| **Komercyjna (SaaS)** | Audyt CASA (Cloud Application Security Assessment) | $5k–$50k+ |
| **Remote (VPS/Cloud)** | Generuj token lokalnie + prześlij SSH, lub Flask OAuth flow | Koszt serwera |
| **Firmowa (Workspace Internal)** | Ustawienie "Internal" w GCC | 0 zł |

---

## Pytanie 9

**Użytkownik:** włączyłem YouTube, Sheets, Fitness, Analytics, AdSense, Calendar API

**Gemini:**

```python
SCOPES = [
    'https://www.googleapis.com/auth/drive.readonly',
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/youtube.readonly',
    'https://www.googleapis.com/auth/spreadsheets',
    # ... Fitness, Analytics, AdSense
]
```

**Ważne:** Po zmianie SCOPES skasuj stary `token_*.json` – przy kolejnym uruchomieniu przeglądarka poprosi o nowe zgody.

**Inicjalizacja różnych usług:**
```python
get_google_service(account_id, 'youtube', 'v3')
get_google_service(account_id, 'sheets', 'v4')
get_google_service(account_id, 'calendar', 'v3')
```

---

## Pytanie 10

**Użytkownik:** czy muszę dawać uprawnienia do wszystkiego?

**Gemini:** NIE. Dwa poziomy kontroli:

1. **Włączenie API w GCC** – tylko "techniczne pozwolenie". Nic nie działa automatycznie.
2. **SCOPES w kodzie** – to tu decydujesz co faktycznie żądasz. Wpisz tylko YouTube + Calendar → tylko o te dwa pyta okienko logowania.

**Google Granular Consent:** Użytkownik może odhaczyć konkretne uprawnienia w okienku, nawet jeśli aplikacja prosi o więcej.
