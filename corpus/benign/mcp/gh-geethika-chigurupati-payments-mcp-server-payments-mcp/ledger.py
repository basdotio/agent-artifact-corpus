"""In-memory mock ledger. No real money moves; data is lost when the process exits."""
import threading
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field

SUPPORTED_CURRENCIES = {"USD", "EUR", "GBP"}
MAX_AMOUNT = Decimal("1000000.00")
CENT = Decimal("0.01")

Status = Literal["succeeded", "partially_refunded", "refunded"]


class PaymentError(Exception):
    """Raised for invalid input or a rule violation (safe to show to the caller)."""


class Payment(BaseModel):
    id: str
    amount: Decimal
    currency: str
    description: str
    status: Status = "succeeded"
    refunded_amount: Decimal = Decimal("0.00")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


def parse_amount(value: str) -> Decimal:
    """Parse a decimal string like '19.99'. Rejects floats, negatives, and >2 decimals."""
    try:
        amount = Decimal(str(value).strip())
    except (InvalidOperation, ValueError) as exc:
        raise PaymentError(f"invalid amount: {value!r}") from exc
    if not amount.is_finite():
        raise PaymentError("amount must be a finite number")
    if amount <= 0:
        raise PaymentError("amount must be greater than 0")
    if amount != amount.quantize(CENT):
        raise PaymentError("amount can have at most 2 decimal places")
    if amount > MAX_AMOUNT:
        raise PaymentError(f"amount exceeds the maximum of {MAX_AMOUNT}")
    return amount.quantize(CENT)


class Ledger:
    def __init__(self) -> None:
        self._payments: dict[str, Payment] = {}
        # idempotency key -> (request fingerprint, payment id)
        self._keys: dict[str, tuple[tuple[Decimal, str, str], str]] = {}
        self._lock = threading.Lock()

    def create_payment(
        self, amount: str, currency: str, description: str, idempotency_key: str
    ) -> tuple[Payment, bool]:
        """Create a payment. Returns (payment, created).

        Repeating a request with the same key and same details returns the original
        payment with created=False. Reusing a key with different details is an error.
        """
        if not idempotency_key or len(idempotency_key) > 128:
            raise PaymentError("idempotency_key must be 1-128 characters")
        parsed = parse_amount(amount)
        currency = currency.strip().upper()
        if currency not in SUPPORTED_CURRENCIES:
            raise PaymentError(f"unsupported currency; use one of {sorted(SUPPORTED_CURRENCIES)}")
        description = description.strip()
        if len(description) > 200:
            raise PaymentError("description is limited to 200 characters")

        fingerprint = (parsed, currency, description)
        with self._lock:
            existing = self._keys.get(idempotency_key)
            if existing is not None:
                saved_fingerprint, payment_id = existing
                if saved_fingerprint != fingerprint:
                    raise PaymentError(
                        "idempotency_key was already used with different payment details"
                    )
                return self._payments[payment_id], False

            payment = Payment(
                id=f"pay_{uuid4().hex[:16]}",
                amount=parsed,
                currency=currency,
                description=description,
            )
            self._payments[payment.id] = payment
            self._keys[idempotency_key] = (fingerprint, payment.id)
            return payment, True

    def get_payment(self, payment_id: str) -> Payment:
        with self._lock:
            payment = self._payments.get(payment_id)
        if payment is None:
            raise PaymentError(f"payment not found: {payment_id}")
        return payment

    def refund_payment(self, payment_id: str, amount: str | None = None) -> Payment:
        """Refund part or all of the remaining balance. Omit `amount` to refund the rest."""
        with self._lock:
            payment = self._payments.get(payment_id)
            if payment is None:
                raise PaymentError(f"payment not found: {payment_id}")
            remaining = payment.amount - payment.refunded_amount
            if remaining <= 0:
                raise PaymentError("payment is already fully refunded")
            refund = remaining if amount is None else parse_amount(amount)
            if refund > remaining:
                raise PaymentError(f"refund exceeds the refundable balance of {remaining}")
            payment.refunded_amount += refund
            payment.status = (
                "refunded" if payment.refunded_amount == payment.amount else "partially_refunded"
            )
            return payment
