"""
LocalExpenseServer
Transport: stdio
Purpose: Privacy-first personal finance tracking. Data is kept 100% on the local machine.
"""

import json
from pathlib import Path
from datetime import datetime
from fastmcp import FastMCP

# Define data storage path
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
EXPENSE_FILE = DATA_DIR / "expenses.json"

if not EXPENSE_FILE.exists():
    EXPENSE_FILE.write_text(json.dumps([
        {"id": 1, "date": "2026-10-01", "category": "Food", "amount": 450.0, "currency": "INR", "note": "Groceries at supermarket"},
        {"id": 2, "date": "2026-10-03", "category": "Travel", "amount": 120.0, "currency": "INR", "note": "Metro card recharge"},
        {"id": 3, "date": "2026-10-05", "category": "Bills", "amount": 899.0, "currency": "INR", "note": "Wifi fiber connection"}
    ], indent=2))

mcp = FastMCP("LocalExpenseServer")

MONTHLY_BUDGET_INR = 15000.0


def _load_expenses():
    try:
        return json.loads(EXPENSE_FILE.read_text())
    except Exception:
        return []


def _save_expenses(data):
    EXPENSE_FILE.write_text(json.dumps(data, indent=2))


@mcp.tool()
def add_expense(category: str, amount: float, note: str, currency: str = "INR") -> str:
    """Record a new private expense into the local ledger."""
    expenses = _load_expenses()
    new_id = (max([e.get("id", 0) for e in expenses]) + 1) if expenses else 1
    today = datetime.now().strftime("%Y-%m-%d")
    
    entry = {
        "id": new_id,
        "date": today,
        "category": category.strip().title(),
        "amount": round(float(amount), 2),
        "currency": currency.upper(),
        "note": note.strip()
    }
    expenses.append(entry)
    _save_expenses(expenses)
    
    return f"Expense logged successfully! ID: {new_id} | {entry['category']}: {entry['amount']} {entry['currency']} ('{entry['note']}') on {today}"


@mcp.tool()
def get_monthly_summary() -> str:
    """Get category-wise breakdown, total spending, and count of transactions."""
    expenses = _load_expenses()
    if not expenses:
        return "No expenses recorded yet in local database."
    
    total = sum(e["amount"] for e in expenses)
    by_category = {}
    for e in expenses:
        cat = e.get("category", "General")
        by_category[cat] = by_category.get(cat, 0.0) + e["amount"]
        
    lines = [
        f"📊 **Monthly Expense Summary**",
        f"- Total Transactions: {len(expenses)}",
        f"- Total Spent: ₹{total:,.2f} INR",
        "",
        "**Category Breakdown:**"
    ]
    for cat, amt in sorted(by_category.items(), key=lambda x: x[1], reverse=True):
        pct = (amt / total * 100) if total > 0 else 0
        lines.append(f"  • {cat}: ₹{amt:,.2f} ({pct:.1f}%)")
        
    return "\n".join(lines)


@mcp.tool()
def check_budget_status() -> str:
    """Check current spending against the monthly budget limit (₹15,000 INR)."""
    expenses = _load_expenses()
    total = sum(e["amount"] for e in expenses)
    remaining = MONTHLY_BUDGET_INR - total
    pct_used = (total / MONTHLY_BUDGET_INR) * 100
    
    if total > MONTHLY_BUDGET_INR:
        status = f"⚠️ BUDGET EXCEEDED by ₹{abs(remaining):,.2f}! Total spent: ₹{total:,.2f} / ₹{MONTHLY_BUDGET_INR:,.2f} ({pct_used:.1f}%)"
    elif pct_used >= 80:
        status = f"🟡 WARNING: You have used {pct_used:.1f}% of your budget. Remaining: ₹{remaining:,.2f} INR."
    else:
        status = f"✅ HEALTHY: Spending is within budget ({pct_used:.1f}% used). Remaining: ₹{remaining:,.2f} INR."
    return status


@mcp.resource("resource://finance/rules")
def financial_guidelines() -> str:
    """Returns the user's personal financial guidelines and savings goals."""
    return (
        "USER FINANCIAL RULES:\n"
        "1. Monthly budget cap is ₹15,000 INR.\n"
        "2. Needs (Food, Bills, Rent) should not exceed 50%.\n"
        "3. Prioritize 20% savings target before discretionary spending."
    )


if __name__ == "__main__":
    mcp.run()
