from typing import Any, Dict, List


def format_query_results(result: Dict[str, Any]) -> str:
    """Format query results from either SDK or direct API style into a readable string."""

    if not result:
        return "No results or invalid result format."
    
    column_names: List[str] = []
    rows: List[List[Any]] = [] # For new style, this will be list of dicts initially
    data_rows_formatted: List[str] = []

    # Try to parse as output from execute_databricks_sql (SDK based)
    if result.get("status") == "success" and "data" in result:
        print("Formatting results from SDK-based execute_databricks_sql output.")
        sdk_data = result.get("data", [])
        if not sdk_data: # No rows, but query was successful
            # Try to get column names if available even with no data (e.g., from a manifest if we adapt execute_databricks_sql later)
            # For now, if no data, we might not have explicit column names easily in this path.
            # However, execute_databricks_sql returns column names implicit in the (empty) list of dicts.
            # This part needs careful handling if sdk_data is empty but we still want headers.
            # Let's assume if sdk_data is empty, we might not have columns easily unless manifest is also passed.
            # For now, if sdk_data is empty, we report no data rows. Future improvement: get columns from manifest if possible.
            if result.get("message") == "Query succeeded but returned no data.":
                 # If we had column names from execute_databricks_sql (e.g. if it returned them separately)
                 # we could print headers. For now, this message is sufficient.
                return "Query succeeded but returned no data."
            return "Query succeeded but returned no data rows."

        # Assuming sdk_data is a list of dictionaries, get column names from the first row's keys
        if isinstance(sdk_data, list) and len(sdk_data) > 0 and isinstance(sdk_data[0], dict):
            column_names = list(sdk_data[0].keys())
        
        for row_dict in sdk_data:
            row_values = []
            for col_name in column_names: # Iterate in order of discovered column names
                value = row_dict.get(col_name)
                if value is None:
                    row_values.append("NULL")
                else:
                    row_values.append(str(value))
            data_rows_formatted.append(" | ".join(row_values))
    
    # Try to parse as old direct API style output (from dbapi.execute_statement)
    elif 'manifest' in result and 'result' in result:
        print("Formatting results from original dbapi.execute_statement output.")
        if result['manifest'].get('schema') and result['manifest']['schema'].get('columns'):
            columns_schema = result['manifest']['schema']['columns']
            column_names = [col['name'] for col in columns_schema if 'name' in col] if columns_schema else []
        
        if result['result'].get('data_array'):
            raw_rows = result['result']['data_array']
            for row_list in raw_rows:
                row_values = []
                for value in row_list:
                    if value is None:
                        row_values.append("NULL")
                    else:
                        row_values.append(str(value))
                data_rows_formatted.append(" | ".join(row_values))
    else:
        # Fallback if structure is completely unrecognized or an error dict itself
        if result.get("status") == "error" and result.get("error"):
            return f"Error from query execution: {result.get('error')} Details: {result.get('details', 'N/A')}"
        return "Invalid or unrecognized result format."

    # Common formatting part for table output
    if not column_names:
        return "No column names found in the result."
    
    output_lines = []
    output_lines.append(" | ".join(column_names))
    output_lines.append("-" * (sum(len(name) + 3 for name in column_names) - 1 if column_names else 0))

    if not data_rows_formatted:
        output_lines.append("No data rows found.")
    else:
        output_lines.extend(data_rows_formatted)
    
    return "\n".join(output_lines) 