"""
------------------------------------------------------
NAME:        BOESDKParser
DESCRIPTION: Unified Facade to manage connections to SAP BusinessObjects 4.3 SP5
             and orchestrate Web Intelligence, Semantic Layer, CMS Admin,
             and InfoStore domain services.
AUTHOR:      Ballarin, Alessio
VERSION:     0.2 (Modular Domain Architecture)
------------------------------------------------------
"""

from typing import Any, Dict, List, Optional, Tuple, Union

from core.client import BOEClient
from core.exceptions import (
    BOEProcessingError,
)
from services.admin_service import AdminService
from services.infostore_service import InfostoreService
from services.schedule_service import ScheduleService
from services.universe_service import UniverseService
from services.webi_service import WebiService


class BOESDKParser:
    """
    Unified Facade providing access to all SAP BusinessObjects BI Platform 4.3 SP5 REST capabilities.
    Delegates to modular domain services while maintaining 100% backward compatibility.
    """

    def __init__(
        self,
        protocol: str = "http",
        host: str = "localhost",
        port: str = "8080",
        content_type: str = "application/json",
        base_url: Optional[str] = None,
        timeout: int = 120,
    ):
        self.client = BOEClient(
            base_url=base_url,
            protocol=protocol,
            host=host,
            port=port,
            content_type=content_type,
            timeout=timeout,
        )

        # Domain Services
        self.webi = WebiService(self.client)
        self.universe = UniverseService(self.client)
        self.schedule = ScheduleService(self.client)
        self.admin = AdminService(self.client)
        self.infostore = InfostoreService(self.client)

    # =========================================================================
    # Compatibility Properties
    # =========================================================================

    @property
    def bip_url(self) -> str:
        return self.client.bip_url

    @property
    def webi_url(self) -> str:
        return self.client.webi_url

    @property
    def sl_url(self) -> str:
        return self.client.sl_url

    @property
    def query_url(self) -> str:
        return self.client.query_url

    @property
    def headers(self) -> Dict[str, str]:
        return self.client.headers

    @property
    def session(self):
        return self.client.session

    @property
    def logon_token(self) -> Optional[str]:
        return self.client.logon_token

    # =========================================================================
    # Authentication & Session
    # =========================================================================

    def set_logon_token(self, username: str, password: str) -> str:
        """Authenticates with username and password, storing logonToken."""
        return self.client.set_logon_token(username, password)

    def set_trusted_token(self, username: str = "Administrator") -> str:
        """Authenticates using trusted principal token."""
        return self.client.set_trusted_token(username)

    def bo_logoff(self) -> bool:
        """Logs off and closes the session."""
        return self.client.bo_logoff()

    # =========================================================================
    # Universes & Semantic Layer
    # =========================================================================

    def get_universes(self) -> List[Dict[str, Any]]:
        """Retrieves list of all universes (id, name, folderId)."""
        # Kept matching old key names {'u_id', 'u_name', 'u_folderid'} for backward compatibility
        res = self.universe.get_universes()
        return [{"u_id": u["id"], "u_name": u["name"], "u_folderid": u["folderId"]} for u in res]

    def get_univ_details(self, universe_id: str) -> Dict[str, str]:
        """Retrieves details of a universe (u_type, u_name, u_cuid)."""
        return self.universe.get_universe_details(universe_id)

    def get_universe_structure(self, universe_id: str) -> Dict[str, Any]:
        """Retrieves full semantic layer tree of a universe."""
        return self.universe.get_universe_structure(universe_id)

    def get_universe_related_reports(self, universe_id: str) -> Tuple[str, str, List[str]]:
        """Gets reports related to a UNX or UNV universe."""
        data = self.universe.get_universe_related_reports(universe_id)
        return data["universe_id"], data["universe_name"], data["reports"]

    def get_univ_related_conn_id(self, universe_id: str) -> Optional[str]:
        """Gets data connection ID for a universe."""
        return self.universe.get_univ_related_conn_id(universe_id)

    # =========================================================================
    # InfoStore & Folders
    # =========================================================================

    def get_folders(self, folder_id: str, folder_list: Optional[List[str]] = None) -> List[str]:
        """Recursively retrieves folder IDs."""
        return self.infostore.get_folders(folder_id, recursive=True, folder_list=folder_list)

    def get_webi_docs(self, folder_id: str, webi_list: Optional[List[str]] = None) -> List[str]:
        """Gets all Webi document IDs in a folder."""
        res = self.infostore.get_webi_docs(folder_id)
        if webi_list is not None:
            webi_list.extend(res)
            return webi_list
        return res

    def get_folder_details(self, folder_id: str) -> Dict[str, Any]:
        """Gets folder metadata."""
        return self.infostore.get_folder_details(folder_id)

    def get_categories(self) -> List[Dict[str, str]]:
        """Lists corporate categories."""
        return self.infostore.get_categories()

    # =========================================================================
    # Web Intelligence Documents, Prompts, Data & Lifecycle
    # =========================================================================

    def get_documents(self, page: int = 1, pagesize: int = 50) -> List[Dict[str, Any]]:
        """Lists Webi documents."""
        return self.webi.get_documents(page=page, pagesize=pagesize)

    def get_doc_details(self, webi_doc_id: str) -> Optional[Dict[str, Any]]:
        """Gets document info (name, path, cuid, scheduled, state)."""
        try:
            return self.webi.get_doc_details(webi_doc_id)
        except Exception:
            return None

    def get_doc_status(self, webi_doc_id: str) -> Optional[Union[Dict[str, str], str]]:
        """Gets document status with WSR 00999 trapping."""
        try:
            details = self.webi.get_doc_details(webi_doc_id)
            return {"webi_doc_state": details["webi_doc_state"]}
        except BOEProcessingError:
            return "WSR 00999"
        except Exception:
            return None

    def save_webi_doc(
        self, webi_doc_id: str, webi_doc_name: Optional[str] = None, folder_id: Optional[int] = None
    ) -> str:
        """Saves a Webi document in place, or saves it with a new name/folder (Save As)."""
        return self.webi.save_webi_doc(webi_doc_id, webi_doc_name=webi_doc_name, folder_id=folder_id)

    def delete_webi_doc(self, webi_doc_id: str) -> bool:
        """Deletes a Webi document."""
        try:
            return self.webi.delete_webi_doc(webi_doc_id)
        except Exception:
            return False

    def get_doc_parameters(self, webi_doc_id: str) -> List[Dict[str, Any]]:
        """Retrieves prompt parameters required by a document."""
        return self.webi.get_doc_parameters(webi_doc_id)

    def get_parameter_lov(self, webi_doc_id: str, parameter_id: Union[int, str]) -> List[Any]:
        """Gets List of Values (LOV) for a prompt."""
        return self.webi.get_parameter_lov(webi_doc_id, parameter_id)

    def refresh_webi_doc(self, webi_doc_id: str, parameters: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Refreshes a Webi report, answering prompts if provided."""
        return self.webi.refresh_webi_doc(webi_doc_id, parameters)

    def get_reports(self, webi_doc_id: str) -> List[Dict[str, Any]]:
        """Lists sheets/tabs in a document."""
        return self.webi.get_reports(webi_doc_id)

    def get_report_elements(self, webi_doc_id: str, report_id: str) -> List[Dict[str, Any]]:
        """Lists blocks/tables in a report tab."""
        return self.webi.get_report_elements(webi_doc_id, report_id)

    def get_report_element_data(
        self, webi_doc_id: str, report_id: str, element_id: str, max_rows: int = 1000
    ) -> Dict[str, Any]:
        """Extracts tabular cell data from a table/chart block."""
        return self.webi.get_report_element_data(webi_doc_id, report_id, element_id, max_rows=max_rows)

    def get_variables(self, webi_doc_id: str) -> List[Dict[str, Any]]:
        """Lists calculated variables/formulas in a document."""
        return self.webi.get_variables(webi_doc_id)

    def get_comments(self, webi_doc_id: str) -> List[Dict[str, Any]]:
        """Lists user comments in a document."""
        return self.webi.get_comments(webi_doc_id)

    # =========================================================================
    # Data Providers
    # =========================================================================

    def get_dp(self, webi_doc_id: str) -> List[str]:
        """Gets Data Provider IDs."""
        return self.webi.get_dp(webi_doc_id)

    def get_dp_details(self, webi_doc_id: str, dp_id: str) -> Optional[Dict[str, str]]:
        """Gets details of a specific Data Provider."""
        try:
            return self.webi.get_dp_details(webi_doc_id, dp_id)
        except Exception:
            return None

    def get_dp_sql(self, webi_doc_id: str, dp_id: str) -> str:
        """Extracts generated SQL of a Data Provider."""
        return self.webi.get_dp_sql(webi_doc_id, dp_id)

    def refresh_dp(self, webi_doc_id: str, dp_id: str) -> str:
        """Refreshes a single Data Provider."""
        return self.webi.refresh_dp(webi_doc_id, dp_id)

    def get_dp_specification(self, webi_doc_id: str, dp_id: str) -> Dict[str, Any]:
        """Retrieves query specification (objects, filters, sorting) of a Data Provider."""
        return self.webi.get_dp_specification(webi_doc_id, dp_id)

    def get_dp_mapping_proposal(
        self,
        webi_doc_id: str,
        dp_id: str,
        target_datasource_id: str,
        strategies: Optional[Union[List[str], str]] = None,
        resolve_names: bool = True,
    ) -> Dict[str, Any]:
        """
        Generates and analyzes a Change Data Source mapping proposal with strategy evaluation
        and human-readable object names.
        """
        return self.webi.get_dp_mapping_proposal(
            webi_doc_id=webi_doc_id,
            dp_id=dp_id,
            target_datasource_id=target_datasource_id,
            strategies=strategies,
            resolve_names=resolve_names,
        )

    def change_dp_datasource(
        self,
        webi_doc_id: str,
        dp_id: str,
        target_datasource_id: str,
        strategies: Optional[Union[List[str], str]] = None,
        custom_mappings: Optional[List[Dict[str, str]]] = None,
        save: bool = True,
    ) -> Dict[str, Any]:
        """
        Executes Change Data Source on a Data Provider (UNV->UNX or repointing),
        applying strategy matching, custom overrides, and persistence.
        """
        return self.webi.change_dp_datasource(
            webi_doc_id=webi_doc_id,
            dp_id=dp_id,
            target_datasource_id=target_datasource_id,
            strategies=strategies,
            custom_mappings=custom_mappings,
            save=save,
        )

    def purge_dp(self, webi_doc_id: str, dp_id: str) -> bool:
        """Purges cached data from a Data Provider."""
        try:
            return self.webi.purge_dp(webi_doc_id, dp_id)
        except Exception:
            return False

    # =========================================================================
    # CMS Administration & Security
    # =========================================================================

    def cms_query(self, query: str, page: int = 1, pagesize: int = 1000) -> Dict[str, Any]:
        """Executes a CMS SQL query."""
        return self.admin.cms_query(query, page=page, pagesize=pagesize)

    def get_users(self, page: int = 1, pagesize: int = 100) -> List[Dict[str, Any]]:
        """Lists user accounts."""
        return self.admin.get_users(page=page, pagesize=pagesize)

    def get_user_details(self, user_id: str) -> Dict[str, Any]:
        """Gets user properties."""
        return self.admin.get_user_details(user_id)

    def set_user_status(self, user_id: str, disabled: bool) -> str:
        """Enables or disables a user account."""
        return self.admin.set_user_status(user_id, disabled)

    def get_user_groups(self, page: int = 1, pagesize: int = 100) -> List[Dict[str, Any]]:
        """Lists user groups."""
        return self.admin.get_user_groups(page=page, pagesize=pagesize)

    def get_group_users(self, group_id: str) -> List[Dict[str, str]]:
        """Lists members of a group."""
        return self.admin.get_group_users(group_id)

    def get_active_sessions(self) -> List[Dict[str, Any]]:
        """Lists active CMS connections."""
        return self.admin.get_active_sessions()

    def terminate_session(self, session_id: str) -> str:
        """Terminates an active session."""
        return self.admin.terminate_session(session_id)

    # =========================================================================
    # Schedules & Instances
    # =========================================================================

    def get_doc_schedules(self, webi_doc_id: str) -> List[Dict[str, Any]]:
        """Lists schedules of a document."""
        return self.schedule.get_doc_schedules(webi_doc_id)

    def get_doc_instances(self, webi_doc_id: str, max_instances: int = 50) -> List[Dict[str, Any]]:
        """Lists instance run history."""
        return self.schedule.get_doc_instances(webi_doc_id, max_instances=max_instances)

    def get_instance_details(self, instance_id: str) -> Dict[str, Any]:
        """Gets diagnostics and error message of an instance."""
        return self.schedule.get_instance_details(instance_id)

    def delete_instance(self, instance_id: str) -> bool:
        """Deletes an execution instance."""
        return self.schedule.delete_instance(instance_id)
