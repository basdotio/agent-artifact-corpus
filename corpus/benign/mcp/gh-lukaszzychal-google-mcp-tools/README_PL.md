# 🔗 Google Multi-Account MCP Server

**Autor:** [Łukasz Zychal](https://lukaszzychal.dev/) | [LinkedIn](https://www.linkedin.com/in/lukaszzychal/?isSelfProfile=true)
Własny serwer **MCP (Model Context Protocol)** w Pythonie dający Claude i Gemini dostęp do wielu kont Google jednocześnie — bez zewnętrznych pośredników, w 100% prywatnie.

**Obsługiwane usługi:** Gmail · Google Drive · Calendar · YouTube · Sheets · Analytics · AdSense · Fitness

### 🛠️ Pełne wsparcie CRUD (Tworzenie, Podgląd, Edycja, Usuwanie):
| Usługa | 👁️ Podgląd (Read) | ➕ Tworzenie (Create) | ✏️ Edycja (Update) | 🗑️ Usuwanie (Delete) |
|---|---|---|---|---|
| **Kalendarz** | `calendar_list_events`, `calendar_get_event`, `calendar_list_calendars` | `calendar_create_event` (+ Google Meet) | `calendar_update_event` (czas, tytuł, opis) | `calendar_delete_event` |
| **Dysk Google** | `drive_list_files`, `drive_search_files`, `drive_get_file_info`, `drive_read_text_file`, `drive_list_folders` | `drive_create_folder`, `drive_upload_text_file` | `drive_rename_file` | `drive_trash_file`, `drive_delete_file` |
| **Gmail** | `gmail_list_emails`, `gmail_get_email`, `gmail_search_emails` | `gmail_send_email`, `gmail_create_draft` | `gmail_mark_as_read` | `gmail_trash_email`, `gmail_untrash_email` |
| **Google Sheets** | `sheets_read_range`, `sheets_list_sheets` | `sheets_create`, `sheets_add_sheet` | `sheets_write_range`, `sheets_append_row` | `sheets_clear_range`, `sheets_delete_sheet` |
| **Konta Google** | `list_accounts` | `python auth.py add <id>` | — | `revoke_account_access` |

---

## 📋 Spis treści

1. [Wymagania wstępne](#1-wymagania-wstępne)
2. [Konfiguracja Google Cloud Console](#2-konfiguracja-google-cloud-console)
3. [Instalacja projektu](#3-instalacja-projektu)
4. [Integracja z Claude Desktop](#4-integracja-z-claude-desktop)
5. [Integracja z Gemini (Google AI Studio)](#5-integracja-z-gemini-google-ai-studio)
6. [Pierwsze logowanie — OAuth2](#6-pierwsze-logowanie--oauth2)
7. [Przykładowe zapytania](#7-przykładowe-zapytania)
8. [Zarządzanie kontami](#8-zarządzanie-kontami)
9. [Rozszerzenie o nowe API](#9-rozszerzenie-o-nowe-api)
10. [Wersja Open-Source](#10-wersja-open-source)
11. [Rozwiązywanie problemów](#11-rozwiązywanie-problemów)

---

## 1. Wymagania wstępne

| Wymaganie | Wersja minimalna | Sprawdzenie |
|-----------|-----------------|-------------|
| Python | 3.10+ | `python --version` |
| pip | 23+ | `pip --version` |
| Claude Desktop | najnowsza | [pobierz](https://claude.ai/download) |
| Konto Google | dowolne | — |

---

## 2. Konfiguracja Google Cloud Console

> ⏱ Czas: **ok. 15 minut** | Wykonujesz to **jednorazowo**.

### Krok 2.1 — Utwórz projekt

1. Wejdź na **[console.cloud.google.com](https://console.cloud.google.com/)**
2. Kliknij selektor projektów (górny pasek) → **"NOWY PROJEKT"**
3. Nazwa projektu: `google-mcp-server` (dowolna)
4. Kliknij **"UTWÓRZ"** i poczekaj na inicjalizację (~10 sekund)
5. Upewnij się, że nowy projekt jest wybrany w selektorze

---

### Krok 2.2 — Włącz potrzebne API

1. W menu bocznym wejdź w **"APIs & Services"** → **"Library"**
2. Wyszukaj i włącz **każde** z poniższych API (kliknij → "ENABLE"):

| API do włączenia | Gdzie szukać |
|-----------------|--------------|
| **Gmail API** | wyszukaj: `gmail` |
| **Google Drive API** | wyszukaj: `drive` |
| **Google Calendar API** | wyszukaj: `calendar` |
| **YouTube Data API v3** | wyszukaj: `youtube data` |
| **YouTube Analytics API** | wyszukaj: `youtube analytics` |
| **YouTube Reporting API** | wyszukaj: `youtube reporting` |
| **Google Sheets API** | wyszukaj: `sheets` |
| **Google Analytics Data API** | wyszukaj: `analytics data` |
| **AdSense Management API** | wyszukaj: `adsense` |
| **Fitness API** | wyszukaj: `fitness` |

> 💡 **Wskazówka:** Możesz włączyć tylko te API, których faktycznie będziesz używać. Reszta będzie nieaktywna nawet jeśli jest w SCOPES.

---

### Krok 2.3 — Konfiguracja ekranu zgody OAuth

1. W menu bocznym: **"APIs & Services"** → **"OAuth consent screen"**
2. Wybierz typ użytkownika: **"External"** → kliknij **"CREATE"**

**Wypełnij formularz:**

| Pole | Wartość |
|------|---------|
| App name | `Google MCP Server` (dowolna) |
| User support email | Twój adres e-mail |
| App logo | (opcjonalnie, pomiń) |
| App domain | (puste — pomiń całą sekcję) |
| Developer contact | Twój adres e-mail |

3. Kliknij **"SAVE AND CONTINUE"**

**Zakładka "Scopes":**

4. Kliknij **"ADD OR REMOVE SCOPES"**
5. W polu wyszukiwania wpisz kolejno i zaznacz:
   - `gmail.readonly`, `gmail.send`, `gmail.modify`
   - `drive.readonly`
   - `calendar.readonly`, `calendar`
   - `youtube.readonly`, `yt-analytics.readonly`
   - `spreadsheets`
   - `analytics.readonly`
   - `adsense.readonly`
   - `fitness.activity.read`
6. Kliknij **"UPDATE"** → **"SAVE AND CONTINUE"**

> ⚠️ Nie musisz zaznaczać wszystkich. Wybierz tylko te, których planujesz używać.

**Zakładka "Test users":**

7. Kliknij **"ADD USERS"**
8. Wpisz **swoje adresy e-mail** — **każde konto Google**, które chcesz używać, np.:
   ```
   jan.kowalski@gmail.com
   jan.kowalski@firma.pl
   ```
9. Kliknij **"ADD"** → **"SAVE AND CONTINUE"**

> 🔐 **Dlaczego?** Twoja aplikacja jest w trybie "Testing". Google wpuszcza przez nią tylko adresy z tej listy. Nie jest to konieczne po przejściu do trybu "In production" (wymagane dla wersji komercyjnej).

---

### Krok 2.4 — Utwórz dane uwierzytelniające (credentials.json)

1. W menu bocznym: **"APIs & Services"** → **"Credentials"**
2. Kliknij **"+ CREATE CREDENTIALS"** → **"OAuth client ID"**
3. Typ aplikacji: **"Desktop app"**
4. Nazwa: `MCP Local Client`
5. Kliknij **"CREATE"**
6. W oknie popup kliknij **"DOWNLOAD JSON"**
7. Zapisz pobrany plik jako:
   ```
   GoogleMCP/credentials/credentials.json
   ```

> 🚨 **NIGDY nie wgrywaj tego pliku na GitHub ani nie udostępniaj!** Zawiera Twój prywatny klucz aplikacji.

---

## 3. Instalacja projektu

```bash
# 1. Sklonuj lub pobierz projekt
cd /ścieżka/do/GoogleMCP

# 2. Utwórz wirtualne środowisko
python -m venv venv

# 3. Aktywuj środowisko
source venv/bin/activate          # macOS / Linux
# lub: venv\Scripts\activate      # Windows

# 4. Zainstaluj zależności
pip install -r requirements.txt

# 5. Sprawdź, czy wszystko działa
python -c "import mcp; import googleapiclient; print('OK')"
```

Upewnij się, że plik credentials jest na miejscu:
```
credentials/credentials.json   ← pobrany w kroku 2.4
```

### Opcja z użyciem Dockera 🐳
Jeśli nie chcesz konfigurować środowiska Python lokalnie, możesz zbudować obraz Dockera i uruchomić serwer w kontenerze. Zamontuj katalog `credentials` jako wolumen, aby zachować tokeny pomiędzy restartami.

```bash
# Zbuduj obraz (będąc w katalogu z projektem)
docker build -t google-mcp-server .

# Przetestuj działanie (powinien czekać na dane ze stdio)
docker run -i -v $(pwd)/credentials:/app/credentials google-mcp-server
```

---

## 4. Integracja z Claude

> **Dlaczego Claude w przeglądarce (claude.ai) nie ma dostępu do MCP?**  
> Claude uruchomiony w przeglądarce działa **w chmurze** — nie ma wglądu do Twojego komputera. Ten serwer MCP działa **lokalnie**. Żeby Claude miał do niego dostęp, musisz użyć lokalnego klienta: **Claude Desktop** (aplikacja) lub **Claude Code CLI** (terminal).

---

### Opcja A — Claude Code CLI (terminal, analogicznie do Antigravity IDE)

Claude Code CLI działa tak samo jak Antigravity IDE — uruchamia serwer MCP jako lokalny proces potomny.

#### Instalacja
```bash
npm install -g @anthropic-ai/claude-code
```

#### Rejestracja serwera MCP
```bash
claude mcp add --scope user google-multi-account -- \
  /Users/TWOJA_NAZWA/mcp-servers/google-mcp-tools/venv/bin/python \
  /Users/TWOJA_NAZWA/mcp-servers/google-mcp-tools/server.py
```

#### Uruchomienie
```bash
claude
```
Następnie w czacie zapytaj np. `"Wylistuj dostępne konta Google"` — narzędzia będą w pełni dostępne.

---

### Opcja B — Claude Desktop (aplikacja)

#### Krok 4.1 — Znajdź plik konfiguracyjny

| System | Ścieżka |
|--------|---------|
| **macOS** | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| **Windows** | `%APPDATA%\Claude\claude_desktop_config.json` |
| **Linux** | `~/.config/claude/claude_desktop_config.json` |

```bash
# macOS — otwórz folder w Finderze
open ~/Library/Application\ Support/Claude/
```

#### Krok 4.2 — Dodaj konfigurację serwera

Otwórz plik `claude_desktop_config.json` i dodaj (lub uzupełnij istniejący):

```json
{
  "mcpServers": {
    "google-multi-account": {
      "command": "/Users/TWOJA_NAZWA/mcp-servers/google-mcp-tools/venv/bin/python",
      "args": [
        "/Users/TWOJA_NAZWA/mcp-servers/google-mcp-tools/server.py"
      ]
    }
  }
}
```

> ⚠️ **Ważne:** Użyj **pełnej ścieżki** do Pythona z wirtualnego środowiska (`venv/bin/python`), nie systemowego `python`.

Szybkie sprawdzenie ścieżki:
```bash
cd /Users/TWOJA_NAZWA/mcp-servers/google-mcp-tools
source venv/bin/activate
which python
# Skopiuj ten output do pola "command" w JSON powyżej
```

#### Krok 4.3 — Weryfikacja

1. **Zrestartuj Claude Desktop całkowicie** (nie tylko zamknij okno — użyj Quit z paska menu)
2. Otwórz **nowy** czat
3. Szukaj ikony 🔨 (młotek/tools) w interfejsie
4. Kliknij → powinna pojawić się lista narzędzi z `google-multi-account`
5. Przetestuj: napisz do Claude:
   > `"Jakie mam podłączone konta Google?"`  
   Powinieneś dostać listę: `praca_dev`, `prywatne`, `prywatne2`, `publiczne`

---

## 5. Integracja z Gemini i Antigravity IDE

---

### Ścieżka 0 — Antigravity IDE (Gemini w IDE) — ✅ SKONFIGUROWANE

W **Antigravity IDE** serwery MCP konfiguruje się w pliku:
`~/.gemini/config/mcp_config.json`

Serwer został już dodany do Twojej konfiguracji:
```json
"google-multi-account": {
  "command": "/Users/lukaszzychal/PhpstormProjects/GoogleMCP/venv/bin/python",
  "args": [
    "/Users/lukaszzychal/PhpstormProjects/GoogleMCP/server.py"
  ],
  "env": {}
}
```

> **UWAGA — Czy potrzebujesz klucza Gemini API w Antigravity IDE?**
> **NIE.** W Antigravity IDE agent korzysta z wbudowanej subskrypcji / sesji środowiska IDE. Serwer MCP działa lokalnie jako proces potomny przez stdio.
> 
> **Po co w takim razie jest klucz `GEMINI_API_KEY`?**
> Klucz Gemini API (`GEMINI_API_KEY`) z [Google AI Studio](https://aistudio.google.com/apikey) jest potrzebny **wyłącznie** wtedy, gdy uruchamiasz zewnętrzne skrypty programistyczne w Pythonie (np. `gemini_client.py`) poza środowiskiem Antigravity, które bezpośrednio łączą się z API Gemini przez SDK `google-genai`.

---

### Ścieżka A — Gemini CLI (lokalna, przez terminal)

Google udostępnia narzędzie `gemini` CLI, które obsługuje protokół MCP.

#### Instalacja Gemini CLI

```bash
# Wymagany Node.js 18+
npm install -g @google/gemini-cli

# Zaloguj się
gemini auth login
```

#### Konfiguracja MCP w Gemini CLI

Utwórz lub edytuj plik konfiguracyjny:

```bash
# macOS / Linux
nano ~/.gemini/settings.json

# Windows
notepad %USERPROFILE%\.gemini\settings.json
```

Dodaj konfigurację serwera MCP:

```json
{
  "mcpServers": {
    "google-multi-account": {
      "command": "/Users/TWOJA_NAZWA/PhpstormProjects/GoogleMCP/venv/bin/python",
      "args": [
        "/Users/TWOJA_NAZWA/PhpstormProjects/GoogleMCP/server.py"
      ]
    }
  }
}
```

#### Uruchomienie

```bash
# Interaktywny tryb czatu z dostępem do narzędzi
gemini chat

# Lub jednorazowe zapytanie
gemini -p "Pokaż moje nieprzeczytane maile na koncie praca"
```

---

### Ścieżka B — Gemini API + Python SDK (programistyczna)

Możesz wywołać serwer MCP bezpośrednio ze swojego kodu Python.

#### Instalacja

```bash
pip install google-genai
```

#### Kod integracji

Utwórz plik `gemini_client.py`:

```python
"""
gemini_client.py
Klient Gemini łączący się z lokalnym serwerem MCP.
"""

import asyncio
import os
from google import genai
from google.genai import types

# Klucz API z https://aistudio.google.com/apikey
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "twój-klucz-api")

# Ścieżka do Pythona z venv i do server.py
PYTHON_PATH = "/Users/TWOJA_NAZWA/PhpstormProjects/GoogleMCP/venv/bin/python"
SERVER_PATH = "/Users/TWOJA_NAZWA/PhpstormProjects/GoogleMCP/server.py"


async def chat_with_google_tools():
    """Czat z Gemini z dostępem do narzędzi Google przez MCP."""

    client = genai.Client(api_key=GEMINI_API_KEY)

    # Konfiguracja serwera MCP
    mcp_config = types.MCPServerConfig(
        command=PYTHON_PATH,
        args=[SERVER_PATH],
    )

    # Sesja czatu z narzędziami MCP
    async with client.aio.chats.create(
        model="gemini-2.5-pro",
        config=types.GenerateContentConfig(
            tools=[types.Tool(mcp_servers=[mcp_config])],
            temperature=0.7,
        ),
    ) as chat:
        print("Gemini + Google MCP gotowy! Wpisz 'quit' aby wyjść.\n")

        while True:
            user_input = input("Ty: ").strip()
            if user_input.lower() in ("quit", "exit", "q"):
                break
            if not user_input:
                continue

            response = await chat.send_message(user_input)
            print(f"\nGemini: {response.text}\n")


if __name__ == "__main__":
    asyncio.run(chat_with_google_tools())
```

#### Uruchomienie

```bash
# Ustaw klucz API
export GEMINI_API_KEY="twój-klucz-z-ai-studio"

# Uruchom klienta
source venv/bin/activate
python gemini_client.py
```

---

### Ścieżka C — Google AI Studio (przeglądarkowy, wkrótce)

> ⏳ Google AI Studio aktualnie dodaje wsparcie MCP do interfejsu webowego. Gdy funkcja będzie dostępna:
>
> 1. Wejdź na **[aistudio.google.com](https://aistudio.google.com)**
> 2. Otwórz **Settings** → **MCP Servers**
> 3. Dodaj serwer:
>    - **Type:** `stdio`
>    - **Command:** `/ścieżka/do/venv/bin/python /ścieżka/do/server.py`
> 4. Zapisz i odśwież — narzędzia pojawią się w interfejsie

---

### Uzyskanie klucza API Gemini

1. Wejdź na **[aistudio.google.com/apikey](https://aistudio.google.com/apikey)**
2. Kliknij **"Create API Key"**
3. Wybierz projekt Google Cloud (ten sam co `credentials.json`!)
4. Skopiuj klucz

```bash
# Dodaj do środowiska (lub do .env)
echo 'export GEMINI_API_KEY="AIza..."' >> ~/.zshrc
source ~/.zshrc
```

---

## 6. Pierwsze logowanie — OAuth2

Przy **pierwszym użyciu** każdego nowego konta (`account_id`) serwer automatycznie otwiera przeglądarkę.

### Co się dzieje krok po kroku:

```
Claude/Gemini → wywołuje gmail_list_emails(account_id='praca')
     ↓
server.py → szuka pliku credentials/token_praca.json
     ↓
Plik nie istnieje → otwiera przeglądarkę z ekranem logowania Google
     ↓
Logujesz się na swoje konto (np. jan@gmail.com)
     ↓
Google pyta: "Czy pozwolić Google MCP Server na dostęp do...?"
     ↓
Klikasz "Zezwól"
     ↓
Token zapisany w: credentials/token_praca.json
     ↓
Kolejne użycia → automatycznie, bez przeglądarki (token odświeżany co godzinę)
```

### Czym jest `account_id` (np. `"praca"`, `"prywatne"`)?

`account_id` to **Twój własny, krótki alias (etykieta)**, który nadajesz danemu kontu Google:
- **Nie musisz podawać pełnego adresu e-mail** w promptach. Zamiast pisać *"Sprawdź pocztę na lukasz.kowalski.firma@gmail.com"*, mówisz modelowi: *"Sprawdź pocztę na koncie **praca**"*.
- Każdy alias tworzy osobny plik tokena w katalogu `credentials/token_<alias>.json` (np. `token_praca.json`, `token_prywatne.json`).
- Możesz użyć dowolnej nazwy: `praca`, `prywatne`, `firma`, `marketing`, `youtube-kanal` itp.

---

### Dwa sposoby logowania / dodawania kont:

#### Sposób A — Przez terminal (CLI – zalecany na start):
Możesz zalogować konto z góry przed uruchomieniem czatu:
```bash
# Aktywuj venv i dodaj konto o wybranym aliasie:
source venv/bin/activate
python auth.py add praca
```
> W przeglądarce otworzy się okno logowania Google. Po zalogowaniu i kliknięciu "Zezwól", token zapisze się w `credentials/token_praca.json`.

#### Sposób B — Automatycznie przez zapytanie w czacie (Claude / Gemini):
Wystarczy użyć nazwy konta w zapytaniu:
```
"Sprawdź maile na koncie 'praca'"
```
Serwer wykryje brak tokenu, otworzy okno w przeglądarce i automatycznie zapisze token po zalogowaniu.

---

## 7. Przykładowe zapytania

### Gmail

```
"Pokaż moje 10 ostatnich nieprzeczytanych maili na koncie 'praca'"
"Czy mam jakieś maile od szef@firma.pl na koncie 'praca'?"
"Wyślij maila do jan@example.com z konta 'praca' z tematem 'Oferta'"
"Utwórz wersję roboczą (szkic) maila do klienta z podsumowaniem oferty"
"Przenieś mail o ID '18f2...' do kosza"
"Przeszukaj maile z załącznikami na koncie 'prywatne'"
```

### Google Drive

```
"Pokaż pliki z Drive na koncie 'praca' zmodyfikowane ostatnio"
"Znajdź pliki PDF na moim dysku 'prywatne'"
"Odczytaj zawartość dokumentu o ID '1abc...xyz' z konta 'praca'"
"Utwórz folder 'Raporty 2026' na dysku 'praca'"
"Zapisz plik tekstowy 'notatka.md' z treścią spotkania na dysku"
"Zmień nazwę pliku o ID '1abc...' na 'Stary raport'"
"Przenieś plik o ID '1abc...' do kosza na Google Drive"
```

### Google Calendar

```
"Co mam zaplanowane w ciągu najbliższych 7 dni? Konto: 'praca'"
"Utwórz spotkanie 'Stand-up' jutro o 9:00 na koncie 'praca' z linkiem do Google Meet"
"Zmień godzinę spotkania o ID 'abc123' na jutro 11:30"
"Usuń spotkanie o ID 'abc123' i powiadom uczestników"
"Dodaj wydarzenie 'Urodziny Ani' na 15 października"
```

### YouTube

```
"Podaj statystyki mojego kanału YouTube (konto: 'praca')"
"Pokaż moje 5 najpopularniejszych filmów"
"Wyszukaj filmy na temat 'Python MCP tutorial'"
"Jakie są statystyki wideo o ID 'dQw4w9WgXcQ'?"
```

### Google Sheets

```
"Odczytaj dane z zakresu 'Arkusz1!A1:D20' w pliku '1xyz...'"
"Dodaj wiersz ['Jan', 'Kowalski', '500', '2026-09-27'] do arkusza"
"Utwórz nowy arkusz o nazwie 'Raport Miesięczny'"
"Dodaj nową zakładkę 'Październik' do pliku '1xyz...'"
"Wyczyść dane z komórek 'Arkusz1!B2:D10'"
"Jakie zakładki ma plik o ID '1abc...xyz'?"
```

### Google Analytics

```
"Pokaż statystyki mojej strony z ostatnich 30 dni (property: '123456789')"
"Które strony mają najwięcej wejść?"
"Skąd pochodzi ruch na mojej stronie?"
```

### Wielokontowe

```
"Sprawdź maile na koncie 'praca', a potem przeszukaj Drive na koncie 'prywatne'"
"Porównaj statystyki YouTube dla konta 'praca' i 'firma'"
"Zapisz dane z maila na koncie 'praca' do arkusza na koncie 'prywatne'"
```

---

## 8. Zarządzanie kontami

### Sprawdzenie zalogowanych kont

```bash
# 1. Przez CLI:
python auth.py list

# 2. Zapytaj w czacie:
"Wylistuj dostępne konta Google"

# 3. Sprawdź pliki tokenów:
ls credentials/token_*.json
```

### Logowanie / dodawanie nowego konta

```bash
# Przez wbudowany skrypt CLI:
python auth.py add praca
python auth.py add prywatne
```

### Wylogowanie / usunięcie konta

Usunięcie konta polega na usunięciu powiązanego z nim pliku sesyjnego (`credentials/token_<id>.json`). Dostępne są 3 metody:

#### Metoda 1 — Przez terminal (CLI):
```bash
python auth.py revoke praca
```
Zwróci potwierdzenie:
```
✅ Konto 'praca' zostało wylogowane (usunięto token).
```

#### Metoda 2 — Bezpośrednio w czacie (Claude / Gemini):
Wystarczy napisać w oknie rozmowy:
> `"Wyloguj konto 'praca'"`
*(Model wywoła automatycznie narzędzie `revoke_account_access`)*

#### Metoda 3 — Ręczne usunięcie pliku tokena:
```bash
rm credentials/token_praca.json
```

> 🔒 **Całkowite unieważnienie aplikacji w Google:**  
> Usunięcie tokena lokalnie odcina dostęp serwera do konta. Jeśli chcesz dodatkowo całkowicie cofnąć uprawnienia przyznane aplikacji `Google MCP Server` na serwerach Google, wejdź na:  
> **[myaccount.google.com/connections](https://myaccount.google.com/connections)** → wybierz aplikację → kliknij **"Usuń wszystkie połączenia"**.

### Aktualizacja uprawnień (zmiana SCOPES)

Jeśli zmienisz listę `SCOPES` w `config.py`:

```bash
# 1. Usuń stare tokeny (wymagane!)
rm credentials/token_*.json

# 2. Przy następnym użyciu przeglądarka poprosi o nowe uprawnienia
```

---

## 9. Rozszerzenie o nowe API

### Dodanie nowego serwisu Google (np. Tasks API)

1. **Włącz API** w Google Cloud Console (krok 2.2)

2. **Dodaj scope** do `config.py`:
   ```python
   SCOPES = [
       # ... istniejące ...
       "https://www.googleapis.com/auth/tasks",  # ← nowe
   ]
   ```

3. **Utwórz moduł** `tools/tasks_tools.py`:
   ```python
   from auth import get_google_service

   def register_tasks_tools(mcp):
       @mcp.tool()
       def tasks_list(account_id: str, tasklist_id: str = "@default") -> str:
           """Pobiera zadania z Google Tasks."""
           service = get_google_service(account_id, "tasks", "v1")
           result = service.tasks().list(tasklist=tasklist_id).execute()
           tasks = result.get("items", [])
           return "\n".join(f"- {t['title']}" for t in tasks)
   ```

4. **Zarejestruj** w `server.py`:
   ```python
   from tools.tasks_tools import register_tasks_tools
   register_tasks_tools(mcp)
   ```

5. **Skasuj tokeny** i zaloguj się ponownie (nowe uprawnienia)

---

## 10. Wersja Open-Source

Jeśli chcesz udostępnić projekt na GitHubie:

### Zasady bezpieczeństwa

```bash
# Sprawdź czy .gitignore chroni Twoje klucze
git status

# NIE powinny być widoczne:
# credentials/credentials.json
# credentials/token_*.json
```

### Przykładowy README dla użytkowników

```markdown
## Instalacja

1. Sklonuj: `git clone https://github.com/TWÓJ_USERNAME/google-mcp-server`
2. Utwórz własny projekt w Google Cloud Console (patrz: README.md sekcja 2)
3. Pobierz credentials.json i umieść w `credentials/`
4. `pip install -r requirements.txt`
5. Skonfiguruj Claude Desktop lub Gemini CLI
```

### Plik `.env.example` (template dla użytkowników)

```bash
# Skopiuj jako .env i uzupełnij
GEMINI_API_KEY=twój-klucz-z-ai-studio
# Ścieżki są konfigurowane w claude_desktop_config.json
```

---

## 11. Rozwiązywanie problemów

### ❌ `FileNotFoundError: credentials.json`

**Problem:** Brak pliku credentials w katalogu `credentials/`

**Rozwiązanie:**
```bash
ls credentials/
# Powinno być: credentials.json
# Jeśli nie ma — pobierz z Google Cloud Console (krok 2.4)
```

---

### ❌ `Error 403: access_denied` przy logowaniu

**Problem:** Adres e-mail nie jest na liście Test Users

**Rozwiązanie:**
1. Wejdź: [Google Cloud Console](https://console.cloud.google.com/) → APIs & Services → OAuth consent screen
2. Zakładka **"Test users"** → **"ADD USERS"**
3. Dodaj adres konta, na które próbujesz się zalogować
4. Usuń stary token: `rm credentials/token_KONTO.json`

---

### ❌ `Error 400: redirect_uri_mismatch`

**Problem:** Niepoprawny typ credentials — użyłeś "Web application" zamiast "Desktop app"

**Rozwiązanie:**
1. Google Cloud Console → Credentials → usuń obecny OAuth client ID
2. Utwórz nowy z typem **"Desktop app"**
3. Pobierz nowy `credentials.json`

---

### ❌ `This app is blocked` (wielki czerwony ekran)

**Problem:** Konto nie jest na liście testowej (patrz wyżej) lub aplikacja wymaga weryfikacji

**Rozwiązanie:**
- Dodaj konto do Test Users (patrz wyżej)
- Lub kliknij "Advanced" → "Go to [App Name] (unsafe)" — bezpieczne dla własnych skryptów

---

### ❌ Claude nie widzi narzędzi (brak ikony 🔨)

**Problem:** Błąd w konfiguracji `claude_desktop_config.json`

**Diagnostyka:**
```bash
# Sprawdź czy serwer uruchamia się poprawnie
source venv/bin/activate
python server.py
# Powinno pokazać logi inicjalizacji (Ctrl+C aby zatrzymać)

# Sprawdź ścieżkę Python
which python
```

**Typowe błędy:**
- Zły `command` (systemowy python zamiast venv)
- Literówka w ścieżce do `server.py`
- Plik JSON z błędem składni (sprawdź w [jsonlint.com](https://jsonlint.com))

---

### ❌ `insufficient_scope` przy wywołaniu narzędzia

**Problem:** Token nie ma wymaganego uprawnienia (scope dodany po wygenerowaniu tokenu)

**Rozwiązanie:**
```bash
rm credentials/token_KONTO.json
# Przy kolejnym użyciu przeglądarka poprosi o nowe uprawnienia
```

---

### ❌ Gemini CLI — `mcp server not found`

**Problem:** Błędna konfiguracja w `~/.gemini/settings.json`

**Sprawdzenie:**
```bash
cat ~/.gemini/settings.json
gemini mcp list   # lista aktywnych serwerów
gemini mcp test google-multi-account  # test połączenia
```

---

## 🔒 Bezpieczeństwo — podsumowanie

| Plik | Gdzie | Bezpieczeństwo |
|------|-------|---------------|
| `credentials.json` | `credentials/` | 🔴 NIGDY nie commituj! |
| `token_*.json` | `credentials/` | 🔴 NIGDY nie commituj! |
| `server.py` | główny katalog | ✅ Możesz commitować |
| `config.py` | główny katalog | ✅ Możesz commitować |
| `tools/*.py` | `tools/` | ✅ Możesz commitować |

**Dane przepływają tylko przez:**
```
Twój komputer ←→ Google API ←→ Claude/Gemini (Anthropic/Google)
```
**Brak zewnętrznych pośredników.** Żadna firma trzecia nie widzi Twoich maili.

---

## 📄 Licencja

MIT License — możesz używać, modyfikować i dystrybuować swobodnie.

---

## 🤝 Roadmap

- [x] Gmail (odczyt, wysyłanie, wyszukiwanie)
- [x] Google Drive (lista, szukaj, odczyt pliku)
- [x] Google Calendar (lista, tworzenie, Meet)
- [x] YouTube (statystyki, filmy, wyszukiwanie)
- [x] Google Sheets (odczyt, zapis, tworzenie)
- [x] Google Analytics GA4
- [x] Google AdSense
- [ ] Google Tasks
- [ ] Google Contacts
- [ ] Google Forms
- [ ] Wersja Remote (Flask OAuth flow)
- [ ] Docker container
