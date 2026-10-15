import asyncio
import csv
import importlib
import os
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

@pytest.fixture
def app(tmp_path, monkeypatch):
    # Use a temporary database so real expenses remain untouched.
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "test.db"))

    # Import or reload after setting the database path.
    if "main" in sys.modules:
        module = importlib.reload(sys.modules["main"])
    else:
        module = importlib.import_module("main")

    # Keep generated CSV files inside the temporary test directory.
    module.EXPORT_DIR = str(tmp_path / "exports")
    os.makedirs(module.EXPORT_DIR, exist_ok=True)

    return module


def test_expense_crud(app):
    # CREATE
    created = asyncio.run(
        app.manage_expenses(
            action=app.CRUDAction.CREATE,
            title="Dinner",
            amount=500,
            category="Food",
            date="2026-10-09",
            description="Test expense",
        )
    )

    assert created["message"] == "Expense created"
    expense_id = created["id"]

    # READ
    expenses = asyncio.run(
        app.manage_expenses(action=app.CRUDAction.READ)
    )

    assert len(expenses) == 1
    assert expenses[0]["title"] == "Dinner"
    assert expenses[0]["amount"] == 500

    # UPDATE
    updated = asyncio.run(
        app.manage_expenses(
            action=app.CRUDAction.UPDATE,
            expense_id=expense_id,
            amount=750,
        )
    )

    assert updated["message"] == "Expense updated"

    expenses = asyncio.run(
        app.manage_expenses(action=app.CRUDAction.READ)
    )

    assert expenses[0]["amount"] == 750
    assert expenses[0]["title"] == "Dinner"

    # DELETE
    deleted = asyncio.run(
        app.manage_expenses(
            action=app.CRUDAction.DELETE,
            expense_id=expense_id,
        )
    )

    assert deleted["message"] == "Expense deleted"

    expenses = asyncio.run(
        app.manage_expenses(action=app.CRUDAction.READ)
    )

    assert expenses == []


def test_expense_create_requires_fields(app):
    result = asyncio.run(
        app.manage_expenses(
            action=app.CRUDAction.CREATE,
            title="Dinner",
        )
    )

    assert "error" in result


def test_large_expense_export_threshold(app):
    # Insert 50 test records directly into the isolated database.
    with sqlite3.connect(app.DB) as conn:
        conn.executemany(
            """
            INSERT INTO expenses
            (title, amount, category, date, description)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                (
                    f"Expense {i}",
                    100,
                    "Food",
                    "2026-10-09",
                    "Test",
                )
                for i in range(50)
            ],
        )

    # Exactly 50 records should return JSON-style records.
    result_50 = asyncio.run(
        app.manage_expenses(action=app.CRUDAction.READ)
    )

    assert isinstance(result_50, list)
    assert len(result_50) == 50

    # Add one more record.
    with sqlite3.connect(app.DB) as conn:
        conn.execute(
            """
            INSERT INTO expenses
            (title, amount, category, date, description)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("Expense 51", 200, "Travel", "2026-10-09", "Test"),
        )

    # 51 records should trigger CSV export.
    result_51 = asyncio.run(
        app.manage_expenses(action=app.CRUDAction.READ)
    )

    assert isinstance(result_51, dict)
    assert result_51["export_required"] is True
    assert result_51["record_count"] == 51

    csv_path = os.path.join(
        app.EXPORT_DIR,
        result_51["filename"],
    )

    assert os.path.exists(csv_path)

    with open(csv_path, newline="", encoding="utf-8") as file:
        rows = list(csv.reader(file))

    # One header row plus 51 expense records.
    assert len(rows) == 52



def test_budget_crud(app):
    create = asyncio.run(
        app.manage_budgets(
            action=app.CRUDAction.CREATE,
            category="Food",
            amount=1000,
            month="2026-10"
        )
    )
    budget_id = create["id"]
    assert create["message"] == "Budget created"

    budgets = asyncio.run(
        app.manage_budgets(action=app.CRUDAction.READ, month="2026-10")
    )
    assert any(b["id"] == budget_id and b["amount"] == 1000 for b in budgets)

    update = asyncio.run(
        app.manage_budgets(
            action=app.CRUDAction.UPDATE,
            budget_id=budget_id,
            amount=1500
        )
    )
    assert update["message"] == "Budget updated"

    budgets = asyncio.run(
        app.manage_budgets(action=app.CRUDAction.READ, month="2026-10")
    )
    assert any(b["id"] == budget_id and b["amount"] == 1500 for b in budgets)

    delete = asyncio.run(
        app.manage_budgets(
            action=app.CRUDAction.DELETE,
            budget_id=budget_id
        )
    )
    assert delete["message"] == "Budget deleted"

    budgets = asyncio.run(
        app.manage_budgets(action=app.CRUDAction.READ, month="2026-10")
    )
    assert not any(b["id"] == budget_id for b in budgets)


