# SPDX-FileCopyrightText: 2026 The avenir-mcp contributors
# SPDX-License-Identifier: MIT

"""In what order, and by when, the debts would be paid off with a fixed monthly sum.

Each month, every debt is charged a twelfth of its yearly rate on its balance, then
gets its minimum payment; what is left of the monthly sum goes to the first debt of
the strategy: the highest rate first (avalanche) or the smallest balance first
(snowball). A debt paid off frees its minimum for the next. Sums are made in
milliunits; interest is rounded to the cent each month, as a lender does.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated, Any, Literal

from pydantic import Field

from avenir_mcp.amounts import MAX_AMOUNT
from avenir_mcp.client import amount_to_milliunit, milliunit_to_amount
from avenir_mcp.forecast import months_before
from avenir_mcp.model import Model
from avenir_mcp.networth import DEBT_TYPES
from avenir_mcp.text import untrusted

MAX_MONTHS = 1200
"""A hundred years: the longest plan simulated."""
DEFAULT_MONTHS = 600
"""Fifty years: past this, a plan says the debts are not paid off."""
PAYMENT_MONTHS = 3
"""Complete months of past payments averaged when no budget or minimum is known."""

Strategy = Literal["avalanche", "snowball", "both"]
"""Highest rate first, smallest balance first, or both to compare them."""
Source = Literal["YNAB", "override", "missing"]
"""Where a term comes from: the loan's details in YNAB, the caller, or nowhere."""


class Override(Model):
    """A debt's interest rate or minimum payment, given by the caller."""

    account: Annotated[str, Field(min_length=1, max_length=200)]
    """The debt account's name (whatever the case) or id, from list_accounts."""
    interest_rate: Annotated[float, Field(ge=0, le=100, allow_inf_nan=False)] | None = None
    """Yearly interest rate in percent, such as 21.9; omit to keep YNAB's."""
    minimum_payment: Annotated[float, Field(ge=0, le=MAX_AMOUNT, allow_inf_nan=False)] | None = None
    """Minimum monthly payment in currency units; omit to keep YNAB's."""


class Debt(Model):
    """A debt account and the terms the plan uses."""

    account_id: str
    """The account's id."""
    name: str
    """Account name, as the user wrote it in YNAB."""
    type: str
    """YNAB account type: creditCard, autoLoan, mortgage…"""
    owed: float
    """What is owed today, in currency units, positive."""
    interest_rate: float
    """Yearly interest rate in percent; 0 when missing."""
    rate_from: Source
    """Where the rate comes from."""
    minimum_payment: float
    """Minimum monthly payment in currency units; 0 when missing."""
    minimum_from: Source
    """Where the minimum payment comes from."""
    escrow: float
    """Escrow in force today (taxes, insurance paid with a mortgage), in currency units:
    paid with the loan, it does not reduce it and is not part of the plan."""


class DebtPayoff(Model):
    """When one debt is paid off, and what it costs."""

    name: str
    """Account name, as the user wrote it in YNAB."""
    payoff_month: str | None
    """The month of its last payment, YYYY-MM; null when not paid off within the plan."""
    months: int | None
    """Payments until it is paid off; null when not paid off within the plan."""
    interest: float
    """Interest charged until then, in currency units."""
    paid: float
    """Everything paid to it, in currency units: what was owed plus the interest."""


class StrategyPlan(Model):
    """One strategy, month by month until the debts are paid off."""

    strategy: Literal["avalanche", "snowball"]
    """avalanche: highest rate first; snowball: smallest balance first."""
    debts: list[DebtPayoff]
    """Each debt in the order it is paid off; those not paid off last."""
    months_to_debt_free: int | None
    """Payments until every debt is paid off; null when that is beyond the plan."""
    debt_free_month: str | None
    """The month of the last payment, YYYY-MM; null when beyond the plan."""
    total_interest: float
    """Interest charged over the plan, in currency units."""
    total_paid: float
    """Everything paid over the plan, in currency units."""


