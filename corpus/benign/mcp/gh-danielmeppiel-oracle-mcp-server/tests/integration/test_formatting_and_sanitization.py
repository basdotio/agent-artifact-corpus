import re
import pytest
from db_context import DatabaseContext
from db_context.schema.formatter import format_sql_query_result
from db_context.utils import wrap_untrusted

pytestmark = pytest.mark.asyncio

async def test_markdown_table_alignment(db_context_read_only: DatabaseContext):
    result = await db_context_read_only.run_sql_query("SELECT 1 AS A, 22 AS BB, 333 AS CCC FROM dual")
    table = format_sql_query_result(result)
    lines = table.splitlines()
    assert lines[0].startswith("| A ")
    # Separator row length matches columns: at least 3 dashes
    assert re.match(r"^\| -+ \| -+ \| -+ \|$", lines[1])

async def test_empty_result_message(db_context_read_only: DatabaseContext):
    result = await db_context_read_only.run_sql_query("SELECT * FROM dual WHERE 1=0")
    assert result["row_count"] == 0
    formatted = format_sql_query_result(result)
    assert "returned no rows" in formatted

async def test_wrap_untrusted_integration():
    sample_table = "| A |\n| - |\n| <script> |"
    wrapped = wrap_untrusted(sample_table)
    assert "&lt;script&gt;" in wrapped
    # Unique tag boundaries
    opening = re.search(r"<untrusted-data-[0-9a-f-]+>", wrapped)
    closing = re.search(r"</untrusted-data-[0-9a-f-]+>", wrapped)
    assert opening and closing
    assert opening.group(0)[1:] in closing.group(0)  # same UUID
