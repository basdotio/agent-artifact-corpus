"""Module for formatting database schema information in a readable and scalable way.

The formatter employs a hierarchical grouping strategy for relationships when there are more than
RELATIONSHIP_GROUPING_THRESHOLD relationships:
1. Common patterns (HIST_*, TMP_*, etc.)
2. Common prefixes (if no pattern match)
3. Column pattern grouping (as fallback)

For less than RELATIONSHIP_GROUPING_THRESHOLD relationships, each relationship is listed individually without grouping.

Example Output Scenarios:

1. Simple table with few relationships (no grouping needed):
```
Table: EMPLOYEES
Columns:
  - employee_id: NUMBER NOT NULL
  - first_name: VARCHAR2(50) NULL
  - last_name: VARCHAR2(50) NOT NULL
  - email: VARCHAR2(100) NULL
  - department_id: NUMBER NOT NULL
  - hire_date: DATE NOT NULL
  - salary: NUMBER NOT NULL

Relationships:
  References:
    - DEPARTMENTS (department_id->id)
    - LOCATIONS (location_id->id)
  Referenced by:
    - PROJECTS (project_manager_id->employee_id)
    - TIMESHEET_ENTRIES (employee_id->employee_id)
```

2. Table with many columns (compact format) and common pattern relationships:
```
Table: CUSTOMER_TRANSACTIONS
Columns:
  NOT NULL: id(NUMBER), transaction_date(TIMESTAMP), customer_id(NUMBER), amount(DECIMAL), 
           status(VARCHAR2), created_by(VARCHAR2), last_updated_at(TIMESTAMP)
  NULL: description(VARCHAR2), reference_no(VARCHAR2), notes(CLOB), approved_by(VARCHAR2),
        external_ref(VARCHAR2), batch_id(NUMBER), discount_code(VARCHAR2)

Relationships:
  References:
    - CUSTOMERS (customer_id->id)
    - PAYMENT_METHODS (payment_method_id->id)
  Referenced by:
    - HIST_* (transaction_id->id):
      created_by->user_id
      modified_by->user_id
    - AUDIT_* (entity_id->id, entity_type='TRANSACTION')
    - FINANCIAL_* (source_id->id):
      transaction_id->id
      reversal_id->id
```

3. Table with complex relationships and multiple foreign keys:
```
Table: ORDER_ITEMS
Columns:
  - order_id: NUMBER NOT NULL
  - line_id: NUMBER NOT NULL
  - product_id: NUMBER NOT NULL
  - variant_id: NUMBER NULL
  - quantity: NUMBER NOT NULL
  - unit_price: DECIMAL NOT NULL
  - discount_amount: DECIMAL NULL

Relationships:
  References:
    - ORDERS:
      order_id->id
      (order_id,line_id)->(id,line_no)
    - PRODUCTS (product_id->id)
    - PRODUCT_VARIANTS:
      variant_id->id
      (product_id,variant_id)->(product_id,id)
  Referenced by:
    - SHIPPING_* (order_id,line_id)->(order_ref,line_ref)
    - INVENTORY_* (product_id->item_id):
      reserved_by_order->order_id
      reserved_line_id->line_id
```

For less than RELATIONSHIP_GROUPING_THRESHOLD relationships, each relationship is listed individually without grouping.
"""
from typing import List, Dict, Any, Set, Tuple
import re
from collections import defaultdict

# Configuration constants
RELATIONSHIP_GROUPING_THRESHOLD = 10  # Number of relationships before grouping is applied
COLUMN_GROUPING_THRESHOLD = 20        # Number of columns before compact format is used
MIN_PREFIX_LENGTH = 3                 # Minimum length for meaningful prefix grouping
# Output safety/UX limits
MAX_CELL_WIDTH = 120                  # Truncate very wide cell values to prevent token bloat / prompt abuse

