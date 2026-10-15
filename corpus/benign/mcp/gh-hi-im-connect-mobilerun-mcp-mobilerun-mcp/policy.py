"""Sensitive-action policy. Modes: off (default) | standard | strict. Pure functions."""

from __future__ import annotations

import re
from dataclasses import dataclass

_TOKEN = re.compile(r"[a-z0-9]+")
_BANKING = {
    "bank",
    "banking",
    "banque",
    "wallet",
    "paypal",
    "venmo",
    "cashapp",
    "zelle",
    "revolut",
    "monzo",
    "n26",
    "instapay",
    "fawry",
    "stripe",
    "payments",
    "payment",
    "pay",
    "moneytransfer",
}
_AUTHENTICATOR = {"authenticator", "authy", "totp", "otp", "2fa", "yubico", "duo"}
_PASSWORDS = {"1password", "bitwarden", "lastpass", "keepass", "dashlane", "keeper", "passwords"}
_CATEGORIES = (
    ("banking", _BANKING),
    ("authenticator", _AUTHENTICATOR),
    ("password_manager", _PASSWORDS),
)
_CVV_FIELD = re.compile(r"cvv|cvc|security.?code|card.?verification", re.I)
_PASSWORD_FIELD = re.compile(r"password|passcode|\bpin\b|passwd", re.I)
_SSN = re.compile(r"^\d{3}-\d{2}-\d{4}$")
_EG_NATIONAL_ID = re.compile(r"^[23]\d{13}$")


@dataclass(frozen=True)
class Decision:
    allowed: bool
    category: str = ""
    reason: str = ""


ALLOW = Decision(True)


def luhn_valid(digits: str) -> bool:
    total, flip = 0, False
    for ch in reversed(digits):
        n = int(ch)
        if flip:
            n = n * 2 - 9 if n * 2 > 9 else n * 2
        total += n
        flip = not flip
    return total % 10 == 0


def looks_like_card(text: str) -> bool:
    digits = re.sub(r"[\s-]", "", text)
    return digits.isdigit() and 13 <= len(digits) <= 19 and luhn_valid(digits)


def check_app(mode: str, package: str, label: str = "") -> Decision:
    if mode == "off":
        return ALLOW
    tokens = set(_TOKEN.findall(f"{package} {label}".lower()))
    for category, words in _CATEGORIES:
        if tokens & words:
            return Decision(
                False, category, f"{label or package} is a {category.replace('_', ' ')} app"
            )
    return ALLOW


def check_text(
    mode: str, text: str, field_hint: str = "", password_field: bool = False
) -> Decision:
    if mode == "off":
        return ALLOW
    if looks_like_card(text):
        return Decision(False, "card_number", "text looks like a payment card number")
    if _CVV_FIELD.search(field_hint):
        return Decision(False, "cvv", "the focused field asks for a card security code")
    if mode == "strict":
        stripped = text.strip()
        if password_field or _PASSWORD_FIELD.search(field_hint):
            return Decision(False, "password", "the focused field is a password/PIN field")
        if _SSN.match(stripped) or _EG_NATIONAL_ID.match(stripped):
            return Decision(False, "national_id", "text looks like a national ID number")
    return ALLOW
