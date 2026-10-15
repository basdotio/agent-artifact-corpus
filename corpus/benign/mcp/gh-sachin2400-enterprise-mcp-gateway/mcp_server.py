"""MCP server with read-only SQL and policy search tools."""

import os
import re
import sqlite3
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("gateway")

DB = sqlite3.connect(":memory:", check_same_thread=False)
DB.execute("CREATE TABLE employees (id INT, name TEXT, email TEXT, ssn TEXT, department TEXT, salary INT)")
DB.execute("CREATE TABLE policies (id INT, title TEXT, body TEXT)")
DB.executemany(
    "INSERT INTO employees VALUES (?,?,?,?,?,?)",
    [
        (1, "Alice Smith", "alice.smith@acme.com", "123-45-6789", "Engineering", 95000),
        (2, "Bob Jones", "bob.jones@acme.com", "234-56-7890", "Engineering", 88000),
        (3, "Carol White", "carol.white@acme.com", "345-67-8901", "Sales", 72000),
        (4, "Dan Brown", "dan.brown@acme.com", "456-78-9012", "Sales", 68000),
        (5, "Eve Davis", "eve.davis@acme.com", "567-89-0123", "HR", 75000),
        (6, "Frank Miller", "frank.miller@acme.com", "678-90-1234", "HR", 71000),
        (7, "Grace Wilson", "grace.wilson@acme.com", "789-01-2345", "Engineering", 92000),
        (8, "Henry Moore", "henry.moore@acme.com", "890-12-3456", "Sales", 69000),
    ],
)
DB.executemany(
    "INSERT INTO policies VALUES (?,?,?)",
    [
        (1, "Leave Policy", "Employees are entitled to 20 days of paid leave per year. Request must be submitted two weeks in advance and approved by the department head."),
        (2, "Remote Work Policy", "Remote work is permitted up to three days per week. Employees must maintain core hours from 10am to 3pm and be reachable via chat or phone."),
        (3, "Expense Policy", "Business expenses must be submitted within 30 days. Receipts are required for any amount over $25. Reimbursement is processed bi-weekly."),
    ],
)
DB.commit()

ROLE_TABLES = {
    "admin": {"employees", "policies"},
    "analyst": {"employees", "policies"},
    "viewer": {"policies"},
}
USER_ROLE = os.getenv("USER_ROLE", "analyst")

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
SSN_RE = re.compile(r"\b\d{3}-?\d{2}-?\d{4}\b")


def mask_pii(text: str) -> str:
    """Mask emails and SSNs in text."""
    text = EMAIL_RE.sub("[EMAIL]", text)
    text = SSN_RE.sub("[SSN]", text)
    return text


def execute_read_only_sql(sql: str, role: str) -> dict:
    """Execute a read-only SELECT query after validating safety constraints."""
    sql = sql.strip().rstrip(";").strip()
    if ";" in sql or "--" in sql or "/*" in sql:
        return {"ok": False, "rows": [], "error": "Forbidden SQL syntax"}
    if not re.match(r"^\s*select\b", sql, re.IGNORECASE):
        return {"ok": False, "rows": [], "error": "Only SELECT allowed"}
    forbidden = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "CREATE", "ATTACH", "PRAGMA", "REPLACE"]
    for word in forbidden:
        if re.search(rf"\b{word}\b", sql, re.IGNORECASE):
            return {"ok": False, "rows": [], "error": f"Forbidden keyword: {word}"}
    allowed = ROLE_TABLES.get(role, set())
    tables = set(re.findall(r"\b(?:from|join)\s+(\w+)", sql, re.IGNORECASE))
    if not tables:
        return {"ok": False, "rows": [], "error": "No tables found"}
    if not tables.issubset(allowed):
        return {"ok": False, "rows": [], "error": "Table access not permitted for role"}
    def authorizer(action, arg1, arg2, arg3, arg4):
        if action in (sqlite3.SQLITE_SELECT, sqlite3.SQLITE_FUNCTION):
            return sqlite3.SQLITE_OK
        if action == sqlite3.SQLITE_READ:
            return sqlite3.SQLITE_OK if arg1 in allowed else sqlite3.SQLITE_DENY
        return sqlite3.SQLITE_DENY

    try:
        DB.set_authorizer(authorizer)
        cur = DB.execute(f"SELECT * FROM ({sql}) LIMIT 10")
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, [mask_pii(str(v)) if isinstance(v, str) else v for v in row])) for row in cur.fetchall()]
        return {"ok": True, "rows": rows, "error": None}
    except sqlite3.Error as e:
        return {"ok": False, "rows": [], "error": str(e)}
    finally:
        DB.set_authorizer(None)


@mcp.tool()
def query_database(sql: str) -> dict:
    """Query the employee and policy tables with a read-only SELECT."""
    return execute_read_only_sql(sql, USER_ROLE)


@mcp.tool()
def search_policies(query: str) -> dict:
    """Search policy documents by keyword."""
    rows = DB.execute(
        "SELECT id, title, body FROM policies WHERE title LIKE ? OR body LIKE ? LIMIT 3",
        (f"%{query}%", f"%{query}%"),
    ).fetchall()
    out = []
    for r in rows:
        body = mask_pii(str(r[2]))[:200]
        out.append({"id": r[0], "title": mask_pii(str(r[1])), "body": body})
    return {"ok": True, "rows": out, "error": None}


if __name__ == "__main__":
    mcp.run()