def format_schema(table_name: str, columns: List[Dict[str, Any]], 
                relationships: Dict[str, Dict[str, Any]]) -> str:
    """Format complete schema information for a table."""
    result = [f"\nTable: {table_name}"]
    
    # Format columns with automatic compaction for large column sets
    result.append("Columns:")
    column_lines = format_columns(columns, compact=len(columns) > COLUMN_GROUPING_THRESHOLD)
    result.extend(column_lines)
    
    # Format relationships if present
    if relationships:
        result.append("Relationships:")
        relationship_lines = format_relationships(relationships)
        result.extend(relationship_lines)
    
    return "\n".join(result)

def format_columns(columns: List[Dict[str, Any]], compact: bool = False) -> List[str]:
    """Format column information, with option for compact representation for many columns."""
    result = []
    
    if compact:
        # Group columns by nullability for compact view
        null_cols = []
        not_null_cols = []
        for column in columns:
            col_str = f"{column['name']}({column['type']})"
            if column["nullable"]:
                null_cols.append(col_str)
            else:
                not_null_cols.append(col_str)
        
        if not_null_cols:
            result.append("  NOT NULL: " + ", ".join(not_null_cols))
        if null_cols:
            result.append("  NULL: " + ", ".join(null_cols))
    else:
        # Detailed view for fewer columns
        for column in columns:
            nullable = "NULL" if column["nullable"] else "NOT NULL"
            result.append(f"  - {column['name']}: {column['type']} {nullable}")
    
    return result

def format_relationships(relationships: Dict[str, Dict[str, Any]]) -> List[str]:
    """Format relationship information with smart grouping for larger sets."""
    if not relationships:
        return []
    
    result = []
    # Split relationships by direction
    incoming = []
    outgoing = []
    
    for ref_table, rel in relationships.items():
        # Handle case where rel is a list of relationships rather than a single relationship
        if isinstance(rel, list):
            for single_rel in rel:
                if 'direction' not in single_rel:
                    continue  # Skip if no direction
                
                # Use safe attribute access
                direction = single_rel.get('direction', '')
                local_column = single_rel.get('local_column', '')
                foreign_column = single_rel.get('foreign_column', '')
                
                if direction == 'INCOMING':
                    incoming.append((ref_table, {'direction': direction, 'local_column': local_column, 'foreign_column': foreign_column}))
                else:
                    outgoing.append((ref_table, {'direction': direction, 'local_column': local_column, 'foreign_column': foreign_column}))
        else:
            # Handle dict format
            if 'direction' not in rel:
                continue  # Skip if no direction
                
            # Use safe attribute access
            direction = rel.get('direction', '')
            local_column = rel.get('local_column', '')
            foreign_column = rel.get('foreign_column', '')
            
            if direction == 'INCOMING':
                incoming.append((ref_table, {'direction': direction, 'local_column': local_column, 'foreign_column': foreign_column}))
            else:
                outgoing.append((ref_table, {'direction': direction, 'local_column': local_column, 'foreign_column': foreign_column}))
    
    # Format outgoing relationships
    if outgoing:
        result.append("  References:")
        if len(outgoing) < RELATIONSHIP_GROUPING_THRESHOLD:
            # Simple list format for small sets
            for ref_table, rel in sorted(outgoing, key=lambda x: x[0]):
                col_pattern = f"{rel['local_column']}->{rel['foreign_column']}"
                result.append(f"    - {ref_table} ({col_pattern})")
        else:
            # Use grouping for larger sets
            groups = _group_relationships(outgoing)
            _format_relationship_groups(groups, result)
    
    # Format incoming relationships
    if incoming:
        result.append("  Referenced by:")
        if len(incoming) < RELATIONSHIP_GROUPING_THRESHOLD:
            # Simple list format for small sets
            for ref_table, rel in sorted(incoming, key=lambda x: x[0]):
                col_pattern = f"{rel['local_column']}->{rel['foreign_column']}"
                result.append(f"    - {ref_table} ({col_pattern})")
        else:
            # Use grouping for larger sets
            groups = _group_relationships(incoming)
            _format_relationship_groups(groups, result)
    
    return result

