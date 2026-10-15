import os
import sys
import unittest
from unittest.mock import patch, MagicMock

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)

sys.path.insert(0, PROJECT_ROOT)

import main

class TestMCPTools(unittest.TestCase):

    # ----------------------------------
    # system_info_tool
    # ----------------------------------
    @patch("main.process_service.get_system_info")
    def test_system_info_tool(self, mock_get_system_info):

        mock_obj = MagicMock()
        mock_obj.to_dict.return_value = {
            "System": "Windows",
            "CPU Usage": 25
        }

        mock_get_system_info.return_value = mock_obj

        result = main.system_info_tool()

        self.assertEqual(result["System"], "Windows")
        self.assertEqual(result["CPU Usage"], 25)
        mock_get_system_info.assert_called_once()


    # ----------------------------------
    # resource_usage_tool
    # ----------------------------------
    @patch("main.process_service.get_high_resource_usage")
    def test_resource_usage_tool(self, mock_get_usage):

        mock_get_usage.return_value = [
            {"pid": 1234}
        ]

        result = main.resource_usage_tool()

        self.assertEqual(result[0]["pid"], 1234)
        mock_get_usage.assert_called_once()

    # ----------------------------------
    # terminate_process_tool - no confirm
    # ----------------------------------
    def test_terminate_without_confirmation(self):

        result = main.terminate_process_tool(
            pid=111,
            confirmed=False
        )

        self.assertFalse(result["success"])
        self.assertEqual(result["pid"], 111)
        self.assertEqual(
            result["message"],
            "User confirmation required"
        )


    # ----------------------------------
    # terminate_process_tool - success
    # ----------------------------------
    @patch("main.process_service.terminate_process_with_validation")
    def test_terminate_success(self, mock_terminate):

        mock_terminate.return_value = {"success": True}

        result = main.terminate_process_tool(
            pid=111,
            confirmed=True
        )

        mock_terminate.assert_called_once_with(111)
        self.assertTrue(result["success"])


    # ----------------------------------
    # list_processes_tool
    # ----------------------------------
    @patch("main.process_service.get_processes")
    def test_list_processes_tool(self, mock_list):

        mock_list.return_value = [
            {"pid": 1},
            {"pid": 2},
        ]

        result = main.list_processes_tool(2)

        mock_list.assert_called_once_with(2)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["pid"], 1)


if __name__ == "__main__":
    unittest.main()