def test_budget_create_requires_fields(app):
    result = asyncio.run(
        app.manage_budgets(
            action=app.CRUDAction.CREATE,
            category="Food"
        )
    )
    assert "error" in result


def test_budget_update_and_delete_missing_ids(app):
    update = asyncio.run(
        app.manage_budgets(
            action=app.CRUDAction.UPDATE,
            budget_id=99999
        )
    )
    assert update["error"] == "Budget not found"

    delete = asyncio.run(
        app.manage_budgets(
            action=app.CRUDAction.DELETE,
            budget_id=99999
        )
    )
    assert delete["error"] == "Budget not found"



def test_budget_vs_expense_calculation(app):
    asyncio.run(
        app.manage_budgets(
            action=app.CRUDAction.CREATE,
            category="Food",
            amount=1000,
            month="2026-10"
        )
    )
    asyncio.run(
        app.manage_expenses(
            action=app.CRUDAction.CREATE,
            title="Groceries",
            amount=600,
            category="Food",
            date="2026-10-05"
        )
    )

    result = asyncio.run(
        app.budget_vs_expense(month="2026-10", category="Food")
    )

    assert result["budget"] == 1000
    assert result["expense"] == 600
    assert result["remaining"] == 400
    assert result["over_budget"] is False


def test_budget_vs_expense_over_budget(app):
    asyncio.run(
        app.manage_budgets(
            action=app.CRUDAction.CREATE,
            category="Food",
            amount=500,
            month="2026-10"
        )
    )
    asyncio.run(
        app.manage_expenses(
            action=app.CRUDAction.CREATE,
            title="Groceries",
            amount=700,
            category="Food",
            date="2026-10-05"
        )
    )

    result = asyncio.run(
        app.budget_vs_expense(month="2026-10", category="Food")
    )

    assert result["remaining"] == -200
    assert result["over_budget"] is True


def test_budget_vs_expense_without_data(app):
    result = asyncio.run(
        app.budget_vs_expense(month="2099-01")
    )

    assert result["budget"] == 0
    assert result["expense"] == 0
    assert result["remaining"] == 0
    assert result["over_budget"] is False



def test_financial_health_score(app):
    asyncio.run(
        app.manage_budgets(
            action=app.CRUDAction.CREATE,
            category="Food",
            amount=1000,
            month="2026-10"
        )
    )
    asyncio.run(
        app.manage_expenses(
            action=app.CRUDAction.CREATE,
            title="Groceries",
            amount=400,
            category="Food",
            date="2026-10-05"
        )
    )

    result = asyncio.run(
        app.financial_health_score(month="2026-10")
    )

    assert result["score"] == 100
    assert result["status"] == "Excellent"
    assert result["budget"] == 1000
    assert result["expense"] == 400


def test_financial_health_score_without_budget(app):
    result = asyncio.run(
        app.financial_health_score(month="2099-01")
    )

    assert result["score"] == 0
    assert result["status"] == "No budget available"


def test_financial_health_score_over_budget(app):
    asyncio.run(
        app.manage_budgets(
            action=app.CRUDAction.CREATE,
            category="Food",
            amount=1000,
            month="2026-10"
        )
    )
    asyncio.run(
        app.manage_expenses(
            action=app.CRUDAction.CREATE,
            title="Groceries",
            amount=1200,
            category="Food",
            date="2026-10-05"
        )
    )

    result = asyncio.run(
        app.financial_health_score(month="2026-10")
    )

    assert result["score"] == 30
    assert result["status"] == "Needs attention"



def test_seed_test_expenses(app):
    result = asyncio.run(app.seed_test_expenses(count=5))

    assert result["count"] == 5

    expenses = asyncio.run(
        app.manage_expenses(action=app.CRUDAction.READ)
    )
    assert len(expenses) == 5


def test_seed_test_expenses_invalid_counts(app):
    for count in (0, 101):
        result = asyncio.run(
            app.seed_test_expenses(count=count)
        )
        assert "error" in result


def test_expense_summary_resource(app):
    result = asyncio.run(app.expense_summary())

    assert "Total Budget:" in result
    assert "Total Expenses:" in result
    assert "Remaining:" in result


def test_expense_categories_resource(app):
    result = asyncio.run(app.expense_categories())

    for category in ("Food", "Travel", "Bills", "Shopping", "Education"):
        assert category in result


def test_prompts(app):
    financial = asyncio.run(app.financial_review())
    advice = asyncio.run(app.budget_advice())

    assert "financial situation" in financial.lower()
    assert "budget" in advice.lower()
    assert "expenses" in advice.lower()
