from fastmcp import FastMCP
import os
import sqlite3
from typing import Optional


# ============================================================
# FILE PATHS
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB_PATH = os.path.join(BASE_DIR, "expense.db")
CATEGORIES_PATH = os.path.join(BASE_DIR, "categories.json")


# ============================================================
# CREATE MCP SERVER
# ============================================================

mcp = FastMCP("ExpenseTracker")


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

def init_db() -> None:
    """Create the expenses table if it does not already exist."""

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                subcategory TEXT DEFAULT '',
                note TEXT DEFAULT ''
            )
        """)


# Initialize database when server starts
init_db()


# ============================================================
# TOOL 1: ADD EXPENSE
# ============================================================

@mcp.tool()
def add_expense(
    date: str,
    amount: float,
    category: str,
    subcategory: str = "",
    note: str = ""
) -> dict:
    """Add a new expense to the database."""

    with sqlite3.connect(DB_PATH) as conn:

        cursor = conn.execute(
            """
            INSERT INTO expenses
            (date, amount, category, subcategory, note)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                date,
                amount,
                category,
                subcategory,
                note
            )
        )

        return {
            "status": "ok",
            "id": cursor.lastrowid
        }


# ============================================================
# TOOL 2: LIST EXPENSES
# ============================================================

@mcp.tool()
def list_expenses(
    start_date: str,
    end_date: str
) -> list:
    """List expense entries within an inclusive date range."""

    with sqlite3.connect(DB_PATH) as conn:

        cursor = conn.execute(
            """
            SELECT
                id,
                date,
                amount,
                category,
                subcategory,
                note
            FROM expenses
            WHERE date BETWEEN ? AND ?
            ORDER BY id ASC
            """,
            (
                start_date,
                end_date
            )
        )

        columns = [
            description[0]
            for description in cursor.description
        ]

        rows = cursor.fetchall()

        return [
            dict(zip(columns, row))
            for row in rows
        ]


# ============================================================
# TOOL 3: SUMMARIZE EXPENSES
# ============================================================

@mcp.tool()
def summarize(
    start_date: str,
    end_date: str,
    category: Optional[str] = None
) -> list:
    """Summarize expenses by category within an inclusive date range."""

    with sqlite3.connect(DB_PATH) as conn:

        query = """
            SELECT
                category,
                SUM(amount) AS total_amount
            FROM expenses
            WHERE date BETWEEN ? AND ?
        """

        params = [
            start_date,
            end_date
        ]

        # If category is provided,
        # add an additional filter.
        if category:
            query += """
                AND category = ?
            """

            params.append(category)

        # Group results by category.
        query += """
            GROUP BY category
            ORDER BY category ASC
        """

        cursor = conn.execute(
            query,
            params
        )

        columns = [
            description[0]
            for description in cursor.description
        ]

        rows = cursor.fetchall()

        return [
            dict(zip(columns, row))
            for row in rows
        ]


# ============================================================
# RESOURCE: CATEGORIES
# ============================================================

@mcp.resource(
    "expense://categories",
    mime_type="application/json"
)
def categories() -> str:
    """Return available expense categories."""

    with open(
        CATEGORIES_PATH,
        "r",
        encoding="utf-8"
    ) as file:

        return file.read()


# ============================================================
# START MCP SERVER
# ============================================================

if __name__ == "__main__":
    mcp.run()