class DebtPayoffPlan(Model):
    """When the debts would be paid off, by strategy, and what each costs."""

    message: str
    """The conclusion in one sentence or two, for the agent to relay."""
    monthly_budget: float
    """What goes to the debts each month, in currency units."""
    budget_from: Literal["given", "minimum payments", "past payments"]
    """Where the monthly budget comes from: the caller, the sum of the minimum payments,
    or the average paid into the debt accounts over the last complete months."""
    first_month: str
    """The month of the first payment, YYYY-MM: next month."""
    debts: list[Debt]
    """The debts and the terms used."""
    plans: list[StrategyPlan]
    """One plan per strategy asked."""
    interest_saved_by_avalanche: float | None
    """Snowball's interest less avalanche's, in currency units; null unless both were
    asked and both end."""
    months_saved_by_avalanche: int | None
    """Snowball's months less avalanche's; null unless both were asked and both end."""
    notes: list[str]
    """What the figures assume, to tell the user."""


def _in_force(values: dict[str, float], today: date) -> float | None:
    """Give the value that holds today in a dated series.

    Args:
        values: Values keyed by the date from which each holds, YYYY-MM-DD.
        today: The day of the question.

    Returns:
        The value of the latest date on or before today; None when there is none.
    """
    held = [day for day in values if day <= today.isoformat()]
    return values[max(held)] if held else None


def _overrides_by_debt(
    accounts: list[dict[str, Any]], overrides: list[Override]
) -> dict[str, Override]:
    """Find the debt each override names, by id or by name whatever the case.

    Args:
        accounts: The debt accounts.
        overrides: The caller's overrides.

    Returns:
        Per account id, its override.

    Raises:
        ValueError: If an override names no debt account, with the debts it could be.
    """
    found: dict[str, Override] = {}
    unknown: list[str] = []
    for item in overrides:
        key = item.account.strip()
        match = next(
            (
                a
                for a in accounts
                if a["id"] == key or a["name"].strip().casefold() == key.casefold()
            ),
            None,
        )
        if match is None:
            unknown.append(item.account)
        else:
            found[match["id"]] = item
    if unknown:
        given = ", ".join(repr(untrusted(name)) for name in unknown)
        names = ", ".join(untrusted(a["name"]) for a in accounts)
        raise ValueError(
            f"Unknown debt account(s) {given}: give names or ids of the open accounts that "
            f"owe money: {names}."
        )
    return found


def _term(given: float | None, values: dict[str, float], today: date) -> tuple[float, Source]:
    """Choose a term: the caller's, else YNAB's in force today, else 0.

    Args:
        given: The caller's value, or None.
        values: YNAB's dated values.
        today: The day of the question.

    Returns:
        The value and where it comes from.
    """
    if given is not None:
        return given, "override"
    held = _in_force(values, today)
    return (held, "YNAB") if held is not None else (0.0, "missing")


def debts_of(
    accounts: list[dict[str, Any]], today: date, overrides: list[Override] | None
) -> list[Debt]:
    """Find the debts to pay off: the open debt accounts that owe money.

    Args:
        accounts: The plan's accounts with their loan terms, as client.get_debt_terms
            gives them.
        today: The day of the question; the terms in force that day are used.
        overrides: Rates and minimum payments the caller gives, or None.

    Returns:
        The debts, in the plan's order of accounts.

    Raises:
        ValueError: If an override names no debt account.
    """
    owing = [
        a for a in accounts if a["type"] in DEBT_TYPES and not a["closed"] and a["balance"] < 0
    ]
    chosen = _overrides_by_debt(owing, overrides or [])
    debts: list[Debt] = []
    for account in owing:
        override = chosen.get(account["id"])
        rate, rate_from = _term(
            override.interest_rate if override else None, account["interest_rates"], today
        )
        minimum, minimum_from = _term(
            override.minimum_payment if override else None, account["minimum_payments"], today
        )
        debts.append(
            Debt(
                account_id=account["id"],
                name=untrusted(account["name"]),
                type=account["type"],
                owed=-account["balance"],
                interest_rate=rate,
                rate_from=rate_from,
                minimum_payment=minimum,
                minimum_from=minimum_from,
                escrow=_in_force(account["escrow_amounts"], today) or 0.0,
            )
        )
    return debts


def needs_history(debts: list[Debt]) -> bool:
    """Say whether past payments are needed to choose a budget: a minimum is missing.

    Args:
        debts: The debts to pay off.

    Returns:
        True when a debt has no minimum payment.
    """
    return any(debt.minimum_from == "missing" for debt in debts)


