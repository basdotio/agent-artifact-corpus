"""
Unit tests for UniverseService in services/universe_service.py.
"""

from unittest.mock import MagicMock

import pytest

from core.exceptions import BOEError
from services.universe_service import UniverseService


class TestUniverseService:
    def test_get_universes(self, universe_service: UniverseService, mock_client: MagicMock):
        mock_client.get.return_value = {
            "universes": {
                "universe": [
                    {"id": "5508", "name": "eFashion.unx", "folderId": "5511"},
                    {"id": "5518", "name": "Rio2016.unx", "folderId": "5511"},
                ]
            }
        }
        res = universe_service.get_universes()
        assert len(res) == 2
        assert res[0]["name"] == "eFashion.unx"
        mock_client.get.assert_called_once_with(f"{mock_client.webi_url}/universes")

    def test_get_universe_details_unx(self, universe_service: UniverseService, mock_client: MagicMock):
        mock_client.get.return_value = {
            "universe": {
                "id": "5508",
                "name": "eFashion",
                "type": "unx",
                "cuid": "AYkR0J_v6mR",
            }
        }
        details = universe_service.get_universe_details("5508")
        assert details["u_type"] == "unx"
        assert details["u_name"] == "eFashion"
        assert details["u_cuid"] == "AYkR0J_v6mR"

    def test_get_universe_details_error(self, universe_service: UniverseService, mock_client: MagicMock):
        mock_client.get.return_value = {}
        with pytest.raises(BOEError) as exc:
            universe_service.get_universe_details("9999")
        assert "Could not parse universe details" in str(exc.value)

    def test_get_universe_structure(self, universe_service: UniverseService, mock_client: MagicMock):
        mock_client.get.return_value = {"universe": {"outline": {"folder": [{"name": "Measures"}]}}}
        struct = universe_service.get_universe_structure("5508")
        assert "universe" in struct

    def test_get_universe_related_reports_unx(self, universe_service: UniverseService, mock_client: MagicMock):
        universe_service.get_universe_details = MagicMock(
            return_value={"u_name": "eFashion.unx", "u_type": "unx", "u_cuid": "CUID1"}
        )
        mock_client.post.return_value = {
            "entries": [
                {
                    "SI_ID": 5508,
                    "SI_NAME": "eFashion.unx",
                    "SI_SL_DOCUMENTS": {
                        "SI_TOTAL": 2,
                        "1": 23856,
                        "2": 5503,
                    },
                }
            ]
        }
        res = universe_service.get_universe_related_reports("5508")
        assert res["universe_id"] == "5508"
        assert res["reports_count"] == 2
        assert res["reports"] == [23856, 5503]

    def test_get_univ_related_conn_id(self, universe_service: UniverseService, mock_client: MagicMock):
        mock_client.post.return_value = {"entries": [{"SI_DATACONNECTION": {"1": 6001}}]}
        conn_id = universe_service.get_univ_related_conn_id("5508")
        assert conn_id == "6001"
