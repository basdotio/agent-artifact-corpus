# SPDX-FileCopyrightText: 2026 The avenir-mcp contributors
# SPDX-License-Identifier: MIT

"""Account-level tools: reconcile with the bank, forecast the balance."""

from __future__ import annotations

import calendar
import logging
from datetime import date, timedelta
from typing import Literal

from fastmcp import Context
from fastmcp.exceptions import ToolError
from mcp.types import InputRequiredResult
from pydantic import Field

from avenir_mcp import app, client, forecast, journal, reconcile, schedule
from avenir_mcp.amounts import Amount
from avenir_mcp.app import WRITE_TAG, mcp
from avenir_mcp.classifier import normalize_payee
from avenir_mcp.confirm import WriteStatus, gate, merged
from avenir_mcp.model import Model
from avenir_mcp.text import MAX_MEMO, MAX_PAYEE, YnabText, untrusted
from avenir_mcp.triage import CARD_CATEGORY, card_payments

logger = logging.getLogger(__name__)


ReconcileStatus = Literal[
    "applied", "confirmation_required", "declined", "nothing_to_do", "difference_found"
]


class ReconcileResult(Model):
    """The outcome of reconcile_account."""

    status: ReconcileStatus
    """Outcome: difference_found (nothing changed; see analysis), confirmation_required, applied,
    declined, or nothing_to_do (already reconciled).
    """
    message: str
    """What happened and what to do next, for the agent to relay."""
    account: str
    """Account name."""
    analysis: reconcile.Analysis
    """The comparison with the bank."""
    adjustment: float | None
    """Amount of the balance adjustment created, if adjust was requested; else null."""
    confirmation: str | None
    """Single-use code confirming exactly this preview, valid 10 minutes; null unless status is
    confirmation_required.
    """
    operation_id: str | None
    """Journal id of the applied operation, for undo_operation; null unless status is applied."""


# YNAB's own group, which holds the single "Inflow: Ready to Assign" category.
READY_TO_ASSIGN_GROUP = "Internal Master Category"