def _past_payments(debts: list[Debt], transactions: list[dict[str, Any]], today: date) -> int:
    """Average what was paid into the debt accounts over the last complete months.

    A payment is a transfer into a debt account; refunds and charges are not.

    Args:
        debts: The debts to pay off.
        transactions: The plan's transactions, amounts in milliunits.
        today: The day of the question; its month is incomplete and not counted.

    Returns:
        The monthly average, in milliunits.
    """
    ids = {debt.account_id for debt in debts}
    months = months_before(today, PAYMENT_MONTHS)
    paid: int = sum(
        max(tx["amount"], 0)
        for tx in transactions
        if tx["account_id"] in ids
        and not tx.get("deleted")
        and tx["date"][:7] in months
        and tx.get("transfer_account_id")
    )
    return round(paid / PAYMENT_MONTHS)


def _label(index: int) -> str:
    """Name a month from its index.

    Args:
        index: Year times twelve plus the month less one.

    Returns:
        The month, YYYY-MM.
    """
    return f"{index // 12:04d}-{index % 12 + 1:02d}"


def _label_of(start: int, month: int | None) -> str | None:
    """Name the month of a payment.

    Args:
        start: The index of the first month.
        month: The payment's number, 1 for the first; None when there is none.

    Returns:
        The month, YYYY-MM, or None.
    """
    return None if month is None else _label(start + month - 1)


def _priority(strategy: str, debts: list[Debt]) -> list[int]:
    """Order the debts the extra money goes to.

    Args:
        strategy: avalanche or snowball.
        debts: The debts to pay off.

    Returns:
        Their indexes: highest rate first for avalanche, smallest balance first for
        snowball, the other criterion and the name breaking ties.
    """
    if strategy == "avalanche":
        return sorted(
            range(len(debts)),
            key=lambda i: (-debts[i].interest_rate, debts[i].owed, debts[i].name),
        )
    return sorted(
        range(len(debts)), key=lambda i: (debts[i].owed, -debts[i].interest_rate, debts[i].name)
    )


def _schedule(  # pylint: disable=too-many-locals
    strategy: Literal["avalanche", "snowball"],
    debts: list[Debt],
    budget: int,
    start: int,
    max_months: int,
) -> tuple[StrategyPlan, bool]:
    """Pay the debts month by month with one strategy.

    Args:
        strategy: avalanche or snowball.
        debts: The debts to pay off.
        budget: What goes to the debts each month, in milliunits.
        start: The index of the first month (year times twelve plus month less one).
        max_months: The longest plan.

    Returns:
        The plan, and True when the first month's payments did not cover its interest:
        the debt never shrinks.
    """
    owed = [amount_to_milliunit(debt.owed) for debt in debts]
    minimums = [amount_to_milliunit(debt.minimum_payment) for debt in debts]
    interest, paid = [0] * len(debts), [0] * len(debts)
    done: list[int | None] = [None] * len(debts)
    order = _priority(strategy, debts)
    first_total, never, month = sum(owed), False, 0
    while any(owed) and month < max_months and not never:
        month += 1
        for i, balance in enumerate(owed):
            charge = int(round(balance * (debts[i].interest_rate / 100) / 12, -1))
            owed[i] += charge
            interest[i] += charge
        left = budget
        # Every minimum first, then what is left down the strategy's order.
        for i, cap in [*enumerate(minimums), *((i, budget) for i in order)]:
            pay = min(owed[i], left, cap)
            owed[i] -= pay
            paid[i] += pay
            left -= pay
            if not owed[i] and done[i] is None:
                done[i] = month
        never = month == 1 and sum(owed) >= first_total
    # A debt not paid off sorts after every debt that is, so the month it sorts on only
    # has to be one the plan did not reach: another one sorts the same. On its own line,
    # so the pragma covers no more than that month.
    unpaid = month + 1  # pragma: no mutate
    rows = sorted(range(len(debts)), key=lambda i: (done[i] or unpaid, order.index(i)))
    free = None if any(owed) else month
    return (
        StrategyPlan(
            strategy=strategy,
            debts=[
                DebtPayoff(
                    name=debts[i].name,
                    payoff_month=_label_of(start, done[i]),
                    months=done[i],
                    interest=milliunit_to_amount(interest[i]),
                    paid=milliunit_to_amount(paid[i]),
                )
                for i in rows
            ],
            months_to_debt_free=free,
            debt_free_month=_label_of(start, free),
            total_interest=milliunit_to_amount(sum(interest)),
            total_paid=milliunit_to_amount(sum(paid)),
        ),
        never,
    )


