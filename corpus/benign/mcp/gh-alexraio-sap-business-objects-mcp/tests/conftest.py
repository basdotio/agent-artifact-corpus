"""
Pytest configuration and shared fixtures for SAP BusinessObjects MCP server.
Provides mocked BOEClient and canned response data for offline unit testing.
"""

from typing import Any, Dict
from unittest.mock import MagicMock

import pytest

from core.client import BOEClient
from services.admin_service import AdminService
from services.infostore_service import InfostoreService
from services.schedule_service import ScheduleService
from services.universe_service import UniverseService
from services.webi_service import WebiService


@pytest.fixture
def mock_client() -> MagicMock:
    """Creates a mock BOEClient with pre-configured URLs and session attributes."""
    client = MagicMock(spec=BOEClient)
    client.base_url = "http://localhost:8080/biprws"
    client.bip_url = client.base_url
    client.webi_url = f"{client.base_url}/raylight/v1"
    client.sl_url = f"{client.base_url}/sl/v1"
    client.query_url = f"{client.base_url}/v1"
    client.logon_token = "MOCK_SESSION_TOKEN_12345"
    client.headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "X-SAP-LogonToken": client.logon_token,
    }
    return client


@pytest.fixture
def webi_service(mock_client: MagicMock) -> WebiService:
    return WebiService(mock_client)


@pytest.fixture
def universe_service(mock_client: MagicMock) -> UniverseService:
    return UniverseService(mock_client)


@pytest.fixture
def admin_service(mock_client: MagicMock) -> AdminService:
    return AdminService(mock_client)


@pytest.fixture
def schedule_service(mock_client: MagicMock) -> ScheduleService:
    return ScheduleService(mock_client)


@pytest.fixture
def infostore_service(mock_client: MagicMock) -> InfostoreService:
    return InfostoreService(mock_client)


@pytest.fixture
def sample_webi_doc() -> Dict[str, Any]:
    return {
        "document": {
            "id": "23856",
            "cuid": "AYkR0J_v6mRFsKzZt7LqM2I",
            "name": "Quarterly Sales Report",
            "folderId": "1001",
            "path": "Corporate Documents/Finance",
            "scheduled": "false",
            "state": "Unused",
        }
    }


@pytest.fixture
def sample_mapping_proposal() -> Dict[str, Any]:
    return {
        "mappings": {
            "content": {
                "mapping": [
                    {
                        "@status": "Ok",
                        "source": {"id": "OBJ_147"},
                        "target": {"id": "OBJ_147"},
                    },
                    {
                        "@status": "Ok",
                        "source": {"id": "OBJ_188"},
                        "target": {"id": "OBJ_188"},
                    },
                ]
            }
        }
    }