@mcp.tool(
    tags={WRITE_TAG},
    annotations={
        "title": "Reconcile an account with the bank",
        "read_only_hint": False,
        "destructive_hint": True,
        "idempotent_hint": False,
        "open_world_hint": True,
    },
)
async def reconcile_account(  # pylint: disable=too-many-arguments,too-many-locals
    plan_id: str,
    account_id: str,
    bank_balance: Amount,
    ctx: Context,
    *,
    adjust: bool = False,
    confirmation: str | None = None,
) -> ReconcileResult | InputRequiredResult:
    """Compare an account with the balance your bank shows, then reconcile it.

    Give the balance shown by the bank today (currency units). If YNAB's cleared
    balance differs, nothing is written: the result explains the gap with the
    pending transactions, the one whose amount matches the difference
    (`explained_by`) and likely duplicates. Fix those first (with the user), then
    call again. Only if the user wants to accept the remaining gap, call with
    adjust=true: a "Balance adjustment" transaction is added to Ready to Assign.
    When balances match, every cleared transaction is marked reconciled after the
    user confirms (as for apply_categories). undo_operation reverts it.

    Args:
        plan_id: YNAB plan id or 'last-used'.
        account_id: Account to reconcile (from list_accounts).
        bank_balance: Balance shown by the bank, in currency units.
        ctx: The MCP context, used to ask the user.
        adjust: Record the remaining difference as an adjustment.
        confirmation: Code from a previous "confirmation_required" result.

    Returns:
        The comparison with the bank and what was done, or an input request the client answers by
        asking the user (protocol 2026-07-28).

    Raises:
        ToolError: If the account is not in the plan, or the confirmation code is refused.
    """
    logger.info("Tool called: reconcile_account(adjust=%s)", adjust)
    accounts = {a["id"]: a["name"] for a in await client.get_accounts(plan_id)}
    if account_id not in accounts:
        raise ToolError(f"Account {account_id} is not in this plan: use an id from list_accounts.")
    transactions = await client.get_transactions(plan_id)
    analysis = reconcile.analyse(account_id, transactions, bank_balance)
    difference = analysis.difference
    result = ReconcileResult(
        status="nothing_to_do",
        message="Already reconciled: nothing to do.",
        account=untrusted(accounts[account_id]),
        analysis=analysis,
        adjustment=None,
        confirmation=None,
        operation_id=None,
    )
    if difference and not adjust:
        return result.model_copy(
            update={
                "status": "difference_found",
                "message": (
                    f"YNAB's cleared balance differs from the bank by {difference:.2f}. Nothing "
                    "was changed. Check explained_by, uncleared and possible_duplicates with the "
                    "user; call again once fixed, or with adjust=true to record the gap as an "
                    "adjustment."
                ),
            }
        )
    if not difference and not analysis.to_reconcile_count:
        return result
    question = (
        f"Reconcile {result.account}: mark {analysis.to_reconcile_count} "
        "cleared transaction(s) reconciled"
        + (f" and add a balance adjustment of {difference:.2f}?" if difference else "?")
    )
    # The code confirms these exact transactions: any cleared after the preview
    # changes the subject, so the code no longer applies.
    to_reconcile = sorted(
        tx["id"]
        for tx in transactions
        if tx.get("account_id") == account_id
        and not tx.get("deleted")
        and tx.get("cleared") == "cleared"
    )
    subject = {
        "account": account_id,
        "balance": bank_balance,
        "adjust": difference,
        "transactions": to_reconcile,
    }
    stop = await gate(ctx, plan_id, subject, question, confirmation)
    if stop is not None:
        return stop if isinstance(stop, InputRequiredResult) else merged(result, stop)
    adjustment_id = None
    if difference:
        inflow = next(
            (
                c["id"]
                for c in await client.get_categories(plan_id)
                if c.get("category_group_name") == READY_TO_ASSIGN_GROUP
            ),
            None,
        )
        created = await client.create_transactions(
            plan_id,
            account_id,
            [
                {
                    "date": app.today().isoformat(),
                    "amount": difference,
                    "payee_name": "Balance adjustment",
                    "memo": "Entered by reconcile_account",
                    "category_id": inflow,
                }
            ],
        )
        adjustment_id = created["transaction_ids"][0]
        to_reconcile.append(adjustment_id)
    await client.set_transactions_cleared(plan_id, to_reconcile, "reconciled")
    operation_id = journal.Journal(journal.default_path()).record(
        plan_id,
        "reconcile",
        [],
        {"account_id": account_id, "reconciled_ids": to_reconcile, "adjustment_id": adjustment_id},
    )
    return result.model_copy(
        update={
            "status": "applied",
            "message": f"Reconciled. undo_operation with operation_id {operation_id} reverts it.",
            "adjustment": difference or None,
            "operation_id": operation_id,
        }
    )


MAX_FORECAST_MONTHS = 24


class ForecastAssumptions(Model):
    """What the projection assumed, so the user can correct it."""

    recurring: list[forecast.Recurring]
    """Charges and income found recurring in the history."""
    variable_monthly: float
    """Monthly spending besides recurring charges, negative."""
    monthly_income: float
    """Monthly income assumed, besides recurring income."""
    one_offs: list[forecast.OneOff]
    """One-off amounts given by the caller."""
    scheduled: list[schedule.Occurrence]
    """Scheduled transactions of the projected accounts, from tomorrow to the last month;
    they replace what the history suggests for the same payees. Transfers between the
    projected accounts are left out."""


class ForecastResult(Model):
    """A balance projection and what it rests on."""

    message: str
    """The conclusion in one sentence, for the agent to relay."""
    accounts: list[str]
    """Names of the accounts projected together."""
    start_balance: float
    """Their total balance today."""
    assumptions: ForecastAssumptions
    """Everything the projection assumed, to check with the user."""
    months: list[forecast.MonthProjection]
    """The projected months."""
    first_shortfall: str | None
    """First month whose lowest balance is below zero; null if none."""