def _budget(
    debts: list[Debt], given: float | None, transactions: list[dict[str, Any]] | None, today: date
) -> tuple[int, Literal["given", "minimum payments", "past payments"]]:
    """Choose what goes to the debts each month.

    Args:
        debts: The debts to pay off.
        given: The caller's monthly budget, in currency units, or None.
        transactions: The plan's transactions, needed when a minimum is missing and no
            budget is given; None otherwise.
        today: The day of the question.

    Returns:
        The budget in milliunits, and where it comes from.

    Raises:
        ValueError: If the given budget is below the minimum payments, or no budget can
            be chosen.
    """
    minimums = sum(amount_to_milliunit(debt.minimum_payment) for debt in debts)
    if given is not None:
        if amount_to_milliunit(given) < minimums:
            raise ValueError(
                f"monthly_budget {given:.2f} is less than the minimum payments, "
                f"{milliunit_to_amount(minimums):.2f}: give at least that much."
            )
        return amount_to_milliunit(given), "given"
    past = _past_payments(debts, transactions or [], today) if needs_history(debts) else 0
    if past > minimums:
        return past, "past payments"
    if not minimums:
        raise ValueError(
            "No minimum payment is known and nothing was paid into the debt accounts over "
            f"the last {PAYMENT_MONTHS} complete months: give monthly_budget, or "
            "minimum_payment in overrides."
        )
    return minimums, "minimum payments"


def _notes(  # pylint: disable=too-many-arguments
    *,
    debts: list[Debt],
    budget: int,
    budget_from: str,
    first_month: str,
    max_months: int,
    capped: bool,
) -> list[str]:
    """Write down what the figures assume.

    Args:
        debts: The debts to pay off.
        budget: The monthly budget, in milliunits.
        budget_from: Where the budget comes from.
        first_month: The month of the first payment, YYYY-MM.
        max_months: The longest plan.
        capped: True when a plan did not end within max_months.

    Returns:
        The notes, one sentence each.
    """
    notes = [
        "Rates and minimum payments are those in force today and are assumed fixed; no "
        "new charges are made on the debts.",
        f"Each month, from {first_month}, every debt is charged a twelfth of its yearly "
        "rate on its balance, then gets its minimum payment; the rest of the monthly "
        "budget goes to the first debt of the strategy (avalanche: highest rate first; "
        "snowball: smallest balance first), and a debt paid off frees its minimum for the "
        "next.",
    ]
    if missing := [debt.name for debt in debts if debt.rate_from == "missing"]:
        notes.append(
            f"No interest rate in YNAB for {', '.join(missing)}: counted at 0 %, so the "
            "interest is understated; ask the user for the rate and give it as interest_rate "
            "in overrides (YNAB keeps rates for loans only, not for credit cards)."
        )
    if missing := [debt.name for debt in debts if debt.minimum_from == "missing"]:
        notes.append(
            f"No minimum payment in YNAB for {', '.join(missing)}: counted at 0, so only "
            "what is left of the budget goes there; give minimum_payment in overrides."
        )
    amount = f"{milliunit_to_amount(budget):.2f}"
    if budget_from == "past payments":
        notes.append(
            f"monthly_budget was not given: {amount} is the average paid into the debt "
            f"accounts over the last {PAYMENT_MONTHS} complete months."
        )
    elif budget_from == "minimum payments":
        notes.append(
            f"monthly_budget was not given: {amount} is the sum of the minimum payments, so "
            "nothing extra; give a larger monthly_budget to see how much sooner the debts "
            "would be paid off."
        )
    if escrow := [debt.name for debt in debts if debt.escrow]:
        notes.append(
            f"Escrow ({', '.join(escrow)}) is paid with the loan but does not reduce it: "
            "it is not part of the plan, nor should it be of monthly_budget."
        )
    if capped:
        notes.append(f"The plan stops after {max_months} months: max_months.")
    return notes


def _saved(plans: list[StrategyPlan]) -> float:
    """Say what avalanche saves over snowball in interest.

    Args:
        plans: Both plans, avalanche first.

    Returns:
        Snowball's interest less avalanche's, in currency units.
    """
    difference = plans[1].total_interest - plans[0].total_interest
    # Interest is rounded to the cent every month, so two totals differ by whole cents:
    # rounding their difference to a third decimal changes nothing. The precision is alone
    # on its line, so the pragma covers no more than it.
    to_the_cent = 2  # pragma: no mutate
    return round(difference, to_the_cent)


