"""
tools/gmail_tools.py – Narzędzia MCP dla Gmail.

Dostępne narzędzia:
  - gmail_list_emails      Pobiera listę maili (z opcjonalnym filtrem)
  - gmail_get_email        Odczytuje pełną treść konkretnego maila
  - gmail_send_email       Wysyła wiadomość e-mail
  - gmail_search_emails    Zaawansowane wyszukiwanie (składnia Gmail query)
  - gmail_mark_as_read     Oznacza wiadomość jako przeczytaną
  - gmail_trash_email      Przenosi maila do kosza
  - gmail_untrash_email    Przywraca maila z kosza
  - gmail_create_draft     Tworzy wersję roboczą (szkic)
"""

import base64
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from auth import get_google_service

logger = logging.getLogger(__name__)


def register_gmail_tools(mcp) -> None:
    """Rejestruje wszystkie narzędzia Gmail w serwerze MCP."""

    # ── 1. Lista maili ────────────────────────────────────────────────────────

    @mcp.tool()
    def gmail_list_emails(
        account_id: str,
        limit: int = 10,
        query: str = "",
        include_body: bool = False,
    ) -> str:
        """
        Pobiera listę maili z Gmaila dla wskazanego konta.

        Args:
            account_id:   Nazwa konta Google (np. 'praca', 'prywatne')
            limit:        Liczba maili do pobrania (1-50, domyślnie 10)
            query:        Filtr wyszukiwania w składni Gmail, np.:
                          'is:unread', 'from:szef@firma.pl', 'subject:faktura',
                          'after:2026/09/01', 'has:attachment'
            include_body: Czy dołączyć snippet treści maila (domyślnie False)

        Returns:
            Sformatowana lista maili lub komunikat o błędzie.
        """
        try:
            service = get_google_service(account_id, "gmail", "v1")
            result = (
                service.users()
                .messages()
                .list(
                    userId="me",
                    maxResults=min(limit, 50),
                    q=query,
                )
                .execute()
            )

            messages = result.get("messages", [])
            if not messages:
                q_info = f" dla zapytania '{query}'" if query else ""
                return f"📭 Brak maili{q_info} na koncie '{account_id}'."

            output_lines = [
                f"📬 Konto: {account_id} | Znaleziono: {len(messages)} maili\n"
            ]
            for msg_ref in messages:
                msg = (
                    service.users()
                    .messages()
                    .get(
                        userId="me",
                        id=msg_ref["id"],
                        format="metadata",
                        metadataHeaders=["From", "To", "Subject", "Date"],
                    )
                    .execute()
                )

                headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
                labels = msg.get("labelIds", [])
                unread = "🔴 " if "UNREAD" in labels else "   "
                snippet = (
                    f"\n   💬 {msg.get('snippet', '')[:120]}..." if include_body else ""
                )

                output_lines.append(
                    f"{unread}📧 Od: {headers.get('From', 'N/A')}\n"
                    f"   Temat: {headers.get('Subject', '(brak)')}\n"
                    f"   Data: {headers.get('Date', 'N/A')}"
                    f"{snippet}"
                )

            return "\n\n".join(output_lines)
        except Exception as e:
            logger.error(f"gmail_list_emails [{account_id}]: {e}")
            return f"❌ Błąd Gmaila ({account_id}): {str(e)}"

    # ── 2. Odczyt pełnej wiadomości ───────────────────────────────────────────

    @mcp.tool()
    def gmail_get_email(account_id: str, message_id: str) -> str:
        """
        Odczytuje pełną treść konkretnego maila.

        Args:
            account_id: Nazwa konta Google
            message_id: ID wiadomości (z wyników gmail_list_emails lub gmail_search_emails)

        Returns:
            Pełna treść maila (nadawca, temat, data, treść tekstowa).
        """
        try:
            service = get_google_service(account_id, "gmail", "v1")
            msg = (
                service.users()
                .messages()
                .get(
                    userId="me",
                    id=message_id,
                    format="full",
                )
                .execute()
            )

            headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
            body = _extract_body(msg["payload"])

            return (
                f"📧 WIADOMOŚĆ\n"
                f"{'─' * 50}\n"
                f"Od:      {headers.get('From', 'N/A')}\n"
                f"Do:      {headers.get('To', 'N/A')}\n"
                f"Temat:   {headers.get('Subject', '(brak)')}\n"
                f"Data:    {headers.get('Date', 'N/A')}\n"
                f"{'─' * 50}\n"
                f"{body or '(brak treści tekstowej)'}"
            )
        except Exception as e:
            logger.error(f"gmail_get_email [{account_id}/{message_id}]: {e}")
            return f"❌ Błąd odczytu maila ({account_id}): {str(e)}"

    # ── 3. Wysyłanie maila ────────────────────────────────────────────────────

    @mcp.tool()
    def gmail_send_email(
        account_id: str,
        to: str,
        subject: str,
        body: str,
        cc: str = "",
        reply_to_id: str = "",
    ) -> str:
        """
        Wysyła wiadomość e-mail z konta Google.

        Args:
            account_id:   Nazwa konta nadawcy
            to:           Adres lub adresy odbiorców (oddzielone przecinkami)
            subject:      Temat wiadomości
            body:         Treść wiadomości (zwykły tekst)
            cc:           Adresy do wiadomości CC (opcjonalnie)
            reply_to_id:  ID wiadomości, na którą odpowiadamy (opcjonalnie)

        Returns:
            Potwierdzenie wysłania lub komunikat o błędzie.
        """
        try:
            service = get_google_service(account_id, "gmail", "v1")

            message = MIMEMultipart()
            message["to"] = to
            message["subject"] = subject
            if cc:
                message["cc"] = cc
            message.attach(MIMEText(body, "plain", "utf-8"))

            raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
            send_body = {"raw": raw}

            # Dołącz do wątku jeśli odpowiedź
            if reply_to_id:
                orig = (
                    service.users()
                    .messages()
                    .get(
                        userId="me",
                        id=reply_to_id,
                        format="metadata",
                        metadataHeaders=["Message-Id", "References"],
                    )
                    .execute()
                )
                orig_headers = {
                    h["name"]: h["value"] for h in orig["payload"]["headers"]
                }
                send_body["threadId"] = orig.get("threadId")

            sent = (
                service.users().messages().send(userId="me", body=send_body).execute()
            )

            return f"✅ Wiadomość wysłana pomyślnie!\n   ID: {sent['id']}\n   Do: {to}"
        except Exception as e:
            logger.error(f"gmail_send_email [{account_id}]: {e}")
            return f"❌ Błąd wysyłania maila ({account_id}): {str(e)}"

    # ── 4. Wyszukiwanie maili ─────────────────────────────────────────────────

    @mcp.tool()
    def gmail_search_emails(account_id: str, query: str, limit: int = 20) -> str:
        """
        Zaawansowane wyszukiwanie maili (składnia Gmail query).

        Przykłady query:
          'is:unread'                   – nieprzeczytane
          'from:szef@firma.pl'          – od konkretnej osoby
          'subject:faktura'             – po temacie
          'has:attachment'              – z załącznikiem
          'after:2026/09/01'            – po określonej dacie
          'label:INBOX -label:SPAM'     – skrzynka bez spamu
          'larger:10M'                  – maile większe niż 10 MB

        Args:
            account_id: Nazwa konta Google
            query:      Zapytanie Gmail search
            limit:      Maksymalna liczba wyników (domyślnie 20)

        Returns:
            Lista pasujących maili z metadanymi.
        """
        # Deleguje do gmail_list_emails z odpowiednim query
        return gmail_list_emails(account_id=account_id, limit=limit, query=query)

    # ── 5. Oznacz jako przeczytane ────────────────────────────────────────────

    @mcp.tool()
    def gmail_mark_as_read(account_id: str, message_id: str) -> str:
        """
        Oznacza wiadomość jako przeczytaną.

        Args:
            account_id: Nazwa konta Google
            message_id: ID wiadomości

        Returns:
            Potwierdzenie lub komunikat o błędzie.
        """
        try:
            service = get_google_service(account_id, "gmail", "v1")
            service.users().messages().modify(
                userId="me",
                id=message_id,
                body={"removeLabelIds": ["UNREAD"]},
            ).execute()
            return f"✅ Wiadomość {message_id} oznaczona jako przeczytana."
        except Exception as e:
            logger.error(f"gmail_mark_as_read [{account_id}/{message_id}]: {e}")
            return f"❌ Błąd ({account_id}): {str(e)}"

    # ── 6. Przeniesienie maila do kosza ───────────────────────────────────────

    @mcp.tool()
    def gmail_trash_email(account_id: str, message_id: str) -> str:
        """
        Przenosi wiadomość e-mail do kosza w Gmailu (bezpieczne usuwanie).

        Args:
            account_id: Nazwa konta Google
            message_id: ID wiadomości do usunięcia

        Returns:
            Potwierdzenie przeniesienia do kosza.
        """
        try:
            service = get_google_service(account_id, "gmail", "v1")
            service.users().messages().trash(userId="me", id=message_id).execute()
            return f"🗑️ Wiadomość {message_id} została przeniesiona do kosza Gmail."
        except Exception as e:
            logger.error(f"gmail_trash_email [{account_id}/{message_id}]: {e}")
            return f"❌ Błąd usuwania maila ({account_id}): {str(e)}"

    # ── 7. Przywrócenie z kosza ───────────────────────────────────────────────

    @mcp.tool()
    def gmail_untrash_email(account_id: str, message_id: str) -> str:
        """
        Przywraca wiadomość z kosza Gmail z powrotem do skrzynki odbiorczej.

        Args:
            account_id: Nazwa konta Google
            message_id: ID wiadomości do przywrócenia

        Returns:
            Potwierdzenie przywrócenia.
        """
        try:
            service = get_google_service(account_id, "gmail", "v1")
            service.users().messages().untrash(userId="me", id=message_id).execute()
            return f"✅ Wiadomość {message_id} została przywrócona z kosza."
        except Exception as e:
            logger.error(f"gmail_untrash_email [{account_id}/{message_id}]: {e}")
            return f"❌ Błąd przywracania maila ({account_id}): {str(e)}"

    # ── 8. Tworzenie wersji roboczej (Draft) ───────────────────────────────────

    @mcp.tool()
    def gmail_create_draft(
        account_id: str,
        to: str,
        subject: str,
        body: str,
    ) -> str:
        """
        Tworzy wersję roboczą (szkic) wiadomości w Gmailu (bez wysyłania).

        Args:
            account_id: Nazwa konta Google
            to:         Adres e-mail odbiorcy
            subject:    Temat wiadomości
            body:       Treść wiadomości tekstowej

        Returns:
            Potwierdzenie utworzenia wersji roboczej z jej ID.
        """
        try:
            service = get_google_service(account_id, "gmail", "v1")
            message = MIMEText(body, "plain", "utf-8")
            message["to"] = to
            message["subject"] = subject

            raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
            draft = (
                service.users()
                .drafts()
                .create(
                    userId="me",
                    body={"message": {"raw": raw}},
                )
                .execute()
            )

            return f"📝 Utworzono wersję roboczą (Draft)!\n   ID: {draft['id']}\n   Do: {to}\n   Temat: {subject}"
        except Exception as e:
            logger.error(f"gmail_create_draft [{account_id}]: {e}")
            return f"❌ Błąd tworzenia wersji roboczej ({account_id}): {str(e)}"


# ── Pomocnicze funkcje (nie są narzędziami MCP) ───────────────────────────────


def _extract_body(payload: dict) -> str:
    """Rekurencyjnie wydobywa tekst z ładunku wiadomości Gmail."""
    if payload.get("mimeType") == "text/plain":
        data = payload.get("body", {}).get("data", "")
        if data:
            return base64.urlsafe_b64decode(data + "==").decode(
                "utf-8", errors="replace"
            )

    for part in payload.get("parts", []):
        result = _extract_body(part)
        if result:
            return result

    return ""
