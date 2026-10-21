"""
Schedule and Instance Monitoring Service for SAP BusinessObjects 4.3 SP5.
Handles scheduled executions, report instance histories, and execution failure diagnostics.
"""

import logging
from typing import Any, Dict, List

from core.client import BOEClient
from core.exceptions import BOEError

logger = logging.getLogger("ScheduleService")


class ScheduleService:
    """Service to inspect, trigger, and diagnose report schedules and execution instances."""

    STATUS_MAP = {
        0: "Running",
        1: "Success",
        2: "Recurring",
        3: "Failed",
        8: "Paused",
        9: "Pending",
    }

    def __init__(self, client: BOEClient):
        self.client = client

    def get_doc_schedules(self, webi_doc_id: str) -> List[Dict[str, Any]]:
        """
        Retrieves scheduled execution rules defined on a Web Intelligence report.
        """
        url = f"{self.client.webi_url}/documents/{webi_doc_id}/schedules"
        try:
            resp = self.client.get(url)
            schedules: List[Dict[str, Any]] = []
            if isinstance(resp, dict) and "schedules" in resp:
                raw_sched = resp["schedules"].get("schedule", [])
                if isinstance(raw_sched, dict):
                    raw_sched = [raw_sched]
                for s in raw_sched:
                    schedules.append(
                        {
                            "id": str(s.get("id", "")),
                            "name": str(s.get("name", "")),
                            "status": str(s.get("status", "")),
                        }
                    )
            return schedules
        except Exception:
            return []

    def get_doc_instances(self, webi_doc_id: str, max_instances: int = 50) -> List[Dict[str, Any]]:
        """
        Retrieves the historical execution instances of a Webi document (Success, Failed, Running).
        """
        query = (
            f"SELECT TOP {max_instances} SI_ID, SI_NAME, SI_STARTTIME, SI_ENDTIME, "
            f"SI_SCHEDULE_STATUS, SI_STATUSINFO FROM CI_INFOOBJECTS "
            f"WHERE SI_PARENTID = {webi_doc_id} AND SI_INSTANCE = 1 ORDER BY SI_STARTTIME DESC"
        )
        url = f"{self.client.query_url}/cmsquery?page=1&pagesize={max_instances}"
        resp = self.client.post(url, json_data={"query": query})
        instances: List[Dict[str, Any]] = []

        if isinstance(resp, dict) and resp.get("entries"):
            for entry in resp["entries"]:
                status_code = entry.get("SI_SCHEDULE_STATUS", -1)
                status_str = self.STATUS_MAP.get(status_code, f"Status_{status_code}")
                instances.append(
                    {
                        "instance_id": str(entry.get("SI_ID", "")),
                        "name": str(entry.get("SI_NAME", "")),
                        "start_time": str(entry.get("SI_STARTTIME", "")),
                        "end_time": str(entry.get("SI_ENDTIME", "")),
                        "status_code": status_code,
                        "status": status_str,
                        "status_info": str(entry.get("SI_STATUSINFO", "")),
                    }
                )
        return instances

    def get_instance_details(self, instance_id: str) -> Dict[str, Any]:
        """
        Retrieves detailed diagnostic information for a specific execution instance,
        including failure error messages and parameter values.
        """
        query = f"SELECT * FROM CI_INFOOBJECTS WHERE SI_ID = {instance_id} AND SI_INSTANCE = 1"
        url = f"{self.client.query_url}/cmsquery?page=1&pagesize=1"
        resp = self.client.post(url, json_data={"query": query})

        if isinstance(resp, dict) and resp.get("entries"):
            entry = resp["entries"][0]
            status_code = entry.get("SI_SCHEDULE_STATUS", -1)
            return {
                "instance_id": str(entry.get("SI_ID", instance_id)),
                "name": str(entry.get("SI_NAME", "")),
                "parent_doc_id": str(entry.get("SI_PARENTID", "")),
                "start_time": str(entry.get("SI_STARTTIME", "")),
                "end_time": str(entry.get("SI_ENDTIME", "")),
                "status": self.STATUS_MAP.get(status_code, f"Status_{status_code}"),
                "error_message": str(entry.get("SI_STATUSINFO", "")),
                "format": str(entry.get("SI_FORMAT", "")),
                "file_size": entry.get("SI_FILE_SIZE"),
            }
        raise BOEError(f"Instance ID {instance_id} not found.")

    def delete_instance(self, instance_id: str) -> bool:
        """
        Deletes a report execution instance from the CMS repository.
        """
        url = f"{self.client.bip_url}/infostore/{instance_id}"
        self.client.delete(url)
        return True