def _message(
    plans: list[StrategyPlan], debts: list[Debt], budget: int, never: bool, max_months: int
) -> str:
    """Sum the plans up in a sentence or two.

    Args:
        plans: One plan per strategy.
        debts: The debts to pay off.
        budget: The monthly budget, in milliunits.
        never: True when the budget does not cover the first month's interest.
        max_months: The longest plan.

    Returns:
        The conclusion.
    """
    amount = f"{milliunit_to_amount(budget):.2f}"
    owed = f"{sum(debt.owed for debt in debts):.2f}"
    if never:
        return (
            f"At {amount} a month, the payments do not cover the interest charged on the "
            f"{owed} owed: the debt never shrinks. Pay more each month to pay it off."
        )
    first = plans[0]
    if first.months_to_debt_free is None:
        return (
            f"At {amount} a month, the {owed} owed is not paid off within {max_months} "
            f"months: {first.total_interest:.2f} of interest is charged meanwhile."
        )
    message = (
        f"At {amount} a month, the {owed} owed on {len(debts)} "
        f"{'debt' if len(debts) == 1 else 'debts'} is paid off in "
        f"{first.months_to_debt_free} months, by {first.debt_free_month}, with "
        f"{first.total_interest:.2f} of interest ({first.strategy})."
    )
    if len(plans) == 2:
        saved = _saved(plans)
        message += (
            f" Avalanche saves {saved:.2f} of interest over snowball."
            if saved
            else " Avalanche and snowball cost the same here."
        )
    return message


def plan(  # pylint: disable=too-many-arguments,too-many-locals
    debts: list[Debt],
    *,
    today: date,
    strategy: Strategy,
    monthly_budget: float | None = None,
    transactions: list[dict[str, Any]] | None = None,
    max_months: int = DEFAULT_MONTHS,
) -> DebtPayoffPlan:
    """Say in what order, and by when, the debts would be paid off.

    Args:
        debts: The debts to pay off, from debts_of.
        today: The day of the question; payments start next month.
        strategy: avalanche, snowball, or both to compare them.
        monthly_budget: What goes to the debts each month, in currency units; None for
            the minimum payments, or past payments when a minimum is missing.
        transactions: The plan's transactions, when needs_history says so and no budget
            is given; amounts in milliunits.
        max_months: The longest plan.

    Returns:
        The debts and their terms, one plan per strategy, and the comparison.

    Raises:
        ValueError: If the budget is below the minimum payments, or none can be chosen.
    """
    start = today.year * 12 + today.month
    first_month = _label(start)
    if not debts:
        return DebtPayoffPlan(
            message="No open debt account owes money: nothing to pay off.",
            monthly_budget=monthly_budget or 0.0,
            budget_from="given" if monthly_budget is not None else "minimum payments",
            first_month=first_month,
            debts=[],
            plans=[],
            interest_saved_by_avalanche=None,
            months_saved_by_avalanche=None,
            notes=[],
        )
    budget, budget_from = _budget(debts, monthly_budget, transactions, today)
    asked: list[Literal["avalanche", "snowball"]] = (
        ["avalanche", "snowball"] if strategy == "both" else [strategy]
    )
    plans, never = [], False
    for name in asked:
        found, shrinks_not = _schedule(name, debts, budget, start, max_months)
        plans.append(found)
        never = never or shrinks_not
    saved = months = None
    if len(plans) == 2 and not never:
        fast, slow = plans[0].months_to_debt_free, plans[1].months_to_debt_free
        if fast is not None and slow is not None:
            saved = _saved(plans)
            months = slow - fast
    return DebtPayoffPlan(
        message=_message(plans, debts, budget, never, max_months),
        monthly_budget=milliunit_to_amount(budget),
        budget_from=budget_from,
        first_month=first_month,
        debts=debts,
        plans=plans,
        interest_saved_by_avalanche=saved,
        months_saved_by_avalanche=months,
        notes=_notes(
            debts=debts,
            budget=budget,
            budget_from=budget_from,
            first_month=first_month,
            max_months=max_months,
            capped=not never and any(p.months_to_debt_free is None for p in plans),
        ),
    )
