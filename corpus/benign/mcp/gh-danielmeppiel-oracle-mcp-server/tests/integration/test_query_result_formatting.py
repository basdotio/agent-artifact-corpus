import pytest
from db_context import DatabaseContext
from db_context.schema.formatter import format_sql_query_result, MAX_CELL_WIDTH

pytestmark = pytest.mark.asyncio

async def test_max_rows_and_truncation(db_context_read_only: DatabaseContext):
    # Generate a long string exceeding MAX_CELL_WIDTH
    long_literal = 'X' * (MAX_CELL_WIDTH + 50)
    sql = f"SELECT '{long_literal}' AS LONGCOL FROM dual"
    result = await db_context_read_only.run_sql_query(sql, max_rows=1)
    table_md = format_sql_query_result(result)
    assert 'LONGCOL' in table_md
    # Ensure truncated (ellipsis)
    assert '…' in table_md
    assert len(table_md.split('\n')[2]) < MAX_CELL_WIDTH + 20  # padded row line
    assert 'Note: Some values truncated' in table_md

async def test_escape_pipes_and_backticks(db_context_read_only: DatabaseContext):
    sql = "SELECT 'a|b`c' AS COL FROM dual"
    result = await db_context_read_only.run_sql_query(sql)
    md = format_sql_query_result(result)
    # Escaped pipe
    assert 'a\\|b' in md
    # Backticks replaced
    assert '`' not in md
