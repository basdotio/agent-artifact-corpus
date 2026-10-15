"""
tools/sheets_tools.py – Narzędzia MCP dla Google Sheets.

Dostępne narzędzia:
  - sheets_read_range      Odczyt zakresu komórek
  - sheets_write_range     Zapis danych do zakresu
  - sheets_append_row      Dodanie wiersza na końcu
  - sheets_list_sheets     Lista arkuszy w pliku
  - sheets_create          Tworzenie nowego arkusza
  - sheets_clear_range     Czyszczenie zakresu komórek
  - sheets_add_sheet       Dodanie nowej zakładki (pod-arkusza)
  - sheets_delete_sheet    Usunięcie zakładki z arkusza
"""

import logging
from auth import get_google_service

logger = logging.getLogger(__name__)


def register_sheets_tools(mcp) -> None:
    """Rejestruje wszystkie narzędzia Google Sheets w serwerze MCP."""

    # ── 1. Odczyt zakresu ─────────────────────────────────────────────────────

    @mcp.tool()
    def sheets_read_range(
        account_id: str,
        spreadsheet_id: str,
        range_name: str,
        value_render: str = "FORMATTED_VALUE",
    ) -> str:
        """
        Odczytuje dane z zakresu komórek Google Sheets.

        Args:
            account_id:     Nazwa konta Google
            spreadsheet_id: ID arkusza (z URL: docs.google.com/spreadsheets/d/{ID}/)
            range_name:     Zakres, np. 'Arkusz1!A1:D10' lub 'Arkusz1' (cały arkusz)
            value_render:   Format wartości: 'FORMATTED_VALUE' (tekst) lub 'UNFORMATTED_VALUE' (liczby)

        Returns:
            Dane z arkusza w formacie tabelarycznym.
        """
        try:
            service = get_google_service(account_id, "sheets", "v4")
            result = (
                service.spreadsheets()
                .values()
                .get(
                    spreadsheetId=spreadsheet_id,
                    range=range_name,
                    valueRenderOption=value_render,
                )
                .execute()
            )

            rows = result.get("values", [])
            if not rows:
                return f"📊 Zakres '{range_name}' jest pusty."

            # Wyrównaj szerokości kolumn
            max_cols = max(len(row) for row in rows)
            padded = [row + [""] * (max_cols - len(row)) for row in rows]
            col_widths = [
                max(len(str(row[i])) for row in padded) for i in range(max_cols)
            ]

            lines = [f"📊 {spreadsheet_id} | {range_name} ({len(rows)} wierszy):\n"]
            for i, row in enumerate(padded):
                formatted = " | ".join(
                    str(cell).ljust(col_widths[j]) for j, cell in enumerate(row)
                )
                if i == 0:
                    lines.append(formatted)
                    lines.append("─" * len(formatted))
                else:
                    lines.append(formatted)

            return "\n".join(lines)
        except Exception as e:
            logger.error(f"sheets_read_range [{account_id}/{spreadsheet_id}]: {e}")
            return f"❌ Błąd Sheets ({account_id}): {str(e)}"

    # ── 2. Zapis zakresu ─────────────────────────────────────────────────────

    @mcp.tool()
    def sheets_write_range(
        account_id: str,
        spreadsheet_id: str,
        range_name: str,
        values: list,
    ) -> str:
        """
        Zapisuje dane do zakresu komórek (nadpisuje istniejące wartości).

        Args:
            account_id:     Nazwa konta Google
            spreadsheet_id: ID arkusza
            range_name:     Zakres docelowy, np. 'Arkusz1!A1:C3'
            values:         Dwuwymiarowa lista wartości, np. [['A', 'B'], ['1', '2']]

        Returns:
            Potwierdzenie z liczbą zaktualizowanych komórek.
        """
        try:
            service = get_google_service(account_id, "sheets", "v4")
            body = {"values": values}
            result = (
                service.spreadsheets()
                .values()
                .update(
                    spreadsheetId=spreadsheet_id,
                    range=range_name,
                    valueInputOption="USER_ENTERED",
                    body=body,
                )
                .execute()
            )

            updated_cells = result.get("updatedCells", 0)
            return (
                f"✅ Zapisano {updated_cells} komórek\n"
                f"   Arkusz: {spreadsheet_id}\n"
                f"   Zakres: {result.get('updatedRange', range_name)}"
            )
        except Exception as e:
            logger.error(f"sheets_write_range [{account_id}/{spreadsheet_id}]: {e}")
            return f"❌ Błąd zapisu Sheets ({account_id}): {str(e)}"

    # ── 3. Dodaj wiersz ───────────────────────────────────────────────────────

    @mcp.tool()
    def sheets_append_row(
        account_id: str,
        spreadsheet_id: str,
        range_name: str,
        values: list,
    ) -> str:
        """
        Dodaje nowy wiersz na końcu danych w arkuszu.

        Args:
            account_id:     Nazwa konta Google
            spreadsheet_id: ID arkusza
            range_name:     Zakres kolumn, np. 'Arkusz1!A:Z'
            values:         Lista wartości dla jednego wiersza, np. ['Jan', '500', '2026-09-27']

        Returns:
            Potwierdzenie dodania wiersza.
        """
        try:
            service = get_google_service(account_id, "sheets", "v4")
            body = {"values": [values]}
            result = (
                service.spreadsheets()
                .values()
                .append(
                    spreadsheetId=spreadsheet_id,
                    range=range_name,
                    valueInputOption="USER_ENTERED",
                    insertDataOption="INSERT_ROWS",
                    body=body,
                )
                .execute()
            )

            table_range = result.get("updates", {}).get("updatedRange", "?")
            return (
                f"✅ Wiersz dodany pomyślnie!\n"
                f"   Zapisano w: {table_range}\n"
                f"   Wartości:   {' | '.join(str(v) for v in values)}"
            )
        except Exception as e:
            logger.error(f"sheets_append_row [{account_id}/{spreadsheet_id}]: {e}")
            return f"❌ Błąd dodawania wiersza Sheets ({account_id}): {str(e)}"

    # ── 4. Lista arkuszy ──────────────────────────────────────────────────────

    @mcp.tool()
    def sheets_list_sheets(account_id: str, spreadsheet_id: str) -> str:
        """
        Pobiera listę arkuszy (zakładek) w pliku Google Sheets.

        Args:
            account_id:     Nazwa konta Google
            spreadsheet_id: ID pliku Google Sheets

        Returns:
            Lista nazw zakładek z ich ID i liczbą wierszy/kolumn.
        """
        try:
            service = get_google_service(account_id, "sheets", "v4")
            spreadsheet = (
                service.spreadsheets()
                .get(
                    spreadsheetId=spreadsheet_id,
                    fields="properties.title,sheets.properties",
                )
                .execute()
            )

            title = spreadsheet.get("properties", {}).get("title", "Nieznany")
            sheets = spreadsheet.get("sheets", [])

            lines = [
                f"📊 Plik: {title} ({spreadsheet_id})\n   Zakładki ({len(sheets)}):\n"
            ]
            for sheet in sheets:
                props = sheet["properties"]
                grid = props.get("gridProperties", {})
                lines.append(
                    f"  📋 {props['title']}\n"
                    f"     ID: {props['sheetId']}"
                    f" | Wiersze: {grid.get('rowCount', '?')}"
                    f" | Kolumny: {grid.get('columnCount', '?')}"
                )

            return "\n".join(lines)
        except Exception as e:
            logger.error(f"sheets_list_sheets [{account_id}/{spreadsheet_id}]: {e}")
            return f"❌ Błąd Sheets ({account_id}): {str(e)}"

    # ── 5. Tworzenie arkusza ──────────────────────────────────────────────────

    @mcp.tool()
    def sheets_create(
        account_id: str,
        title: str,
        sheet_names: list = None,
    ) -> str:
        """
        Tworzy nowy plik Google Sheets.

        Args:
            account_id:  Nazwa konta Google
            title:       Tytuł nowego pliku
            sheet_names: Lista nazw zakładek (opcjonalnie, domyślnie ['Arkusz1'])

        Returns:
            ID i link do nowego pliku.
        """
        try:
            service = get_google_service(account_id, "sheets", "v4")

            sheets_config = [
                {"properties": {"title": name}} for name in (sheet_names or ["Arkusz1"])
            ]

            spreadsheet = (
                service.spreadsheets()
                .create(
                    body={
                        "properties": {"title": title},
                        "sheets": sheets_config,
                    }
                )
                .execute()
            )

            spreadsheet_id = spreadsheet["spreadsheetId"]
            link = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"

            return (
                f"✅ Arkusz utworzony!\n"
                f"   Tytuł: {title}\n"
                f"   ID:    {spreadsheet_id}\n"
                f"   Link:  {link}"
            )
        except Exception as e:
            logger.error(f"sheets_create [{account_id}]: {e}")
            return f"❌ Błąd tworzenia arkusza ({account_id}): {str(e)}"

    # ── 6. Czyszczenie zakresu ────────────────────────────────────────────────

    @mcp.tool()
    def sheets_clear_range(
        account_id: str,
        spreadsheet_id: str,
        range_name: str,
    ) -> str:
        """
        Czyści wartości w zadanym zakresie komórek (np. 'Arkusz1!A1:D10').

        Args:
            account_id:     Nazwa konta Google
            spreadsheet_id: ID arkusza Google
            range_name:     Zakres do wyczyszczenia w notacji A1

        Returns:
            Potwierdzenie wyczyszczenia zakresu.
        """
        try:
            service = get_google_service(account_id, "sheets", "v4")
            service.spreadsheets().values().clear(
                spreadsheetId=spreadsheet_id,
                range=range_name,
            ).execute()
            return f"✅ Zakres '{range_name}' w arkuszu {spreadsheet_id} został pomyślnie wyczyszczony."
        except Exception as e:
            logger.error(f"sheets_clear_range [{account_id}/{spreadsheet_id}]: {e}")
            return f"❌ Błąd czyszczenia zakresu ({account_id}): {str(e)}"

    # ── 7. Dodanie nowej zakładki (arkusza) ───────────────────────────────────

    @mcp.tool()
    def sheets_add_sheet(
        account_id: str,
        spreadsheet_id: str,
        title: str,
    ) -> str:
        """
        Dodaje nową zakładkę (pod-arkusz) do istniejącego pliku Google Sheets.

        Args:
            account_id:     Nazwa konta Google
            spreadsheet_id: ID arkusza Google
            title:          Nazwa nowej zakładki

        Returns:
            Potwierdzenie utworzenia nowej zakładki wraz z jej sheetId.
        """
        try:
            service = get_google_service(account_id, "sheets", "v4")
            request_body = {
                "requests": [{"addSheet": {"properties": {"title": title}}}]
            }
            res = (
                service.spreadsheets()
                .batchUpdate(
                    spreadsheetId=spreadsheet_id,
                    body=request_body,
                )
                .execute()
            )
            new_sheet_id = res["replies"][0]["addSheet"]["properties"]["sheetId"]
            return f"✅ Dodano zakładkę '{title}' (ID zakładki: {new_sheet_id}) do arkusza {spreadsheet_id}."
        except Exception as e:
            logger.error(f"sheets_add_sheet [{account_id}/{spreadsheet_id}]: {e}")
            return f"❌ Błąd dodawania zakładki ({account_id}): {str(e)}"

    # ── 8. Usunięcie zakładki (arkusza) ───────────────────────────────────────

    @mcp.tool()
    def sheets_delete_sheet(
        account_id: str,
        spreadsheet_id: str,
        sheet_id: int,
    ) -> str:
        """
        Usuwa wybraną zakładkę (pod-arkusz) z pliku Google Sheets na podstawie jej numerycznego ID.

        Args:
            account_id:     Nazwa konta Google
            spreadsheet_id: ID pliku arkusza Google
            sheet_id:       Numeryczne ID zakładki (pobrane np. z sheets_list_sheets)

        Returns:
            Potwierdzenie usunięcia zakładki.
        """
        try:
            service = get_google_service(account_id, "sheets", "v4")
            request_body = {"requests": [{"deleteSheet": {"sheetId": sheet_id}}]}
            service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body=request_body,
            ).execute()
            return f"✅ Zakładka o ID {sheet_id} została usunięta z arkusza {spreadsheet_id}."
        except Exception as e:
            logger.error(f"sheets_delete_sheet [{account_id}/{spreadsheet_id}]: {e}")
            return f"❌ Błąd usuwania zakładki ({account_id}): {str(e)}"
