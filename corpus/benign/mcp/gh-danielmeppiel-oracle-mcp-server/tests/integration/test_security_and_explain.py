import pytest
from db_context import DatabaseContext

pytestmark = pytest.mark.asyncio

async def test_injection_semicolon_blocked(db_context_read_only: DatabaseContext):
    with pytest.raises(PermissionError):
        await db_context_read_only.run_sql_query("SELECT 1 FROM dual; DROP TABLE no_table")

async def test_comment_obfuscation_still_select(db_context_read_only: DatabaseContext):
    # Should still classify as SELECT and execute
    res = await db_context_read_only.run_sql_query("/*INSERT*/ SELECT 42 AS ANSWER FROM dual")
    assert res["rows"][0]["ANSWER"] == 42

async def test_explain_query_plan_read_only_error(db_context_read_only: DatabaseContext):
    # In read-only mode this likely returns an error structure due to plan_table maintenance
    plan = await db_context_read_only.explain_query_plan("SELECT 1 FROM dual")
    # Expect either execution_plan empty with error
    assert "execution_plan" in plan
    assert "error" in plan or plan["execution_plan"] == []

async def test_explain_query_plan_write_mode(db_context_write_enabled: DatabaseContext):
    plan = await db_context_write_enabled.explain_query_plan("SELECT 1 FROM dual")
    assert "execution_plan" in plan
    # Might still be empty depending on plan_table; just ensure it returns dictionary without error
    assert isinstance(plan["optimization_suggestions"], list)
