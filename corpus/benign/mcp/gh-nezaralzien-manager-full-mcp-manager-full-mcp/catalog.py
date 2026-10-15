"""Resource catalog built from the live Manager.io OpenAPI document.

Manager exposes its whole API surface (~650 paths) as an OpenAPI document at the
API base URL. We turn that into a catalog of *resources*, each with the four
operations the permission layer can gate: read / create / update / delete.

Nothing here is hand-curated except the group labels and a handful of
list<->form pairings Manager spells irregularly, so a Manager upgrade that adds
new document types shows up automatically.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any

OPS = ("read", "create", "update", "delete")

# Writes to these are never offered: they change who can reach the books.
LOCKED_WRITE_PREFIXES = ("access-token", "user-permissions", "customer-portal")

# Groups whose writes reshape the books themselves rather than record a
# transaction. These are the ones the old server refused outright, and the ones
# a wrong tick hurts most, so the panel paints them red and asks twice.
HIGH_RISK_GROUPS = frozenset(
    {"security", "accounts", "starting_balances", "tax", "currencies", "customization"}
)
HIGH_RISK_NAMES = frozenset({"bank_reconciliations", "lock_date", "summary"})

RISK_NOTES: dict[str, str] = {
    "security": (
        "Controls who can reach these books. Writes are permanently blocked here."
    ),
    "accounts": (
        "Account definitions decide how every past and future transaction is "
        "classified. Editing or deleting one can move or orphan whole balances."
    ),
    "starting_balances": (
        "Opening balances feed every period after them. A wrong figure here "
        "silently shifts every report."
    ),
    "tax": (
        "Tax codes and withholding rules apply to documents that already exist, "
        "so a change can restate filed tax totals."
    ),
    "currencies": (
        "Base currency and exchange rates revalue every foreign-currency "
        "transaction in the books."
    ),
    "customization": (
        "Business-wide settings: lock date, custom fields, themes, email "
        "templates. They change behaviour everywhere at once."
    ),
    "bank_reconciliations": (
        "Reconciliation records are audit evidence that a bank account was "
        "checked against the statement."
    ),
    "lock_date": (
        "The lock date is what stops closed periods from being edited. Opening "
        "it up exposes filed periods to change."
    ),
    "summary": "The Summary form defines the main dashboard for the business.",
}


def risk_for(name: str, group: str) -> tuple[str, str]:
    """('high'|'normal', explanation) for one resource."""
    if name in HIGH_RISK_NAMES:
        return "high", RISK_NOTES.get(name, "")
    if group in HIGH_RISK_GROUPS:
        return "high", RISK_NOTES.get(group, "")
    return "normal", ""

# list stems Manager spells differently from the form stem.
_PAIR_OVERRIDES = {
    "bank-or-cash-account": "bank-and-cash-accounts",
    "billable-time-entry": "billable-time",
    "inventment": "investments",  # Manager's own spelling of the investment form
}

GROUPS: list[tuple[str, str]] = [
    ("parties", "Customers & Suppliers"),
    ("sales", "Sales"),
    ("purchases", "Purchases"),
    ("banking", "Banking & Cash"),
    ("inventory", "Inventory"),
    ("payroll", "Payroll & Expense Claims"),
    ("assets", "Fixed Assets, Intangibles & Investments"),
    ("ledger", "General Ledger"),
    ("projects", "Projects, Divisions & Folders"),
    ("tax", "Tax"),
    ("currencies", "Currencies & Exchange Rates"),
    ("recurring", "Recurring Transactions"),
    ("starting_balances", "Starting Balances"),
    ("accounts", "Chart of Accounts & Account Definitions"),
    ("reports", "Reports & Analysis"),
    ("customization", "Custom Fields, Themes & Settings"),
    ("attachments", "Attachments, Emails & History"),
    ("security", "Account Security (locked)"),
    ("other", "Other"),
]
GROUP_LABELS = dict(GROUPS)
GROUP_ORDER = [g for g, _ in GROUPS]

_REPORT_EXACT = {
    "summary",
    "transactions",
    "trial-balance",
    "balance-sheet",
    "balance-sheet-by-group",
    "balance-sheet-transactions",
    "profit-and-loss-statement",
    "profit-and-loss-statement-by-group",
    "cash-flow-statement",
    "statement-of-changes-in-equity",
    "aged-receivables",
    "aged-payables",
    "custom-report",
    "report-transformation-report",
    "forecast",
    "forecast-profit-and-loss-statement",
    "division-exception-report",
    "receipts-and-payments-summary",
    "bank-account-summary",
    "realized-currency-gains-losses",
    "realized-investment-gains-summary",
    "realized-investment-gains-summary-list",
}

# (regex on the stem, group id) -- first match wins, so order matters.
_RULES: list[tuple[str, str]] = [
    (r"^(access-token|user-permissions|customer-portal)", "security"),
    (r"starting-balance|^starting-exchange-rates$", "starting_balances"),
    (r"^(recurring-|pending-recurring-)", "recurring"),
    (r"^balance-sheet-.*(account|group|clearing|transfers)", "accounts"),
    (r"^profit-and-loss-statement-(account|group|subtotal|total)", "accounts"),
    (r"^control-account-for", "accounts"),
    (r"^chart-of-accounts$", "accounts"),
    (r"(^|-)(summary|statements)-|(-summary|-summary-list|-transactions|-worksheet"
     r"|-worksheet-list|-price-list|-profit-margin|-totals)$", "reports"),
    (r"^(profit-and-loss-statement|balance-sheet|cash-flow-statement|trial-balance"
     r"|general-ledger|forecast|tax-audit|tax-reconciliation|tax-totals|taxable-)", "reports"),
    (r"^(sales-invoice-totals-by|payslip-totals|inventory-(quantity|value)"
     r"|customers-qty|suppliers-qty|.*-qty-)", "reports"),
    (r"^(email-template|email-settings|emails$)", "customization"),
    (r"custom-field|custom-button|custom-theme|^tabs$|^script-extension$"
     r"|^business-details$|^date-and-number-format$|^lock-date$", "customization"),
    (r"^(attachment|attachments|history|emails)$", "attachments"),
    (r"withholding-tax|^tax-code|^tax-summary|^tax-", "tax"),
    (r"^(base-currency|foreign-currenc|exchange-rate|starting-exchange"
     r"|web-service-for-exchange-rates)", "currencies"),
    (r"^(sales-quote|sales-order|sales-invoice|credit-note|delivery-note"
     r"|late-payment-fee|new-sales-invoice|pending-sales|pending-early-payment"
     r"|pending-late-payment)", "sales"),
    (r"^(purchase-quote|purchase-order|purchase-invoice|debit-note|goods-receipt"
     r"|pending-purchase)", "purchases"),
    (r"^(receipt|payment|inter-account-transfer|new-inter-account|bank-or-cash"
     r"|bank-and-cash|bank-reconciliation|pending-payments|pending-receipts"
     r"|pending-inter-account)", "banking"),
    (r"^(inventory|non-inventory-item|production-order|custom-inventory-location"
     r"|default-inventory-location)", "inventory"),
    (r"^(payslip|employee|expense-claim)", "payroll"),
    (r"^(fixed-asset|intangible-asset|investment|inventment|depreciation"
     r"|amortization|new-depreciation)", "assets"),
    (r"^(journal-entry|journal-entries)", "ledger"),
    (r"^(project|division|folder)", "projects"),
    (r"^(customer|supplier)", "parties"),
    (r"^billable-", "projects"),
    (r"^capital-", "ledger"),
    (r"^special-account", "ledger"),
]
_COMPILED = [(re.compile(p), g) for p, g in _RULES]


def classify(stem: str) -> str:
    if stem in _REPORT_EXACT:
        return "reports"
    for rx, group in _COMPILED:
        if rx.search(stem):
            return group
    return "other"


def _singular(word: str) -> str:
    if word.endswith("ies"):
        return word[:-3] + "y"
    for suffix in ("ses", "xes", "ches", "shes"):
        if word.endswith(suffix):
            return word[:-2]
    if word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


def _norm(stem: str) -> str:
    return _singular(stem.replace("-", ""))


def _snake(stem: str) -> str:
    return stem.replace("-", "_")


def _title(stem: str) -> str:
    return stem.replace("-", " ").title()


def _pretty(label: str, stem: str) -> str:
    """Manager's summaries are sometimes CamelCase ('CreditNoteFooters')."""
    if not label:
        return _title(stem)
    if " " in label:
        return label
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", label)


