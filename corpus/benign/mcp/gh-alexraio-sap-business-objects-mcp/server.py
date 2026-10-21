import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from fastmcp import FastMCP

from sdk_parser_new import BOESDKParser

# Load environment variables relative to this script directory
load_dotenv(Path(__file__).parent / ".env")

# Initialize FastMCP Server
mcp = FastMCP("SAP Business Objects")

# Parse configuration
api_url = os.getenv("SAP_BO_REST_API_URL")
username_env = os.getenv("SAP_BO_USERNAME")
password_env = os.getenv("SAP_BO_PASSWORD")

# Initialize parser instance
parser = BOESDKParser(base_url=api_url) if api_url else BOESDKParser()


# =============================================================================
# 1. Authentication Tools
# =============================================================================


@mcp.tool()
def login(username: Optional[str] = None, password: Optional[str] = None) -> str:
    """
    Log in to the SAP BusinessObjects BI Platform.
    Establishes an active enterprise session and acquires a logon token (X-SAP-LogonToken).
    If username/password are omitted, values from .env are used automatically.
    """
    user = username or username_env
    pwd = password or password_env

    if not user or not pwd:
        return "Login failed: Missing credentials. Provide username/password or configure SAP_BO_USERNAME and SAP_BO_PASSWORD in .env"

    try:
        parser.set_logon_token(user, pwd)
        return f"Login successful for user '{user}'"
    except Exception as e:
        return f"Login failed: {str(e)}"


@mcp.tool()
def logout() -> str:
    """
    Log out from the SAP BusinessObjects platform and invalidate the active session token.
    """
    try:
        parser.bo_logoff()
        return "Logout successful"
    except Exception as e:
        return f"Logout failed: {str(e)}"


# =============================================================================
# 2. Semantic Layer & Universes
# =============================================================================


@mcp.tool()
def get_universes() -> List[Dict[str, str]]:
    """
    Retrieves all published Universes (UNX and UNV) from the BI platform.
    Returns a list of objects containing 'id', 'name', and 'folderId'.
    """
    try:
        universes = parser.get_universes()
        return [
            {
                "id": str(u["u_id"]),
                "name": str(u["u_name"]),
                "folderId": str(u["u_folderid"]),
            }
            for u in universes
        ]
    except Exception as e:
        raise RuntimeError(f"Failed to get universes: {str(e)}")


@mcp.tool()
def get_universe_details(universe_id: str) -> Dict[str, str]:
    """
    Retrieves detailed metadata of a specific Universe (engine type: 'unx' or 'unv', name, CUID).
    """
    try:
        return parser.get_univ_details(universe_id)
    except Exception as e:
        raise RuntimeError(f"Failed to get universe details for ID {universe_id}: {str(e)}")


@mcp.tool()
def get_universe_structure(universe_id: str) -> Dict[str, Any]:
    """
    Retrieves the complete business layer hierarchy (classes, dimensions, measures, attributes)
    of a universe using the Semantic Layer REST API (/sl/v1/universes/{id}).
    """
    try:
        return parser.get_universe_structure(universe_id)
    except Exception as e:
        raise RuntimeError(f"Failed to get universe structure: {str(e)}")


@mcp.tool()
def get_universe_related_reports(universe_id: str) -> Dict[str, Any]:
    """
    Queries the CMS to discover all Web Intelligence reports built on top of a specific universe.
    Returns universe ID, name, universe type, and the list of related Webi report IDs.
    """
    try:
        u_id, u_name, reports = parser.get_universe_related_reports(universe_id)
        return {
            "universe_id": u_id,
            "universe_name": u_name,
            "total_reports": len(reports),
            "reports": reports,
        }
    except Exception as e:
        raise RuntimeError(f"Failed to get related reports: {str(e)}")


@mcp.tool()
def get_universe_connection_id(universe_id: str) -> Optional[str]:
    """
    Retrieves the Data Connection ID associated with a Universe.
    """
    try:
        return parser.get_univ_related_conn_id(universe_id)
    except Exception as e:
        raise RuntimeError(f"Failed to get connection ID: {str(e)}")


# =============================================================================
# 3. Web Intelligence Documents & Lifecycle
# =============================================================================


@mcp.tool()
def get_documents(page: int = 1, pagesize: int = 50) -> List[Dict[str, Any]]:
    """
    Retrieves a paginated list of Web Intelligence documents from the repository.
    Returns document ID, CUID, name, folder ID, and last updated timestamp.
    """
    try:
        return parser.get_documents(page=page, pagesize=pagesize)
    except Exception as e:
        raise RuntimeError(f"Failed to list documents: {str(e)}")


