"""
Unit tests for ScheduleService and InfostoreService.
"""

from unittest.mock import MagicMock

from services.infostore_service import InfostoreService
from services.schedule_service import ScheduleService


class TestScheduleService:
    def test_get_doc_schedules(self, schedule_service: ScheduleService, mock_client: MagicMock):
        mock_client.get.return_value = {
            "schedules": {
                "schedule": [
                    {
                        "id": "7001",
                        "name": "Daily Refresh",
                        "status": "Running",
                    }
                ]
            }
        }
        scheds = schedule_service.get_doc_schedules("23856")
        assert len(scheds) == 1
        assert scheds[0]["status"] == "Running"
        assert scheds[0]["id"] == "7001"

    def test_get_instance_details_failed(self, schedule_service: ScheduleService, mock_client: MagicMock):
        mock_client.post.return_value = {
            "entries": [
                {
                    "SI_ID": 8001,
                    "SI_NAME": "Instance 1",
                    "SI_SCHEDULE_STATUS": 3,
                    "SI_STATUSINFO": "Database connection timeout",
                    "SI_STARTTIME": "2026-10-19 09:00",
                    "SI_ENDTIME": "2026-10-19 09:02",
                }
            ]
        }
        details = schedule_service.get_instance_details("8001")
        assert details["status"] == "Failed"
        assert "timeout" in details["error_message"]

    def test_delete_instance(self, schedule_service: ScheduleService, mock_client: MagicMock):
        mock_client.delete.return_value = {"success": True}
        res = schedule_service.delete_instance("8001")
        assert res is True
        mock_client.delete.assert_called_once()


class TestInfostoreService:
    def test_get_folders_recursive(self, infostore_service: InfostoreService, mock_client: MagicMock):
        # First call: root folder 100 has child 101
        # Second call: child 101 has no children
        mock_client.get.side_effect = [
            {"entries": [{"id": 101, "name": "Subfolder"}]},
            {"entries": []},
        ]
        folders = infostore_service.get_folders("100", recursive=True)
        assert "101" in folders

    def test_get_categories(self, infostore_service: InfostoreService, mock_client: MagicMock):
        mock_client.post.return_value = {
            "entries": [{"SI_ID": 301, "SI_NAME": "Finance Reports", "SI_CUID": "CUID_FIN"}]
        }
        cats = infostore_service.get_categories()
        assert len(cats) == 1
        assert cats[0]["name"] == "Finance Reports"