def _locked(stem: str) -> bool:
    return any(stem.startswith(p) for p in LOCKED_WRITE_PREFIXES)


@dataclass
class Resource:
    """One addressable Manager resource and the operations it supports."""

    name: str
    label: str
    group: str
    ops: dict[str, bool]
    list_path: str | None = None
    form_path: str | None = None
    list_params: list[str] = field(default_factory=list)
    description: str = ""
    doc_url: str = ""
    locked: bool = False
    risk: str = "normal"
    risk_note: str = ""

    @property
    def write_ops(self) -> list[str]:
        return [op for op in ("create", "update", "delete") if self.ops.get(op)]

    def supports(self, op: str) -> bool:
        return bool(self.ops.get(op))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> Resource:
        known = {k: raw[k] for k in raw if k in cls.__dataclass_fields__}
        return cls(**known)


@dataclass
class Catalog:
    """All resources exposed by one Manager instance."""

    resources: dict[str, Resource]
    api_version: str = ""
    built_at: str = ""

    def get(self, name: str) -> Resource | None:
        return self.resources.get(name)

    def by_group(self) -> dict[str, list[Resource]]:
        out: dict[str, list[Resource]] = {g: [] for g in GROUP_ORDER}
        for res in self.resources.values():
            out.setdefault(res.group, []).append(res)
        for items in out.values():
            items.sort(key=lambda r: r.label.lower())
        return {g: items for g, items in out.items() if items}

    def search(self, term: str) -> list[Resource]:
        needle = term.strip().casefold()
        if not needle:
            return list(self.resources.values())
        return [
            r
            for r in self.resources.values()
            if needle in r.name.casefold()
            or needle in r.label.casefold()
            or needle in r.group.casefold()
        ]

    def to_dict(self) -> dict[str, Any]:
        return {
            "api_version": self.api_version,
            "built_at": self.built_at,
            "resources": {n: r.to_dict() for n, r in self.resources.items()},
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> Catalog:
        return cls(
            resources={
                n: Resource.from_dict(r) for n, r in (raw.get("resources") or {}).items()
            },
            api_version=raw.get("api_version", ""),
            built_at=raw.get("built_at", ""),
        )


def _get_params(spec: dict[str, Any]) -> list[str]:
    return [
        p["name"]
        for p in (spec.get("parameters") or [])
        if p.get("in") == "query" and p.get("name")
    ]


def _clean_description(raw: str) -> tuple[str, str]:
    """Split Manager's 'text ... see https://...' description into text + url."""
    if not raw:
        return "", ""
    match = re.search(r"(https?://\S+)", raw)
    url = match.group(1).rstrip(".") if match else ""
    text = re.sub(r"\s*For more information,? see\s+https?://\S+\.?", "", raw).strip()
    return text, url


def build_catalog(openapi: dict[str, Any], *, built_at: str = "") -> Catalog:
    """Turn an OpenAPI document into a permission-gated resource catalog."""
    paths: dict[str, Any] = openapi.get("paths") or {}
    form_stems = {p[1:-len("-form")] for p in paths if p.endswith("-form")}
    list_stems = {
        p[1:] for p in paths if "-form" not in p and "{" not in p and p.startswith("/")
    }

    by_norm: dict[str, str] = {}
    for stem in list_stems:
        by_norm.setdefault(_norm(stem), stem)

    resources: dict[str, Resource] = {}
    paired_lists: set[str] = set()

    for stem in sorted(form_stems):
        list_stem = _PAIR_OVERRIDES.get(stem)
        if list_stem not in list_stems:
            list_stem = None
        if list_stem is None and f"{stem}-list" in list_stems:
            list_stem = f"{stem}-list"
        if list_stem is None:
            list_stem = by_norm.get(_norm(stem))
        if list_stem:
            paired_lists.add(list_stem)

        form_path = f"/{stem}-form"
        keyed = paths.get(f"{form_path}/{{key}}") or {}
        form_root = paths.get(form_path) or {}
        list_spec = (paths.get(f"/{list_stem}") or {}).get("get") if list_stem else None
        locked = _locked(stem)

        ops = {
            "read": bool(list_spec) or "get" in keyed,
            "create": "post" in form_root and not locked,
            "update": ("put" in keyed or "patch" in keyed) and not locked,
            "delete": "delete" in keyed and not locked,
        }
        label_source = (list_spec or {}).get("summary") if list_spec else None
        description, doc_url = _clean_description(
            (list_spec or {}).get("description", "") if list_spec else ""
        )
        name = _snake(list_stem or stem)
        group = classify(list_stem or stem)
        risk, risk_note = risk_for(name, group)
        resources[name] = Resource(
            name=name,
            label=_pretty(label_source or "", stem),
            group=group,
            ops=ops,
            list_path=f"/{list_stem}" if list_stem else None,
            form_path=form_path,
            list_params=_get_params(list_spec) if list_spec else [],
            description=description,
            doc_url=doc_url,
            locked=locked,
            risk=risk,
            risk_note=risk_note,
        )

    for stem in sorted(list_stems - paired_lists):
        spec = (paths.get(f"/{stem}") or {}).get("get")
        if not spec:
            continue
        name = _snake(stem)
        if name in resources:
            continue
        description, doc_url = _clean_description(spec.get("description", ""))
        group = classify(stem)
        risk, risk_note = risk_for(name, group)
        resources[name] = Resource(
            name=name,
            label=_pretty(spec.get("summary") or "", stem),
            group=group,
            ops={"read": True, "create": False, "update": False, "delete": False},
            list_path=f"/{stem}",
            form_path=None,
            list_params=_get_params(spec),
            description=description,
            doc_url=doc_url,
            locked=_locked(stem),
            risk=risk,
            risk_note=risk_note,
        )

    return Catalog(
        resources=resources,
        api_version=str((openapi.get("info") or {}).get("version", "")),
        built_at=built_at,
    )