def _group_relationships(relationships: List[tuple]) -> List[Dict[str, Any]]:
    """Group relationships by common patterns in table names and column mappings."""
    if not relationships:
        return []
    
    # Sort relationships for consistent grouping
    relationships.sort(key=lambda x: x[0])
    
    # First try grouping by common patterns
    pattern_groups = _group_by_patterns(relationships)
    if pattern_groups:
        return pattern_groups
    
    # If no pattern groups found, try prefix grouping
    prefix_groups = _group_by_prefix(relationships)
    if prefix_groups:
        return prefix_groups
    
    # If no groups found, fall back to simple grouping by column patterns
    return _group_by_column_patterns(relationships)

def _group_by_patterns(relationships: List[Tuple[str, Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """Group tables by common naming patterns like HIST_, TMP_, etc."""
    common_patterns = {
        r'^HIST_': 'HIST_*',
        r'^TMP_': 'TMP_*',
        r'^BAK_': 'BAK_*',
        r'^ARCH_': 'ARCH_*',
        r'_HISTORY$': '*_HISTORY',
        r'_ARCHIVE$': '*_ARCHIVE',
        r'_BACKUP$': '*_BACKUP',
        r'_\d{4,}$': '*_YYYY',  # Tables with year suffixes
        r'_[A-Z]{2,3}$': '*_XX',  # Tables with 2-3 letter suffixes
    }
    
    groups = defaultdict(lambda: {'pattern': '', 'tables': [], 'column_patterns': set()})
    unmatched = []
    
    for table, rel in relationships:
        matched = False
        for pattern, display in common_patterns.items():
            if re.search(pattern, table):
                col_pattern = f"{rel['local_column']}->{rel['foreign_column']}"
                groups[display]['pattern'] = display
                groups[display]['tables'].append((table, rel))
                groups[display]['column_patterns'].add(col_pattern)
                matched = True
                break
        if not matched:
            unmatched.append((table, rel))
    
    # Process any unmatched relationships
    if unmatched:
        unmatched_group = _group_by_prefix(unmatched)
        return list(groups.values()) + unmatched_group
    
    return list(groups.values())

def _group_by_prefix(relationships: List[Tuple[str, Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """Group tables by common prefixes."""
    groups = []
    current_group = {
        'pattern': '',
        'tables': [],
        'column_patterns': set()
    }
    
    for i, (table, rel) in enumerate(relationships):
        col_pattern = f"{rel['local_column']}->{rel['foreign_column']}"
        
        if not current_group['tables']:
            current_group['tables'].append((table, rel))
            current_group['column_patterns'].add(col_pattern)
            continue
        
        prev_table = current_group['tables'][-1][0]
        common_prefix = _get_common_prefix([prev_table, table])
        
        if len(common_prefix) >= MIN_PREFIX_LENGTH:
            current_group['tables'].append((table, rel))
            current_group['column_patterns'].add(col_pattern)
        else:
            if current_group['tables']:
                _finalize_group(current_group)
                groups.append(current_group)
            current_group = {
                'pattern': '',
                'tables': [(table, rel)],
                'column_patterns': {col_pattern}
            }
    
    if current_group['tables']:
        _finalize_group(current_group)
        groups.append(current_group)
    
    return groups

def _group_by_column_patterns(relationships: List[Tuple[str, Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """Group tables by common column patterns when no other grouping is possible."""
    pattern_groups = defaultdict(lambda: {'pattern': '', 'tables': [], 'column_patterns': set()})
    
    for table, rel in relationships:
        col_pattern = f"{rel['local_column']}->{rel['foreign_column']}"
        pattern_groups[col_pattern]['tables'].append((table, rel))
        pattern_groups[col_pattern]['column_patterns'].add(col_pattern)
    
    # Finalize groups
    result = []
    for group in pattern_groups.values():
        tables = [t[0] for t in group['tables']]
        if len(tables) > 3:
            group['pattern'] = f"[{len(tables)} tables]"
        else:
            group['pattern'] = ", ".join(tables)
        result.append(group)
    
    return result

def _finalize_group(group: Dict[str, Any]) -> None:
    """Finalize a group by setting its pattern based on its contents."""
    if not group['tables']:
        return
        
    tables = [t[0] for t in group['tables']]
    if len(group['tables']) == 1:
        group['pattern'] = tables[0]
    else:
        common_prefix = _get_common_prefix(tables)
        if len(common_prefix) >= MIN_PREFIX_LENGTH:
            group['pattern'] = f"{common_prefix}*"
        else:
            group['pattern'] = ", ".join(tables)

def _get_common_prefix(strings: List[str]) -> str:
    """Find the longest common prefix among strings."""
    if not strings:
        return ""
    shortest = min(strings)
    for i, char in enumerate(shortest):
        if not all(s[i] == char for s in strings):
            return shortest[:i]
    return shortest

def _format_relationship_groups(groups: List[Dict[str, Any]], result: List[str]) -> None:
    """Format grouped relationships and append to result list."""
    for group in groups:
        if len(group['column_patterns']) == 1:
            col_pattern = next(iter(group['column_patterns']))
            result.append(f"    - {group['pattern']} ({col_pattern})")
        else:
            result.append(f"    - {group['pattern']}:")
            for pattern in sorted(group['column_patterns']):
                result.append(f"      {pattern}")

def format_sql_query_result(result: Dict[str, Any]) -> str:
    """
    Format SQL query results as a markdown table.
    
    Args:
        result: Dictionary containing query results with 'columns' and 'rows' keys
        
    Returns:
        Formatted markdown table string
    """
    if not result.get("rows"):
        return "Query executed successfully, but returned no rows."

    headers = [str(h) for h in result["columns"]]
    rows = result["rows"]

    def _escape(val: Any) -> str:
        if val is None:
            return ""
        s = str(val)
        # Normalize whitespace to single spaces to avoid multi-line table injection
        s = s.replace("\r", " ").replace("\n", " ")
        # Truncate overly long values
        truncated = False
        if len(s) > MAX_CELL_WIDTH:
            s = s[: MAX_CELL_WIDTH - 1] + "…"
            truncated = True
        # Escape pipe which breaks markdown tables
        s = s.replace("|", "\\|")
        # Backticks sometimes cause rendering issues inside larger markdown contexts
        s = s.replace("`", "'")
        return s, truncated

    # Preprocess cells to apply escaping + truncation and compute widths
    processed_rows: List[List[str]] = []
    truncated_any = False
    col_widths = [len(h) for h in headers]
    for row in rows:
        processed_row: List[str] = []
        for idx, header in enumerate(headers):
            cell_raw = row.get(header, "")
            cell, was_trunc = _escape(cell_raw)
            if was_trunc:
                truncated_any = True
            processed_row.append(cell)
            if len(cell) > col_widths[idx]:
                col_widths[idx] = len(cell)
        processed_rows.append(processed_row)

    def _pad(cell: str, width: int) -> str:
        return cell.ljust(width)

    lines: List[str] = []
    # Header
    lines.append("| " + " | ".join(_pad(h, col_widths[i]) for i, h in enumerate(headers)) + " |")
    # Separator
    lines.append("| " + " | ".join("-" * max(3, col_widths[i]) for i in range(len(headers))) + " |")
    # Data
    for prow in processed_rows:
        lines.append("| " + " | ".join(_pad(prow[i], col_widths[i]) for i in range(len(headers))) + " |")

    if truncated_any:
        lines.append("\nNote: Some values truncated to " + str(MAX_CELL_WIDTH) + " chars (…)")

    return "\n".join(lines)