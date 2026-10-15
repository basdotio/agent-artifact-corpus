#!/usr/bin/env python3
"""innbucks_cli.py - InnBucks Merchant API helper for the innbucks-integration Claude skill.

Python 3.8+, standard library only. Reads the same INNBUCKS_* variables as the templates:
INNBUCKS_BASE_URL, INNBUCKS_API_KEY, INNBUCKS_USERNAME, INNBUCKS_PASSWORD, INNBUCKS_ENV.

Offline commands (no credentials, no network):
  self-test                        check the payload linter against built-in good/bad payloads
  lint KIND FILE|-                 check a request body. KIND: login generate inquiry deposit
                                   deposit-inquiry reversal bank-change utility statement
  deeplink CODE                    the deep link for INNBUCKS_ENV (test or production)

API commands (log in, then one call; --dry-run prints the request with secrets masked):
  login                            prove the credentials work (token masked)
  generate  --amount CENTS --reference REF [--narration N] [--currency USD] [--type PAYMENT]
  inquiry   --code CODE [--reference REF]
  wait      --code CODE [--interval 30] [--max 660]    one inquiry per 30 s until final
  linked-account --msisdn 263XXXXXXXXX [--currency USD]
  deposit   --account ACC --amount CENTS --reference REF [--narration N] [--currency USD]
  deposit-inquiry --account ACC --original-ref REF --inquiry-ref NEWREF
  reversal  --account ACC --amount CENTS --original-ref REF --reversal-ref NEWREF [--currency USD]
  bank-change --msisdn 263XXXXXXXXX --amount CENTS --reference REF [--narration N]
  utility   --provider P --product P --account ACC --amount CENTS --reference REF [--narration N]
  statement --account ACC --start "YYYY-MM-DD HH:MM:SS" --end "YYYY-MM-DD HH:MM:SS" [--currency USD]
  response-codes                   download the response-code list

Safety rules built in:
  * amounts are integer cents; "4.50" or 4.5 is refused with a hint
  * deposit, reversal, bank-change and utility refuse INNBUCKS_ENV=production without --allow-live
  * a request is never re-sent after a timeout or a 5xx (only once after a 401, which means
    it was not processed); after a lost deposit, use deposit-inquiry with the same reference
  * wait never checks a code more often than every 30 seconds
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

CURRENCIES = ("USD", "ZWG")
MSISDN = re.compile(r"^263\d{9}$")
DATETIME = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")
MONEY_MOVING = {"deposit", "reversal", "bank-change", "utility"}

# kind -> (path, required keys, optional keys)
KINDS = {
    "login": ("/auth/third-party", {"username", "password"}, set()),
    "generate": ("/api/code/generate", {"currency", "amount", "type"}, {"reference", "narration"}),
    "inquiry": ("/api/code/inquiry", {"code"}, {"reference"}),
    "deposit": ("/api/transaction/deposit", {"currency", "amount", "destinationAccount"},
                {"reference", "narration", "type"}),
    "deposit-inquiry": ("/bank/api/transaction/inquiry",
                        {"accountNumber", "participantReference", "originalParticipantReference"}, set()),
    "reversal": ("/api/transaction/reversal/v2",
                 {"amount", "currency", "type", "destinationAccount", "participantReference",
                  "originalParticipantReference"}, set()),
    "bank-change": ("/api/transaction/bankChange", {"currency", "amount", "destinationMsisdn"},
                    {"reference", "narration"}),
    "utility": ("/api/utility/provider/payment",
                {"provider", "providerProduct", "amount", "currency", "destinationAccount"},
                {"reference", "narration", "additionalData"}),
    "statement": ("/api/account/fullStatement",
                  {"accountNumber", "currency", "startDateTime", "endDateTime"}, set()),
}

# common wrong spellings -> the documented field name
MISSPELLINGS = {
    "destinationMSISDN": "destinationMsisdn", "msisdn": "destinationMsisdn", "phone": "destinationMsisdn",
    "originalReference": "originalParticipantReference", "originalRef": "originalParticipantReference",
    "originalParticipantRef": "originalParticipantReference", "participantRef": "participantReference",
    "accountNo": "accountNumber", "account": "destinationAccount / accountNumber",
    "destinationAccountNumber": "destinationAccount", "Amount": "amount", "Currency": "currency",
    "product": "providerProduct", "productCode": "providerProduct", "startDate": "startDateTime",
    "endDate": "endDateTime", "paymentToken": "code", "narrative": "narration", "description": "narration",
    "codeType": "type", "transactionType": "type",
}


# ---------------------------------------------------------------------------
# linter
# ---------------------------------------------------------------------------

def lint(kind, body):
    """Return (errors, warnings) for a request body of the given kind."""
    errors, warnings = [], []
    if kind not in KINDS:
        return ["unknown kind %r (one of: %s)" % (kind, ", ".join(KINDS))], []
    if not isinstance(body, dict):
        return ["the body must be a JSON object"], []
    _, required, optional = KINDS[kind]
    for k in sorted(set(body) - required - optional):
        if k in MISSPELLINGS:
            errors.append("%r is not an InnBucks field: use %r" % (k, MISSPELLINGS[k]))
        else:
            warnings.append("%r is not a documented field for %s" % (k, kind))
    for k in sorted(required - set(body)):
        errors.append("missing required field %r" % k)

    if "amount" in body:
        a = body["amount"]
        if isinstance(a, bool) or not isinstance(a, int):
            errors.append("amount must be a JSON integer in cents (450 = 4.50), got %r" % (a,))
        elif a <= 0:
            errors.append("amount must be positive, got %d" % a)
        elif kind == "bank-change" and body.get("currency") == "USD" and a > 500:
            errors.append("bank change is limited to 500 cents (US$5.00), got %d" % a)
        elif a < 10 and kind in ("generate", "deposit", "utility"):
            warnings.append("amount %d is %d cent(s): did you mean %d?" % (a, a, a * 100))
    if "currency" in body and body["currency"] not in CURRENCIES:
        errors.append("currency must be USD or ZWG, got %r" % (body["currency"],))
    if kind == "generate" and "type" in body and body["type"] not in ("PAYMENT", "WITHDRAWAL"):
        errors.append("type must be PAYMENT or WITHDRAWAL, got %r" % (body["type"],))
    if kind == "reversal" and body.get("type") != "CREDIT":
        errors.append('reversal type must be "CREDIT", got %r' % (body.get("type"),))
    if kind in ("reversal", "deposit-inquiry") and body.get("participantReference") and \
            body.get("participantReference") == body.get("originalParticipantReference"):
        errors.append("participantReference must be NEW, not the original reference")
    if kind == "bank-change" and "destinationMsisdn" in body and not MSISDN.match(str(body["destinationMsisdn"])):
        errors.append("destinationMsisdn must be 263XXXXXXXXX (12 digits), got %r" % (body["destinationMsisdn"],))
    if kind == "statement":
        for k in ("startDateTime", "endDateTime"):
            if k in body and not DATETIME.match(str(body[k])):
                errors.append("%s must be 'yyyy-MM-dd HH:mm:ss', got %r" % (k, body[k]))
        s, e = str(body.get("startDateTime", "")), str(body.get("endDateTime", ""))
        if DATETIME.match(s) and DATETIME.match(e) and s[:7] != e[:7]:
            warnings.append("the period spans more than one calendar month; request one month at a time")
    if kind == "inquiry" and "code" in body and not re.fullmatch(r"\d{6,12}", str(body["code"])):
        warnings.append("code %r does not look like an InnBucks code (digits only)" % (body["code"],))
    if kind in ("generate", "deposit", "bank-change", "utility"):
        ref = body.get("reference")
        if not ref:
            warnings.append("no reference: send your own, unique per request, and save it first")
        elif re.search(r"(?i)^(ref-?0*1|test|1234|12346765|123456789abc)$", str(ref)):
            warnings.append("reference %r looks hard-coded; it must be unique per request" % ref)
        if kind == "generate" and ref and ref not in str(body.get("narration", "")):
            warnings.append("narration does not contain the reference; it is what appears on your statement")
    if kind == "deposit" and not body.get("reference"):
        errors.append("a deposit needs your own reference: it is the key for deposit inquiry and reversal")
    return errors, warnings


def self_test():
    good = {
        "generate": {"reference": "ORD-1", "narration": "Order ORD-1", "currency": "USD", "amount": 450, "type": "PAYMENT"},
        "inquiry": {"code": "535403380"},
        "deposit": {"reference": "DEP-1", "currency": "USD", "amount": 1000, "narration": "d", "destinationAccount": "3003373465942"},
        "deposit-inquiry": {"accountNumber": "3003373465942", "participantReference": "INQ-1", "originalParticipantReference": "DEP-1"},
        "reversal": {"amount": 1000, "currency": "USD", "type": "CREDIT", "destinationAccount": "3003373465942",
                     "participantReference": "REV-1", "originalParticipantReference": "DEP-1"},
        "bank-change": {"reference": "CHG-1", "currency": "USD", "amount": 150, "narration": "c", "destinationMsisdn": "263770123123"},
        "utility": {"provider": "ECONET", "providerProduct": "AIRTIME", "amount": 100, "currency": "USD",
                    "reference": "UTL-1", "narration": "a", "destinationAccount": "263771234567", "additionalData": {}},
        "statement": {"accountNumber": "1", "currency": "USD", "startDateTime": "2026-09-01 00:00:00",
                      "endDateTime": "2026-09-30 23:59:59"},
        "login": {"username": "u", "password": "p"},
    }
    bad = [
        ("generate", dict(good["generate"], amount=4.5), "integer in cents"),
        ("generate", dict(good["generate"], amount="450"), "integer in cents"),
        ("generate", dict(good["generate"], currency="ZWL"), "USD or ZWG"),
        ("generate", dict(good["generate"], type="PURCHASE"), "PAYMENT or WITHDRAWAL"),
        ("deposit", {k: v for k, v in good["deposit"].items() if k != "reference"}, "needs your own reference"),
        ("reversal", dict(good["reversal"], type="DEBIT"), '"CREDIT"'),
        ("reversal", dict(good["reversal"], participantReference="DEP-1"), "must be NEW"),
        ("bank-change", dict(good["bank-change"], amount=600), "500 cents"),
        ("bank-change", dict(good["bank-change"], destinationMsisdn="0770123123"), "263XXXXXXXXX"),
        ("bank-change", {**{k: v for k, v in good["bank-change"].items() if k != "destinationMsisdn"},
                         "destinationMSISDN": "263770123123"}, "use 'destinationMsisdn'"),
        ("reversal", {**{k: v for k, v in good["reversal"].items() if k != "originalParticipantReference"},
                      "originalReference": "DEP-1"}, "use 'originalParticipantReference'"),
        ("statement", dict(good["statement"], startDateTime="2026-09-01"), "yyyy-MM-dd HH:mm:ss"),
    ]
    failures = 0
    for kind, body in good.items():
        errs, _ = lint(kind, body)
        if errs:
            failures += 1
            print("FAIL good %s: %s" % (kind, errs))
    for kind, body, expect in bad:
        errs, _ = lint(kind, body)
        if not any(expect in e for e in errs):
            failures += 1
            print("FAIL bad %s (expected %r): %s" % (kind, expect, errs))
    _, warns = lint("generate", dict(good["generate"], amount=1))
    if not any("did you mean 100" in w for w in warns):
        failures += 1
        print("FAIL: amount 1 should warn 'did you mean 100'")
    if deep_link("535403380", "test") != "zw.co.innbucksnova.test://purchase?paymentToken=535403380" or \
            deep_link("535403380", "production") != "com.innbucks.customer://purchase?paymentToken=535403380":
        failures += 1
        print("FAIL: deep links")
    for raw, want in (("Claimed", "claimed"), ("Timed Out", "timed_out"), ("TIMED_OUT", "timed_out"), ("Paid", "paid")):
        if code_status({"status": raw}) != want:
            failures += 1
            print("FAIL: status %r -> %r" % (raw, code_status({"status": raw})))
    print("self-test: %s (%d good, %d bad payloads)" % ("PASS" if not failures else "FAIL", len(good), len(bad)))
    return 1 if failures else 0


# ---------------------------------------------------------------------------
# helpers shared with the templates' behaviour
# ---------------------------------------------------------------------------

def deep_link(code, environment):
    scheme = "com.innbucks.customer" if environment == "production" else "zw.co.innbucksnova.test"
    return "%s://purchase?paymentToken=%s" % (scheme, urllib.parse.quote(str(code)))


def ok(body):
    return (body or {}).get("responseCode") in ("00", "000")


def message(body):
    body = body or {}
    return str(body.get("responseMsg") or body.get("responseDescription") or "no message")


def code_status(body):
    s = re.sub(r"[\s_-]+", "", str((body or {}).get("status") or "")).lower()
    return {"new": "new", "claimed": "claimed", "paid": "paid", "expired": "expired", "timedout": "timed_out"}.get(s)


def mask(value, keep=4):
    value = str(value or "")
    return value[:keep] + "…" + "*" * 4 if len(value) > keep else "****"


def load_env_file(path):
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            v = v.split(" #", 1)[0].strip().strip('"').strip("'")
            os.environ.setdefault(k.strip(), v)


def cents(value):
    try:
        n = int(value)
    except ValueError:
        sys.exit("--amount is integer cents: US$4.50 is 450 (got %r)" % value)
    if n <= 0:
        sys.exit("--amount must be positive")
    return n


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------

class Api:
    def __init__(self, args):
        self.args = args
        self.base = os.environ.get("INNBUCKS_BASE_URL", "").rstrip("/")
        self.key = os.environ.get("INNBUCKS_API_KEY")
        self.user = os.environ.get("INNBUCKS_USERNAME")
        self.password = os.environ.get("INNBUCKS_PASSWORD")
        self.env = os.environ.get("INNBUCKS_ENV", "test")
        self.token = None
        if not args.dry_run:
            missing = [n for n, v in (("INNBUCKS_BASE_URL", self.base), ("INNBUCKS_API_KEY", self.key),
                                      ("INNBUCKS_USERNAME", self.user), ("INNBUCKS_PASSWORD", self.password)) if not v]
            if missing:
                sys.exit("missing configuration: %s (use --env-file .env)" % ", ".join(missing))

    def _raw(self, method, path, body, bearer):
        headers = {"X-Api-Key": self.key or "", "Accept": "application/json"}
        if bearer:
            headers["Authorization"] = "Bearer " + bearer
        data = None
        if body is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(body).encode()
        req = urllib.request.Request(self.base + path, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=self.args.timeout) as res:
                status, raw, trace = res.status, res.read(), res.headers.get("X-Trace-Id")
        except urllib.error.HTTPError as e:
            status, raw, trace = e.code, e.read(), e.headers.get("X-Trace-Id")
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            print(json.dumps({"error": "no response: %s" % e,
                              "advice": "do NOT re-send; for a deposit run deposit-inquiry with the same "
                                        "reference, for a code run inquiry"}, indent=2))
            sys.exit(3)
        try:
            parsed = json.loads(raw) if raw else {}
        except ValueError:
            parsed = {"raw": raw.decode("utf-8", "replace")}
        return status, parsed, trace

    def login(self):
        body = {"username": self.user, "password": self.password}
        if self.args.dry_run:
            self.show("POST", "/auth/third-party", dict(body, password="****"), bearer=False)
            self.token = "DRY-RUN-TOKEN"
            return self.token
        status, data, trace = self._raw("POST", "/auth/third-party", body, None)
        if not ok(data) or not data.get("accessToken"):
            print(json.dumps({"http": status, "traceId": trace, "response": data}, indent=2))
            sys.exit("login failed: %s" % message(data))
        self.token = data["accessToken"]
        return self.token

    def show(self, method, path, body, bearer=True):
        print(json.dumps({"dry_run": True, "method": method, "url": (self.base or "{baseUrl}") + path,
                          "headers": dict({"X-Api-Key": mask(self.key)},
                                          **({"Authorization": "Bearer ****"} if bearer else {})),
                          "body": body}, indent=2))

    def call(self, method, path, body=None):
        if self.args.dry_run:
            self.show(method, path, body)
            return {}
        if not self.token:
            self.login()
        status, data, trace = self._raw(method, path, body, self.token)
        if status == 401:  # not processed: log in again and retry once
            self.login()
            status, data, trace = self._raw(method, path, body, self.token)
        out = {"http": status, "traceId": trace, "ok": ok(data), "message": message(data), "response": data}
        if "status" in data:
            out["codeStatus"] = code_status(data)
        print(json.dumps(out, indent=2))
        return data


# ---------------------------------------------------------------------------
# commands
# ---------------------------------------------------------------------------

def build_parser():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--env-file", help="read INNBUCKS_* variables from this .env file")
    p.add_argument("--dry-run", action="store_true", help="print the request (secrets masked); send nothing")
    p.add_argument("--allow-live", action="store_true", help="allow money-moving calls when INNBUCKS_ENV=production")
    p.add_argument("--timeout", type=float, default=30.0)
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("self-test")
    s = sub.add_parser("lint"); s.add_argument("kind", choices=sorted(KINDS)); s.add_argument("file")
    s = sub.add_parser("deeplink"); s.add_argument("code")
    sub.add_parser("login")
    sub.add_parser("response-codes")

    def money(s, ref=True):
        s.add_argument("--amount", required=True, help="integer cents: 450 = 4.50")
        s.add_argument("--currency", default="USD", choices=CURRENCIES)
        if ref:
            s.add_argument("--reference", required=True)
            s.add_argument("--narration")

    s = sub.add_parser("generate"); money(s); s.add_argument("--type", default="PAYMENT", choices=("PAYMENT", "WITHDRAWAL"))
    s = sub.add_parser("inquiry"); s.add_argument("--code", required=True); s.add_argument("--reference")
    s = sub.add_parser("wait"); s.add_argument("--code", required=True)
    s.add_argument("--interval", type=float, default=30.0); s.add_argument("--max", type=float, default=660.0)
    s = sub.add_parser("linked-account"); s.add_argument("--msisdn", required=True)
    s.add_argument("--currency", default="USD", choices=CURRENCIES)
    s = sub.add_parser("deposit"); s.add_argument("--account", required=True); money(s); s.add_argument("--type", dest="deposit_type")
    s = sub.add_parser("deposit-inquiry"); s.add_argument("--account", required=True)
    s.add_argument("--original-ref", required=True); s.add_argument("--inquiry-ref", required=True)
    s = sub.add_parser("reversal"); s.add_argument("--account", required=True); money(s, ref=False)
    s.add_argument("--original-ref", required=True); s.add_argument("--reversal-ref", required=True)
    s = sub.add_parser("bank-change"); s.add_argument("--msisdn", required=True); money(s)
    s = sub.add_parser("utility"); s.add_argument("--provider", required=True); s.add_argument("--product", required=True)
    s.add_argument("--account", required=True); money(s)
    s = sub.add_parser("statement"); s.add_argument("--account", required=True)
    s.add_argument("--currency", default="USD", choices=CURRENCIES)
    s.add_argument("--start", required=True); s.add_argument("--end", required=True)
    return p


def checked(kind, body):
    errs, warns = lint(kind, body)
    for w in warns:
        print("warning: " + w, file=sys.stderr)
    if errs:
        for e in errs:
            print("error: " + e, file=sys.stderr)
        sys.exit(2)
    return body


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.env_file:
        load_env_file(args.env_file)
    env = os.environ.get("INNBUCKS_ENV", "test")

    if args.cmd == "self-test":
        return self_test()
    if args.cmd == "lint":
        raw = sys.stdin.read() if args.file == "-" else open(args.file, encoding="utf-8").read()
        try:
            body = json.loads(raw)
        except ValueError as e:
            print("error: not valid JSON: %s" % e)
            return 2
        errs, warns = lint(args.kind, body)
        for e in errs:
            print("error: " + e)
        for w in warns:
            print("warning: " + w)
        print("%s: %d error(s), %d warning(s)" % ("FAIL" if errs else "OK", len(errs), len(warns)))
        return 1 if errs else 0
    if args.cmd == "deeplink":
        print(deep_link(args.code, env))
        return 0
    if args.cmd in MONEY_MOVING and env == "production" and not args.allow_live:
        sys.exit("refusing to run %s against production without --allow-live" % args.cmd)

    api = Api(args)
    if args.cmd == "login":
        tok = api.login()
        print(json.dumps({"ok": True, "accessToken": mask(tok, 6), "environment": env}, indent=2))
        return 0
    if args.cmd == "response-codes":
        api.call("GET", "/api/file/response-codes")
        return 0

    narration = getattr(args, "narration", None)
    if args.cmd == "generate":
        body = checked("generate", {"reference": args.reference, "narration": narration or "Payment " + args.reference,
                                    "currency": args.currency, "amount": cents(args.amount), "type": args.type})
        res = api.call("POST", KINDS["generate"][0], body)
        if res.get("code"):
            print("deep link: " + deep_link(res["code"], env), file=sys.stderr)
    elif args.cmd == "inquiry":
        body = {"reference": args.reference, "code": args.code} if args.reference else {"code": args.code}
        api.call("POST", KINDS["inquiry"][0], checked("inquiry", body))
    elif args.cmd == "wait":
        interval = max(30.0, args.interval)  # InnBucks: one inquiry per 30 seconds
        started = time.time()
        while True:
            time.sleep(interval)
            res = api.call("POST", KINDS["inquiry"][0], {"code": args.code})
            if args.dry_run or (ok(res) and code_status(res) in ("claimed", "paid", "expired", "timed_out")):
                return 0
            if time.time() - started >= args.max:
                print("no final status after %ds: mark the payment UNKNOWN and review; do not call it failed"
                      % args.max, file=sys.stderr)
                return 4
    elif args.cmd == "linked-account":
        if not MSISDN.match(args.msisdn):
            sys.exit("--msisdn must be 263XXXXXXXXX")
        api.call("GET", "/api/v1/account/msisdn/%s/details?currency=%s" % (args.msisdn, args.currency))
    elif args.cmd == "deposit":
        body = {"reference": args.reference, "currency": args.currency, "amount": cents(args.amount),
                "narration": narration or "Deposit " + args.reference, "destinationAccount": args.account}
        if args.deposit_type:
            body["type"] = args.deposit_type
        api.call("POST", KINDS["deposit"][0], checked("deposit", body))
    elif args.cmd == "deposit-inquiry":
        api.call("POST", KINDS["deposit-inquiry"][0], checked("deposit-inquiry", {
            "accountNumber": args.account, "participantReference": args.inquiry_ref,
            "originalParticipantReference": args.original_ref}))
    elif args.cmd == "reversal":
        api.call("POST", KINDS["reversal"][0], checked("reversal", {
            "amount": cents(args.amount), "currency": args.currency, "type": "CREDIT",
            "destinationAccount": args.account, "participantReference": args.reversal_ref,
            "originalParticipantReference": args.original_ref}))
    elif args.cmd == "bank-change":
        api.call("POST", KINDS["bank-change"][0], checked("bank-change", {
            "reference": args.reference, "currency": args.currency, "amount": cents(args.amount),
            "narration": narration or "Change " + args.reference, "destinationMsisdn": args.msisdn}))
    elif args.cmd == "utility":
        api.call("POST", KINDS["utility"][0], checked("utility", {
            "provider": args.provider, "providerProduct": args.product, "amount": cents(args.amount),
            "currency": args.currency, "reference": args.reference, "narration": narration or "",
            "destinationAccount": args.account, "additionalData": {}}))
    elif args.cmd == "statement":
        api.call("POST", KINDS["statement"][0], checked("statement", {
            "accountNumber": args.account, "currency": args.currency,
            "startDateTime": args.start, "endDateTime": args.end}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
