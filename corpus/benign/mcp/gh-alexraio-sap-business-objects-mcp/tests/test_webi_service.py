"""
Unit tests for WebiService in services/webi_service.py.
"""

from unittest.mock import MagicMock

import pytest

from core.exceptions import BOEError
from services.webi_service import WebiService


class TestWebiServiceDocuments:
    def test_get_documents_success(self, webi_service: WebiService, mock_client: MagicMock):
        mock_client.get.return_value = {
            "documents": {
                "document": [
                    {"id": "100", "cuid": "C100", "name": "Report 1", "folderId": "10", "updated": "2026-01-01"},
                    {"id": "101", "cuid": "C101", "name": "Report 2", "folderId": "10", "updated": "2026-01-02"},
                ]
            }
        }
        docs = webi_service.get_documents(page=1, pagesize=10)
        assert len(docs) == 2
        assert docs[0]["id"] == "100"
        assert docs[0]["name"] == "Report 1"
        mock_client.get.assert_called_once_with(f"{mock_client.webi_url}/documents?page=1&pagesize=10")

    def test_get_documents_empty(self, webi_service: WebiService, mock_client: MagicMock):
        mock_client.get.return_value = {}
        docs = webi_service.get_documents()
        assert docs == []

    def test_get_doc_details_success(self, webi_service: WebiService, mock_client: MagicMock, sample_webi_doc):
        mock_client.get.return_value = sample_webi_doc
        details = webi_service.get_doc_details("23856")
        assert details["webi_doc_id"] == "23856"
        assert details["webi_doc_name"] == "Quarterly Sales Report"
        assert details["webi_doc_cuid"] == "AYkR0J_v6mRFsKzZt7LqM2I"

    def test_get_doc_details_not_found(self, webi_service: WebiService, mock_client: MagicMock):
        mock_client.get.return_value = {}
        with pytest.raises(BOEError) as exc:
            webi_service.get_doc_details("99999")
        assert "Unable to read document details" in str(exc.value)

    def test_save_webi_doc_in_place(self, webi_service: WebiService, mock_client: MagicMock):
        mock_client.put.return_value = {"success": {"message": "Document updated"}}
        res = webi_service.save_webi_doc("23856")
        assert "in place" in res
        mock_client.put.assert_called_once_with(f"{mock_client.webi_url}/documents/23856")

    def test_save_webi_doc_save_as(self, webi_service: WebiService, mock_client: MagicMock):
        mock_client.post.return_value = {"success": {"message": "Document saved"}}
        res = webi_service.save_webi_doc("23856", webi_doc_name="New Name", folder_id=500)
        assert "New Name" in res
        mock_client.post.assert_called_once()


class TestWebiServicePrompts:
    def test_get_doc_parameters(self, webi_service: WebiService, mock_client: MagicMock):
        mock_client.get.return_value = {
            "parameters": {
                "parameter": [
                    {"id": 0, "name": "Enter Year:", "technicalName": "Year", "type": "String", "optional": False},
                ]
            }
        }
        params = webi_service.get_doc_parameters("23856")
        assert len(params) == 1
        assert params[0]["name"] == "Enter Year:"
        assert params[0]["optional"] is False

    def test_refresh_webi_doc_with_answers(self, webi_service: WebiService, mock_client: MagicMock):
        mock_client.put.return_value = {"success": {"message": "Refreshed"}}
        res = webi_service.refresh_webi_doc("23856", parameters=[{"id": 0, "value": "2026"}])
        assert res["status"] == "refreshed"
        mock_client.put.assert_called_once()


class TestWebiServiceDataProviders:
    def test_get_dp(self, webi_service: WebiService, mock_client: MagicMock):
        mock_client.get.return_value = {"dataproviders": {"dataprovider": [{"id": "DP0"}, {"id": "DP1"}]}}
        dps = webi_service.get_dp("23856")
        assert dps == ["DP0", "DP1"]

    def test_get_dp_sql(self, webi_service: WebiService, mock_client: MagicMock):
        mock_client.get.return_value = {"queryplan": {"statement": {"$": "SELECT Year, Sales FROM Table"}}}
        sql = webi_service.get_dp_sql("23856", "DP0")
        assert "SELECT Year, Sales" in sql

    def test_get_dp_specification_xml_header(self, webi_service: WebiService, mock_client: MagicMock):
        mock_client.get.return_value = "<queryspec>XML Data</queryspec>"
        spec = webi_service.get_dp_specification("23856", "DP0")
        assert spec == {"raw": "<queryspec>XML Data</queryspec>"}
        # Ensure Accept: text/xml is sent
        mock_client.get.assert_called_once_with(
            f"{mock_client.webi_url}/documents/23856/dataproviders/DP0/specification",
            headers={"Accept": "text/xml"},
        )


class TestWebiServiceChangeDataSource:
    def test_get_dp_mapping_proposal(self, webi_service: WebiService, mock_client: MagicMock, sample_mapping_proposal):
        mock_client.get.return_value = sample_mapping_proposal
        proposal = webi_service.get_dp_mapping_proposal(
            webi_doc_id="23856",
            dp_id="DP0",
            target_datasource_id="55037",
            strategies="SameID,SamePath,SameName",
            resolve_names=False,
        )
        assert proposal["summary"]["total_objects"] == 2
        assert proposal["summary"]["mapped_ok"] == 2
        assert proposal["summary"]["all_mapped"] is True
        assert proposal["summary"]["match_rate_percentage"] == 100.0

    def test_change_dp_datasource_with_custom_mapping(
        self, webi_service: WebiService, mock_client: MagicMock, sample_mapping_proposal
    ):
        # Proposal get
        mock_client.get.return_value = sample_mapping_proposal
        # Post mappings
        mock_client.post.return_value = {"success": {"message": "Document updated", "id": "23856"}}
        # Details check
        webi_service.get_dp_details = MagicMock(return_value={"id": "DP0", "dataSourceId": "55037"})
        # In-place save
        webi_service.save_webi_doc = MagicMock(return_value="Saved")

        result = webi_service.change_dp_datasource(
            webi_doc_id="23856",
            dp_id="DP0",
            target_datasource_id="55037",
            custom_mappings=[{"source_id": "OBJ_147", "target_id": "OBJ_OVERRIDE"}],
            save=True,
        )
        assert result["status"] == "success"
        assert result["save_status"] == "saved_in_place"
        mock_client.post.assert_called_once()
