"""
tests/test_auth.py – Testy modułu autoryzacji.

Uruchomienie:
    source venv/bin/activate
    python -m pytest tests/ -v
"""

import sys
import os
from pathlib import Path

# Dodaj katalog główny do ścieżki
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from unittest.mock import patch, MagicMock
from auth import list_available_accounts, revoke_account, _token_path


class TestListAvailableAccounts:
    """Testy funkcji list_available_accounts."""

    def test_empty_directory(self, tmp_path):
        """Brak tokenów → pusta lista."""
        with patch("auth.CREDENTIALS_DIR", tmp_path):
            result = list_available_accounts()
        assert result == []

    def test_multiple_tokens(self, tmp_path):
        """Kilka tokenów → lista posortowana."""
        (tmp_path / "token_praca.json").write_text("{}")
        (tmp_path / "token_prywatne.json").write_text("{}")
        (tmp_path / "token_backup.json").write_text("{}")

        with patch("auth.CREDENTIALS_DIR", tmp_path):
            result = list_available_accounts()

        assert result == ["backup", "praca", "prywatne"]

    def test_ignores_non_token_files(self, tmp_path):
        """Pliki bez prefixu token_ są ignorowane."""
        (tmp_path / "credentials.json").write_text("{}")
        (tmp_path / "token_praca.json").write_text("{}")

        with patch("auth.CREDENTIALS_DIR", tmp_path):
            result = list_available_accounts()

        assert result == ["praca"]


class TestRevokeAccount:
    """Testy funkcji revoke_account."""

    def test_revoke_existing(self, tmp_path):
        """Token istnieje → usunięcie i zwrot True."""
        token_file = tmp_path / "token_praca.json"
        token_file.write_text("{}")

        with patch("auth.CREDENTIALS_DIR", tmp_path):
            result = revoke_account("praca")

        assert result is True
        assert not token_file.exists()

    def test_revoke_nonexistent(self, tmp_path):
        """Token nie istnieje → zwrot False, brak błędu."""
        with patch("auth.CREDENTIALS_DIR", tmp_path):
            result = revoke_account("nieistniejace")

        assert result is False


class TestTokenPath:
    """Testy funkcji _token_path."""

    def test_returns_correct_path(self, tmp_path):
        """Sprawdza poprawną ścieżkę tokenu."""
        with patch("auth.CREDENTIALS_DIR", tmp_path):
            result = _token_path("praca")
        assert result == tmp_path / "token_praca.json"