@mcp.tool()
def get_doc_details(webi_doc_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieves metadata of a Webi report (name, repository folder path, CUID, scheduled status, and state).
    """
    try:
        return parser.get_doc_details(webi_doc_id)
    except Exception as e:
        raise RuntimeError(f"Failed to get doc details for {webi_doc_id}: {str(e)}")


@mcp.tool()
def get_doc_properties(webi_doc_id: str) -> Dict[str, Any]:
    """
    Retrieves document configuration properties (refreshOnOpen, usePersonalData, formatting locale).
    """
    try:
        return parser.webi.get_doc_properties(webi_doc_id)
    except Exception as e:
        raise RuntimeError(f"Failed to get doc properties: {str(e)}")


@mcp.tool()
def save_webi_doc(webi_doc_id: str, webi_doc_name: Optional[str] = None) -> str:
    """
    Saves a Web Intelligence document in place (if webi_doc_name is omitted),
    or saves/overwrites it with a specified name (Save As). Preserves user comments and annotations.
    """
    try:
        return parser.save_webi_doc(webi_doc_id, webi_doc_name)
    except Exception as e:
        return f"Error saving document: {str(e)}"


@mcp.tool()
def delete_webi_doc(webi_doc_id: str) -> str:
    """
    Permanently deletes a Web Intelligence document from the repository.
    """
    try:
        success = parser.delete_webi_doc(webi_doc_id)
        if success:
            return f"Successfully deleted document {webi_doc_id}"
        return f"Failed to delete document {webi_doc_id}"
    except Exception as e:
        return f"Error deleting document: {str(e)}"


# =============================================================================
# 4. Webi Prompts, Parameters & Refresh
# =============================================================================


@mcp.tool()
def get_doc_parameters(webi_doc_id: str) -> List[Dict[str, Any]]:
    """
    Retrieves all prompt parameters required by a Web Intelligence report.
    Returns parameter ID, prompt question/name, technical name, data type, and whether it is mandatory or optional.
    """
    try:
        return parser.get_doc_parameters(webi_doc_id)
    except Exception as e:
        raise RuntimeError(f"Failed to get doc parameters for {webi_doc_id}: {str(e)}")


@mcp.tool()
def get_parameter_lov(webi_doc_id: str, parameter_id: int) -> List[Any]:
    """
    Retrieves the List of Values (LOV) allowed for a constrained prompt parameter in a Webi document.
    """
    try:
        return parser.get_parameter_lov(webi_doc_id, parameter_id)
    except Exception as e:
        raise RuntimeError(f"Failed to get LOV for parameter {parameter_id}: {str(e)}")


@mcp.tool()
def refresh_webi_doc(webi_doc_id: str, parameters: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """
    Refreshes a Web Intelligence document. If the report requires prompts, answers can be passed
    as a list of objects, e.g. [{"id": 0, "value": "2026"}, {"id": 1, "value": ["Region A", "Region B"]}].
    """
    try:
        return parser.refresh_webi_doc(webi_doc_id, parameters)
    except Exception as e:
        raise RuntimeError(f"Failed to refresh document {webi_doc_id}: {str(e)}")


# =============================================================================
# 5. Webi Tabs, Blocks & Tabular Data Extraction
# =============================================================================


@mcp.tool()
def get_reports(webi_doc_id: str) -> List[Dict[str, Any]]:
    """
    Lists all sheets/tabs in a Web Intelligence document (returns report IDs and tab names).
    """
    try:
        return parser.get_reports(webi_doc_id)
    except Exception as e:
        raise RuntimeError(f"Failed to get reports for {webi_doc_id}: {str(e)}")


@mcp.tool()
def get_report_elements(webi_doc_id: str, report_id: str) -> List[Dict[str, Any]]:
    """
    Lists all visual and data elements (tables, charts, sections) inside a report sheet/tab.
    """
    try:
        return parser.get_report_elements(webi_doc_id, report_id)
    except Exception as e:
        raise RuntimeError(f"Failed to get report elements: {str(e)}")


@mcp.tool()
def get_report_element_data(
    webi_doc_id: str,
    report_id: str,
    element_id: str,
    max_rows: int = 1000,
) -> Dict[str, Any]:
    """
    Extracts structured tabular data rows from a table or chart block in a report tab.
    Caps output to max_rows (default 1000) to protect LLM context windows.
    Returns column names and a list of dictionary rows.
    """
    try:
        return parser.get_report_element_data(webi_doc_id, report_id, element_id, max_rows=max_rows)
    except Exception as e:
        raise RuntimeError(f"Failed to extract element data: {str(e)}")


@mcp.tool()
def get_variables(webi_doc_id: str) -> List[Dict[str, Any]]:
    """
    Retrieves all custom formulas and calculated variables defined inside a Webi document.
    """
    try:
        return parser.get_variables(webi_doc_id)
    except Exception as e:
        raise RuntimeError(f"Failed to get variables: {str(e)}")


@mcp.tool()
def get_comments(webi_doc_id: str) -> List[Dict[str, Any]]:
    """
    Retrieves collaborative user comments and cell annotations in a Webi document.
    """
    try:
        return parser.get_comments(webi_doc_id)
    except Exception as e:
        raise RuntimeError(f"Failed to get comments: {str(e)}")


# =============================================================================
# 6. Data Providers & SQL
# =============================================================================


@mcp.tool()
def get_dp(webi_doc_id: str) -> List[str]:
    """
    Lists all Data Provider identifiers (e.g. 'DP0', 'DP1') within a Webi document.
    """
    try:
        return parser.get_dp(webi_doc_id)
    except Exception as e:
        raise RuntimeError(f"Failed to get data providers: {str(e)}")


@mcp.tool()
def get_dp_details(webi_doc_id: str, dp_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieves metadata of a specific Data Provider (data source name, ID, type, and update status).
    """
    try:
        return parser.get_dp_details(webi_doc_id, dp_id)
    except Exception as e:
        raise RuntimeError(f"Failed to get data provider details: {str(e)}")


@mcp.tool()
def get_dp_sql(webi_doc_id: str, dp_id: str) -> str:
    """
    Extracts the generated SQL query statement of a Data Provider.
    """
    try:
        return parser.get_dp_sql(webi_doc_id, dp_id)
    except Exception as e:
        raise RuntimeError(f"Failed to get SQL for data provider {dp_id}: {str(e)}")


@mcp.tool()
def get_dp_specification(webi_doc_id: str, dp_id: str) -> Dict[str, Any]:
    """
    Retrieves the query specification tree (result objects, query filters, sort rules) of a Data Provider.
    """
    try:
        return parser.webi.get_dp_specification(webi_doc_id, dp_id)
    except Exception as e:
        raise RuntimeError(f"Failed to get data provider specification: {str(e)}")


@mcp.tool()
def refresh_dp(webi_doc_id: str, dp_id: str) -> str:
    """
    Refreshes a single Data Provider without recalculating the rest of the report.
    """
    try:
        return parser.refresh_dp(webi_doc_id, dp_id)
    except Exception as e:
        return f"Error refreshing data provider {dp_id}: {str(e)}"


@mcp.tool()
def purge_dp(webi_doc_id: str, dp_id: str) -> str:
    """
    Purges cached data rows from a specific Data Provider to reduce document storage size.
    """
    try:
        success = parser.purge_dp(webi_doc_id, dp_id)
        if success:
            return f"Successfully purged data provider {dp_id} from document {webi_doc_id}"
        return f"Failed to purge data provider {dp_id}"
    except Exception as e:
        return f"Error purging data provider: {str(e)}"


@mcp.tool()
def get_dp_mapping_proposal(
    webi_doc_id: str,
    dp_id: str,
    target_datasource_id: str,
    strategies: Optional[str] = "SameID,SamePath,SameName",
    resolve_names: bool = True,
) -> Dict[str, Any]:
    """
    Generates and evaluates a Change Data Source mapping proposal for a Data Provider.
    Simulates repointing a Web Intelligence query to a target universe (e.g. UNV to UNX or repointed UNX)
    and reports matching status ('Ok', 'Ambiguous', 'NotFound') for all objects.

    Mapping Strategies (evaluated in sequence):
      - SameID: Matches objects having identical unique IDs. Recommended for UNV->UNX converted via IDT (100% precision).
      - SamePath: Matches objects by full folder hierarchy path (e.g. [Folder]/[Subfolder]/[Object]). Distinguishes homonyms safely.
      - SameTechnicalName: Matches objects by underlying database column or technical field name.
      - SameName: Matches objects by display name across any folder reorganization.
      - CloseName: Fuzzy string distance matching (Levenshtein). Helpful for minor typos/casing, but caution recommended.

    Recommended default: 'SameID,SamePath,SameName'.
    """
    try:
        return parser.get_dp_mapping_proposal(
            webi_doc_id=webi_doc_id,
            dp_id=dp_id,
            target_datasource_id=target_datasource_id,
            strategies=strategies,
            resolve_names=resolve_names,
        )
    except Exception as e:
        raise RuntimeError(f"Failed to generate mapping proposal: {str(e)}")


@mcp.tool()
def change_dp_datasource(
    webi_doc_id: str,
    dp_id: str,
    target_datasource_id: str,
    strategies: Optional[str] = "SameID,SamePath,SameName",
    custom_mappings: Optional[List[Dict[str, str]]] = None,
    save: bool = True,
) -> Dict[str, Any]:
    """
    Executes Change Data Source on a Web Intelligence Data Provider (e.g. migrating UNV to UNX or repointing universes).
    Generates mapping proposal using evaluated strategies, applies any custom mapping overrides,
    submits changes to Raylight, and optionally saves the document permanently in the repository.

    Parameters:
      webi_doc_id: ID of the Web Intelligence document.
      dp_id: Data Provider identifier (e.g. 'DP0').
      target_datasource_id: ID of the target universe (UNX or UNV).
      strategies: Comma-separated list of strategies (default: 'SameID,SamePath,SameName').
      custom_mappings: Optional list of explicit overrides, e.g. [{"source_id": "OBJ_147", "target_id": "OBJ_147"}].
      save: If True (default), permanently commits changes to the repository via in-place save.
    """
    try:
        return parser.change_dp_datasource(
            webi_doc_id=webi_doc_id,
            dp_id=dp_id,
            target_datasource_id=target_datasource_id,
            strategies=strategies,
            custom_mappings=custom_mappings,
            save=save,
        )
    except Exception as e:
        raise RuntimeError(f"Failed to change data source: {str(e)}")


# =============================================================================
# 7. Central Management Server (CMS) Administration & Queries
# =============================================================================


@mcp.tool()
def cms_query(query: str, page: int = 1, pagesize: int = 1000) -> Dict[str, Any]:
    """
    Executes an arbitrary SQL-like query against the CMS repository tables
    (CI_INFOOBJECTS, CI_APPOBJECTS, CI_SYSTEMOBJECTS).
    Examples:
      - 'SELECT SI_ID, SI_NAME FROM CI_INFOOBJECTS WHERE SI_KIND = \"Webi\"'
      - 'SELECT SI_ID, SI_NAME, SI_LASTLOGONTIME FROM CI_SYSTEMOBJECTS WHERE SI_KIND = \"User\"'
    """
    try:
        return parser.cms_query(query, page=page, pagesize=pagesize)
    except Exception as e:
        raise RuntimeError(f"CMS query failed: {str(e)}")


@mcp.tool()
def get_users(page: int = 1, pagesize: int = 100) -> List[Dict[str, Any]]:
    """
    Lists user accounts in the BI platform repository (ID, username, email, disabled status, last logon).
    """
    try:
        return parser.get_users(page=page, pagesize=pagesize)
    except Exception as e:
        raise RuntimeError(f"Failed to list users: {str(e)}")


@mcp.tool()
def get_user_details(user_id: str) -> Dict[str, Any]:
    """
    Retrieves full profile properties of a specific user ID.
    """
    try:
        return parser.get_user_details(user_id)
    except Exception as e:
        raise RuntimeError(f"Failed to get user details for {user_id}: {str(e)}")


@mcp.tool()
def set_user_status(user_id: str, disabled: bool) -> str:
    """
    Enables (disabled=False) or disables (disabled=True) a user account in the BI platform.
    """
    try:
        return parser.set_user_status(user_id, disabled)
    except Exception as e:
        return f"Error setting user status: {str(e)}"


@mcp.tool()
def get_user_groups(page: int = 1, pagesize: int = 100) -> List[Dict[str, Any]]:
    """
    Retrieves all User Groups configured in the BI platform along with member counts.
    """
    try:
        return parser.get_user_groups(page=page, pagesize=pagesize)
    except Exception as e:
        raise RuntimeError(f"Failed to list user groups: {str(e)}")


@mcp.tool()
def get_group_users(group_id: str) -> List[Dict[str, str]]:
    """
    Lists all users that are members of a specific User Group.
    """
    try:
        return parser.get_group_users(group_id)
    except Exception as e:
        raise RuntimeError(f"Failed to list group users: {str(e)}")


@mcp.tool()
def get_active_sessions() -> List[Dict[str, Any]]:
    """
    Monitors active connections and user sessions currently open on the Central Management Server.
    """
    try:
        return parser.get_active_sessions()
    except Exception as e:
        raise RuntimeError(f"Failed to get active sessions: {str(e)}")


@mcp.tool()
def terminate_session(session_id: str) -> str:
    """
    Forcibly disconnects and terminates an active user session by connection ID.
    """
    try:
        return parser.terminate_session(session_id)
    except Exception as e:
        return f"Error terminating session {session_id}: {str(e)}"


# =============================================================================
# 8. Schedules & Instances Monitoring
# =============================================================================


@mcp.tool()
def get_doc_schedules(webi_doc_id: str) -> List[Dict[str, Any]]:
    """
    Lists scheduled execution rules defined for a Web Intelligence document.
    """
    try:
        return parser.get_doc_schedules(webi_doc_id)
    except Exception as e:
        raise RuntimeError(f"Failed to get schedules: {str(e)}")


@mcp.tool()
def get_doc_instances(webi_doc_id: str, max_instances: int = 50) -> List[Dict[str, Any]]:
    """
    Retrieves historical run instances of a Webi report, including execution status (Success, Failed, Running)
    and execution timestamps.
    """
    try:
        return parser.get_doc_instances(webi_doc_id, max_instances=max_instances)
    except Exception as e:
        raise RuntimeError(f"Failed to get instances: {str(e)}")


@mcp.tool()
def get_instance_details(instance_id: str) -> Dict[str, Any]:
    """
    Retrieves detailed diagnostic information for a specific instance run,
    including failure error messages and file sizes.
    """
    try:
        return parser.get_instance_details(instance_id)
    except Exception as e:
        raise RuntimeError(f"Failed to get instance details: {str(e)}")


@mcp.tool()
def delete_instance(instance_id: str) -> str:
    """
    Deletes a historical report execution instance from the CMS repository.
    """
    try:
        success = parser.delete_instance(instance_id)
        if success:
            return f"Successfully deleted instance {instance_id}"
        return f"Failed to delete instance {instance_id}"
    except Exception as e:
        return f"Error deleting instance: {str(e)}"


# =============================================================================
# 9. InfoStore & Folders
# =============================================================================


@mcp.tool()
def get_folders(folder_id: str) -> List[str]:
    """
    Gets all subfolder IDs recursively starting from a root folder ID.
    """
    try:
        return parser.get_folders(folder_id)
    except Exception as e:
        raise RuntimeError(f"Failed to get folders: {str(e)}")


@mcp.tool()
def get_folder_details(folder_id: str) -> Dict[str, Any]:
    """
    Retrieves metadata of a repository folder (name, CUID, parent ID, description).
    """
    try:
        return parser.get_folder_details(folder_id)
    except Exception as e:
        raise RuntimeError(f"Failed to get folder details: {str(e)}")


@mcp.tool()
def create_folder(name: str, parent_folder_id: str, description: Optional[str] = None) -> Dict[str, Any]:
    """
    Creates a new folder in the InfoStore repository under a parent folder.
    """
    try:
        return parser.infostore.create_folder(name, parent_folder_id, description)
    except Exception as e:
        raise RuntimeError(f"Failed to create folder: {str(e)}")


@mcp.tool()
def delete_folder(folder_id: str) -> str:
    """
    Permanently deletes a folder from the InfoStore repository.
    """
    try:
        success = parser.infostore.delete_folder(folder_id)
        if success:
            return f"Successfully deleted folder {folder_id}"
        return f"Failed to delete folder {folder_id}"
    except Exception as e:
        return f"Error deleting folder: {str(e)}"


@mcp.tool()
def get_webi_docs(folder_id: str) -> List[str]:
    """
    Lists all Web Intelligence document IDs located directly inside a repository folder.
    """
    try:
        return parser.get_webi_docs(folder_id)
    except Exception as e:
        raise RuntimeError(f"Failed to get webi docs: {str(e)}")


@mcp.tool()
def get_categories() -> List[Dict[str, str]]:
    """
    Lists all Corporate Categories defined in the BI platform repository.
    """
    try:
        return parser.get_categories()
    except Exception as e:
        raise RuntimeError(f"Failed to get categories: {str(e)}")


if __name__ == "__main__":
    mcp.run()
