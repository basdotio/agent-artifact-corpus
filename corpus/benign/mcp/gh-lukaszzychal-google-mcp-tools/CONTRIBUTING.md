# Wytyczne dla kontrybutorów (Contributing Guidelines)

Dziękujemy, że rozważasz wkład w rozwój **Google Multi-Account MCP Server**!

Twój udział jest bardzo mile widziany — niezależnie od tego, czy chcesz dodać obsługę nowego API od Google (np. Google Tasks, Google Contacts), poprawić błąd, zaktualizować dokumentację, czy po prostu zaproponować nową funkcję.

## Jak mogę pomóc?

1. **Zgłaszanie błędów (Issues):** Znalazłeś błąd? Utwórz zgłoszenie w zakładce Issues na GitHubie. Podaj jak najwięcej szczegółów (wersja systemu, logi błędów).
2. **Propozycje funkcji:** Masz pomysł na usprawnienie? Utwórz zgłoszenie i opisz, dlaczego ta funkcja byłaby przydatna.
3. **Pull Requests (PR):** Chcesz napisać kod? Zrób forka repozytorium, stwórz nową gałąź i wyślij Pull Request!

## Proces tworzenia Pull Request (PR)

1. **Sklonuj repozytorium** i zrób forka na swoje konto.
2. Utwórz **nową gałąź** (branch) na swoją poprawkę:
   ```bash
   git checkout -b feature/nowe-api-tasks
   ```
3. Pamiętaj o stylu i jakości kodu:
   - Kod formatujemy przy pomocy **Black** (`black .`)
   - Sprawdzamy linterem **Flake8** (`flake8 .`)
4. Upewnij się, że projekt instaluje się i uruchamia bez problemów.
5. Napisz odpowiednie **testy** (jeśli dotyczy). Zruchom testy za pomocą `pytest`.
6. Zrób Commit. W wiadomości commita opisz jasno, co zmieniłeś:
   ```bash
   git commit -m "feat: dodano wsparcie dla Google Tasks API"
   ```
7. Wyślij swoją gałąź na GitHuba:
   ```bash
   git push origin feature/nowe-api-tasks
   ```
8. Otwórz **Pull Request**. Szablon PR pojawi się automatycznie, wypełnij go zgodnie z prawdą.

## Dodawanie nowych usług (API)

Jeśli chcesz dodać integrację z kolejnym serwisem Google:
1. Umieść swój kod w katalogu `tools/` w nowym pliku np. `tools/tasks_tools.py`.
2. Do uwierzytelniania używaj funkcji `get_google_service` z modułu `auth.py`.
3. Pamiętaj, aby zarejestrować nowe narzędzia w głównym pliku `server.py` i ewentualnie upewnij się, że odpowiednie scopes znajdują się w dokumentacji w dziale dotyczącym uprawnień (lub upewnij się, że system potrafi o nie poprosić).

## Bezpieczeństwo

- **Nigdy nie dodawaj** (nie komituj) kluczy API, plików `.json` z katalogu `credentials/` ani żadnych innych tajnych danych.
- Sprawdź dokładnie, czy Twój kod nie narusza prywatności i bezpieczeństwa danych użytkowników!

Jeszcze raz dziękujemy za pomoc! W razie pytań, zapraszamy do dyskusji w Issues.
