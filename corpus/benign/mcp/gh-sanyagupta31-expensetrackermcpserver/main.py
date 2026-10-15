import sqlite3
from pathlib import Path

from fastmcp import FastMCP


BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "expenses.db"
CATEGORIES_PATH = BASE_DIR / "categories.json"

mcp = FastMCP(name="ExpenseTracker")

def init_db():
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS expenses(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                subcategory TEXT DEFAULT '',
                note TEXT DEFAULT ''
            )
            """
        )

init_db()

@mcp.tool()
def add_expense(
    date: str,
    amount: float,
    category: str,
    subcategory: str = "",
    note: str = "",
) -> dict[str, int | str]:
    """Add a new expense entry to the database."""
    with sqlite3.connect(DB_PATH) as connection:
        cursor = connection.execute(
            """
            INSERT INTO expenses(date, amount, category, subcategory, note)
            VALUES (?, ?, ?, ?, ?)
            """,
            (date, amount, category, subcategory, note),
        )
        return {"status": "ok", "id": cursor.lastrowid}


@mcp.tool()
def list_expenses(start_date: str, end_date: str) -> list[dict[str, object]]:
    """List all expense entries in an inclusive date range."""
    with sqlite3.connect(DB_PATH) as connection:
        cursor = connection.execute(
            """
            SELECT id, date, amount, category, subcategory, note
            FROM expenses
            WHERE date BETWEEN ? AND ?
            ORDER BY id ASC
            """,
            (start_date, end_date),
        )
        columns = [description[0] for description in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]


@mcp.tool()
def summarize(
    start_date: str, end_date: str, category: str | None = None
) -> list[dict[str, object]]:
    """Summarize expenses by category within an inclusive date range."""
    with sqlite3.connect(DB_PATH) as connection:
        query = (
            """
            SELECT category, SUM(amount) AS total_amount
            FROM expenses
            WHERE date BETWEEN ? AND ?
            """
        )
        params = [start_date, end_date]
        if category:
            query += "AND category = ?"
            params.append(category)
        query += "GROUP BY category ORDER BY category ASC"
        cursor = connection.execute(query, params)
        columns = [description[0] for description in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]


@mcp.resource("expense://categories", mime_type="application/json")
def categories() -> str:
    """Return the supported expense categories and subcategories."""
    return CATEGORIES_PATH.read_text(encoding="utf-8")


if __name__ == "__main__":
    mcp.run()