def _check_horizon(until: str, now: date) -> None:
    """Refuse a forecast horizon that is malformed, past, or too far ahead.

    Args:
        until: Last month to project, YYYY-MM.
        now: Today.

    Raises:
        ToolError: If until is not YYYY-MM, before this month, or more than
            MAX_FORECAST_MONTHS months ahead.
    """
    try:
        year, month = (int(part) for part in until.split("-"))
        date(year, month, 1)
    except ValueError as error:
        raise ToolError(f"until must be a month as YYYY-MM, got {until!r}.") from error
    ahead = (year - now.year) * 12 + month - now.month
    if ahead < 0:
        raise ToolError("until must be the current month or later.")
    if ahead > MAX_FORECAST_MONTHS:
        raise ToolError(f"until must be at most {MAX_FORECAST_MONTHS} months ahead.")


@mcp.tool(
    annotations={
        "title": "Forecast the balance",
        "read_only_hint": True,
        "idempotent_hint": True,
        "open_world_hint": True,
    }
)
async def forecast_balance(  # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals
    plan_id: str,
    until: str,
    account_ids: list[str] | None = None,
    monthly_income: Amount | None = None,
    variable_monthly: Amount | None = None,
    one_offs: list[forecast.OneOff] | None = None,
) -> ForecastResult:
    """Project the balance month by month and say when money would run out.

    Starts from today's balance of the open on-budget accounts (or those given).
    For the current month, what was already spent or received since the 1st is
    deducted from the monthly averages, so only what is left is projected.
    Assumes, and returns as `assumptions` so the user can correct them:
    YNAB's scheduled transactions on their dates (a payee with a schedule is
    projected by it alone; transfers between projected accounts left out),
    charges that recur in the last 4 months (same payee, stable amount), the
    average of all other spending over the last 3 months, and what you pass:
    expected monthly income (default: the last 3 months' non-recurring inflows,
    which may include one-off money such as capital injections) and one-off amounts
    such as a tax bill (negative) or a refund (positive). Amounts in currency
    units. `lowest` is the lowest point within a month; `first_shortfall` is the
    first month it goes below zero. Changes nothing.

    Args:
        plan_id: YNAB plan id or 'last-used'.
        until: Last month to project, YYYY-MM, at most 24 months ahead.
        account_ids: Accounts to include (from list_accounts); default all open
            on-budget accounts.
        monthly_income: Income expected each month, replacing the income found in
            the history (recurring or average) and scheduled in YNAB; default: what
            they show.
        variable_monthly: Monthly spending besides recurring charges (negative);
            default: the last 3 months' average.
        one_offs: Expected one-off amounts: {date YYYY-MM-DD, amount, label}; not
            those already scheduled in YNAB, which are counted.

    Returns:
        The month-by-month projection and the assumptions it rests on.

    Raises:
        ToolError: If until is malformed, in the past or too far ahead, or an account is unknown.
    """
    logger.info("Tool called: forecast_balance")
    now = app.today()
    _check_horizon(until, now)
    accounts = await client.get_accounts(plan_id)
    if account_ids is not None:
        unknown = sorted(set(account_ids) - {a["id"] for a in accounts})
        if unknown:
            raise ToolError(f"Unknown account(s) {', '.join(unknown)}: use ids from list_accounts.")
        chosen = [a for a in accounts if a["id"] in account_ids]
    else:
        chosen = [a for a in accounts if a["on_budget"] and not a["closed"]]
    ids = {a["id"] for a in chosen}
    history = [tx for tx in await client.get_transactions(plan_id) if tx.get("account_id") in ids]
    plans = [
        item
        for item in await client.get_scheduled_transactions(plan_id)
        if not item.get("deleted")
        and item["account_id"] in ids
        and item.get("transfer_account_id") not in ids
        # The income the caller gives replaces every income, scheduled ones too.
        and (monthly_income is None or item["amount"] < 0)
    ]
    # A payee with a schedule is projected by it, not guessed from the history.
    planned = frozenset(
        (normalize_payee(item.get("payee_name") or ""), item["amount"] < 0) for item in plans
    )
    year, month = (int(part) for part in until.split("-"))
    upcoming = schedule.occurrences(
        plans,
        {a["id"]: a["name"] for a in accounts},
        {c["id"]: c["name"] for c in await client.get_categories(plan_id)},
        now + timedelta(days=1),
        date(year, month, calendar.monthrange(year, month)[1]),
    )
    charges = [
        r
        for r in forecast.recurring(history, now)
        if not forecast.is_scheduled(r.payee, r.amount < 0, planned)
    ]
    if monthly_income is not None:
        # The income given replaces what the history suggests, recurring salary included.
        charges = [r for r in charges if r.amount < 0]
    variable = (
        variable_monthly
        if variable_monthly is not None
        else forecast.variable_average(history, now, charges, also=planned)
    )
    income = (
        monthly_income
        if monthly_income is not None
        else forecast.income_average(history, now, charges, also=planned)
    )
    start = client.milliunit_to_amount(
        sum(client.amount_to_milliunit(a["balance"]) for a in chosen)
    )
    spent, received = forecast.month_to_date(history, now, charges, also=planned)
    projection = forecast.project(
        start_balance=start,
        today=now,
        until=until,
        recurring=charges,
        variable_monthly=variable,
        monthly_income=income,
        one_offs=(one_offs or [])
        + [
            forecast.OneOff(date=date.fromisoformat(o.date), amount=o.amount, label=o.payee)
            for o in upcoming
        ],
        spent_this_month=spent,
        received_this_month=received,
    )
    shortfall = projection.first_shortfall
    message = (
        f"The balance goes below zero in {shortfall}."
        if shortfall
        else f"The balance stays above zero until {until}."
    ) + " This rests on the assumptions listed: check them with the user."
    return ForecastResult(
        message=message,
        accounts=[a["name"] for a in chosen],
        start_balance=start,
        assumptions=ForecastAssumptions(
            recurring=charges,
            variable_monthly=variable,
            monthly_income=income,
            one_offs=one_offs or [],
            scheduled=upcoming,
        ),
        months=projection.months,
        first_shortfall=shortfall,
    )


