"""
tools/drive_tools.py – Narzędzia MCP dla Google Drive.

Dostępne narzędzia:
  - drive_list_files        Lista plików (z opcjonalnym filtrem folderu)
  - drive_search_files      Wyszukiwanie plików po nazwie lub typie
  - drive_get_file_info     Szczegóły konkretnego pliku (metadane)
  - drive_read_text_file    Odczyt zawartości pliku tekstowego lub Google Docs
  - drive_list_folders      Lista folderów na dysku
  - drive_create_folder     Tworzenie nowego folderu
  - drive_upload_text_file  Tworzenie/zapis pliku tekstowego na dysku
  - drive_rename_file       Zmiana nazwy pliku lub folderu
  - drive_trash_file        Przeniesienie do kosza
  - drive_delete_file       Trwałe usunięcie pliku lub folderu
"""

import logging
from io import BytesIO

from auth import get_google_service
from googleapiclient.http import MediaInMemoryUpload, MediaIoBaseDownload

logger = logging.getLogger(__name__)

# Typy MIME, które można odczytać jako tekst
TEXT_MIME_TYPES = {
    "application/vnd.google-apps.document": "text/plain",
    "application/vnd.google-apps.spreadsheet": "text/csv",
}


def register_drive_tools(mcp) -> None:
    """Rejestruje wszystkie narzędzia Google Drive w serwerze MCP."""

    # ── 1. Lista plików ───────────────────────────────────────────────────────

    @mcp.tool()
    def drive_list_files(
        account_id: str,
        limit: int = 20,
        folder_id: str = "",
        order_by: str = "modifiedTime desc",
    ) -> str:
        """
        Pobiera listę plików z Google Drive.

        Args:
            account_id: Nazwa konta Google (np. 'praca', 'prywatne')
            limit:      Maksymalna liczba plików (domyślnie 20)
            folder_id:  ID folderu (puste = cały dysk bez usuniętych)
            order_by:   Sortowanie: 'modifiedTime desc', 'name', 'createdTime desc'

        Returns:
            Sformatowana lista plików z metadanymi.
        """
        try:
            service = get_google_service(account_id, "drive", "v3")

            if folder_id:
                q = f"'{folder_id}' in parents and trashed = false"
            else:
                q = "trashed = false"

            results = (
                service.files()
                .list(
                    pageSize=min(limit, 100),
                    q=q,
                    orderBy=order_by,
                    fields="files(id, name, mimeType, modifiedTime, size, webViewLink, parents)",
                )
                .execute()
            )

            files = results.get("files", [])
            if not files:
                return f"📁 Brak plików na koncie '{account_id}'" + (
                    f" w folderze {folder_id}" if folder_id else ""
                )

            lines = [f"📁 Konto: {account_id} | Pliki ({len(files)}):\n"]
            for f in files:
                size_raw = f.get("size")
                size_str = _format_size(int(size_raw)) if size_raw else "—"
                icon = _mime_icon(f.get("mimeType", ""))
                modified = f.get("modifiedTime", "")[:10]
                lines.append(
                    f"{icon} {f['name']}\n"
                    f"   ID: {f['id']} | Rozmiar: {size_str} | Zmodyfikowano: {modified}"
                )

            return "\n\n".join(lines)
        except Exception as e:
            logger.error(f"drive_list_files [{account_id}]: {e}")
            return f"❌ Błąd Drive ({account_id}): {str(e)}"

    # ── 2. Wyszukiwanie plików ────────────────────────────────────────────────

    @mcp.tool()
    def drive_search_files(
        account_id: str,
        query: str,
        file_type: str = "",
        limit: int = 20,
    ) -> str:
        """
        Wyszukuje pliki na Google Drive po nazwie lub typie.

        Args:
            account_id: Nazwa konta Google
            query:      Fraza wyszukiwania w nazwie pliku
            file_type:  Filtr typu pliku (opcjonalnie):
                        'doc'    – Google Dokumenty
                        'sheet'  – Google Arkusze
                        'pdf'    – pliki PDF
                        'image'  – obrazy (jpg, png, gif)
                        'folder' – tylko foldery
            limit:      Maksymalna liczba wyników

        Returns:
            Lista pasujących plików z linkami.
        """
        try:
            service = get_google_service(account_id, "drive", "v3")

            type_filters = {
                "doc": "mimeType = 'application/vnd.google-apps.document'",
                "sheet": "mimeType = 'application/vnd.google-apps.spreadsheet'",
                "pdf": "mimeType = 'application/pdf'",
                "image": "mimeType contains 'image/'",
                "folder": "mimeType = 'application/vnd.google-apps.folder'",
            }

            q_parts = [f"name contains '{query}'", "trashed = false"]
            if file_type and file_type in type_filters:
                q_parts.append(type_filters[file_type])

            results = (
                service.files()
                .list(
                    pageSize=min(limit, 100),
                    q=" and ".join(q_parts),
                    fields="files(id, name, mimeType, modifiedTime, webViewLink)",
                )
                .execute()
            )

            files = results.get("files", [])
            if not files:
                return f"🔍 Brak wyników dla '{query}' na koncie '{account_id}'."

            lines = [f"🔍 Wyniki wyszukiwania '{query}' ({len(files)} plików):\n"]
            for f in files:
                icon = _mime_icon(f.get("mimeType", ""))
                link = f.get("webViewLink", "brak linku")
                lines.append(f"{icon} {f['name']}\n   🔗 {link}\n   ID: {f['id']}")

            return "\n\n".join(lines)
        except Exception as e:
            logger.error(f"drive_search_files [{account_id}]: {e}")
            return f"❌ Błąd wyszukiwania Drive ({account_id}): {str(e)}"

    # ── 3. Szczegóły pliku ────────────────────────────────────────────────────

    @mcp.tool()
    def drive_get_file_info(account_id: str, file_id: str) -> str:
        """
        Pobiera szczegółowe metadane konkretnego pliku.

        Args:
            account_id: Nazwa konta Google
            file_id:    ID pliku (z wyników drive_list_files lub drive_search_files)

        Returns:
            Szczegółowe informacje o pliku (właściciel, rozmiar, uprawnienia, link).
        """
        try:
            service = get_google_service(account_id, "drive", "v3")
            f = (
                service.files()
                .get(
                    fileId=file_id,
                    fields="id, name, mimeType, size, createdTime, modifiedTime, "
                    "owners, webViewLink, description, starred, shared",
                )
                .execute()
            )

            size_str = _format_size(int(f["size"])) if f.get("size") else "—"
            owners = ", ".join(o.get("emailAddress", "?") for o in f.get("owners", []))

            return (
                f"📄 SZCZEGÓŁY PLIKU\n{'─' * 40}\n"
                f"Nazwa:         {f['name']}\n"
                f"ID:            {f['id']}\n"
                f"Typ:           {f.get('mimeType', 'N/A')}\n"
                f"Rozmiar:       {size_str}\n"
                f"Właściciel:    {owners}\n"
                f"Utworzono:     {f.get('createdTime', 'N/A')[:10]}\n"
                f"Zmodyfikowano: {f.get('modifiedTime', 'N/A')[:10]}\n"
                f"Udostępniony:  {'Tak' if f.get('shared') else 'Nie'}\n"
                f"Ulubiony:      {'⭐ Tak' if f.get('starred') else 'Nie'}\n"
                f"Link:          {f.get('webViewLink', 'brak')}"
            )
        except Exception as e:
            logger.error(f"drive_get_file_info [{account_id}/{file_id}]: {e}")
            return f"❌ Błąd ({account_id}): {str(e)}"

    # ── 4. Odczyt zawartości pliku ────────────────────────────────────────────

    @mcp.tool()
    def drive_read_text_file(account_id: str, file_id: str) -> str:
        """
        Odczytuje zawartość pliku tekstowego lub Google Docs/Sheets.

        Obsługuje:
          - Google Dokumenty (eksportuje jako plain text)
          - Google Arkusze (eksportuje jako CSV)
          - Pliki .txt, .md, .py, .json, .csv i inne tekstowe

        Args:
            account_id: Nazwa konta Google
            file_id:    ID pliku do odczytania

        Returns:
            Zawartość pliku (pierwsze 5000 znaków).
        """
        try:
            service = get_google_service(account_id, "drive", "v3")
            meta = (
                service.files().get(fileId=file_id, fields="name, mimeType").execute()
            )
            mime = meta.get("mimeType", "")
            name = meta.get("name", file_id)

            # Google Docs/Sheets – eksport
            if mime in TEXT_MIME_TYPES:
                export_mime = TEXT_MIME_TYPES[mime]
                request = service.files().export_media(
                    fileId=file_id, mimeType=export_mime
                )
            else:
                # Zwykły plik binarny/tekstowy
                request = service.files().get_media(fileId=file_id)

            buffer = BytesIO()
            downloader = MediaIoBaseDownload(buffer, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()

            content = buffer.getvalue().decode("utf-8", errors="replace")
            truncated = len(content) > 5000
            preview = content[:5000]

            header = f"📄 {name}\n{'─' * 40}\n"
            footer = (
                "\n\n⚠️ [Wyświetlono pierwsze 5000 znaków z większego pliku]"
                if truncated
                else ""
            )
            return header + preview + footer

        except Exception as e:
            logger.error(f"drive_read_text_file [{account_id}/{file_id}]: {e}")
            return f"❌ Błąd odczytu pliku ({account_id}): {str(e)}"

    # ── 5. Lista folderów ─────────────────────────────────────────────────────

    @mcp.tool()
    def drive_list_folders(account_id: str, parent_id: str = "") -> str:
        """
        Pobiera listę folderów na Google Drive.

        Args:
            account_id: Nazwa konta Google
            parent_id:  ID folderu nadrzędnego (puste = główny poziom)

        Returns:
            Lista folderów z ich ID.
        """
        try:
            service = get_google_service(account_id, "drive", "v3")
            q_parts = [
                "mimeType = 'application/vnd.google-apps.folder'",
                "trashed = false",
            ]
            if parent_id:
                q_parts.append(f"'{parent_id}' in parents")

            results = (
                service.files()
                .list(
                    q=" and ".join(q_parts),
                    orderBy="name",
                    fields="files(id, name, modifiedTime)",
                )
                .execute()
            )

            folders = results.get("files", [])
            if not folders:
                return f"📁 Brak folderów na koncie '{account_id}'."

            lines = [f"📁 Foldery na koncie '{account_id}' ({len(folders)}):\n"]
            for folder in folders:
                lines.append(f"  📂 {folder['name']}\n     ID: {folder['id']}")

            return "\n".join(lines)
        except Exception as e:
            logger.error(f"drive_list_folders [{account_id}]: {e}")
            return f"❌ Błąd Drive ({account_id}): {str(e)}"

    # ── 6. Tworzenie folderu ──────────────────────────────────────────────────

    @mcp.tool()
    def drive_create_folder(
        account_id: str,
        name: str,
        parent_id: str = "",
    ) -> str:
        """
        Tworzy nowy folder na Google Drive.

        Args:
            account_id: Nazwa konta Google
            name:       Nazwa nowego folderu
            parent_id:  ID folderu nadrzędnego (puste = główny katalog dysku)

        Returns:
            Potwierdzenie utworzenia wraz z ID nowego folderu.
        """
        try:
            service = get_google_service(account_id, "drive", "v3")
            meta = {
                "name": name,
                "mimeType": "application/vnd.google-apps.folder",
            }
            if parent_id:
                meta["parents"] = [parent_id]

            created = (
                service.files()
                .create(body=meta, fields="id, name, webViewLink")
                .execute()
            )
            return (
                f"✅ Utworzono folder na Google Drive!\n"
                f"   Nazwa: {created['name']}\n"
                f"   ID:    {created['id']}"
            )
        except Exception as e:
            logger.error(f"drive_create_folder [{account_id}]: {e}")
            return f"❌ Błąd tworzenia folderu ({account_id}): {str(e)}"

    # ── 7. Zapis/wgrywanie pliku tekstowego ────────────────────────────────────

    @mcp.tool()
    def drive_upload_text_file(
        account_id: str,
        name: str,
        content: str,
        parent_id: str = "",
        mime_type: str = "text/plain",
    ) -> str:
        """
        Tworzy lub wgrywa plik tekstowy (np. txt, md, csv, json, html) na Google Drive.

        Args:
            account_id: Nazwa konta Google
            name:       Nazwa pliku z rozszerzeniem (np. 'raport.md', 'dane.csv')
            content:    Treść pliku tekstowego
            parent_id:  ID folderu docelowego (puste = główny katalog)
            mime_type:  Typ MIME (domyślnie 'text/plain', lub 'text/markdown', 'text/csv', 'application/json')

        Returns:
            Potwierdzenie z ID i linkiem do pliku.
        """
        try:
            service = get_google_service(account_id, "drive", "v3")
            meta = {"name": name}
            if parent_id:
                meta["parents"] = [parent_id]

            media = MediaInMemoryUpload(
                content.encode("utf-8"), mimetype=mime_type, resumable=False
            )
            uploaded = (
                service.files()
                .create(
                    body=meta,
                    media_body=media,
                    fields="id, name, webViewLink, size",
                )
                .execute()
            )

            link = uploaded.get("webViewLink", "")
            return (
                f"✅ Plik został zapisany na Google Drive!\n"
                f"   Nazwa: {uploaded['name']}\n"
                f"   ID:    {uploaded['id']}\n"
                f"   Link:  {link}"
            )
        except Exception as e:
            logger.error(f"drive_upload_text_file [{account_id}]: {e}")
            return f"❌ Błąd zapisu pliku ({account_id}): {str(e)}"

    # ── 8. Zmiana nazwy pliku lub folderu ─────────────────────────────────────

    @mcp.tool()
    def drive_rename_file(
        account_id: str,
        file_id: str,
        new_name: str,
    ) -> str:
        """
        Zmienia nazwę pliku lub folderu na Google Drive.

        Args:
            account_id: Nazwa konta Google
            file_id:    ID pliku lub folderu
            new_name:   Nowa nazwa

        Returns:
            Potwierdzenie zmiany nazwy.
        """
        try:
            service = get_google_service(account_id, "drive", "v3")
            updated = (
                service.files()
                .update(
                    fileId=file_id,
                    body={"name": new_name},
                    fields="id, name",
                )
                .execute()
            )
            return f"✅ Nazwa zmieniona na: '{updated['name']}' (ID: {file_id})."
        except Exception as e:
            logger.error(f"drive_rename_file [{account_id}/{file_id}]: {e}")
            return f"❌ Błąd zmiany nazwy ({account_id}): {str(e)}"

    # ── 9. Przeniesienie pliku do kosza ───────────────────────────────────────

    @mcp.tool()
    def drive_trash_file(
        account_id: str,
        file_id: str,
    ) -> str:
        """
        Przenosi plik lub folder do kosza na Google Drive (bezpieczne usuwanie).

        Args:
            account_id: Nazwa konta Google
            file_id:    ID pliku lub folderu do wyrzucenia do kosza

        Returns:
            Potwierdzenie przeniesienia do kosza.
        """
        try:
            service = get_google_service(account_id, "drive", "v3")
            service.files().update(fileId=file_id, body={"trashed": True}).execute()
            return (
                f"🗑️ Plik/folder {file_id} został przeniesiony do kosza Google Drive."
            )
        except Exception as e:
            logger.error(f"drive_trash_file [{account_id}/{file_id}]: {e}")
            return f"❌ Błąd przenoszenia do kosza ({account_id}): {str(e)}"

    # ── 10. Trwałe usunięcie pliku ────────────────────────────────────────────

    @mcp.tool()
    def drive_delete_file(
        account_id: str,
        file_id: str,
    ) -> str:
        """
        Trwale usuwa plik lub folder z Google Drive (bez możliwości przywrócenia z kosza).

        Args:
            account_id: Nazwa konta Google
            file_id:    ID pliku lub folderu

        Returns:
            Potwierdzenie trwałego usunięcia.
        """
        try:
            service = get_google_service(account_id, "drive", "v3")
            service.files().delete(fileId=file_id).execute()
            return (
                f"⚠️ Plik/folder {file_id} został bezpowrotnie usunięty z Google Drive."
            )
        except Exception as e:
            logger.error(f"drive_delete_file [{account_id}/{file_id}]: {e}")
            return f"❌ Błąd trwałego usuwania ({account_id}): {str(e)}"


# ── Pomocnicze funkcje ────────────────────────────────────────────────────────


def _format_size(size_bytes: int) -> str:
    """Formatuje rozmiar pliku w czytelny sposób."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def _mime_icon(mime: str) -> str:
    """Zwraca emoji odpowiadające typowi pliku."""
    if "folder" in mime:
        return "📂"
    if "document" in mime or "word" in mime:
        return "📝"
    if "spreadsheet" in mime or "excel" in mime:
        return "📊"
    if "presentation" in mime or "powerpoint" in mime:
        return "📽"
    if "pdf" in mime:
        return "📕"
    if "image" in mime:
        return "🖼"
    if "video" in mime:
        return "🎬"
    if "audio" in mime:
        return "🎵"
    if "zip" in mime or "archive" in mime:
        return "🗜"
    return "📄"
