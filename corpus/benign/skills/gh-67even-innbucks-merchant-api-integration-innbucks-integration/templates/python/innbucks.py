"""InnBucks Merchant API client. Amounts are integer cents: 450 == 4.50."""
import os
import re
import time
from urllib.parse import quote

import requests

BASE_URL = os.environ.get("INNBUCKS_BASE_URL", "").rstrip("/")
API_KEY = os.environ.get("INNBUCKS_API_KEY")
USERNAME = os.environ.get("INNBUCKS_USERNAME")
PASSWORD = os.environ.get("INNBUCKS_PASSWORD")
ENVIRONMENT = os.environ.get("INNBUCKS_ENV", "test")
TOKEN_TTL = int(os.environ.get("INNBUCKS_TOKEN_TTL", "840"))

_session = requests.Session()
_token = None
_token_at = 0.0
last_trace_id = None


class InnBucksError(Exception):
    def __init__(self, message, response=None, trace_id=None, http_status=None):
        super().__init__(message)
        self.response = response or {}
        self.trace_id = trace_id
        self.http_status = http_status


def _request(method, path, body=None, bearer=None):
    global last_trace_id
    headers = {"X-Api-Key": API_KEY, "Accept": "application/json"}
    if bearer:
        headers["Authorization"] = "Bearer " + bearer
    res = _session.request(method, BASE_URL + path, json=body, headers=headers, timeout=30)
    last_trace_id = res.headers.get("X-Trace-Id")
    try:
        data = res.json() if res.content else {}
    except ValueError:
        data = {"raw": res.text}
    return res.status_code, data


def login(fresh=False):
    global _token, _token_at
    if not fresh and _token and time.time() - _token_at < TOKEN_TTL:
        return _token
    status, data = _request("POST", "/auth/third-party", {"username": USERNAME, "password": PASSWORD})
    if not ok(data) or not data.get("accessToken"):
        raise InnBucksError("InnBucks login failed: " + message(data), data, last_trace_id, status)
    _token, _token_at = data["accessToken"], time.time()
    return _token


def _send(method, path, body=None):
    status, data = _request(method, path, body, login())
    if status == 401:  # token expired: log in again, retry once
        status, data = _request(method, path, body, login(fresh=True))
    if status >= 400:
        raise InnBucksError("InnBucks HTTP %d: %s" % (status, message(data)), data, last_trace_id, status)
    return data


def _cents(amount):
    if not isinstance(amount, int) or isinstance(amount, bool) or amount <= 0:
        raise ValueError("Amounts are positive integers in cents: 450 == 4.50")
    return amount


def _currency(currency):
    if currency.upper() not in ("USD", "ZWG"):
        raise ValueError("currency must be USD or ZWG")
    return currency.upper()


# ---- codes ----------------------------------------------------------------

def generate_code(amount, currency, reference, narration, type="PAYMENT"):
    if type not in ("PAYMENT", "WITHDRAWAL"):
        raise ValueError("type must be PAYMENT or WITHDRAWAL")
    return _send("POST", "/api/code/generate", {
        "reference": reference, "narration": narration,
        "currency": _currency(currency), "amount": _cents(amount), "type": type})


def inquire_code(code, reference=None):
    body = {"reference": reference, "code": code} if reference else {"code": code}
    return _send("POST", "/api/code/inquiry", body)


# ---- agent services -------------------------------------------------------

def linked_account(msisdn, currency="USD"):
    return _send("GET", "/api/v1/account/msisdn/%s/details?currency=%s" % (quote(msisdn), _currency(currency)))


def deposit(destination_account, amount, currency, reference, narration, type=None):
    body = {"reference": reference, "currency": _currency(currency), "amount": _cents(amount),
            "narration": narration, "destinationAccount": destination_account}
    if type:
        body["type"] = type
    return _send("POST", "/api/transaction/deposit", body)


def deposit_inquiry(account_number, original_reference, inquiry_reference):
    return _send("POST", "/bank/api/transaction/inquiry", {
        "accountNumber": account_number,
        "participantReference": inquiry_reference,
        "originalParticipantReference": original_reference})


def reverse_deposit(destination_account, amount, currency, original_reference, reversal_reference):
    return _send("POST", "/api/transaction/reversal/v2", {
        "amount": _cents(amount), "currency": _currency(currency), "type": "CREDIT",
        "destinationAccount": destination_account,
        "participantReference": reversal_reference,
        "originalParticipantReference": original_reference})


def bank_change(msisdn, amount, currency, reference, narration):
    if _currency(currency) == "USD" and _cents(amount) > 500:
        raise ValueError("Bank change is limited to 500 cents (US$5.00)")
    return _send("POST", "/api/transaction/bankChange", {
        "reference": reference, "currency": _currency(currency), "amount": _cents(amount),
        "narration": narration, "destinationMsisdn": msisdn})


def utility_payment(provider, product, destination_account, amount, currency, reference,
                    narration="", additional_data=None):
    return _send("POST", "/api/utility/provider/payment", {
        "provider": provider, "providerProduct": product, "amount": _cents(amount),
        "currency": _currency(currency), "reference": reference, "narration": narration,
        "destinationAccount": destination_account, "additionalData": additional_data or {}})


def statement(account_number, currency, start, end):
    """start / end as 'YYYY-MM-DD HH:MM:SS', within one calendar month."""
    return _send("POST", "/api/account/fullStatement", {
        "accountNumber": account_number, "currency": _currency(currency),
        "startDateTime": start, "endDateTime": end})


# ---- helpers --------------------------------------------------------------

def ok(body):
    return (body or {}).get("responseCode") in ("00", "000")


def message(body):
    body = body or {}
    return str(body.get("responseMsg") or body.get("responseDescription") or "no message")


def code_status(body):
    """'new' | 'claimed' | 'paid' | 'expired' | 'timed_out' | None"""
    s = re.sub(r"[\s_-]+", "", str((body or {}).get("status") or "")).lower()
    return {"new": "new", "claimed": "claimed", "paid": "paid",
            "expired": "expired", "timedout": "timed_out"}.get(s)


def is_paid(body):
    return ok(body) and code_status(body) in ("claimed", "paid")


def is_final(body):
    return ok(body) and code_status(body) in ("claimed", "paid", "expired", "timed_out")


def deep_link(code):
    scheme = "com.innbucks.customer" if ENVIRONMENT == "production" else "zw.co.innbucksnova.test"
    return "%s://purchase?paymentToken=%s" % (scheme, quote(str(code)))


def qr_data_uri(body):
    qr = (body or {}).get("qrCode")
    if not qr:
        return None
    return qr if qr.startswith("data:") else "data:image/png;base64," + qr


def wait_for_code(code, interval=30, max_seconds=660):
    """Check a code every `interval` seconds until final; after `max_seconds` return it marked unknown."""
    started = time.time()
    while True:
        time.sleep(interval)
        try:
            body = inquire_code(code)
        except (InnBucksError, requests.RequestException):
            body = {}  # try again at the next check
        if is_final(body):
            return body
        if time.time() - started >= max_seconds:
            return dict(body, unknown=True)