class NewTransaction(Model):
    """A transaction to create; memo and category_id are optional."""

    date: date
    """Date, YYYY-MM-DD, not in the future."""
    amount: Amount
    """Amount in currency units, negative for spending."""
    payee_name: YnabText = Field(min_length=1, max_length=MAX_PAYEE)
    """Payee as it should appear in YNAB; at most 200 characters."""
    memo: YnabText | None = Field(default=None, max_length=MAX_MEMO)
    """Optional note; at most 500 characters."""
    category_id: str | None = None
    """Optional category id."""


class NewTransactionPreview(Model):
    """A transaction to create, as the user sees it."""

    date: str
    """Date, YYYY-MM-DD."""
    amount: float
    """Amount in currency units."""
    payee: str
    """Payee name."""
    category: str | None
    """Category name; null if none was given."""
    memo: str | None
    """Note; null if none."""


class CreateResult(Model):
    """The outcome of create_transactions."""

    status: WriteStatus
    """Outcome: applied, confirmation_required (nothing changed yet; pass the code back once the
    user agrees), declined (the user said no), or nothing_to_do.
    """
    message: str
    """What happened and what to do next, for the agent to relay."""
    account: str
    """Account name."""
    transactions: list[NewTransactionPreview]
    """The transactions, as they will be (or were) created."""
    created_ids: list[str]
    """YNAB ids of the created transactions; empty until applied."""
    duplicate_import_ids: list[str]
    """Import ids YNAB refused as duplicates."""
    confirmation: str | None
    """Single-use code confirming exactly this preview, valid 10 minutes; null unless status is
    confirmation_required.
    """
    operation_id: str | None
    """Journal id of the applied operation, for undo_operation; null unless status is applied."""


