"""
Unit tests for AdminService in services/admin_service.py.
"""

from unittest.mock import MagicMock

from services.admin_service import AdminService


class TestAdminService:
    def test_cms_query_success(self, admin_service: AdminService, mock_client: MagicMock):
        mock_client.post.return_value = {
            "entries": [
                {"SI_ID": 100, "SI_NAME": "Report A"},
                {"SI_ID": 101, "SI_NAME": "Report B"},
            ]
        }
        res = admin_service.cms_query("SELECT SI_ID, SI_NAME FROM CI_INFOOBJECTS", page=1, pagesize=10)
        assert res["total_returned"] == 2
        assert len(res["entries"]) == 2
        mock_client.post.assert_called_once()

    def test_get_users(self, admin_service: AdminService, mock_client: MagicMock):
        mock_client.post.return_value = {
            "entries": [
                {
                    "SI_ID": 12,
                    "SI_NAME": "Administrator",
                    "SI_EMAIL_ADDRESS": "admin@example.com",
                    "SI_ACCOUNT_DISABLED": False,
                    "SI_LASTLOGONTIME": "2026-10-19",
                }
            ]
        }
        users = admin_service.get_users(page=1, pagesize=10)
        assert len(users) == 1
        assert users[0]["username"] == "Administrator"
        assert users[0]["disabled"] is False

    def test_set_user_status(self, admin_service: AdminService, mock_client: MagicMock):
        mock_client.put.return_value = {"success": True}
        msg = admin_service.set_user_status("12", disabled=True)
        assert "disabled" in msg
        mock_client.put.assert_called_once()

    def test_get_active_sessions(self, admin_service: AdminService, mock_client: MagicMock):
        mock_client.post.return_value = {
            "entries": [
                {
                    "SI_ID": 9001,
                    "SI_NAME": "admin_session",
                    "SI_AUTHEN_USER_NAME": "Administrator",
                    "SI_CREATION_TIME": "2026-10-19 10:00",
                    "SI_LASTLOGONTIME": "2026-10-19 12:00",
                }
            ]
        }
        sessions = admin_service.get_active_sessions()
        assert len(sessions) == 1
        assert sessions[0]["user_name"] == "Administrator"
        assert sessions[0]["connection_id"] == "9001"

    def test_terminate_session(self, admin_service: AdminService, mock_client: MagicMock):
        mock_client.delete.return_value = {"success": True}
        res = admin_service.terminate_session("9001")
        assert "terminated" in res
        mock_client.delete.assert_called_once()
