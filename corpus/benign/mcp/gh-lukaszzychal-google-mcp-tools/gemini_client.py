"""
gemini_client.py – Klient Gemini z dostępem do narzędzi Google przez MCP.

Wymagania:
    pip install google-genai

Konfiguracja:
    export GEMINI_API_KEY="twój-klucz-z-aistudio.google.com/apikey"

Uruchomienie:
    source venv/bin/activate
    python gemini_client.py

Klucz API: https://aistudio.google.com/apikey
"""

import asyncio
import os
import sys
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────────
# Konfiguracja
# ─────────────────────────────────────────────────────────────────────────────

# Klucz API z https://aistudio.google.com/apikey
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# Wykryj automatycznie Python i server.py w tym samym projekcie
PROJECT_DIR = Path(__file__).parent
PYTHON_PATH = str(PROJECT_DIR / "venv" / "bin" / "python")
SERVER_PATH = str(PROJECT_DIR / "server.py")

# Model Gemini do użycia
GEMINI_MODEL = "gemini-2.5-pro"


# ─────────────────────────────────────────────────────────────────────────────
# Sprawdzenie konfiguracji
# ─────────────────────────────────────────────────────────────────────────────


def check_config() -> bool:
    """Sprawdza poprawność konfiguracji przed uruchomieniem."""
    ok = True

    if not GEMINI_API_KEY:
        print("❌ Brak klucza GEMINI_API_KEY!")
        print("   Ustaw go: export GEMINI_API_KEY='AIza...'")
        print("   Klucz pobierz z: https://aistudio.google.com/apikey")
        ok = False

    if not Path(PYTHON_PATH).exists():
        print(f"❌ Nie znaleziono Pythona: {PYTHON_PATH}")
        print("   Upewnij się, że środowisko venv jest aktywne.")
        ok = False

    if not Path(SERVER_PATH).exists():
        print(f"❌ Nie znaleziono server.py: {SERVER_PATH}")
        ok = False

    if not (PROJECT_DIR / "credentials" / "credentials.json").exists():
        print("❌ Brak pliku credentials/credentials.json!")
        print("   Pobierz go z Google Cloud Console (patrz README.md sekcja 2.4)")
        ok = False

    return ok


# ─────────────────────────────────────────────────────────────────────────────
# Klient Gemini z MCP
# ─────────────────────────────────────────────────────────────────────────────


async def run_interactive_chat():
    """Uruchamia interaktywny czat z Gemini + narzędziami Google."""

    try:
        from google import genai
        from google.genai import types
    except ImportError:
        print("❌ Brak biblioteki google-genai!")
        print("   Zainstaluj: pip install google-genai")
        sys.exit(1)

    if not check_config():
        sys.exit(1)

    print(f"\n{'─' * 60}")
    print(f"  Gemini {GEMINI_MODEL} + Google Multi-Account MCP")
    print(f"{'─' * 60}")
    print("  Dostępne narzędzia: Gmail, Drive, Calendar, YouTube,")
    print("                      Sheets, Analytics, AdSense")
    print(f"{'─' * 60}")
    print("  Wpisz 'quit' lub Ctrl+C aby wyjść")
    print(f"{'─' * 60}\n")

    client = genai.Client(api_key=GEMINI_API_KEY)

    # Konfiguracja serwera MCP
    mcp_server = types.MCPServerConfig(
        command=PYTHON_PATH,
        args=[SERVER_PATH],
    )

    # System prompt — instrukcje dla Gemini
    system_prompt = """Jesteś asystentem z dostępem do kont Google użytkownika.
    
Masz dostęp do narzędzi MCP które pozwalają Ci:
- Czytać i wysyłać maile (Gmail)
- Przeglądać pliki (Google Drive)  
- Zarządzać kalendarzem (Google Calendar)
- Sprawdzać statystyki YouTube
- Odczytywać i edytować arkusze (Google Sheets)
- Analizować dane Google Analytics
- Sprawdzać przychody AdSense

Konta użytkownika mają nazwy (account_id) jak 'praca', 'prywatne' itp.
Zawsze pytaj o account_id jeśli nie jest podany w zapytaniu.
Odpowiadaj po polsku."""

    # Historia rozmowy
    history = []

    try:
        while True:
            user_input = input("Ty: ").strip()

            if user_input.lower() in ("quit", "exit", "q", "wyjdź"):
                print("\n👋 Do widzenia!")
                break

            if not user_input:
                continue

            history.append({"role": "user", "parts": [{"text": user_input}]})

            try:
                response = await client.aio.models.generate_content(
                    model=GEMINI_MODEL,
                    contents=history,
                    config=types.GenerateContentConfig(
                        tools=[types.Tool(mcp_servers=[mcp_server])],
                        system_instruction=system_prompt,
                        temperature=0.7,
                    ),
                )

                # Wyodrębnij tekst odpowiedzi
                response_text = response.text or "(brak odpowiedzi tekstowej)"

                print(f"\nGemini: {response_text}\n")

                # Dodaj odpowiedź do historii
                history.append({"role": "model", "parts": [{"text": response_text}]})

            except Exception as e:
                print(f"\n❌ Błąd Gemini API: {e}\n")

    except KeyboardInterrupt:
        print("\n\n👋 Do widzenia!")


async def run_single_query(query: str) -> str:
    """
    Wykonuje jednorazowe zapytanie do Gemini z narzędziami MCP.

    Args:
        query: Zapytanie do Gemini

    Returns:
        Odpowiedź tekstowa
    """
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=GEMINI_API_KEY)

    mcp_server = types.MCPServerConfig(
        command=PYTHON_PATH,
        args=[SERVER_PATH],
    )

    response = await client.aio.models.generate_content(
        model=GEMINI_MODEL,
        contents=[{"role": "user", "parts": [{"text": query}]}],
        config=types.GenerateContentConfig(
            tools=[types.Tool(mcp_servers=[mcp_server])],
            temperature=0.7,
        ),
    )

    return response.text or ""


# ─────────────────────────────────────────────────────────────────────────────
# Przykłady użycia biblioteki (do importu z innych skryptów)
# ─────────────────────────────────────────────────────────────────────────────


async def example_check_emails(account_id: str = "praca") -> str:
    """Przykład: sprawdzenie maili przez Gemini."""
    return await run_single_query(
        f"Pokaż moje 5 ostatnich nieprzeczytanych maili na koncie '{account_id}'"
    )


async def example_check_calendar(account_id: str = "praca", days: int = 7) -> str:
    """Przykład: sprawdzenie kalendarza przez Gemini."""
    return await run_single_query(
        f"Jakie mam spotkania w ciągu najbliższych {days} dni? Konto: '{account_id}'"
    )


async def example_youtube_stats(account_id: str = "praca") -> str:
    """Przykład: statystyki YouTube przez Gemini."""
    return await run_single_query(
        f"Podaj statystyki mojego kanału YouTube dla konta '{account_id}'"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Tryb jednorazowego zapytania przez argument CLI
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
        print(f"Zapytanie: {query}\n")
        result = asyncio.run(run_single_query(query))
        print(result)
    else:
        # Tryb interaktywny
        asyncio.run(run_interactive_chat())
