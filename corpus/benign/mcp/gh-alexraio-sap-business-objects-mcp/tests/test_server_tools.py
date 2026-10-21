"""
Unit tests validating FastMCP server initialization, tool registration, and tool signatures.
"""

from unittest.mock import patch

import server


class TestServerToolRegistration:
    def test_total_registered_tools_count(self):
        """Verifies that all 46 enterprise MCP tools are properly registered on FastMCP."""
        tools = server.mcp._tool_manager._tools
        assert len(tools) == 46, f"Expected exactly 46 registered tools, got {len(tools)}"

    def test_essential_tools_present(self):
        tools = server.mcp._tool_manager._tools
        expected_tools = [
            # Auth
            "login",
            "logout",
            # Universes
            "get_universes",
            "get_universe_details",
            "get_universe_structure",
            "get_universe_related_reports",
            "get_universe_connection_id",
            # Webi Docs & Lifecycle
            "get_documents",
            "get_doc_details",
            "get_doc_properties",
            "save_webi_doc",
            "delete_webi_doc",
            # Prompts
            "get_doc_parameters",
            "get_parameter_lov",
            "refresh_webi_doc",
            # Tabs & Blocks
            "get_reports",
            "get_report_elements",
            "get_report_element_data",
            "get_variables",
            "get_comments",
            # Data Providers & SQL
            "get_dp",
            "get_dp_details",
            "get_dp_sql",
            "get_dp_specification",
            "refresh_dp",
            "purge_dp",
            "get_dp_mapping_proposal",
            "change_dp_datasource",
            # CMS Admin & Security
            "cms_query",
            "get_users",
            "get_user_details",
            "set_user_status",
            "get_user_groups",
            "get_group_users",
            "get_active_sessions",
            "terminate_session",
            # Schedules & Instances
            "get_doc_schedules",
            "get_doc_instances",
            "get_instance_details",
            "delete_instance",
            # InfoStore & Folders
            "get_folders",
            "get_folder_details",
            "create_folder",
            "delete_folder",
            "get_webi_docs",
            "get_categories",
        ]
        for t in expected_tools:
            assert t in tools, f"Missing tool in server: {t}"

    def test_tool_docstrings_populated(self):
        """Ensures that all tools have meaningful descriptive docstrings for LLM agents."""
        tools = server.mcp._tool_manager._tools
        for name, tool in tools.items():
            doc = getattr(tool.fn, "__doc__", "")
            assert doc and len(doc.strip()) > 10, f"Tool '{name}' lacks proper docstring documentation"

    @patch.object(server.parser, "set_logon_token")
    def test_login_tool_execution(self, mock_set_token):
        mock_set_token.return_value = "TOKEN_ABC"
        result = server.login.fn(username="test_admin", password="test_password")
        assert "Login successful for user 'test_admin'" in result
        mock_set_token.assert_called_once_with("test_admin", "test_password")

    @patch.object(server.parser, "bo_logoff")
    def test_logout_tool_execution(self, mock_logoff):
        mock_logoff.return_value = True
        result = server.logout.fn()
        assert "Logout successful" in result
        mock_logoff.assert_called_once()
