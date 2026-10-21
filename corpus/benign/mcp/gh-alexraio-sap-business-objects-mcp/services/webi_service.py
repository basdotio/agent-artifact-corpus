"""
Web Intelligence (Webi) Service for SAP BusinessObjects 4.3 SP5.
Handles document lifecycle, prompt parameters, LOVs, refresh execution,
tabular data extraction from report blocks, data provider SQL, and formulas.
"""

import logging
from typing import Any, Dict, List, Optional, Union

from core.client import BOEClient
from core.exceptions import BOEError

logger = logging.getLogger("WebiService")


class WebiService:
    """Service for Web Intelligence (Raylight) REST API operations."""

    def __init__(self, client: BOEClient):
        self.client = client

    # =========================================================================
    # 1. Document Lifecycle & Metadata
    # =========================================================================

    def get_documents(self, page: int = 1, pagesize: int = 50) -> List[Dict[str, Any]]:
        """
        Retrieves a paginated list of Web Intelligence documents from the repository.
        """
        url = f"{self.client.webi_url}/documents?page={page}&pagesize={pagesize}"
        resp = self.client.get(url)
        docs: List[Dict[str, Any]] = []
        if isinstance(resp, dict) and "documents" in resp:
            raw_docs = resp["documents"].get("document", [])
            if isinstance(raw_docs, dict):
                raw_docs = [raw_docs]
            for doc in raw_docs:
                docs.append(
                    {
                        "id": str(doc.get("id", "")),
                        "cuid": str(doc.get("cuid", "")),
                        "name": str(doc.get("name", "")),
                        "folderId": str(doc.get("folderId", "")),
                        "updated": str(doc.get("updated", "")),
                    }
                )
        return docs

    def get_doc_details(self, webi_doc_id: str) -> Dict[str, Any]:
        """
        Gets document metadata: name, repository path, CUID, scheduled status, and state.
        """
        url = f"{self.client.webi_url}/documents/{webi_doc_id}"
        resp = self.client.get(url)
        if isinstance(resp, dict) and "document" in resp:
            doc = resp["document"]
            return {
                "webi_doc_id": str(doc.get("id", webi_doc_id)),
                "webi_doc_name": str(doc.get("name", "")),
                "webi_doc_path": str(doc.get("path", "")),
                "webi_doc_cuid": str(doc.get("cuid", "")),
                "webi_doc_scheduled": str(doc.get("scheduled", "false")).lower(),
                "webi_doc_state": str(doc.get("state", "")),
            }
        raise BOEError(f"Unable to read document details for ID {webi_doc_id}")

    def get_doc_properties(self, webi_doc_id: str) -> Dict[str, Any]:
        """
        Gets document properties (refreshOnOpen, usePersonalData, etc.).
        """
        url = f"{self.client.webi_url}/documents/{webi_doc_id}/properties"
        resp = self.client.get(url)
        if isinstance(resp, dict) and "properties" in resp:
            return resp["properties"]
        return {"raw": resp}

    def save_webi_doc(
        self, webi_doc_id: str, webi_doc_name: Optional[str] = None, folder_id: Optional[int] = None
    ) -> str:
        """
        Saves a Webi document in place, or saves it with a new name/folder (Save As).
        If webi_doc_name is omitted, saves changes in place via PUT.
        """
        if webi_doc_name:
            fid = folder_id if folder_id is not None else -1
            url = f"{self.client.webi_url}/documents/{webi_doc_id}?overwrite=true&withComments=true"
            payload = {
                "document": {
                    "name": webi_doc_name,
                    "folderId": fid,
                }
            }
            self.client.post(url, json_data=payload)
            return f"Successfully saved document {webi_doc_id} as '{webi_doc_name}'"
        else:
            url = f"{self.client.webi_url}/documents/{webi_doc_id}"
            self.client.put(url)
            return f"Successfully saved document {webi_doc_id} in place"

    def delete_webi_doc(self, webi_doc_id: str) -> bool:
        """
        Permanently deletes a Webi document from the CMS repository.
        """
        url = f"{self.client.webi_url}/documents/{webi_doc_id}"
        self.client.delete(url)
        return True

    # =========================================================================
    # 2. Parameters, Prompts & Document Refresh
    # =========================================================================

    def get_doc_parameters(self, webi_doc_id: str) -> List[Dict[str, Any]]:
        """
        Retrieves all prompt parameters required by the Webi document.
        Returns a list of parameters with ID, prompt question, type, and optional flag.
        """
        url = f"{self.client.webi_url}/documents/{webi_doc_id}/parameters"
        resp = self.client.get(url)
        parameters: List[Dict[str, Any]] = []

        if isinstance(resp, dict) and "parameters" in resp:
            raw_params = resp["parameters"].get("parameter", [])
            if isinstance(raw_params, dict):
                raw_params = [raw_params]
            for p in raw_params:
                param_info = {
                    "id": p.get("id"),
                    "name": p.get("name", ""),
                    "technicalName": p.get("technicalName", ""),
                    "type": p.get("type", ""),
                    "cardinality": p.get("cardinality", "Single"),
                    "optional": p.get("optional", False),
                    "constrained": p.get("constrained", False),
                }
                # Include current default answer if present
                if "answer" in p:
                    param_info["current_answer"] = p["answer"]
                parameters.append(param_info)

        return parameters

    def get_parameter_lov(
        self, webi_doc_id: str, parameter_id: Union[int, str], page: int = 1, pagesize: int = 100
    ) -> List[Any]:
        """
        Retrieves the List of Values (LOV) allowed for a specific constrained parameter.
        """
        url = f"{self.client.webi_url}/documents/{webi_doc_id}/parameters/{parameter_id}/values?page={page}&pagesize={pagesize}"
        resp = self.client.get(url)
        values: List[Any] = []
        if isinstance(resp, dict) and "values" in resp:
            val_items = resp["values"].get("value", [])
            if isinstance(val_items, dict):
                val_items = [val_items]
            for v in val_items:
                if isinstance(v, dict):
                    values.append(v.get("$") or v.get("@id") or v)
                else:
                    values.append(v)
        return values

    def refresh_webi_doc(
        self,
        webi_doc_id: str,
        parameters: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Refreshes the Webi document within the active session.
        If parameters are provided, submits prompt answers to trigger execution.
        """
        url = f"{self.client.webi_url}/documents/{webi_doc_id}/parameters?refresh=true"
        payload: Dict[str, Any] = {}

        if parameters:
            formatted_params = []
            for p in parameters:
                p_id = p.get("id")
                p_val = p.get("value")
                if p_id is not None and p_val is not None:
                    # Support single value or list of values
                    if isinstance(p_val, list):
                        val_entries = [{"$": str(v)} for v in p_val]
                    else:
                        val_entries = [{"$": str(p_val)}]

                    formatted_params.append(
                        {
                            "id": p_id,
                            "answer": {"values": {"value": val_entries if len(val_entries) > 1 else val_entries[0]}},
                        }
                    )
            payload = {"parameters": {"parameter": formatted_params}}

        resp = self.client.put(url, json_data=payload if payload else None)
        return {"webi_doc_id": webi_doc_id, "status": "refreshed", "server_response": resp}

    # =========================================================================
    # 3. Data Providers & SQL Extraction
    # =========================================================================

    def get_dp(self, webi_doc_id: str) -> List[str]:
        """
        Lists all Data Provider identifiers (e.g. 'DP0', 'DP1') in a Webi document.
        """
        url = f"{self.client.webi_url}/documents/{webi_doc_id}/dataproviders"
        resp = self.client.get(url)
        if isinstance(resp, dict) and "dataproviders" in resp:
            dps = resp["dataproviders"].get("dataprovider", [])
            if isinstance(dps, dict):
                dps = [dps]
            return [str(dp["id"]) for dp in dps if "id" in dp]
        return []

    def get_dp_details(self, webi_doc_id: str, dp_id: str) -> Dict[str, Any]:
        """
        Retrieves metadata and data source information for a specific Data Provider.
        """
        url = f"{self.client.webi_url}/documents/{webi_doc_id}/dataproviders/{dp_id}"
        resp = self.client.get(url)
        if isinstance(resp, dict) and "dataprovider" in resp:
            dp_data = resp["dataprovider"]
            return {
                "id": str(dp_data.get("id", dp_id)),
                "dataSourceId": str(dp_data.get("dataSourceId", "")),
                "dataSourceType": str(dp_data.get("dataSourceType", "")),
                "dataSourceName": str(dp_data.get("dataSourceName", "")),
                "name": str(dp_data.get("name", "")),
                "isUpdated": dp_data.get("isUpdated", False),
            }
        raise BOEError(f"Data Provider {dp_id} not found in document {webi_doc_id}")

    def get_dp_specification(self, webi_doc_id: str, dp_id: str) -> Dict[str, Any]:
        """
        Retrieves the query specification (selected objects, query filters, sort order) of a Data Provider.
        """
        url = f"{self.client.webi_url}/documents/{webi_doc_id}/dataproviders/{dp_id}/specification"
        resp = self.client.get(url, headers={"Accept": "text/xml"})
        return resp if isinstance(resp, dict) else {"raw": resp}

    def get_dp_sql(self, webi_doc_id: str, dp_id: str) -> str:
        """
        Extracts the generated SQL query statement of a Data Provider.
        """
        url = f"{self.client.webi_url}/documents/{webi_doc_id}/dataproviders/{dp_id}/queryplan"
        try:
            resp = self.client.get(url)
            if isinstance(resp, dict) and "queryplan" in resp:
                plan = resp["queryplan"]
                stmt = plan.get("statement", plan.get("sql", str(plan)))
                if isinstance(stmt, dict) and "$" in stmt:
                    return str(stmt["$"])
                elif isinstance(stmt, list):
                    return "\n\n".join([s.get("$", str(s)) if isinstance(s, dict) else str(s) for s in stmt])
                return str(stmt)
            return str(resp)
        except Exception:
            # Fallback: check details endpoint
            details = self.get_dp_details(webi_doc_id, dp_id)
            return details.get("sql", "SQL statement not directly exposed for this data provider type.")

    def refresh_dp(self, webi_doc_id: str, dp_id: str) -> str:
        """
        Refreshes a single Data Provider without refreshing the entire document.
        """
        url = f"{self.client.webi_url}/documents/{webi_doc_id}/dataproviders/{dp_id}?refresh=true"
        self.client.put(url)
        return f"Successfully refreshed data provider '{dp_id}' in document {webi_doc_id}"

    def purge_dp(self, webi_doc_id: str, dp_id: str) -> bool:
        """
        Purges all cached data from a specific Data Provider to reduce file size.
        """
        url = f"{self.client.webi_url}/documents/{webi_doc_id}/dataproviders/{dp_id}?purge=true"
        self.client.put(url)
        return True

    def _extract_universe_objects(self, universe_id: str) -> Dict[str, Dict[str, Any]]:
        """
        Extracts all queryable objects (dimensions, measures, attributes) from a universe
        keyed by their unique ID (e.g. 'OBJ_147') for human-readable resolution.
        """
        url = f"{self.client.sl_url}/universes/{universe_id}"
        try:
            resp = self.client.get(url)
        except Exception:
            return {}

        found: Dict[str, Dict[str, Any]] = {}

        def recurse(node: Any, path: str = ""):
            if isinstance(node, dict):
                curr_name = node.get("name", "")
                curr_path = f"{path}/{curr_name}" if path else curr_name
                obj_id = node.get("@id") or node.get("id")
                if obj_id:
                    found[str(obj_id)] = {
                        "id": str(obj_id),
                        "name": curr_name,
                        "path": curr_path,
                        "type": node.get("@type") or node.get("type", "Unknown"),
                    }
                for v in node.values():
                    if isinstance(v, (dict, list)):
                        recurse(v, curr_path)
            elif isinstance(node, list):
                for item in node:
                    recurse(item, path)

        recurse(resp)
        return found

    def get_dp_mapping_proposal(
        self,
        webi_doc_id: str,
        dp_id: str,
        target_datasource_id: str,
        strategies: Optional[Union[List[str], str]] = None,
        resolve_names: bool = True,
    ) -> Dict[str, Any]:
        """
        Generates and analyzes a Change Data Source mapping proposal for a Data Provider.
        Evaluates mapping strategies in order (default: SameID, SamePath, SameName).

        Mapping Strategies:
          - SameID: Matches objects having identical unique IDs (100% precise, ideal for UNV->UNX converted via IDT).
          - SamePath: Matches objects having the exact same qualified folder hierarchy (safely distinguishes homonyms).
          - SameTechnicalName: Matches objects by underlying database column or technical name.
          - SameName: Matches objects with identical display names, regardless of folder reorganization.
          - CloseName: Fuzzy matching (Levenshtein distance) on names (handles minor typos, but risk of false positives).

        Returns:
          Enriched mapping proposal including source/target object names, paths, statuses ('Ok', 'Ambiguous', 'NotFound'),
          match statistics, and the raw payload ready for submission.
        """
        # Normalize strategies list
        default_strategies = ["SameID", "SamePath", "SameName"]
        if strategies is None:
            strat_list = default_strategies
        elif isinstance(strategies, str):
            strat_list = [s.strip() for s in strategies.split(",") if s.strip()]
        else:
            strat_list = [str(s).strip() for s in strategies if str(s).strip()]

        strat_param = ",".join(strat_list)

        url = (
            f"{self.client.webi_url}/documents/{webi_doc_id}/dataproviders/mappings"
            f"?originDataproviderIds={dp_id}&targetDatasourceId={target_datasource_id}&strategies={strat_param}"
        )
        resp = self.client.get(url)

        mappings_raw = resp.get("mappings", {}).get("content", {}).get("mapping", [])
        if isinstance(mappings_raw, dict):
            mappings_raw = [mappings_raw]

        # Extract source universe ID from data provider details
        source_universe_id = None
        try:
            dp_details = self.get_dp_details(webi_doc_id, dp_id)
            source_universe_id = dp_details.get("dataSourceId")
        except Exception:
            pass

        # Resolve human-readable object names from universes if requested
        source_objs: Dict[str, Dict[str, Any]] = {}
        target_objs: Dict[str, Dict[str, Any]] = {}
        if resolve_names:
            if source_universe_id:
                source_objs = self._extract_universe_objects(source_universe_id)
            target_objs = self._extract_universe_objects(target_datasource_id)

        enriched_mappings = []
        ok_count = 0
        unmapped_count = 0
        ambiguous_count = 0

        for m in mappings_raw:
            status = m.get("@status", "Unknown")
            source_info = m.get("source", {})
            target_info = m.get("target", {})

            src_id = str(source_info.get("id", ""))
            tgt_id = str(target_info.get("id", "")) if target_info else ""

            src_meta = source_objs.get(src_id, {})
            tgt_meta = target_objs.get(tgt_id, {})

            if status == "Ok":
                ok_count += 1
            elif status == "Ambiguous":
                ambiguous_count += 1
            else:
                unmapped_count += 1

            enriched_mappings.append(
                {
                    "status": status,
                    "source_id": src_id,
                    "source_name": src_meta.get("name", src_id),
                    "source_path": src_meta.get("path", ""),
                    "source_type": src_meta.get("type", "Unknown"),
                    "target_id": tgt_id if tgt_id else None,
                    "target_name": tgt_meta.get("name", tgt_id) if tgt_id else None,
                    "target_path": tgt_meta.get("path", "") if tgt_id else None,
                    "target_type": tgt_meta.get("type", "Unknown") if tgt_id else None,
                }
            )

        total = len(mappings_raw)
        success_rate = round((ok_count / total * 100), 1) if total > 0 else 0.0

        return {
            "webi_doc_id": str(webi_doc_id),
            "dataprovider_id": str(dp_id),
            "source_datasource_id": source_universe_id,
            "target_datasource_id": str(target_datasource_id),
            "strategies_applied": strat_list,
            "summary": {
                "total_objects": total,
                "mapped_ok": ok_count,
                "ambiguous": ambiguous_count,
                "unmapped": unmapped_count,
                "match_rate_percentage": success_rate,
                "all_mapped": (ok_count == total and total > 0),
            },
            "mappings": enriched_mappings,
            "raw_proposal": resp,
        }

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
        Executes Change Data Source on a Web Intelligence Data Provider (e.g. UNV -> UNX migration or universe repointing).
        Generates mapping proposal using evaluated strategies, applies any custom mapping overrides,
        submits changes to Raylight, and optionally saves the document.

        Args:
          webi_doc_id: ID of the Web Intelligence document.
          dp_id: Data Provider identifier (e.g. 'DP0').
          target_datasource_id: ID of the target universe (UNX or UNV).
          strategies: Optional list or comma-separated string of strategies (default: 'SameID,SamePath,SameName').
          custom_mappings: Optional list of explicit mappings to override or supply missing matches.
                           Example: [{"source_id": "OBJ_147", "target_id": "OBJ_147"}]
          save: If True (default), permanently commits changes to the repository via PUT.
        """
        # Step 1: Fetch proposal
        proposal = self.get_dp_mapping_proposal(
            webi_doc_id=webi_doc_id,
            dp_id=dp_id,
            target_datasource_id=target_datasource_id,
            strategies=strategies,
            resolve_names=False,
        )

        payload = proposal.get("raw_proposal", {})
        mappings = payload.get("mappings", {}).get("content", {}).get("mapping", [])
        if isinstance(mappings, dict):
            mappings = [mappings]
            payload["mappings"]["content"]["mapping"] = mappings

        # Step 2: Apply custom mappings if supplied
        if custom_mappings:
            custom_dict = {}
            for cm in custom_mappings:
                s = cm.get("source_id") or cm.get("source")
                t = cm.get("target_id") or cm.get("target")
                if s and t:
                    custom_dict[str(s)] = str(t)

            for m in mappings:
                s_id = str(m.get("source", {}).get("id", ""))
                if s_id in custom_dict:
                    m["@status"] = "Ok"
                    m["target"] = {"id": custom_dict[s_id]}
                    del custom_dict[s_id]

            # Append any remaining custom mappings not in proposal
            for s_id, t_id in custom_dict.items():
                mappings.append(
                    {
                        "@status": "Ok",
                        "source": {"id": s_id},
                        "target": {"id": t_id},
                    }
                )

        # Step 3: POST to mappings endpoint
        post_url = (
            f"{self.client.webi_url}/documents/{webi_doc_id}/dataproviders/mappings"
            f"?originDataproviderIds={dp_id}&targetDatasourceId={target_datasource_id}"
        )
        post_resp = self.client.post(post_url, json_data=payload)

        # Step 4: Save document if requested
        save_status = "not_saved"
        if save:
            self.save_webi_doc(webi_doc_id)
            save_status = "saved_in_place"

        # Step 5: Check updated DP details
        try:
            updated_details = self.get_dp_details(webi_doc_id, dp_id)
        except Exception:
            updated_details = {}

        return {
            "webi_doc_id": str(webi_doc_id),
            "dataprovider_id": str(dp_id),
            "target_datasource_id": str(target_datasource_id),
            "status": "success",
            "save_status": save_status,
            "raylight_response": post_resp,
            "updated_dataprovider": updated_details,
        }

    # =========================================================================
    # 4. Reports (Tabs), Blocks & Tabular Data Extraction
    # =========================================================================

    def get_reports(self, webi_doc_id: str) -> List[Dict[str, Any]]:
        """
        Retrieves all sheets/tabs in a Web Intelligence document.
        """
        url = f"{self.client.webi_url}/documents/{webi_doc_id}/reports"
        resp = self.client.get(url)
        reports: List[Dict[str, Any]] = []
        if isinstance(resp, dict) and "reports" in resp:
            raw_reports = resp["reports"].get("report", [])
            if isinstance(raw_reports, dict):
                raw_reports = [raw_reports]
            for r in raw_reports:
                reports.append(
                    {
                        "id": str(r.get("id", "")),
                        "name": str(r.get("name", "")),
                        "showWhenEmpty": r.get("showWhenEmpty", True),
                    }
                )
        return reports

    def get_report_elements(self, webi_doc_id: str, report_id: str) -> List[Dict[str, Any]]:
        """
        Lists all report elements (tables, charts, sections, forms) within a report tab.
        """
        url = f"{self.client.webi_url}/documents/{webi_doc_id}/reports/{report_id}/elements"
        resp = self.client.get(url)
        elements: List[Dict[str, Any]] = []
        if isinstance(resp, dict) and "elements" in resp:
            raw_elems = resp["elements"].get("element", [])
            if isinstance(raw_elems, dict):
                raw_elems = [raw_elems]
            for el in raw_elems:
                elements.append(
                    {
                        "id": str(el.get("id", "")),
                        "name": str(el.get("name", "")),
                        "type": str(el.get("@type", el.get("type", ""))),
                    }
                )
        return elements

    def get_report_element_data(
        self,
        webi_doc_id: str,
        report_id: str,
        element_id: str,
        max_rows: int = 1000,
    ) -> Dict[str, Any]:
        """
        Extracts structured tabular data rows from a table or chart block in a report tab.
        Limits rows to max_rows (default 1000) to protect LLM token limits.
        """
        url = f"{self.client.webi_url}/documents/{webi_doc_id}/reports/{report_id}/elements/{element_id}/data"
        try:
            resp = self.client.get(url)
        except Exception as e:
            return {
                "webi_doc_id": webi_doc_id,
                "report_id": report_id,
                "element_id": element_id,
                "total_rows_returned": 0,
                "columns": [],
                "data": [],
                "note": f"Element {element_id} does not expose a tabular dataset (it may be a layout cell, PageZone, or chart without table data): {str(e)}",
            }

        if not isinstance(resp, dict):
            return {"raw_data": str(resp)}

        # Parse Raylight dataset structure (columns / rows)
        dataset = resp.get("dataset", resp)
        rows_data: List[Dict[str, Any]] = []
        headers: List[str] = []

        # Extract column metadata
        if "columns" in dataset and "column" in dataset["columns"]:
            cols = dataset["columns"]["column"]
            if isinstance(cols, dict):
                cols = [cols]
            headers = [c.get("name") or c.get("@name") or f"Col_{i}" for i, c in enumerate(cols)]

        # Extract row values
        if "rows" in dataset and "row" in dataset["rows"]:
            raw_rows = dataset["rows"]["row"]
            if isinstance(raw_rows, dict):
                raw_rows = [raw_rows]

            for r_idx, r in enumerate(raw_rows[:max_rows]):
                cell_vals = r.get("cell", [])
                if isinstance(cell_vals, dict):
                    cell_vals = [cell_vals]

                row_dict: Dict[str, Any] = {}
                for c_idx, cell in enumerate(cell_vals):
                    val = cell.get("$") if isinstance(cell, dict) else str(cell)
                    col_name = headers[c_idx] if c_idx < len(headers) else f"Column_{c_idx + 1}"
                    row_dict[col_name] = val
                rows_data.append(row_dict)

        return {
            "webi_doc_id": webi_doc_id,
            "report_id": report_id,
            "element_id": element_id,
            "total_rows_returned": len(rows_data),
            "columns": headers,
            "data": rows_data,
        }

    # =========================================================================
    # 5. Variables, Formulas & Comments
    # =========================================================================

    def get_variables(self, webi_doc_id: str) -> List[Dict[str, Any]]:
        """
        Retrieves all calculated variables and custom formulas defined in a Webi document.
        """
        url = f"{self.client.webi_url}/documents/{webi_doc_id}/variables"
        resp = self.client.get(url)
        variables: List[Dict[str, Any]] = []
        if isinstance(resp, dict) and "variables" in resp:
            raw_vars = resp["variables"].get("variable", [])
            if isinstance(raw_vars, dict):
                raw_vars = [raw_vars]
            for v in raw_vars:
                variables.append(
                    {
                        "id": str(v.get("id", "")),
                        "name": str(v.get("name", "")),
                        "qualification": str(v.get("qualification", "")),
                        "formula": str(v.get("formula", "")),
                    }
                )
        return variables

    def create_variable(
        self, webi_doc_id: str, name: str, formula: str, qualification: str = "Dimension"
    ) -> Dict[str, Any]:
        """
        Creates a new calculated variable / formula in a Webi document.
        """
        url = f"{self.client.webi_url}/documents/{webi_doc_id}/variables"
        payload = {"variable": {"name": name, "formula": formula, "qualification": qualification}}
        return self.client.post(url, json_data=payload)

    def delete_variable(self, webi_doc_id: str, variable_id: str) -> bool:
        """
        Deletes a variable from a Webi document.
        """
        url = f"{self.client.webi_url}/documents/{webi_doc_id}/variables/{variable_id}"
        self.client.delete(url)
        return True

    def get_comments(self, webi_doc_id: str) -> List[Dict[str, Any]]:
        """
        Retrieves all collaborative user comments made on a Webi document.
        """
        url = f"{self.client.webi_url}/documents/{webi_doc_id}/comments"
        resp = self.client.get(url)
        comments: List[Dict[str, Any]] = []
        if isinstance(resp, dict) and "comments" in resp:
            raw_c = resp["comments"].get("comment", [])
            if isinstance(raw_c, dict):
                raw_c = [raw_c]
            for c in raw_c:
                comments.append(
                    {
                        "id": str(c.get("id", "")),
                        "author": str(c.get("author", "")),
                        "created": str(c.get("created", "")),
                        "content": str(c.get("content", "")),
                    }
                )
        return comments
