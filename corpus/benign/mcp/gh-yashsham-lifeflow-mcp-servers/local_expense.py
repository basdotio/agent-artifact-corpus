"""
LocalExpenseServer
Transport: stdio
Purpose: Privacy-first personal finance tracking. Data is kept 100% on the local machine.
Features:
  - Add expense with customizable default currency (defaults to INR)
  - Date-range filtering for expenses (start_date, end_date)
  - Delete expense by ID or clear recent
  - Dynamic user-updatable financial guidelines and budget caps
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional
from fastmcp import FastMCP

# Define data storage paths
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
EXPENSE_FILE = DATA_DIR / "expenses.json"
RULES_FILE = DATA_DIR / "financial_rules.json"

DEFAULT_RULES = {
    "monthly_budget": 15000.0,
    "default_currency": "INR",
    "needs_cap_pct": 50.0,
    "savings_target_pct": 20.0,
    "notes": "Default personal finance guidelines"
}

if not RULES_FILE.exists():
    RULES_FILE.write_text(json.dumps(DEFAULT_RULES, indent=2))

if not EXPENSE_FILE.exists():
    EXPENSE_FILE.write_text(json.dumps([
        {"id": 1, "date": "2026-10-01", "category": "Food", "amount": 450.0, "currency": "INR", "note": "Groceries at supermarket"},
        {"id": 2, "date": "2026-10-03", "category": "Travel", "amount": 120.0, "currency": "INR", "note": "Metro card recharge"},
        {"id": 3, "date": "2026-10-05", "category": "Bills", "amount": 899.0, "currency": "INR", "note": "Wifi fiber connection"}
    ], indent=2))

mcp = FastMCP("LocalExpenseServer")


def _load_rules() -> dict:
    try:
        data = json.loads(RULES_FILE.read_text())
        return {**DEFAULT_RULES, **data}
    except Exception:
        return DEFAULT_RULES.copy()


def _save_rules(rules: dict):
    RULES_FILE.write_text(json.dumps(rules, indent=2))


def _load_expenses() -> list:
    try:
        return json.loads(EXPENSE_FILE.read_text())
    except Exception:
        return []


def _save_expenses(data: list):
    EXPENSE_FILE.write_text(json.dumps(data, indent=2))


@mcp.tool()
def add_expense(category: str, amount: float, note: str = "", currency: Optional[str] = None) -> str:
    """Record a new private expense into the local ledger. Currency defaults to active default currency (INR) unless specified."""
    rules = _load_rules()
    active_currency = (currency or rules.get("default_currency", "INR")).strip().upper()
    
    expenses = _load_expenses()
    new_id = (max([e.get("id", 0) for e in expenses]) + 1) if expenses else 1
    today = datetime.now().strftime("%Y-%m-%d")
    
    entry = {
        "id": new_id,
        "date": today,
        "category": category.strip().title(),
        "amount": round(float(amount), 2),
        "currency": active_currency,
        "note": note.strip()
    }
    expenses.append(entry)
    _save_expenses(expenses)
    
    return f"✅ Expense logged! [ID: {new_id}] {entry['category']}: {entry['amount']} {entry['currency']} ('{entry['note']}') on {today}"


@mcp.tool()
def get_all_expenses(limit: int = 50) -> str:
    """Retrieve and list all recorded expenses from the local database in reverse chronological order."""
    expenses = _load_expenses()
    if not expenses:
        return "No expenses recorded yet in local database."

    rules = _load_rules()
    currency = rules.get("default_currency", "INR")
    
    # Sort by date / id desc
    sorted_expenses = sorted(expenses, key=lambda x: (x.get("date", ""), x.get("id", 0)), reverse=True)[:limit]
    total = sum(e.get("amount", 0.0) for e in sorted_expenses)
    
    lines = [
        f"📋 **All Local Expenses** (Showing {len(sorted_expenses)} of {len(expenses)} items, Total: {total:,.2f} {currency})",
        ""
    ]
    for e in sorted_expenses:
        note_str = f" - *{e.get('note')}*" if e.get("note") else ""
        lines.append(f"• `[ID {e['id']}]` {e.get('date')} | **{e.get('category')}**: {e.get('amount'):,.2f} {e.get('currency', currency)}{note_str}")
        
    return "\n".join(lines)


@mcp.tool()
def get_expense_by_id(expense_id: int) -> str:
    """Retrieve details of a specific expense by its unique ID."""
    expenses = _load_expenses()
    for e in expenses:
        if e.get("id") == expense_id:
            return (
                f"🔍 **Expense Details [ID {e['id']}]**\n"
                f"- **Date:** {e.get('date')}\n"
                f"- **Category:** {e.get('category')}\n"
                f"- **Amount:** {e.get('amount'):,.2f} {e.get('currency', 'INR')}\n"
                f"- **Note:** {e.get('note') or 'None'}"
            )
    return f"❌ Expense with ID {expense_id} not found."


@mcp.tool()
def get_expenses_by_date_range(start_date: Optional[str] = None, end_date: Optional[str] = None, category: Optional[str] = None) -> str:
    """Filter and view expenses by date range (format: YYYY-MM-DD) and optional category."""
    expenses = _load_expenses()
    if not expenses:
        return "No expenses recorded yet in local database."
    
    filtered = []
    for e in expenses:
        e_date = e.get("date", "")
        if start_date and e_date < start_date:
            continue
        if end_date and e_date > end_date:
            continue
        if category and e.get("category", "").lower() != category.strip().lower():
            continue
        filtered.append(e)

    if not filtered:
        return f"No expenses found matching the criteria (Start: {start_date or 'Any'}, End: {end_date or 'Any'}, Category: {category or 'All'})."

    total = sum(e.get("amount", 0.0) for e in filtered)
    lines = [
        f"📅 **Expense Records** ({len(filtered)} items, Total: ₹{total:,.2f})",
        f"Filters: Start={start_date or 'Beginning'}, End={end_date or 'Today'}, Category={category or 'All'}",
        ""
    ]
    for e in filtered:
        lines.append(f"• `[ID {e['id']}]` {e['date']} | **{e['category']}**: {e['amount']} {e.get('currency', 'INR')} - *{e.get('note', '')}*")

    return "\n".join(lines)


@mcp.tool()
def delete_expense(expense_id: int) -> str:
    """Delete an expense entry from the local database by its ID."""
    expenses = _load_expenses()
    target = None
    remaining = []
    
    for e in expenses:
        if e.get("id") == expense_id:
            target = e
        else:
            remaining.append(e)
            
    if not target:
        return f"❌ Expense with ID {expense_id} not found."
        
    _save_expenses(remaining)
    return f"🗑️ Deleted expense ID {expense_id} ({target['category']}: {target['amount']} {target.get('currency', 'INR')} - '{target.get('note')}')"


@mcp.tool()
def update_financial_rules(monthly_budget: Optional[float] = None, default_currency: Optional[str] = None, savings_target_pct: Optional[float] = None, needs_cap_pct: Optional[float] = None) -> str:
    """Update personal financial rules: monthly budget cap, default currency (e.g. INR, USD), savings target percentage, etc."""
    rules = _load_rules()
    changes = []
    
    if monthly_budget is not None and monthly_budget > 0:
        rules["monthly_budget"] = round(float(monthly_budget), 2)
        changes.append(f"Monthly Budget: {rules['monthly_budget']:,.2f}")
        
    if default_currency:
        rules["default_currency"] = default_currency.strip().upper()
        changes.append(f"Default Currency: {rules['default_currency']}")
        
    if savings_target_pct is not None:
        rules["savings_target_pct"] = round(float(savings_target_pct), 1)
        changes.append(f"Savings Target: {rules['savings_target_pct']}%")
        
    if needs_cap_pct is not None:
        rules["needs_cap_pct"] = round(float(needs_cap_pct), 1)
        changes.append(f"Needs Cap: {rules['needs_cap_pct']}%")
        
    if not changes:
        return "No rule changes specified."
        
    _save_rules(rules)
    return "⚙️ **Financial Rules Updated Successfully!**\n" + "\n".join(f"- {c}" for c in changes)


@mcp.tool()
def get_monthly_summary(year_month: Optional[str] = None) -> str:
    """Get category-wise breakdown, total spending, and count of transactions. Optional year_month format: YYYY-MM."""
    expenses = _load_expenses()
    if not expenses:
        return "No expenses recorded yet in local database."
    
    if year_month:
        expenses = [e for e in expenses if e.get("date", "").startswith(year_month)]
        if not expenses:
            return f"No expenses recorded for month {year_month}."

    total = sum(e["amount"] for e in expenses)
    by_category = {}
    for e in expenses:
        cat = e.get("category", "General")
        by_category[cat] = by_category.get(cat, 0.0) + e["amount"]
        
    rules = _load_rules()
    currency = rules.get("default_currency", "INR")
    
    lines = [
        f"📊 **Monthly Expense Summary** {f'({year_month})' if year_month else ''}",
        f"- Total Transactions: {len(expenses)}",
        f"- Total Spent: {total:,.2f} {currency}",
        "",
        "**Category Breakdown:**"
    ]
    for cat, amt in sorted(by_category.items(), key=lambda x: x[1], reverse=True):
        pct = (amt / total * 100) if total > 0 else 0
        lines.append(f"  • {cat}: {amt:,.2f} {currency} ({pct:.1f}%)")
        
    return "\n".join(lines)


@mcp.tool()
def check_budget_status() -> str:
    """Check current spending against the active user-configured budget limit."""
    rules = _load_rules()
    monthly_budget = rules.get("monthly_budget", 15000.0)
    currency = rules.get("default_currency", "INR")
    
    expenses = _load_expenses()
    # Current month expenses
    curr_ym = datetime.now().strftime("%Y-%m")
    curr_expenses = [e for e in expenses if e.get("date", "").startswith(curr_ym)]
    
    total = sum(e["amount"] for e in curr_expenses)
    remaining = monthly_budget - total
    pct_used = (total / monthly_budget * 100) if monthly_budget > 0 else 0
    
    if total > monthly_budget:
        status = f"⚠️ BUDGET EXCEEDED by {abs(remaining):,.2f} {currency}! Spent: {total:,.2f} / {monthly_budget:,.2f} {currency} ({pct_used:.1f}%)"
    elif pct_used >= 80:
        status = f"🟡 WARNING: You have used {pct_used:.1f}% of your budget. Remaining: {remaining:,.2f} {currency}."
    else:
        status = f"✅ HEALTHY: Spending is within budget ({pct_used:.1f}% used). Remaining: {remaining:,.2f} {currency}."
    return status


@mcp.resource("resource://finance/rules")
def financial_guidelines() -> str:
    """Returns the user's dynamic personal financial guidelines and savings goals."""
    rules = _load_rules()
    return (
        f"USER FINANCIAL GUIDELINES (Dynamic):\n"
        f"1. Monthly Budget Cap: {rules.get('monthly_budget', 15000.0):,.2f} {rules.get('default_currency', 'INR')}\n"
        f"2. Default Ledger Currency: {rules.get('default_currency', 'INR')}\n"
        f"3. Maximum Needs Cap (Food/Rent/Bills): {rules.get('needs_cap_pct', 50.0)}%\n"
        f"4. Minimum Savings Target: {rules.get('savings_target_pct', 20.0)}%\n"
        f"5. Strategy: Zero unencrypted personal financial data leaves local disk."
    )


if __name__ == "__main__":
    mcp.run()

