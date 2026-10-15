"""
test_tools_registration.py – Testy weryfikujące rejestrację wszystkich narzędzi MCP (pełny CRUD).
"""

import pytest
from server import mcp


def test_mcp_server_initialization():
    """Weryfikuje, czy instancja serwera FastMCP została zainicjalizowana."""
    assert mcp is not None
    assert mcp.name == "Google-Multi-Account-MCP"


def test_crud_tools_registered():
    """Sprawdza obecność kluczowych narzędzi CRUD dla usług Google."""
    tools = mcp._tool_manager._tools

    # 1. Google Calendar CRUD
    assert "calendar_list_events" in tools
    assert "calendar_get_event" in tools
    assert "calendar_create_event" in tools
    assert "calendar_update_event" in tools
    assert "calendar_delete_event" in tools
    assert "calendar_list_calendars" in tools

    # 2. Google Drive CRUD
    assert "drive_list_files" in tools
    assert "drive_get_file_info" in tools
    assert "drive_read_text_file" in tools
    assert "drive_create_folder" in tools
    assert "drive_upload_text_file" in tools
    assert "drive_rename_file" in tools
    assert "drive_trash_file" in tools
    assert "drive_delete_file" in tools

    # 3. Gmail CRUD
    assert "gmail_list_emails" in tools
    assert "gmail_get_email" in tools
    assert "gmail_send_email" in tools
    assert "gmail_create_draft" in tools
    assert "gmail_mark_as_read" in tools
    assert "gmail_trash_email" in tools
    assert "gmail_untrash_email" in tools

    # 4. Google Sheets CRUD
    assert "sheets_read_range" in tools
    assert "sheets_write_range" in tools
    assert "sheets_append_row" in tools
    assert "sheets_create" in tools
    assert "sheets_clear_range" in tools
    assert "sheets_add_sheet" in tools
    assert "sheets_delete_sheet" in tools

    # 5. Accounts
    assert "list_accounts" in tools
    assert "revoke_account_access" in tools
