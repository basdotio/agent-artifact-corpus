"""
Universe and Semantic Layer service for SAP BusinessObjects 4.3 SP5.
Handles universe discovery, semantic hierarchy traversal, and report-universe lineage.
"""

from typing import Any, Dict, List, Optional

from core.client import BOEClient
from core.exceptions import BOEError


class UniverseService:
    """Service to interact with Universes (UNX and UNV) and the Semantic Layer."""

    def __init__(self, client: BOEClient):
        self.client = client

    def get_universes(self) -> List[Dict[str, str]]:
        """
        Retrieves all universes published to the BI platform.
        Returns a list of dictionaries containing 'id', 'name', and 'folderId'.
        """
        url = f"{self.client.webi_url}/universes"
        resp = self.client.get(url)
        if isinstance(resp, dict) and "universes" in resp:
            univ_list = resp["universes"].get("universe", [])
            # If single universe returned as dict instead of list
            if isinstance(univ_list, dict):
                univ_list = [univ_list]
            return [
                {
                    "id": str(u.get("id", "")),
                    "name": str(u.get("name", "")),
                    "folderId": str(u.get("folderId", "")),
                }
                for u in univ_list
            ]
        return []

    def get_universe_details(self, universe_id: str) -> Dict[str, str]:
        """
        Retrieves detailed metadata for a specific universe (type, name, CUID).
        """
        url = f"{self.client.webi_url}/universes/{universe_id}"
        resp = self.client.get(url)
        if isinstance(resp, dict) and "universe" in resp:
            u_data = resp["universe"]
            return {
                "u_type": str(u_data.get("type", "")).lower(),
                "u_name": str(u_data.get("name", "")),
                "u_cuid": str(u_data.get("cuid", "")),
            }
        raise BOEError(f"Could not parse universe details for ID {universe_id}")

    def get_universe_structure(self, universe_id: str) -> Dict[str, Any]:
        """
        Retrieves the business layer structure (classes, dimensions, measures, attributes)
        using the Semantic Layer REST API (/sl/v1/universes/{id}).
        """
        url = f"{self.client.sl_url}/universes/{universe_id}"
        resp = self.client.get(url)
        if isinstance(resp, dict):
            # Return parsed semantic layer structure
            return resp
        return {"raw": resp}

    def get_universe_related_reports(self, universe_id: str) -> Dict[str, Any]:
        """
        Queries the Central Management Server (CMS) to find all Web Intelligence
        reports referencing this universe (UNX or UNV).
        """
        details = self.get_universe_details(universe_id)
        u_type = details["u_type"]

        url = f"{self.client.query_url}/cmsquery?page=1&pagesize=50000"
        if u_type == "unx":
            payload = {
                "query": f"SELECT TOP 50000 SI_ID, SI_NAME, SI_SL_DOCUMENTS FROM CI_APPOBJECTS WHERE SI_KIND = 'DSL.MetaDataFile' AND SI_ID = {universe_id}"
            }
            report_field = "SI_SL_DOCUMENTS"
        elif u_type == "unv":
            payload = {
                "query": f"SELECT TOP 50000 SI_ID, SI_NAME, SI_WEBI FROM CI_APPOBJECTS WHERE SI_KIND = 'Universe' AND SI_ID = {universe_id}"
            }
            report_field = "SI_WEBI"
        else:
            raise BOEError(f"Unsupported universe type: '{u_type}' for universe ID {universe_id}")

        resp = self.client.post(url, json_data=payload)
        if isinstance(resp, dict) and resp.get("entries"):
            entry = resp["entries"][0]
            raw_reports = entry.get(report_field, {})
            report_ids = [val for key, val in raw_reports.items() if key != "SI_TOTAL"]
            return {
                "universe_id": str(entry.get("SI_ID", universe_id)),
                "universe_name": str(entry.get("SI_NAME", details["u_name"])),
                "universe_type": u_type,
                "reports_count": len(report_ids),
                "reports": report_ids,
            }
        return {
            "universe_id": str(universe_id),
            "universe_name": details.get("u_name", ""),
            "universe_type": u_type,
            "reports_count": 0,
            "reports": [],
        }

    def get_univ_related_conn_id(self, universe_id: str) -> Optional[str]:
        """
        Retrieves the Data Connection ID bound to a universe.
        """
        url = f"{self.client.query_url}/cmsquery?page=1&pagesize=50000"
        payload = {
            "query": f"SELECT SI_NAME, SI_SPECIFIC_KIND, SI_DATACONNECTION FROM CI_APPOBJECTS, CI_INFOOBJECTS WHERE SI_ID = {universe_id}"
        }
        resp = self.client.post(url, json_data=payload)
        if isinstance(resp, dict) and resp.get("entries"):
            entry = resp["entries"][0]
            conn_data = entry.get("SI_DATACONNECTION", {})
            if isinstance(conn_data, dict) and "1" in conn_data:
                return str(conn_data["1"])
        return None
