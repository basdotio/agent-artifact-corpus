"""
DAX Utilities
=============
Helper functions for working with DAX queries.
"""

import re
from typing import Optional, List


def extract_dax_query(text: str) -> Optional[str]:
    """
    Extract DAX query from AI response if it contains one.

    Looks for EVALUATE or DEFINE...EVALUATE queries in code blocks.

    Args:
        text: The AI response text to parse

    Returns:
        The extracted DAX query, or None if not found
    """
    patterns = [
        r'```(?:dax)?\s*(EVALUATE[\s\S]*?)```',
        r'```(?:dax)?\s*(DEFINE[\s\S]*?EVALUATE[\s\S]*?)```',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None


def fix_table_names_in_dax(dax_query: str, table_names: List[str]) -> str:
    """
    Fix table names with spaces by wrapping them in single quotes.

    IMPORTANT: This function must NOT break already-correct table names!

    The AI sometimes:
    1. Forgets to quote table names with spaces
    2. Places closing quote too early: 'Fact Financials' Monthly' instead of 'Fact Financials Monthly'

    This function ensures they are properly quoted for DAX execution.

    Args:
        dax_query: The DAX query to fix
        table_names: List of table names from the model

    Returns:
        The fixed DAX query with properly quoted table names
    """
    if not dax_query or not table_names:
        return dax_query

    fixed_query = dax_query

    # Sort table names by length (longest first) to process longer names first
    sorted_tables = sorted(table_names, key=len, reverse=True)

    # FIRST PASS: Find all table names that are ALREADY correctly quoted
    # This prevents us from breaking them when processing shorter table names
    correctly_quoted_tables = set()
    for table_name in sorted_tables:
        if ' ' in table_name:
            correct_quoted = f"'{table_name}'"
            if correct_quoted in fixed_query:
                correctly_quoted_tables.add(table_name)

    # SECOND PASS: Fix table names that need fixing
    for table_name in sorted_tables:
        # Only process table names that contain spaces
        if ' ' not in table_name:
            continue

        correct_quoted = f"'{table_name}'"

        # If already correctly quoted, skip
        if table_name in correctly_quoted_tables:
            continue

        # CRITICAL: Check if this table name is a SUBSTRING of an already-correct table
        # e.g., "Fact Financials" inside "'Fact Financials Monthly'" - DON'T TOUCH!
        is_substring_of_correct = False
        for correct_table in correctly_quoted_tables:
            if table_name in correct_table and table_name != correct_table:
                is_substring_of_correct = True
                break

        if is_substring_of_correct:
            continue

        # Fix malformed quotes - LLM sometimes puts closing quote too early
        # e.g., 'Fact Financials' Monthly' instead of 'Fact Financials Monthly'
        words = table_name.split()
        for i in range(1, len(words)):
            partial = ' '.join(words[:i])
            remainder = ' '.join(words[i:])

            # Malformed pattern: 'partial' remainder'
            malformed = f"'{partial}' {remainder}'"
            if malformed in fixed_query:
                fixed_query = fixed_query.replace(malformed, correct_quoted)
                # Update correctly quoted tables after fix
                correctly_quoted_tables.add(table_name)

            # Also check: 'partial' remainder[ (without closing quote before column ref)
            for suffix in ['[', ',', ')', '\n', ' ']:
                pattern = f"'{partial}' {remainder}{suffix}"
                if pattern in fixed_query and correct_quoted not in fixed_query:
                    fixed_query = fixed_query.replace(pattern, f"{correct_quoted}{suffix}")
                    correctly_quoted_tables.add(table_name)

        # Fix unquoted table name - but only if not inside an already quoted longer name
        # Re-check if correct_quoted is now in fixed_query (from previous fixes)
        if correct_quoted not in fixed_query and table_name in fixed_query:
            # Make sure we're not matching inside a quoted string
            # Use word boundary-like check: the table name should be preceded/followed by
            # non-alphanumeric characters (except within quotes)
            escaped = re.escape(table_name)
            # Match table_name that is NOT immediately preceded by ' or alphanumeric
            # and NOT immediately followed by alphanumeric (but [ is OK for column refs)
            pattern = re.compile(r"(?<!['\w])" + escaped + r"(?!['\w])")
            fixed_query = pattern.sub(correct_quoted, fixed_query)

        # Fix double quotes at start: ''Table Name' -> 'Table Name'
        double_start = f"''{table_name}'"
        if double_start in fixed_query:
            fixed_query = fixed_query.replace(double_start, correct_quoted)

    return fixed_query


def is_data_question(message: str) -> bool:
    """
    Check if the user is asking for actual data vs. code generation.

    Args:
        message: The user's message

    Returns:
        True if the message appears to be asking for data
    """
    data_keywords = [
        'what is', 'what are', 'how much', 'how many', 'total', 'sum', 'count',
        'show me', 'tell me', 'get me', 'list', 'find', 'calculate',
        'average', 'min', 'max', 'top', 'bottom', 'revenue', 'sales', 'profit',
        'value', 'amount', '?'
    ]
    message_lower = message.lower()
    return any(kw in message_lower for kw in data_keywords)