def _check_new(
    items: list[NewTransaction], categories: dict[str, str], cards: set[str], now: date
) -> None:
    """Refuse what YNAB would refuse, or what cannot be what the user meant.

    Args:
        items: The transactions to create.
        categories: The plan's category names by id.
        cards: Ids of the categories that pay credit cards.
        now: Today.

    Raises:
        ToolError: If the list is empty, a date is in the future, or a category is not
            in the plan or pays a credit card.
    """
    if not items:
        raise ToolError("Give at least one transaction to create.")
    for item in items:
        if item.date > now:
            raise ToolError(
                f"{item.date} is in the future: YNAB only records transactions that happened."
            )
        category = item.category_id
        if category and category not in categories:
            raise ToolError(
                f"Category {category} is not in this plan: "
                "use a category_id from get_category_balances."
            )
        if category in cards:
            raise ToolError(f"Category {category} {CARD_CATEGORY}")


@mcp.tool(
    tags={WRITE_TAG},
    annotations={
        "title": "Create transactions",
        "read_only_hint": False,
        "destructive_hint": False,
        "idempotent_hint": False,
        "open_world_hint": True,
    },
)
async def create_transactions(  # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals
    plan_id: str,
    account_id: str,
    transactions: list[NewTransaction],
    ctx: Context,
    approved: bool = False,
    confirmation: str | None = None,
) -> CreateResult | InputRequiredResult:
    """Create transactions on an account, e.g. ones the bank import missed, after the user confirms.

    Each transaction: date (YYYY-MM-DD, not in the future), amount in currency
    units (negative for spending), payee_name, and optionally memo and
    category_id. They are created cleared and, unless approved is true, left for
    the user to approve in YNAB. undo_operation deletes them. Confirmation works
    as for apply_categories.

    Args:
        plan_id: YNAB plan id or 'last-used'.
        account_id: Account to add them to (from list_accounts).
        transactions: The transactions to create.
        ctx: The MCP context, used to ask the user.
        approved: Skip YNAB's review step.
        confirmation: Code from a previous "confirmation_required" result.

    Returns:
        The transactions as they will be (or were) created, or an input request the client answers
        by asking the user (protocol 2026-07-28).

    Raises:
        ToolError: If the account or a category is not in the plan, a date is in the
            future, the list is empty, or the confirmation code is refused.
    """
    logger.info("Tool called: create_transactions(n=%d)", len(transactions))
    accounts = {a["id"]: a["name"] for a in await client.get_accounts(plan_id)}
    if account_id not in accounts:
        raise ToolError(f"Account {account_id} is not in this plan: use an id from list_accounts.")
    listed = await client.get_categories(plan_id)
    categories = {c["id"]: c["name"] for c in listed}
    _check_new(transactions, categories, card_payments(listed), app.today())
    preview = [
        NewTransactionPreview(
            date=item.date.isoformat(),
            amount=item.amount,
            payee=untrusted(item.payee_name),
            category=untrusted(categories.get(item.category_id or "")) or None,
            memo=untrusted(item.memo) if item.memo else None,
        )
        for item in transactions
    ]
    result = CreateResult(
        status="applied",
        message="",
        account=untrusted(accounts[account_id]),
        transactions=preview,
        created_ids=[],
        duplicate_import_ids=[],
        confirmation=None,
        operation_id=None,
    )
    lines = [
        f"- {p.date} {p.payee} {p.amount:.2f} ({p.category or 'no category'})" for p in preview[:20]
    ]
    question = f"Create {len(preview)} transaction(s) on {result.account}?\n" + "\n".join(lines)
    subject = {"account": account_id, "items": transactions, "approved": approved}
    stop = await gate(ctx, plan_id, subject, question, confirmation)
    if stop is not None:
        return stop if isinstance(stop, InputRequiredResult) else merged(result, stop)
    created = await client.create_transactions(
        plan_id,
        account_id,
        [item.model_dump(mode="json", exclude_none=True) for item in transactions],
        approved=approved,
    )
    operation_id = journal.Journal(journal.default_path()).record(
        plan_id, "create", [], {"transaction_ids": created["transaction_ids"]}
    )
    return result.model_copy(
        update={
            "message": f"Created. undo_operation with operation_id {operation_id} deletes them.",
            "created_ids": created["transaction_ids"],
            "duplicate_import_ids": created["duplicate_import_ids"],
            "operation_id": operation_id,
        }
    )
