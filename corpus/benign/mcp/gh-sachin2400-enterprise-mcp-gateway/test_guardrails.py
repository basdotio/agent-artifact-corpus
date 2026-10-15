"""Direct tests of the MCP gateway guardrails (no LLM, no network)."""

from mcp_server import execute_read_only_sql as run, mask_pii


def blocked(sql, role="analyst"):
    return not run(sql, role)["ok"]


def main():
    assert blocked("DROP TABLE employees")
    assert blocked("SELECT 1; DROP TABLE employees")
    assert blocked("SELECT * FROM employees -- x")
    assert blocked("SELECT * FROM sqlite_master")
    assert blocked("SELECT * FROM employees", "viewer")
    assert blocked("SELECT * FROM policies p, employees e", "viewer"), "comma-join RBAC bypass"
    assert blocked("SELECT * FROM policies WHERE id IN (SELECT id FROM employees)", "viewer")
    assert run("SELECT * FROM policies", "viewer")["ok"]
    rows = run("SELECT * FROM employees", "analyst")["rows"]
    assert len(rows) <= 10 and all(r["email"] == "[EMAIL]" and r["ssn"] == "[SSN]" for r in rows)
    assert mask_pii("a@b.com 123456789 123-45-6789") == "[EMAIL] [SSN] [SSN]"
    print("all guardrail tests passed")


if __name__ == "__main__":
    main()
