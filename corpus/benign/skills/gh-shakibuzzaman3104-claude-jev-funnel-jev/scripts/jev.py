#!/usr/bin/env python3
"""
jev.py - dependency-free CLI for TypeSafe's Jev (System One) decision model.

Commands:
  jev.py [ask flags]   one request: --request FILE|-|JSON, or --state plus --noul/--choice/--score
  jev.py batch         judge many items with a question template (JSONL in, JSONL out, resumable)
  jev.py rank          sort items by one yes/no question
  jev.py eval          accuracy and calibration of a template on labeled cases
  jev.py doctor        check provider, key, credit and model with one tiny call
  jev.py usage         totals from the local usage ledger
  jev.py --version     print the version
Run `jev.py <command> --help` for every flag.

Examples:
  python3 jev.py --state @file.txt --noul id "Question?"
  python3 jev.py --state "text" --choice id "Which?" "a=desc" "b" "none=No listed option fits"
  python3 jev.py --request req.json --dry-run
  python3 jev.py batch --items lines.jsonl --template template.json --out answers.jsonl
  python3 jev.py rank --items files.jsonl --question "Is this item about billing?" --top 10
  python3 jev.py eval --cases labeled.jsonl --template template.json
  python3 jev.py usage --by label

Routes:
  openrouter (default)  POST https://openrouter.ai/api/alpha/decisions  model typesafe/jev-1.13
  typesafe              POST https://api.typesafe.ai/v1/systemone      model jev-1.13.0

Env:
  OPENROUTER_API_KEY  key for the OpenRouter route (not needed for --dry-run or --mock)
  TYPESAFE_API_KEY    key for --provider typesafe
  JEV_PROVIDER        default provider: openrouter or typesafe
  JEV_MODEL           model override
  JEV_APP_URL         optional HTTP-Referer sent to OpenRouter
  JEV_APP_NAME        optional X-Title sent to OpenRouter
  JEV_LEDGER          usage ledger path (default ~/.config/jev/usage.jsonl)
  JEV_NO_LEDGER=1     don't write the ledger
  JEV_CACHE_DIR       answer cache directory (default ~/.cache/jev)

Exit codes: 0 ok, 2 bad input or lint error, 3 auth/credit, 4 API/network, 5 partial batch
(or a single request with a missing or invalid answer).
"""

__version__ = "1.2.0"

import argparse
import collections
import concurrent.futures
import datetime
import email.utils
import hashlib
import http.client
import json
import math
import os
import random
import re
import sqlite3
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request

PROVIDERS = {
    "openrouter": {
        "url": "https://openrouter.ai/api/alpha/decisions",
        "model": "typesafe/jev-1.13",
        "key_env": "OPENROUTER_API_KEY",
        "key_help": "https://openrouter.ai/settings/keys; the account needs prepaid credit",
        # State + all questions combined: https://openrouter.ai/docs/guides/community/jev
        "request_limit": 32_000,
        "state_plus_question_limit": 32_000,
    },
    "typesafe": {
        "url": "https://api.typesafe.ai/v1/systemone",
        "model": "jev-1.13.0",
        "key_env": "TYPESAFE_API_KEY",
        "key_help": "https://console.typesafe.ai/keys",
        # 64k total, 32k for state + the longest question: https://docs.typesafe.ai/models
        "request_limit": 64_000,
        "state_plus_question_limit": 32_000,
    },
}
OPENROUTER_KEY_INFO_URL = "https://openrouter.ai/api/v1/key"
USER_AGENT = f"claude-jev-funnel/{__version__}"
PRICE_PER_MTOK_INPUT = 0.042  # USD, output free: https://docs.typesafe.ai/models
MAX_CHOICE_OPTIONS = 255
MIN_SCORE_LEVELS, MAX_SCORE_LEVELS = 2, 10
LARGE_STATE_TOKENS = 8_000
POSITIONAL_LIST_LIMIT = 5
RETRYABLE_STATUSES = {408, 429, 500, 502, 503, 504, 529}
MAX_ATTEMPTS = 5
TIMEOUT_SECONDS = 30
MAX_RETRY_AFTER_SECONDS = 60.0  # a longer server-requested wait falls back to normal backoff
MAX_RESPONSE_BYTES = 8 * 1024 * 1024  # a decisions body is kilobytes; refuse anything absurd
REQUEST_ID_HEADER = "x-typesafe-request-id"

PACK_TARGET = 0.8  # share of the provider limits a packed request aims for
DEFAULT_PER_REQUEST = 40
DEFAULT_WORKERS = 8
INLINE_STATE_TEXT = "Each question includes the item it asks about."
KEY_SEPARATOR = "__"

# Decision bands per question type (starting points; tune with `eval`)
NOUL_YES, NOUL_NO = 0.8, 0.2
CHOICE_ACT, CHOICE_REVIEW = 0.8, 0.5  # on the chosen option's probability (p_max)
# A choice/score distribution must sum to 1 within the larger of these (rounded values
# drift more with more options).
PROBABILITY_SUM_TOLERANCE, PROBABILITY_ROUNDING_SLACK = 0.02, 0.005
SCORE_CONFIDENT, SCORE_REVIEW = 0.8, 0.5  # on confidence
BAND_ORDER = {
    "noul": ("YES", "NO", "UNCERTAIN"),
    "choice": ("ACT", "REVIEW", "ABSTAIN"),
    "score": ("CONFIDENT", "REVIEW", "UNSURE"),
}

EVAL_TARGET = 0.95
CALIBRATION_EDGES = (0.0, 0.2, 0.4, 0.6, 0.8, 1.0)
CHOICE_EDGES = (0.0, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0)
NOUL_YES_THRESHOLDS = tuple(round(0.5 + 0.05 * i, 2) for i in range(10))
NOUL_NO_THRESHOLDS = tuple(round(0.5 - 0.05 * i, 2) for i in range(10))
CHOICE_THRESHOLDS = tuple(round(0.4 + 0.05 * i, 2) for i in range(12))
MIN_CASES_FOR_TRACKING = 10

SOURCE_WELLPOSED = "https://github.com/suraj-phanindra/wellposed"
SOURCE_POSITIONAL = "https://gist.github.com/pedramamini/014676fa8684d91bf7000f4623701ada"
SOURCE_SCORE_PAGE = "https://docs.typesafe.ai/primitives/score"
SOURCE_CALIBRATION = "https://primeline.cc/blog/typesafe-jev-pre-registered-test"
SCORE_NOTE = (
    "# score answers are the least calibrated type (ECE 0.254 vs 0.012 noul and 0.086 choice "
    f"in one independent test: {SOURCE_CALIBRATION}); use them for ranking or thresholds and "
    "calibrate with `jev.py eval` before auto-acting on them"
)

NO_MATCH_KEYS = {
    "none", "other", "unknown", "no_match", "nomatch", "not_stated", "unclear", "neither",
    "na", "n_a", "none_of_these", "not_applicable", "new", "no_failure", "no_fit", "abstain",
}
NO_MATCH_PHRASES = (
    "none of", "no listed", "not listed", "not stated", "neither", "does not fit",
    "doesn't fit", "no option", "cannot be determined", "can't be determined",
)
RATING_PREFIXES = ("how ", "to what extent", "rate ", "on a scale")
SECRET_PATTERNS = (
    ("an OpenRouter API key (sk-or-v1-...)", re.compile(r"sk-or-v1-[A-Za-z0-9]{20,}")),
    ("an Anthropic API key (sk-ant-...)", re.compile(r"sk-ant-[A-Za-z0-9_-]{20,}")),
    ("an AWS access key id (AKIA...)", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("a GitHub token (gh*_...)", re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}")),
    ("a Google API key (AIza...)", re.compile(r"AIza[0-9A-Za-z_-]{35}")),
    ("a private key block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("a Slack token (xox*-...)", re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}")),
)

PATH_SPAN = re.compile(r"[A-Za-z_][A-Za-z0-9_-]*(?:\.[A-Za-z0-9_-]+|\[\d+\])*")
PATH_ROOT = re.compile(r"[A-Za-z_][A-Za-z0-9_-]*")
PATH_SEGMENT = re.compile(r"\.([A-Za-z0-9_-]+)|\[(\d+)\]")
BACKTICK_SPAN = re.compile(r"`([^`\n]+)`")
ITEM_REFERENCE = re.compile(r"`item((?:\.[A-Za-z0-9_-]+|\[\d+\])*)`")

SUBCOMMANDS = ("batch", "rank", "eval", "doctor", "usage")
LEDGER_LOCK = threading.Lock()
LEDGER_WARNED = []


class InputError(Exception):
    """Bad input or a malformed request; exits 2."""


class ApiError(Exception):
    """A failed API call; fatal ones stop a batch."""

    def __init__(self, message, status=None, exit_code=4, fatal=False):
        super().__init__(message)
        self.message = message
        self.status = status
        self.exit_code = exit_code
        self.fatal = fatal


def fail(message, code):
    """Print an error and exit with code."""
    print(f"jev: error: {message}", file=sys.stderr)
    sys.exit(code)


def warn(message):
    """Print a warning on stderr."""
    print(f"jev: warning: {message}", file=sys.stderr)


def note(message):
    """Print an informational line on stderr."""
    print(message, file=sys.stderr)


def read_text_arg(value):
    """'@path' reads a file, '-' reads stdin, anything else is literal."""
    if value == "-":
        return sys.stdin.read()
    if value.startswith("@"):
        return read_file(value[1:])
    return value


def read_file(path):
    """Read a UTF-8 text file or raise InputError."""
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return handle.read()
    except OSError as error:
        raise InputError(f"cannot read {path}: {error}")


def parse_state(raw):
    """State may be JSON (object/array) or plain text."""
    stripped = raw.strip()
    if stripped[:1] in ("{", "["):
        try:
            return json.loads(stripped)
        except json.JSONDecodeError:
            pass
    return raw


def parse_json_or_text(raw):
    """JSON value when raw parses, else the text itself."""
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def is_wide_char(char):
    """CJK, kana and Hangul: about one token per character, not four."""
    code = ord(char)
    return 0x2E80 <= code <= 0x9FFF or 0xAC00 <= code <= 0xD7AF or 0xF900 <= code <= 0xFAFF


def estimate_tokens(obj):
    """Rough token count: ~4 characters per token, ~1 per CJK/Hangul character."""
    text = obj if isinstance(obj, str) else json.dumps(obj, ensure_ascii=False)
    wide = sum(1 for char in text if is_wide_char(char)) if not text.isascii() else 0
    return max(1, (len(text) - wide) // 4 + wide)


def canonical_json(value):
    """Stable JSON used for hashing."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def utc_timestamp():
    """Current UTC time as ISO-8601 with a Z suffix."""
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def elapsed_ms(started):
    """Milliseconds since a time.monotonic() reading."""
    return int((time.monotonic() - started) * 1000)


def parse_fields(value):
    """Split '--fields a,b' into a list."""
    if not value:
        return None
    fields = [field.strip() for field in value.split(",") if field.strip()]
    if not fields:
        raise InputError("--fields needs at least one field name")
    return fields


def resolve_provider(args):
    """Fill args.provider and args.model from flags, env and defaults."""
    name = getattr(args, "provider", None) or os.environ.get("JEV_PROVIDER") or "openrouter"
    if name not in PROVIDERS:
        raise InputError(f"unknown provider '{name}' (use {' or '.join(sorted(PROVIDERS))})")
    args.provider = name
    args.model = getattr(args, "model", None) or os.environ.get("JEV_MODEL") or PROVIDERS[name]["model"]
    return PROVIDERS[name]


def require_api_key(provider):
    """Return the provider's API key or raise a fatal ApiError."""
    key = os.environ.get(provider["key_env"])
    if not key:
        raise ApiError(f"{provider['key_env']} is not set (get one at {provider['key_help']})",
                       exit_code=3, fatal=True)
    return key


# ---------------------------------------------------------------- questions from flags

def parse_choice_option(spec):
    """'key=description' or a bare key."""
    if "=" in spec:
        key, description = spec.split("=", 1)
        return key.strip(), description.strip() or None
    return spec.strip(), None


def build_questions_from_flags(args):
    """Questions from --noul/--choice/--score flags."""
    questions = {}

    def add(question_id, question):
        """Add a question, rejecting duplicate ids."""
        if question_id in questions:
            raise InputError(f"duplicate question id '{question_id}'")
        questions[question_id] = question

    for question_id, instructions in args.noul or []:
        add(question_id, {"type": "noul", "instructions": instructions})

    for spec in args.choice or []:
        if len(spec) < 4:
            raise InputError("--choice needs: ID INSTRUCTIONS OPTION OPTION [...]")
        question_id, instructions, *options = spec
        criteria = dict(parse_choice_option(option) for option in options)
        add(question_id, {"type": "choice", "instructions": instructions, "criteria": criteria})

    for spec in args.score or []:
        if len(spec) < 4:
            raise InputError("--score needs: ID INSTRUCTIONS LEVEL LEVEL [...]")
        question_id, instructions, *levels = spec
        add(question_id, {"type": "score", "instructions": instructions, "criteria": levels})

    return questions


# ---------------------------------------------------------------- lint

class Findings:
    """Lint warnings and errors, each message kept once."""

    def __init__(self):
        self.entries = []
        self.seen = set()

    def add(self, severity, message):
        """Record a finding unless the same message was already recorded."""
        if message not in self.seen:
            self.seen.add(message)
            self.entries.append((severity, message))

    def error(self, message):
        """Record an error."""
        self.add("error", message)

    def secret(self, message):
        """Record a secret finding; --lenient never relaxes it."""
        self.add("secret", message)

    def warning(self, message):
        """Record a warning."""
        self.add("warning", message)


def report_findings(findings, lenient):
    """Print findings; exit 2 when errors remain and --lenient is off."""
    errors = 0
    secrets = 0
    for severity, message in findings.entries:
        if severity == "secret" or (severity == "error" and not lenient):
            errors += 1
            secrets += severity == "secret"
            print(f"jev: error: {message}", file=sys.stderr)
        else:
            warn(message)
    if secrets:
        fail(f"{errors} lint error(s); remove the secret(s) before sending; "
             "--lenient does not relax this", 2)
    if errors:
        fail(f"{errors} lint error(s); fix them or pass --lenient to send anyway", 2)


def check_question_structure(question_id, question):
    """Raise InputError on a malformed question."""
    if not isinstance(question, dict):
        raise InputError(f"question '{question_id}' must be an object")
    question_type = question.get("type")
    if question_type not in ("noul", "choice", "score"):
        raise InputError(f"question '{question_id}': type must be noul, choice or score")
    if not question.get("instructions"):
        raise InputError(f"question '{question_id}': missing instructions")
    criteria = question.get("criteria")
    if question_type == "choice":
        if not isinstance(criteria, dict) or len(criteria) < 2:
            raise InputError(f"choice '{question_id}': criteria must map 2+ options")
        if len(criteria) > MAX_CHOICE_OPTIONS:
            raise InputError(f"choice '{question_id}': max {MAX_CHOICE_OPTIONS} options")
    elif question_type == "score":
        if not isinstance(criteria, list):
            raise InputError(f"score '{question_id}': criteria must be an ordered array")
        if not MIN_SCORE_LEVELS <= len(criteria) <= MAX_SCORE_LEVELS:
            raise InputError(f"score '{question_id}': needs {MIN_SCORE_LEVELS}-{MAX_SCORE_LEVELS} levels")
    elif criteria is not None:
        if not isinstance(criteria, dict) or not set(criteria) <= {"true", "false"}:
            raise InputError(f"noul '{question_id}': criteria may only have 'true'/'false'")


def check_request_shape(body):
    """Raise InputError unless body has state, model and valid questions."""
    if not isinstance(body, dict):
        raise InputError("request must be a JSON object")
    for field in ("state", "model", "questions"):
        if field not in body:
            raise InputError(f"request is missing '{field}'")
    questions = body["questions"]
    if not isinstance(questions, dict) or not questions:
        raise InputError("'questions' must be a non-empty object keyed by question id")
    for question_id, question in questions.items():
        check_question_structure(question_id, question)


def check_request_limits(body, provider_name):
    """Enforce the provider's token limits; return (total, state) token estimates."""
    provider = PROVIDERS[provider_name]
    longest_question = max(estimate_tokens(question) for question in body["questions"].values())
    state_tokens = estimate_tokens(body["state"])
    total_tokens = estimate_tokens(body)
    pair_limit = provider["state_plus_question_limit"]
    if state_tokens + longest_question > pair_limit:
        raise InputError(
            f"state + longest question is ~{state_tokens + longest_question} tokens "
            f"(limit {pair_limit} on {provider_name}); trim state or use `jev.py batch`"
        )
    if total_tokens > provider["request_limit"]:
        raise InputError(
            f"request is ~{total_tokens} tokens (limit {provider['request_limit']} on "
            f"{provider_name}); split it or use `jev.py batch`"
        )
    return total_tokens, state_tokens


def iter_strings(value):
    """Every string inside a JSON value (dict values and list items)."""
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from iter_strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from iter_strings(child)


def backticked_paths(question):
    """Unique backticked spans in a question that look like state paths."""
    spans = []
    for text in iter_strings([question.get("instructions"), question.get("criteria")]):
        for span in BACKTICK_SPAN.findall(text):
            span = span.strip()
            if PATH_SPAN.fullmatch(span) and span not in spans:
                spans.append(span)
    return spans


def walk_path(span, namespace):
    """Follow a path through namespace; return (resolved, stop_segment, list_sizes)."""
    root = PATH_ROOT.match(span).group(0)
    current = namespace[root]
    sizes, stop = [], None
    for match in PATH_SEGMENT.finditer(span, len(root)):
        key, index = match.group(1), match.group(2)
        if stop is not None:
            if index is not None:
                sizes.append(None)
            continue
        if key is not None:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                stop = key
        elif isinstance(current, list):
            sizes.append(len(current))
            if int(index) < len(current):
                current = current[int(index)]
            else:
                stop = f"[{index}]"
        else:
            sizes.append(None)
            stop = f"[{index}]"
    return stop is None, stop, sizes


def positional_message(question_id, span, size):
    """Warning text for a positional reference."""
    target = (f"a list of {size} items by position" if size is not None
              else "a list by position (jev.py could not find that list)")
    return (
        f"question '{question_id}': `{span}` indexes {target}; answers can land on "
        f"the wrong item in long lists (measured 29/320 wrong at 25 items per request, 0/320 with "
        f"keyed ids: {SOURCE_POSITIONAL}). Use keyed ids (`items.k03`) or `jev.py batch`, which "
        f"does this for you"
    )


def lint_references(question_id, question, state, findings, template_scope=None):
    """Check backticked paths for broken references and positional indexing."""
    namespace = {}
    state_is_object = template_scope is not None or isinstance(state, dict)
    if template_scope is not None:
        namespace.update(template_scope)
    elif isinstance(state, dict):
        namespace.update(state)
    instructions = question.get("instructions")
    if isinstance(instructions, dict):
        namespace.update(instructions)
    for span in backticked_paths(question):
        root = PATH_ROOT.match(span).group(0)
        if root not in namespace:
            if "[" in span:
                findings.warning(positional_message(question_id, span, None))
            elif len(span) > len(root) and state_is_object:
                findings.warning(f"question '{question_id}': `{span}` does not start with a "
                                 f"top-level key of state or instructions")
            continue
        resolved, stop, sizes = walk_path(span, namespace)
        if not resolved:
            message = f"question '{question_id}': `{span}` does not resolve: stops at `{stop}`"
            if template_scope is not None and root == "item":
                findings.warning(message + " (checked against the first item)")
            else:
                findings.error(message)
        for size in sizes:
            if size is None or size > POSITIONAL_LIST_LIMIT:
                findings.warning(positional_message(question_id, span, size))
                break


def has_no_match_option(criteria):
    """True when a choice offers a none/other style option."""
    for key, description in criteria.items():
        label = str(key).strip().lower()
        if re.sub(r"[-\s]+", "_", label) in NO_MATCH_KEYS:
            return True
        texts = [label.replace("_", " ")]
        texts.extend(text.lower() for text in iter_strings(description))
        if any(phrase in text for text in texts for phrase in NO_MATCH_PHRASES):
            return True
    return False


def is_weak_level(level):
    """True for a score level that is a bare number or two words or fewer."""
    if isinstance(level, bool):
        return True
    if isinstance(level, (int, float)):
        return True
    if isinstance(level, str):
        text = level.strip()
        return bool(re.fullmatch(r"[-+]?\d+(?:\.\d+)?%?", text)) or len(text.split()) <= 2
    return False


def instruction_text(instructions):
    """The question text of a string or {question: ...} instructions."""
    if isinstance(instructions, str):
        return instructions
    if isinstance(instructions, dict) and isinstance(instructions.get("question"), str):
        return instructions["question"]
    return ""


def lint_question_content(question_id, question, findings, allow_no_none):
    """Question-level checks: no-match option, score levels, ratings asked as nouls."""
    question_type = question["type"]
    if question_type == "choice" and not has_no_match_option(question["criteria"]):
        message = (
            f"choice '{question_id}' has no no-match option (e.g. \"none\": \"None of the listed "
            f"options fit\"). When the true answer is missing, Jev picks a wrong option at "
            f"confidence 1.00 (measured by wellposed: {SOURCE_WELLPOSED}). Add one, or pass "
            f"--allow-no-none if an option always fits"
        )
        if allow_no_none:
            findings.warning(message)
        else:
            findings.error(message)
    elif question_type == "score":
        weak = [str(index) for index, level in enumerate(question["criteria"]) if is_weak_level(level)]
        if weak:
            findings.warning(
                f"score '{question_id}': level(s) {', '.join(weak)} are bare numbers or 1-2 words; "
                f"descriptive levels calibrate far better (official Score page: 0.55 / confidence "
                f"0.33 with numeric levels vs 0.0 / confidence 1.0 with descriptive ones on the same "
                f"input: {SOURCE_SCORE_PAGE}). Describe what each level looks like"
            )
    elif question_type == "noul":
        text = instruction_text(question["instructions"]).lstrip()
        if text.lower().startswith(RATING_PREFIXES):
            findings.warning(
                f"noul '{question_id}' reads like a rating (\"{text[:40]}\"); a noul answers yes/no. "
                f"Ask a yes/no question, or use a score with descriptive levels"
            )


def scan_for_secrets(value):
    """Names of secret kinds found in a JSON value; never the matches themselves."""
    if value is None:
        return []
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    return [name for name, pattern in SECRET_PATTERNS if pattern.search(text)]


def lint_request(body, provider_name, findings, allow_no_none):
    """Lint one full request; structural problems raise InputError."""
    check_request_shape(body)
    total_tokens, state_tokens = check_request_limits(body, provider_name)
    for question_id, question in body["questions"].items():
        lint_question_content(question_id, question, findings, allow_no_none)
        lint_references(question_id, question, body["state"], findings)
        for kind in scan_for_secrets([question.get("instructions"), question.get("criteria")]):
            findings.secret(f"question '{question_id}' instructions contain what looks like {kind}; "
                           f"remove it before sending")
    for kind in scan_for_secrets(body["state"]):
        findings.secret(f"state contains what looks like {kind}; remove it before sending")
    if state_tokens > LARGE_STATE_TOKENS:
        findings.warning(f"state is ~{state_tokens} tokens; accuracy drops with irrelevant detail, "
                         f"filter if you can")
    return total_tokens


def mentions_item(question):
    """True when a question references `item` in backticks."""
    texts = iter_strings([question.get("instructions"), question.get("criteria")])
    return any(ITEM_REFERENCE.search(text) for text in texts)


def lint_template(template, first_payload, pack, findings, allow_no_none):
    """Lint template questions once, resolving `item` against the first item."""
    scope = {"item": first_payload}
    if "context" in template:
        scope["context"] = template["context"]
        for kind in scan_for_secrets(template["context"]):
            findings.secret(f"template context contains what looks like {kind}; remove it before sending")
    for question_id, question in template["questions"].items():
        instructions = question["instructions"]
        if pack == "inline" and isinstance(instructions, dict) and "item" in instructions:
            raise InputError(f"question '{question_id}': instructions already have an 'item' key, "
                             f"which --pack inline fills with the item")
        lint_question_content(question_id, question, findings, allow_no_none)
        lint_references(question_id, question, None, findings, template_scope=scope)
        if pack == "keyed" and not mentions_item(question):
            findings.warning(
                f"question '{question_id}' never references `item`; with --pack keyed it is judged "
                f"against the whole batch state. Reference it (e.g. \"Does `item.text` ...?\") or "
                f"use --pack inline"
            )
        for kind in scan_for_secrets([instructions, question.get("criteria")]):
            findings.secret(f"question '{question_id}' instructions contain what looks like {kind}; "
                           f"remove it before sending")


def lint_item_secrets(items, findings):
    """One error per secret kind found across item payloads."""
    hits = {}
    for item in items:
        if item.payload is not None:
            for kind in scan_for_secrets(item.payload):
                hits.setdefault(kind, []).append(item.id)
    for kind, ids in hits.items():
        shown = ", ".join(repr(item_id) for item_id in ids[:5]) + (", ..." if len(ids) > 5 else "")
        findings.secret(f"{len(ids)} item(s) contain what looks like {kind} (ids: {shown}); "
                       f"remove it before sending")


# ---------------------------------------------------------------- HTTP, mock, ledger

def build_headers(provider_name, api_key):
    """Request headers for a provider."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": USER_AGENT,
    }
    if provider_name == "openrouter":
        app_url = os.environ.get("JEV_APP_URL")
        app_name = os.environ.get("JEV_APP_NAME")
        if app_url:
            headers["HTTP-Referer"] = app_url
        if app_name:
            headers["X-Title"] = app_name
            headers["X-OpenRouter-Title"] = app_name
    return headers


class NoRedirect(urllib.request.HTTPRedirectHandler):
    """Refuse redirects: following one would resend the Authorization header elsewhere."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


HTTP_OPENER = urllib.request.build_opener(NoRedirect)


def http_open(request, timeout):
    """Open a request without following redirects (3xx surfaces as HTTPError)."""
    return HTTP_OPENER.open(request, timeout=timeout)


def read_capped(response):
    """Response body, or ApiError when it is larger than MAX_RESPONSE_BYTES."""
    raw = response.read(MAX_RESPONSE_BYTES + 1)
    if len(raw) > MAX_RESPONSE_BYTES:
        raise ApiError(f"response larger than {MAX_RESPONSE_BYTES} bytes; refusing to read it",
                       getattr(response, "status", None), 4, False)
    return raw


def retry_after_seconds(headers):
    """Server-requested wait from retry-after-ms or retry-after (seconds or HTTP date), or None."""
    if not headers:
        return None
    value = headers.get("retry-after-ms")
    if value:
        try:
            return max(0.0, float(value) / 1000)
        except ValueError:
            pass
    value = headers.get("retry-after")
    if not value:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        pass
    try:
        when = email.utils.parsedate_to_datetime(value)
    except (TypeError, ValueError, IndexError):
        return None
    if when is None:
        return None
    return max(0.0, when.timestamp() - time.time())


def backoff_delay(attempt, retry_after):
    """Seconds to wait before the next attempt; retry_after is seconds or None."""
    if retry_after is not None and retry_after <= MAX_RETRY_AFTER_SECONDS:
        return float(retry_after)
    return min(30.0, (2 ** (attempt - 1)) + random.uniform(0, 0.5))


def format_validation_detail(text):
    """'loc: msg' lines for a FastAPI-style 422 body, else the text unchanged."""
    try:
        detail = json.loads(text).get("detail")
    except (ValueError, AttributeError):
        return text
    if not isinstance(detail, list):
        return text
    parts = []
    for entry in detail[:10]:
        if isinstance(entry, dict):
            location = ".".join(str(part) for part in entry.get("loc") or [] if part != "body")
            parts.append(f"{location}: {entry.get('msg')}" if location else str(entry.get("msg")))
    return "; ".join(parts) or text


def read_error_detail(error):
    """First part of an HTTP error body, validation errors as 'loc: msg', plus the request id."""
    try:
        text = error.read(64 * 1024).decode("utf-8", errors="replace")
    except (OSError, http.client.HTTPException):
        text = ""
    text = format_validation_detail(text)[:1000]
    request_id = error.headers.get(REQUEST_ID_HEADER) if error.headers else None
    if request_id:
        text = f"{text} (request id {request_id})" if text else f"request id {request_id}"
    return text


def api_error_for(status, detail, key_env):
    """Map a non-retryable HTTP status to an ApiError."""
    detail = f": {detail}" if detail else ""
    if status == 401:
        return ApiError(f"401 Unauthorized: check {key_env}", status, 3, True)
    if status == 402:
        return ApiError(f"402 Payment Required: add credit to the account behind {key_env}", status, 3, True)
    if status == 403:
        return ApiError(f"403 Forbidden (key limits, moderation, or network policy){detail}", status, 3, True)
    if status == 404:
        return ApiError(f"404 Not Found (check the model slug and endpoint){detail}", status, 2, True)
    if status == 400 and "unknown model" in detail.lower():
        return ApiError(f"400 Unknown model (check the model slug; retired pins return this){detail}",
                        status, 2, True)
    if 300 <= status < 400:
        return ApiError(f"HTTP {status} redirect refused (check the endpoint URL){detail}", status, 4, True)
    if status in (400, 422):
        return ApiError(f"HTTP {status} (request rejected){detail}", status, 2, False)
    return ApiError(f"HTTP {status}{detail}", status, 4, False)


def notify(callback, status, response, latency_ms):
    """Call an attempt callback when one is set."""
    if callback is not None:
        callback(status, response, latency_ms)


def post_with_retries(url, body, headers, key_env, on_attempt=None):
    """POST with retries on 429/5xx/529; return (response, status, latency_ms) or raise ApiError."""
    payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
    started = time.monotonic()
    last_error = "unknown error"
    for attempt in range(1, MAX_ATTEMPTS + 1):
        attempt_started = time.monotonic()
        request = urllib.request.Request(url, data=payload, method="POST", headers=headers)
        retry_after = None
        try:
            with http_open(request, timeout=TIMEOUT_SECONDS) as response:
                status = response.status
                raw = read_capped(response)
            try:
                parsed = json.loads(raw.decode("utf-8"))
            except ValueError:
                parsed = None
            if not isinstance(parsed, dict):
                notify(on_attempt, f"http_{status}", None, elapsed_ms(attempt_started))
                raise ApiError(f"HTTP {status} but the body is not a JSON object", status, 4, False)
            notify(on_attempt, "ok", parsed, elapsed_ms(attempt_started))
            return parsed, status, elapsed_ms(started)
        except urllib.error.HTTPError as error:
            notify(on_attempt, f"http_{error.code}", None, elapsed_ms(attempt_started))
            if error.code not in RETRYABLE_STATUSES:
                raise api_error_for(error.code, read_error_detail(error), key_env)
            last_error = f"HTTP {error.code}"
            retry_after = retry_after_seconds(error.headers)
        except (OSError, http.client.HTTPException) as error:
            notify(on_attempt, "network", None, elapsed_ms(attempt_started))
            last_error = f"network error: {error}"
        if attempt < MAX_ATTEMPTS:
            delay = backoff_delay(attempt, retry_after)
            print(f"jev: {last_error}, retrying in {delay:.1f}s ({attempt}/{MAX_ATTEMPTS})",
                  file=sys.stderr)
            time.sleep(delay)
    raise ApiError(f"giving up after {MAX_ATTEMPTS} attempts: {last_error}", None, 4, False)


def mock_response(body):
    """Deterministic fake answers (same body, same answers) for offline testing."""
    rng = random.Random(json.dumps(body, sort_keys=True))
    answers = {}
    for question_id, question in body["questions"].items():
        question_type = question["type"]
        if question_type == "noul":
            answers[question_id] = {"type": "noul", "noul": round(rng.random(), 2)}
            continue
        keys = (list(question["criteria"].keys()) if question_type == "choice"
                else [str(index) for index in range(len(question["criteria"]))])
        weights = [rng.random() ** 3 for _ in keys]
        total = sum(weights) or 1.0
        probabilities = {key: round(weight / total, 3) for key, weight in zip(keys, weights)}
        top = max(probabilities, key=probabilities.get)
        count = len(keys)
        confidence = round(max(0.0, min(1.0, (count * probabilities[top] - 1) / (count - 1))), 2)
        if question_type == "choice":
            answers[question_id] = {"type": "choice", "choice": top, "confidence": confidence,
                                    "probabilities": probabilities}
        else:
            score = round(sum(int(key) * p for key, p in probabilities.items()), 2)
            legend = {str(index): str(level) for index, level in enumerate(question["criteria"])}
            answers[question_id] = {"type": "score", "score": score, "confidence": confidence,
                                    "legend": legend, "probabilities": probabilities}
    return {"model": "mock", "answers": answers,
            "usage": {"input_tokens": estimate_tokens(body), "output_tokens": 0}}


def cost_from_response(response):
    """Return (cost_usd, 'reported'|'estimated', input_tokens) for a response."""
    usage = response.get("usage") or {}
    try:
        input_tokens = int(usage.get("input_tokens") or 0)
    except (TypeError, ValueError):
        input_tokens = 0
    cost = usage.get("cost")
    if cost is not None and not isinstance(cost, bool):
        try:
            return float(cost), "reported", input_tokens
        except (TypeError, ValueError):
            pass
    return input_tokens / 1_000_000 * PRICE_PER_MTOK_INPUT, "estimated", input_tokens


def ledger_path():
    """Where usage rows are appended."""
    return os.environ.get("JEV_LEDGER") or os.path.join(
        os.path.expanduser("~"), ".config", "jev", "usage.jsonl")


def ledger_disabled():
    """True when JEV_NO_LEDGER turns the ledger off."""
    return os.environ.get("JEV_NO_LEDGER", "").strip().lower() in ("1", "true", "yes")


def record_usage(row):
    """Append one row to the usage ledger (thread-safe; never raises)."""
    if ledger_disabled():
        return
    path = ledger_path()
    line = json.dumps(row, ensure_ascii=False) + "\n"
    with LEDGER_LOCK:
        try:
            directory = os.path.dirname(path)
            if directory:
                os.makedirs(directory, exist_ok=True)
            with open(path, "a", encoding="utf-8") as handle:
                handle.write(line)
        except OSError as error:
            if not LEDGER_WARNED:
                LEDGER_WARNED.append(True)
                warn(f"cannot write usage ledger {path}: {error}")


def ledger_recorder(command, args, questions, items):
    """Callback that writes one ledger row per HTTP attempt."""
    def record(status, response, latency_ms):
        """Write the ledger row for one attempt."""
        if response is not None:
            cost, cost_source, input_tokens = cost_from_response(response)
            model = response.get("model") or args.model
        else:
            cost, cost_source, input_tokens, model = 0.0, "estimated", 0, args.model
        record_usage({
            "ts": utc_timestamp(), "cmd": command, "provider": args.provider, "model": model,
            "label": getattr(args, "label", None), "questions": questions, "items": items,
            "input_tokens": input_tokens, "cost_usd": round(cost, 10), "cost_source": cost_source,
            "latency_ms": latency_ms, "status": status,
        })
    return record


# ---------------------------------------------------------------- answer validation

def is_probability(value):
    """A finite number in [0, 1] (bools excluded)."""
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(value) and 0.0 <= value <= 1.0)


def answer_problem(question, answer):
    """Why an answer can't be trusted for this question, or None. Fail closed: a typed
    shape that doesn't match what was asked must never be banded as ACT or YES."""
    question_type = question.get("type")
    if answer.get("type") != question_type:
        return f"expected a {question_type} answer, got {answer.get('type')!r}"
    if question_type == "noul":
        return None if is_probability(answer.get("noul")) else "noul is not a probability"
    if "confidence" in answer and not is_probability(answer["confidence"]):
        return "confidence is not a probability"
    criteria = question.get("criteria")
    options = ([str(key) for key in criteria] if question_type == "choice"
               else [str(index) for index in range(len(criteria))])
    probabilities = answer.get("probabilities")
    if probabilities is not None:
        if not isinstance(probabilities, dict) or not probabilities:
            return "probabilities is not an object"
        unknown = [key for key in probabilities if key not in options]
        if unknown:
            return "probabilities name unknown options: " + ", ".join(sorted(unknown)[:5])
        if not all(is_probability(p) for p in probabilities.values()):
            return "probabilities hold a value outside [0, 1]"
        slack = max(PROBABILITY_SUM_TOLERANCE, PROBABILITY_ROUNDING_SLACK * len(probabilities))
        if abs(sum(probabilities.values()) - 1.0) > slack:
            return "probabilities do not sum to 1"
    if question_type == "choice":
        choice = answer.get("choice")
        if choice not in options:
            return f"choice {choice!r} is not one of the offered options"
        if probabilities and probabilities.get(choice, 0.0) + 1e-6 < max(probabilities.values()):
            return f"choice {choice!r} is not the most probable option"
        return None
    score = answer.get("score")
    if (not isinstance(score, (int, float)) or isinstance(score, bool) or not math.isfinite(score)
            or not -1e-6 <= score <= len(options) - 1 + 1e-6):
        return f"score is outside 0..{len(options) - 1}"
    return None


# ---------------------------------------------------------------- bands and display

def choice_top_probability(answer):
    """Probability of the chosen option (p_max)."""
    probabilities = answer.get("probabilities") or {}
    if answer.get("choice") in probabilities:
        return float(probabilities[answer["choice"]])
    if probabilities:
        return float(max(probabilities.values()))
    return float(answer.get("confidence") or 0.0)


def choice_band(p_max):
    """ACT / REVIEW / ABSTAIN from the chosen option's probability."""
    if p_max >= CHOICE_ACT:
        return "ACT"
    if p_max >= CHOICE_REVIEW:
        return "REVIEW"
    return "ABSTAIN"


def band_for(answer):
    """Default decision band for an answer."""
    answer_type = answer.get("type")
    if answer_type == "noul":
        value = answer.get("noul", 0.5)
        if value >= NOUL_YES:
            return "YES"
        if value <= NOUL_NO:
            return "NO"
        return "UNCERTAIN"
    if answer_type == "choice":
        return choice_band(choice_top_probability(answer))
    confidence = answer.get("confidence", 0.0)
    if confidence >= SCORE_CONFIDENT:
        return "CONFIDENT"
    if confidence >= SCORE_REVIEW:
        return "REVIEW"
    return "UNSURE"


def nearest_level(score):
    """Index of the level nearest a fractional score (halves round up)."""
    return int(math.floor(float(score) + 0.5))


def format_answer(question_id, answer):
    """One display line for an answer."""
    answer_type = answer.get("type")
    band = band_for(answer)
    if answer_type == "noul":
        return f"{question_id:<28} noul    p(yes)={answer.get('noul', 0.0):.2f}  [{band}]"
    if answer_type == "choice":
        choice = answer.get("choice")
        p_choice = choice_top_probability(answer)
        others = sorted(((key, p) for key, p in (answer.get("probabilities") or {}).items() if key != choice),
                        key=lambda pair: pair[1], reverse=True)
        runner_up = others[0] if others else None
        margin = p_choice - (runner_up[1] if runner_up else 0.0)
        next_text = f"  next={runner_up[0]}:{runner_up[1]:.2f}" if runner_up else ""
        return (f"{question_id:<28} choice  {choice}  conf={answer.get('confidence', 0.0):.2f}  "
                f"p={p_choice:.2f}  margin={margin:.2f}{next_text}  [{band}]")
    if answer_type == "score":
        legend = answer.get("legend", {})
        nearest = legend.get(str(nearest_level(answer.get("score", 0.0))), "")
        return (f"{question_id:<28} score   {answer.get('score', 0.0):.2f} (~{nearest})  "
                f"conf={answer.get('confidence', 0.0):.2f}  [{band}]")
    return f"{question_id:<28} {json.dumps(answer)}"


def format_cost(cost, cost_source):
    """'cost=$x (reported)' or 'cost~$x (estimated)'."""
    sign = "=" if cost_source == "reported" else "~"
    return f"cost{sign}${cost:.6f} ({cost_source})"


# ---------------------------------------------------------------- ask (single request)

ASK_EPILOG = """\
commands (run `jev.py <command> --help`):
  batch   judge many items with a question template (JSONL in, JSONL out, resumable)
  rank    sort items by one yes/no question
  eval    accuracy and calibration of a template on labeled cases
  doctor  check provider, key, credit and model with one tiny call
  usage   totals from the local usage ledger

bands: noul YES >= 0.8, NO <= 0.2, else UNCERTAIN
       choice (on the chosen option's probability) ACT >= 0.8, REVIEW >= 0.5, else ABSTAIN
       score (on confidence) CONFIDENT >= 0.8, REVIEW >= 0.5, else UNSURE
exit codes: 0 ok, 2 bad input or lint error, 3 auth/credit, 4 API/network,
            5 partial batch, or a missing/invalid answer
"""


def add_common_flags(parser, with_cache):
    """Flags shared by ask, batch, rank and eval."""
    parser.add_argument("--provider", choices=sorted(PROVIDERS),
                        help="API route: openrouter (default) or typesafe; env JEV_PROVIDER")
    parser.add_argument("--model", help="model id; default $JEV_MODEL, else typesafe/jev-1.13 "
                                        "(openrouter) or jev-1.13.0 (typesafe)")
    parser.add_argument("--label", help="tag stored with each call in the usage ledger")
    parser.add_argument("--dry-run", action="store_true",
                        help="lint and print the request body with a token and cost estimate; send nothing")
    parser.add_argument("--mock", action="store_true",
                        help="deterministic fake answers offline; no key, no ledger, no cache")
    parser.add_argument("--lenient", action="store_true",
                        help="turn lint errors into warnings (malformed questions and detected secrets still fail)")
    parser.add_argument("--allow-no-none", action="store_true",
                        help="allow a choice without a no-match option (warning instead of error)")
    if with_cache:
        parser.add_argument("--no-cache", action="store_true",
                            help="don't read or write the local answer cache")


def build_ask_parser():
    """Parser for the single-request mode."""
    parser = argparse.ArgumentParser(
        prog="jev.py", description="Send one request to Jev (TypeSafe System One) and print banded answers.",
        epilog=ASK_EPILOG, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--request", help="full request JSON: a path, '-' for stdin, or inline JSON")
    parser.add_argument("--state", help="state: literal text/JSON, @path, or '-' for stdin")
    parser.add_argument("--noul", nargs=2, action="append", metavar=("ID", "INSTRUCTIONS"),
                        help="add a yes/no question (repeatable)")
    parser.add_argument("--choice", nargs="+", action="append", metavar="ARG",
                        help="add a choice: ID INSTRUCTIONS OPTION[=desc] OPTION[=desc] ... "
                             "(repeatable; include a no-match option such as none=...)")
    parser.add_argument("--score", nargs="+", action="append", metavar="ARG",
                        help="add a score: ID INSTRUCTIONS LEVEL LEVEL ... lowest first, "
                             "2-10 descriptive levels (repeatable)")
    parser.add_argument("--json", action="store_true", help="print the raw response JSON plus _latency_ms")
    add_common_flags(parser, with_cache=False)
    parser.add_argument("--version", action="version", version=f"jev.py {__version__}")
    return parser


def build_ask_body(args):
    """Request body from --request and/or --state plus question flags."""
    if args.request:
        raw = args.request if args.request.strip().startswith("{") else None
        text = raw if raw is not None else read_text_arg(
            args.request if args.request == "-" else "@" + args.request)
        try:
            body = json.loads(text)
        except json.JSONDecodeError as error:
            raise InputError(f"request is not valid JSON: {error}")
        if not isinstance(body, dict):
            raise InputError("request must be a JSON object")
        body.setdefault("model", args.model)
        if args.state is not None:
            body["state"] = parse_state(read_text_arg(args.state))
        flag_questions = build_questions_from_flags(args)
        if flag_questions:
            body.setdefault("questions", {}).update(flag_questions)
        return body
    if args.state is None:
        raise InputError("provide --request or --state (see --help)")
    return {
        "state": parse_state(read_text_arg(args.state)),
        "model": args.model,
        "questions": build_questions_from_flags(args),
    }


def run_ask(argv):
    """Single-request mode (no subcommand)."""
    args = build_ask_parser().parse_args(argv)
    try:
        provider = resolve_provider(args)
        body = build_ask_body(args)
        findings = Findings()
        estimated_tokens = lint_request(body, args.provider, findings, args.allow_no_none)
    except InputError as error:
        fail(str(error), 2)
    report_findings(findings, args.lenient)

    if args.dry_run:
        print(json.dumps(body, indent=2, ensure_ascii=False))
        estimated_cost = estimated_tokens / 1_000_000 * PRICE_PER_MTOK_INPUT
        note(f"\n# dry run: {len(body['questions'])} questions, ~{estimated_tokens} input tokens "
             f"(limit {provider['request_limit']}), ~${estimated_cost:.6f} at list price, "
             f"provider={args.provider} model={body['model']}")
        return 0

    if args.mock:
        started = time.monotonic()
        response = mock_response(body)
        latency = elapsed_ms(started)
    else:
        try:
            api_key = require_api_key(provider)
            recorder = ledger_recorder("ask", args, len(body["questions"]), None)
            response, _status, latency = post_with_retries(
                provider["url"], body, build_headers(args.provider, api_key), provider["key_env"], recorder)
        except ApiError as error:
            fail(error.message, error.exit_code)
    response["_latency_ms"] = latency

    if args.json:
        print(json.dumps(response, indent=2, ensure_ascii=False))
        return 0

    answers = response.get("answers", {})
    unusable = 0
    for question_id, question in body["questions"].items():
        answer = answers.get(question_id)
        problem = (answer_problem(question, answer) if isinstance(answer, dict)
                   else "no answer returned")
        if problem:
            unusable += 1
            print(f"{question_id:<28} ({problem})")
        else:
            print(format_answer(question_id, answer))

    cost, cost_source, input_tokens = cost_from_response(response)
    latency = response.get("_latency_ms")
    latency_text = f" {latency} ms" if latency is not None else ""
    note(f"# provider={args.provider} model={response.get('model')} input_tokens={input_tokens} "
         f"{format_cost(cost, cost_source)}{latency_text}")
    if any(question.get("type") == "score" for question in body["questions"].values()):
        note(SCORE_NOTE)
    return 5 if unusable else 0


# ---------------------------------------------------------------- items and templates

class Item:
    """One input record: id, payload sent to Jev, optional error and labels."""

    def __init__(self, index, item_id, payload, error=None, expect=None):
        self.index = index
        self.id = item_id
        self.id_key = json.dumps(item_id)
        self.payload = payload
        self.error = error
        self.expect = expect


def as_record(value, raw_line=None):
    """Turn a parsed JSON value (or raw line) into an item record."""
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        return {"text": value}
    return {"text": raw_line if raw_line is not None else json.dumps(value)}


def read_records(path):
    """Read a JSON array or JSONL ('-' = stdin) into (index, record) pairs."""
    text = sys.stdin.read() if path == "-" else read_file(path)
    is_json_file = path.lower().endswith(".json")
    if is_json_file or text.lstrip().startswith("["):
        try:
            data = json.loads(text)
        except json.JSONDecodeError as error:
            if is_json_file:
                raise InputError(f"{path} is not valid JSON: {error}")
            data = None
        if data is not None:
            if not isinstance(data, list):
                raise InputError(f"{path} must contain a JSON array (or use JSONL)")
            return [(index, as_record(value)) for index, value in enumerate(data)]
    records = []
    for index, line in enumerate(text.splitlines()):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            value = line
        records.append((index, as_record(value, line)))
    return records


def load_items(path, fields, is_cases=False):
    """Load items (or eval cases) with ids and payloads."""
    items, seen = [], {}
    for index, record in read_records(path):
        raw_id = record.get("id")
        if raw_id is None:
            item_id = index
        elif isinstance(raw_id, bool) or not isinstance(raw_id, (str, int)):
            raise InputError(f"record {index}: id must be a string or an integer")
        else:
            item_id = raw_id
        id_key = json.dumps(item_id)
        if id_key in seen:
            raise InputError(f"duplicate id {item_id!r} (records {seen[id_key]} and {index})")
        seen[id_key] = index
        expect = record.get("expect") if is_cases else None
        error, payload = None, None
        if fields:
            missing = [field for field in fields if field not in record]
            if missing:
                error = "missing field(s): " + ", ".join(missing)
            else:
                payload = {field: record[field] for field in fields}
        else:
            payload = {key: value for key, value in record.items()
                       if key != "id" and not (is_cases and key == "expect")}
            if not payload:
                error = "item has no fields to send"
                payload = None
        items.append(Item(index, item_id, payload, error, expect))
    if not items:
        raise InputError(f"no items found in {path}")
    return items


def load_template(path):
    """Read and structurally check a question template."""
    text = sys.stdin.read() if path == "-" else read_file(path)
    try:
        template = json.loads(text)
    except json.JSONDecodeError as error:
        raise InputError(f"template {path} is not valid JSON: {error}")
    if not isinstance(template, dict) or not isinstance(template.get("questions"), dict) \
            or not template["questions"]:
        raise InputError("template needs a non-empty \"questions\" object")
    unknown = sorted(set(template) - {"context", "questions"})
    if unknown:
        warn(f"template keys ignored: {', '.join(unknown)} (only context and questions are used)")
    for question_id, question in template["questions"].items():
        check_question_structure(question_id, question)
    return {key: template[key] for key in ("context", "questions") if key in template}


# ---------------------------------------------------------------- packing

PackEntry = collections.namedtuple(
    "PackEntry", "item key questions state_chars question_chars longest_chars")


class PackedRequest:
    """A request body and which item sits under which key."""

    def __init__(self, body, entries):
        self.body = body
        self.entries = entries
        self.tokens = estimate_tokens(body)


def make_key(position):
    """Generated item key: k + zero-padded 5+ digit position."""
    return f"k{position:05d}"


def rewrite_item_refs(value, key):
    """Point backticked `item` paths at `items.<key>`."""
    if isinstance(value, str):
        return ITEM_REFERENCE.sub(lambda match: f"`items.{key}{match.group(1)}`", value)
    if isinstance(value, dict):
        return {name: rewrite_item_refs(child, key) for name, child in value.items()}
    if isinstance(value, list):
        return [rewrite_item_refs(child, key) for child in value]
    return value


def item_questions(template_questions, payload, key, pack):
    """The template's questions for one item, keyed by request question id."""
    questions = {}
    for question_id, question in template_questions.items():
        packed = dict(question)
        if pack == "keyed":
            packed["instructions"] = rewrite_item_refs(question["instructions"], key)
            if "criteria" in question:
                packed["criteria"] = rewrite_item_refs(question["criteria"], key)
        elif isinstance(question["instructions"], dict):
            packed["instructions"] = dict({"item": payload}, **question["instructions"])
        else:
            packed["instructions"] = {"item": payload, "question": question["instructions"]}
        questions[f"{key}{KEY_SEPARATOR}{question_id}"] = packed
    return questions


def build_state(template, pack, entries):
    """Request state for a group of packed items."""
    has_context = "context" in template
    if pack == "keyed":
        items = {entry.key: entry.item.payload for entry in entries}
        return {"context": template["context"], "items": items} if has_context else {"items": items}
    return {"context": template["context"]} if has_context else INLINE_STATE_TEXT


def pack_items(items, template, pack, model, provider, per_request):
    """Greedily pack items into requests; return (requests, [(item, tokens)] too large)."""
    base_state_chars = len(json.dumps(build_state(template, pack, []), ensure_ascii=False))
    overhead_chars = len(json.dumps({"state": None, "model": model, "questions": {}}, ensure_ascii=False))
    request_target = provider["request_limit"] * PACK_TARGET * 4
    pair_target = provider["state_plus_question_limit"] * PACK_TARGET * 4
    request_hard = provider["request_limit"] * 4
    pair_hard = provider["state_plus_question_limit"] * 4

    def measure(item, position):
        """Questions and character sizes for an item at a position."""
        key = make_key(position)
        questions = item_questions(template["questions"], item.payload, key, pack)
        sizes = [len(json.dumps(question, ensure_ascii=False)) for question in questions.values()]
        state_chars = (len(key) + len(json.dumps(item.payload, ensure_ascii=False)) + 6
                       if pack == "keyed" else 0)
        question_chars = sum(sizes) + sum(len(request_id) + 6 for request_id in questions)
        return PackEntry(item, key, questions, state_chars, question_chars, max(sizes))

    def sizes_with(entries):
        """(request chars, state + longest question chars) for a group."""
        state = base_state_chars + sum(entry.state_chars for entry in entries)
        request = overhead_chars + state + sum(entry.question_chars for entry in entries)
        pair = state + max(entry.longest_chars for entry in entries)
        return request, pair

    requests, oversized, group = [], [], []

    def flush():
        """Turn the current group into a request."""
        questions = {}
        for entry in group:
            questions.update(entry.questions)
        body = {"state": build_state(template, pack, group), "model": model, "questions": questions}
        requests.append(PackedRequest(body, [(entry.item, entry.key) for entry in group]))
        group.clear()

    for item in items:
        entry = measure(item, len(group) + 1)
        request_chars, pair_chars = sizes_with(group + [entry])
        if group and (len(group) >= per_request or request_chars > request_target
                      or pair_chars > pair_target):
            flush()
            entry = measure(item, 1)
            request_chars, pair_chars = sizes_with([entry])
        if not group and (request_chars > request_hard or pair_chars > pair_hard):
            oversized.append((item, max(request_chars, pair_chars) // 4))
            continue
        group.append(entry)
        if len(group) == 1 and (request_chars > request_target or pair_chars > pair_target):
            flush()
    if group:
        flush()
    return requests, oversized


# ---------------------------------------------------------------- cache and --out file

def cache_path():
    """sqlite answer cache location."""
    base = os.environ.get("JEV_CACHE_DIR") or os.path.join(os.path.expanduser("~"), ".cache", "jev")
    return os.path.join(base, "cache.sqlite")


def cache_key(model, pack, template, payload):
    """sha256 of the canonical [model, pack, template, payload]."""
    return hashlib.sha256(canonical_json([model, pack, template, payload]).encode("utf-8")).hexdigest()


class AnswerCache:
    """Per-item answers in sqlite, shared across runs."""

    def __init__(self, path):
        self.lock = threading.Lock()
        self.connection = sqlite3.connect(path, timeout=30, check_same_thread=False)
        self.connection.execute("CREATE TABLE IF NOT EXISTS answers "
                                "(key TEXT PRIMARY KEY, value TEXT, model TEXT, ts TEXT)")
        self.connection.commit()

    @classmethod
    def open(cls, create):
        """Open the cache, or None when it is missing (and create is False) or unusable."""
        path = cache_path()
        if not create and not os.path.exists(path):
            return None
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            return cls(path)
        except (OSError, sqlite3.Error) as error:
            warn(f"answer cache unavailable ({error}); continuing without it")
            return None

    def get(self, key):
        """Return (answers, model) or None."""
        try:
            with self.lock:
                row = self.connection.execute(
                    "SELECT value, model FROM answers WHERE key = ?", (key,)).fetchone()
        except sqlite3.Error:
            return None
        if row is None:
            return None
        try:
            return json.loads(row[0]), row[1]
        except ValueError:
            return None

    def put_many(self, rows):
        """Store [(key, answers, model)] in one transaction."""
        if not rows:
            return
        timestamp = utc_timestamp()
        try:
            with self.lock:
                self.connection.executemany(
                    "INSERT OR REPLACE INTO answers (key, value, model, ts) VALUES (?, ?, ?, ?)",
                    [(key, json.dumps(answers, ensure_ascii=False), model, timestamp)
                     for key, answers, model in rows])
                self.connection.commit()
        except sqlite3.Error as error:
            warn(f"cannot write answer cache: {error}")

    def close(self):
        """Close the connection."""
        self.connection.close()


def read_out_file(path):
    """Last row per id in an existing --out file, plus ids in first-seen order."""
    rows, order = {}, []
    if not path or not os.path.exists(path):
        return rows, order
    unreadable = 0
    try:
        with open(path, "r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                except ValueError:
                    unreadable += 1
                    continue
                if not isinstance(row, dict) or "id" not in row:
                    unreadable += 1
                    continue
                key = json.dumps(row["id"])
                if key not in rows:
                    order.append(key)
                rows[key] = row
    except OSError as error:
        raise InputError(f"cannot read {path}: {error}")
    if unreadable:
        warn(f"{path}: skipped {unreadable} unreadable line(s)")
    return rows, order


class OutWriter:
    """Appends rows to --out as requests finish."""

    def __init__(self, path):
        self.lock = threading.Lock()
        needs_newline = False
        if os.path.exists(path) and os.path.getsize(path) > 0:
            with open(path, "rb") as handle:
                handle.seek(-1, os.SEEK_END)
                needs_newline = handle.read(1) != b"\n"
        try:
            self.handle = open(path, "a", encoding="utf-8")
        except OSError as error:
            raise InputError(f"cannot write {path}: {error}")
        if needs_newline:
            self.handle.write("\n")

    def write(self, rows):
        """Append rows and flush."""
        if not rows:
            return
        with self.lock:
            for row in rows:
                self.handle.write(json.dumps(row, ensure_ascii=False) + "\n")
            self.handle.flush()

    def close(self):
        """Close the file."""
        self.handle.close()


def compact_out_file(path, rows, order):
    """Rewrite --out with one row per id in order, via a temp file and os.replace."""
    directory = os.path.dirname(os.path.abspath(path))
    handle, temp_path = tempfile.mkstemp(prefix=".jev-", suffix=".jsonl", dir=directory)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as out:
            for key in order:
                out.write(json.dumps(rows[key], ensure_ascii=False) + "\n")
        os.replace(temp_path, path)
    except BaseException:
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        raise


# ---------------------------------------------------------------- batch engine

def answer_row(item, answers, model, cached):
    """A success row."""
    return {"id": item.id, "answers": answers, "model": model, "cached": cached}


def error_row(item, message):
    """An error row."""
    return {"id": item.id, "error": message}


def percentile(values, fraction):
    """Nearest-rank percentile."""
    ordered = sorted(values)
    return ordered[max(0, math.ceil(fraction * len(ordered)) - 1)]


def run_batch_engine(args, template, items, command, out_path=None):
    """Lint, pack, send and collect rows for a templated job."""
    provider = PROVIDERS[args.provider]
    question_ids = list(template["questions"])
    findings = Findings()
    valid = [item for item in items if item.error is None]
    if valid:
        lint_template(template, valid[0].payload, args.pack, findings, args.allow_no_none)
    lint_item_secrets(items, findings)
    report_findings(findings, args.lenient)

    existing, existing_order = read_out_file(out_path)
    rows, new_rows, todo = {}, [], []
    stats = {"items": len(items), "cached": 0, "resumed": 0, "requests": 0, "input_tokens": 0,
             "cost_reported": 0.0, "cost_estimated": 0.0, "latencies": [], "not_sent": 0}
    for item in items:
        previous = existing.get(item.id_key)
        reusable = (previous is not None and isinstance(previous.get("answers"), dict)
                    and set(question_ids) <= set(previous["answers"])
                    and (args.mock or previous.get("model") != "mock"))
        if reusable:
            rows[item.id_key] = previous
            stats["resumed"] += 1
        elif item.error:
            rows[item.id_key] = error_row(item, item.error)
            new_rows.append(rows[item.id_key])
        else:
            todo.append(item)

    cache = None if (args.no_cache or args.mock) else AnswerCache.open(create=not args.dry_run)
    to_send = []
    for item in todo:
        hit = cache.get(cache_key(args.model, args.pack, template, item.payload)) if cache else None
        if hit is not None:
            rows[item.id_key] = answer_row(item, hit[0], hit[1], True)
            new_rows.append(rows[item.id_key])
            stats["cached"] += 1
        else:
            to_send.append(item)

    requests, oversized = pack_items(to_send, template, args.pack, args.model, provider, args.per_request)
    for item, tokens in oversized:
        rows[item.id_key] = error_row(
            item, f"item is too large for one request (~{tokens} tokens; {args.provider} limits "
                  f"{provider['request_limit']} per request, {provider['state_plus_question_limit']} "
                  f"for state + longest question); trim it or use --fields")
        new_rows.append(rows[item.id_key])

    large_states = 0
    for request in requests:
        check_request_shape(request.body)
        _total, state_tokens = check_request_limits(request.body, args.provider)
        if state_tokens > LARGE_STATE_TOKENS:
            large_states += 1
    if large_states:
        warn(f"{large_states} packed request(s) have state over ~{LARGE_STATE_TOKENS} tokens; accuracy "
             f"drops with irrelevant detail, so lower --per-request or use --pack inline")

    outcome = {"rows": rows, "stats": stats, "fatal": None, "dry_run": args.dry_run,
               "mock": args.mock, "out_path": out_path, "requests": requests, "exit_code": 0}
    if args.dry_run:
        if requests:
            print(json.dumps(requests[0].body, indent=2, ensure_ascii=False))
        tokens = sum(request.tokens for request in requests)
        errors = sum(1 for row in rows.values() if "error" in row)
        note(f"# dry run: items {len(items)}  to send {len(to_send) - len(oversized)}  cached "
             f"{stats['cached']}  resumed {stats['resumed']}  errors {errors}")
        estimated_cost = tokens / 1e6 * PRICE_PER_MTOK_INPUT
        note(f"# requests {len(requests)}  ~{tokens} input tokens  ~${estimated_cost:.6f} "
             f"at list price  provider={args.provider} model={args.model} pack={args.pack}")
        if cache:
            cache.close()
        return outcome

    api_key = require_api_key(provider) if (requests and not args.mock) else None
    headers = build_headers(args.provider, api_key) if api_key else None
    writer = OutWriter(out_path) if out_path else None
    if writer:
        writer.write(new_rows)

    stop = threading.Event()

    def send(request):
        """Send one packed request (or mock it); None once the job has stopped."""
        if stop.is_set():
            return None
        started = time.monotonic()
        if args.mock:
            return mock_response(request.body), elapsed_ms(started)
        recorder = ledger_recorder(command, args, len(request.body["questions"]), len(request.entries))
        response, _status, latency = post_with_retries(
            provider["url"], request.body, headers, provider["key_env"], recorder)
        return response, latency

    def collect(request, result):
        """Split a response into per-item rows and cache them."""
        response, latency = result
        stats["requests"] += 1
        stats["latencies"].append(latency)
        cost, cost_source, input_tokens = cost_from_response(response)
        stats["input_tokens"] += input_tokens
        stats["cost_reported" if cost_source == "reported" else "cost_estimated"] += cost
        answers = response.get("answers") or {}
        model = response.get("model") or args.model
        finished, cache_rows = [], []
        for item, key in request.entries:
            item_answers, missing, invalid = {}, [], []
            for question_id in question_ids:
                sent_id = f"{key}{KEY_SEPARATOR}{question_id}"
                answer = answers.get(sent_id)
                if not isinstance(answer, dict):
                    missing.append(question_id)
                    continue
                problem = answer_problem(request.body["questions"][sent_id], answer)
                if problem:
                    invalid.append(f"{question_id} ({problem})")
                else:
                    item_answers[question_id] = answer
            if missing:
                row = error_row(item, "no answer returned for " + ", ".join(missing))
            elif invalid:
                row = error_row(item, "invalid answer for " + "; ".join(invalid))
            else:
                row = answer_row(item, item_answers, model, False)
                cache_rows.append((cache_key(args.model, args.pack, template, item.payload),
                                   item_answers, model))
            rows[item.id_key] = row
            finished.append(row)
        if cache and not args.mock:
            cache.put_many(cache_rows)
        return finished

    pending = collections.deque(requests)
    in_flight = {}
    pool = concurrent.futures.ThreadPoolExecutor(max_workers=args.workers)
    try:
        while pending or in_flight:
            while pending and not stop.is_set() and len(in_flight) < args.workers:
                request = pending.popleft()
                in_flight[pool.submit(send, request)] = request
            if not in_flight:
                break
            done, _ = concurrent.futures.wait(list(in_flight), return_when=concurrent.futures.FIRST_COMPLETED)
            for future in done:
                request = in_flight.pop(future)
                try:
                    result = future.result()
                except ApiError as error:
                    stats["requests"] += 1
                    finished = []
                    for item, _key in request.entries:
                        rows[item.id_key] = error_row(item, error.message)
                        finished.append(rows[item.id_key])
                    if error.fatal and outcome["fatal"] is None:
                        outcome["fatal"] = error
                        stop.set()
                    if writer:
                        writer.write(finished)
                    continue
                if result is None:
                    stats["not_sent"] += len(request.entries)
                    continue
                finished = collect(request, result)
                if writer:
                    writer.write(finished)
        stats["not_sent"] += sum(len(request.entries) for request in pending)
    finally:
        pool.shutdown(wait=True)
        if writer:
            writer.close()
        if cache:
            cache.close()

    if out_path:
        final = dict(existing)
        final.update(rows)
        input_keys = [item.id_key for item in items if item.id_key in final]
        input_key_set = set(input_keys)
        extra_keys = [key for key in existing_order if key not in input_key_set]
        compact_out_file(out_path, final, input_keys + extra_keys)

    error_count = sum(1 for item in items if "error" in rows.get(item.id_key, {}))
    if outcome["fatal"] is not None:
        outcome["exit_code"] = outcome["fatal"].exit_code
    elif error_count or stats["not_sent"]:
        outcome["exit_code"] = 5
    return outcome


def print_summary(outcome, template, items):
    """Batch totals, cost, latency and band counts on stderr."""
    stats, rows = outcome["stats"], outcome["rows"]
    answered = [rows[item.id_key] for item in items if "answers" in rows.get(item.id_key, {})]
    errors = sum(1 for item in items if "error" in rows.get(item.id_key, {}))
    not_sent = f"  not sent {stats['not_sent']}" if stats["not_sent"] else ""
    note(f"# items {stats['items']}  done {len(answered)}  cached {stats['cached']}  "
         f"resumed {stats['resumed']}  errors {errors}{not_sent}")
    total_cost = stats["cost_reported"] + stats["cost_estimated"]
    if outcome["mock"]:
        cost_text = f"cost $0 (mock; ~${total_cost:.6f} at list price)"
    else:
        cost_text = (f"cost ${total_cost:.6f} (reported ${stats['cost_reported']:.6f} + "
                     f"estimated ${stats['cost_estimated']:.6f})")
    note(f"# requests {stats['requests']}  input_tokens {stats['input_tokens']}  {cost_text}")
    if stats["latencies"]:
        note(f"# latency p50 {percentile(stats['latencies'], 0.5)} ms  "
             f"p95 {percentile(stats['latencies'], 0.95)} ms")
    for question_id, question in template["questions"].items():
        counts = collections.Counter(
            band_for(row["answers"][question_id]) for row in answered if question_id in row["answers"])
        bands = "  ".join(f"{band} {counts.get(band, 0)}" for band in BAND_ORDER[question["type"]])
        note(f"# {question_id} ({question['type']}): {bands}")
    if any(question["type"] == "score" for question in template["questions"].values()):
        note(SCORE_NOTE)
    fatal = outcome["fatal"]
    if fatal is not None:
        hint = "rerun with the same --out to resume" if outcome["out_path"] else "rerun to retry"
        print(f"jev: error: {fatal.message} (stopped early; {hint})", file=sys.stderr)


def add_engine_flags(parser, default_pack):
    """Packing and concurrency flags for commands that run the batch engine."""
    parser.add_argument("--pack", choices=("keyed", "inline"), default=default_pack,
                        help=f"keyed: items sit in state under generated keys (k00001...); inline: "
                             f"each question carries its own item (default {default_pack})")
    parser.add_argument("--fields", help="comma-separated item fields to send (default: the whole "
                                         "item minus id, and minus expect for eval)")
    parser.add_argument("--per-request", type=int, default=DEFAULT_PER_REQUEST, metavar="N",
                        help=f"max items per request (default {DEFAULT_PER_REQUEST}); requests also "
                             f"stay under 80%% of the provider's token limits")
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS, metavar="N",
                        help=f"parallel requests (default {DEFAULT_WORKERS})")


def check_engine_args(args):
    """Validate shared engine flags."""
    if args.per_request < 1:
        raise InputError("--per-request must be at least 1")
    if args.workers < 1:
        raise InputError("--workers must be at least 1")


# ---------------------------------------------------------------- batch

BATCH_EPILOG = """\
template.json:
  {"context": {...optional, shared by every request...},
   "questions": {"is_crash": {"type": "noul",
                              "instructions": "Does `item.text` report an app crash?"}}}
  Refer to the current item as `item` (e.g. `item.text`) and shared data as `context`.

items: a .json array or JSONL. JSONL lines that aren't JSON become {"text": line}.
  id = item["id"] if present (must be unique), else the 0-based line index.

rows (stdout, or --out): {"id": ..., "answers": {"<qid>": answer}, "model": ..., "cached": false}
                         {"id": ..., "error": "..."}
exit codes: 0 all answered, 5 some error rows, 2 bad input or lint error or 404, 3 auth/credit
"""


def build_batch_parser():
    """Parser for `jev.py batch`."""
    parser = argparse.ArgumentParser(
        prog="jev.py batch", description="Judge many items with one question template.",
        epilog=BATCH_EPILOG, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--items", required=True, metavar="F",
                        help="items: JSON array or JSONL file, '-' for stdin")
    parser.add_argument("--template", required=True, metavar="F",
                        help="template JSON with optional context and questions")
    parser.add_argument("--out", metavar="F",
                        help="append rows here as requests finish; a rerun skips answered ids and "
                             "retries errors; compacted at the end (default: JSONL on stdout). Reworded a "
                             "question? Use a new --out: resume matches ids and question ids, not wording")
    add_engine_flags(parser, "keyed")
    add_common_flags(parser, with_cache=True)
    return parser


def run_batch(argv):
    """`jev.py batch`."""
    args = build_batch_parser().parse_args(argv)
    try:
        resolve_provider(args)
        check_engine_args(args)
        if args.items == "-" and args.template == "-":
            raise InputError("--items and --template can't both read stdin")
        template = load_template(args.template)
        items = load_items(args.items, parse_fields(args.fields))
        outcome = run_batch_engine(args, template, items, "batch", out_path=args.out)
    except InputError as error:
        fail(str(error), 2)
    except ApiError as error:
        fail(error.message, error.exit_code)
    if outcome["dry_run"]:
        return 0
    if not args.out:
        for item in items:
            row = outcome["rows"].get(item.id_key)
            if row is not None:
                print(json.dumps(row, ensure_ascii=False))
    print_summary(outcome, template, items)
    return outcome["exit_code"]


# ---------------------------------------------------------------- rank

def item_preview(payload, width=80):
    """First characters of an item's text, or its compact JSON."""
    if isinstance(payload, dict) and isinstance(payload.get("text"), str):
        text = payload["text"]
    else:
        text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return " ".join(text.split())[:width]


def build_rank_parser():
    """Parser for `jev.py rank`."""
    parser = argparse.ArgumentParser(
        prog="jev.py rank", description="Sort items by the probability that one yes/no question holds.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="The question runs once per item as a noul. With the default --pack inline it can say\n"
               "\"this item\" or reference `item.text`.\n"
               "exit codes: 0 all answered, 5 some error rows, 2 bad input or lint error, 3 auth/credit")
    parser.add_argument("--items", required=True, metavar="F",
                        help="items: JSON array or JSONL file, '-' for stdin")
    parser.add_argument("--question", required=True, metavar="TEXT", help="the yes/no question")
    parser.add_argument("--true", dest="true_description", metavar="DESC",
                        help="what counts as yes (noul criteria.true)")
    parser.add_argument("--false", dest="false_description", metavar="DESC",
                        help="what counts as no (noul criteria.false)")
    parser.add_argument("--context", metavar="@F|JSON",
                        help="shared data every request sees as `context`: JSON, text, @path or '-'")
    parser.add_argument("--top", type=int, default=20, metavar="N", help="rows to print (default 20)")
    parser.add_argument("--min", type=float, metavar="P", help="keep only items with p >= P")
    parser.add_argument("--out", metavar="F",
                        help="write every ranked row {id, p, band} as JSONL, best first")
    add_engine_flags(parser, "inline")
    add_common_flags(parser, with_cache=True)
    return parser


def run_rank(argv):
    """`jev.py rank`."""
    args = build_rank_parser().parse_args(argv)
    try:
        resolve_provider(args)
        check_engine_args(args)
        if args.top < 1:
            raise InputError("--top must be at least 1")
        if args.min is not None and not 0.0 <= args.min <= 1.0:
            raise InputError("--min must be between 0 and 1")
        question = {"type": "noul", "instructions": args.question}
        criteria = {}
        if args.true_description:
            criteria["true"] = args.true_description
        if args.false_description:
            criteria["false"] = args.false_description
        if criteria:
            question["criteria"] = criteria
        template = {"questions": {"match": question}}
        if args.context is not None:
            template["context"] = parse_json_or_text(read_text_arg(args.context))
        items = load_items(args.items, parse_fields(args.fields))
        outcome = run_batch_engine(args, template, items, "rank")
    except InputError as error:
        fail(str(error), 2)
    except ApiError as error:
        fail(error.message, error.exit_code)
    if outcome["dry_run"]:
        return 0

    ranked, errors = [], []
    for item in items:
        row = outcome["rows"].get(item.id_key)
        if row is None:
            continue
        if "answers" in row:
            answer = row["answers"]["match"]
            ranked.append((float(answer.get("noul", 0.0)), band_for(answer), item))
        else:
            errors.append(row)
    ranked.sort(key=lambda entry: entry[0], reverse=True)
    if args.min is not None:
        ranked = [entry for entry in ranked if entry[0] >= args.min]

    shown = ranked[:args.top]
    if len(ranked) > args.top and ranked[args.top - 1][0] == ranked[args.top][0]:
        tied = sum(1 for entry in ranked if entry[0] == ranked[args.top][0])
        warn(f"--top {args.top} cuts through a tie: {tied} items share p={ranked[args.top][0]:.2f} "
             "(answers are rounded); the cut among them is arbitrary. Widen --top or break the tie "
             "with a second question")
    id_width = min(24, max([len(str(entry[2].id)) for entry in shown] + [2]))
    print(f"{'rank':>4}  {'p':<4}  {'band':<9}  {'id':<{id_width}}  preview")
    for position, (p, band, item) in enumerate(shown, 1):
        print(f"{position:>4}  {p:.2f}  {band:<9}  {str(item.id)[:id_width]:<{id_width}}  "
              f"{item_preview(item.payload)}")
    if errors:
        print("\nerrors:")
        for row in errors:
            print(f"  {row['id']}  {row['error']}")
        warn(f"{len(errors)} item(s) have no answer (listed after the table)")
    if args.out:
        try:
            with open(args.out, "w", encoding="utf-8") as handle:
                for p, band, item in ranked:
                    handle.write(json.dumps({"id": item.id, "p": p, "band": band}, ensure_ascii=False) + "\n")
        except OSError as error:
            fail(f"cannot write {args.out}: {error}", 2)
    print_summary(outcome, template, items)
    return outcome["exit_code"]


# ---------------------------------------------------------------- eval

def normalize_expected(question_id, question, value):
    """Turn a label into a bool (noul), option key (choice) or level index (score)."""
    question_type = question["type"]
    if question_type == "noul":
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)) and value in (0, 1):
            return bool(value)
        if isinstance(value, str) and value.strip().lower() in ("yes", "true", "y", "1"):
            return True
        if isinstance(value, str) and value.strip().lower() in ("no", "false", "n", "0"):
            return False
        raise InputError(f"expect for noul '{question_id}' must be true/false, yes/no or 1/0, got {value!r}")
    if question_type == "choice":
        if isinstance(value, str) and value in question["criteria"]:
            return value
        raise InputError(f"expect for choice '{question_id}' must be one of "
                         f"{', '.join(map(str, question['criteria']))}; got {value!r}")
    levels = question["criteria"]
    if isinstance(value, int) and not isinstance(value, bool) and 0 <= value < len(levels):
        return value
    if isinstance(value, str):
        for index, level in enumerate(levels):
            if level == value:
                return index
        if value.strip().isdigit() and int(value) < len(levels):
            return int(value)
    raise InputError(f"expect for score '{question_id}' must be a level index 0-{len(levels) - 1} "
                     f"or the exact level text; got {value!r}")


def read_expectations(items, template):
    """Normalized labels per item: {id_key: {qid: value}}."""
    questions = template["questions"]
    labels, unknown = {}, set()
    for item in items:
        if item.expect is None:
            continue
        if not isinstance(item.expect, dict):
            raise InputError(f"case {item.id!r}: expect must be an object keyed by question id")
        normalized = {}
        for question_id, value in item.expect.items():
            if question_id not in questions:
                unknown.add(question_id)
                continue
            normalized[question_id] = normalize_expected(question_id, questions[question_id], value)
        labels[item.id_key] = normalized
    if unknown:
        warn(f"expect keys not in the template are ignored: {', '.join(sorted(unknown))}")
    if not labels:
        raise InputError("no case has an \"expect\" object; nothing to evaluate")
    return labels


def mean(values):
    """Average, or None for no values."""
    return sum(values) / len(values) if values else None


def bucket_label(edges, index):
    """'[lo,hi)' label, closed on the last bucket."""
    closing = "]" if index == len(edges) - 2 else ")"
    return f"[{edges[index]:.1f},{edges[index + 1]:.1f}{closing}"


def bucket_index(value, edges):
    """Bucket of value for the given edges."""
    for index in range(len(edges) - 1):
        if value < edges[index + 1]:
            return index
    return len(edges) - 2


def group_by_bucket(pairs, edges):
    """Group (value, record) pairs into buckets."""
    groups = [[] for _ in range(len(edges) - 1)]
    for value, record in pairs:
        groups[bucket_index(value, edges)].append((value, record))
    return groups


def confidence_tracks_accuracy(pairs):
    """False when the more confident half is not more accurate; None when too few cases."""
    if len(pairs) < MIN_CASES_FOR_TRACKING:
        return None
    ordered = sorted(pairs, key=lambda pair: pair[0])
    if ordered[0][0] == ordered[-1][0]:
        return None
    half = len(ordered) // 2
    low = mean([1.0 if correct else 0.0 for _signal, correct in ordered[:half]])
    high = mean([1.0 if correct else 0.0 for _signal, correct in ordered[-half:]])
    return high > low or (high == low == 1.0)


def noul_metrics(cases, target):
    """Accuracy, calibration, bands and suggested thresholds for a noul."""
    n = len(cases)
    calibration = []
    for index, group in enumerate(group_by_bucket(cases, CALIBRATION_EDGES)):
        calibration.append({"bucket": bucket_label(CALIBRATION_EDGES, index), "n": len(group),
                            "mean_p": mean([p for p, _label in group]),
                            "yes_rate": mean([1.0 if label else 0.0 for _p, label in group])})
    yes_band = [label for p, label in cases if p >= NOUL_YES]
    no_band = [not label for p, label in cases if p <= NOUL_NO]

    def first_threshold(thresholds, select):
        """First threshold whose selected cases reach the target."""
        for threshold in thresholds:
            chosen = [correct for _p, correct in select(threshold)]
            if chosen and mean([1.0 if correct else 0.0 for correct in chosen]) >= target:
                return {"threshold": threshold, "precision": mean([1.0 if c else 0.0 for c in chosen]),
                        "coverage": len(chosen) / n}
        return None

    return {
        "type": "noul", "n": n,
        "accuracy": mean([1.0 if (p >= 0.5) == label else 0.0 for p, label in cases]),
        "calibration": calibration,
        "bands": {"YES": {"n": len(yes_band), "precision": mean([1.0 if c else 0.0 for c in yes_band])},
                  "NO": {"n": len(no_band), "precision": mean([1.0 if c else 0.0 for c in no_band])},
                  "UNCERTAIN": {"n": n - len(yes_band) - len(no_band)}},
        "suggested": {
            "yes": first_threshold(NOUL_YES_THRESHOLDS,
                                   lambda t: [(p, label) for p, label in cases if p >= t]),
            "no": first_threshold(NOUL_NO_THRESHOLDS,
                                  lambda t: [(p, not label) for p, label in cases if p <= t]),
        },
        "confidence_tracks_accuracy": confidence_tracks_accuracy(
            [(abs(p - 0.5), (p >= 0.5) == label) for p, label in cases]),
    }


def choice_metrics(cases, target):
    """Accuracy by p_max bucket and band, plus a suggested p_max threshold."""
    n = len(cases)
    pairs = [(choice_top_probability(answer), answer.get("choice") == expected) for answer, expected in cases]
    by_bucket = [{"bucket": bucket_label(CHOICE_EDGES, index), "n": len(group),
                  "accuracy": mean([1.0 if correct else 0.0 for _p, correct in group])}
                 for index, group in enumerate(group_by_bucket(pairs, CHOICE_EDGES))]
    bands = {}
    for band in BAND_ORDER["choice"]:
        members = [correct for p, correct in pairs if choice_band(p) == band]
        bands[band] = {"n": len(members), "accuracy": mean([1.0 if c else 0.0 for c in members])}
    suggested = None
    for threshold in CHOICE_THRESHOLDS:
        chosen = [correct for p, correct in pairs if p >= threshold]
        accuracy = mean([1.0 if c else 0.0 for c in chosen])
        if chosen and accuracy >= target:
            suggested = {"threshold": threshold, "accuracy": accuracy, "coverage": len(chosen) / n}
            break
    return {"type": "choice", "n": n, "accuracy": mean([1.0 if c else 0.0 for _p, c in pairs]),
            "by_p_max": by_bucket, "bands": bands, "suggested": suggested,
            "confidence_tracks_accuracy": confidence_tracks_accuracy(pairs)}


def score_metrics(cases):
    """Exact and within-one accuracy, MAE, and accuracy by confidence bucket."""
    records = []
    for answer, expected in cases:
        score = float(answer.get("score", 0.0))
        records.append((float(answer.get("confidence", 0.0)), nearest_level(score) == expected,
                        abs(nearest_level(score) - expected) <= 1, abs(score - expected)))
    by_bucket = [{"bucket": bucket_label(CALIBRATION_EDGES, index), "n": len(group),
                  "exact_accuracy": mean([1.0 if record[1] else 0.0 for _c, record in group])}
                 for index, group in enumerate(group_by_bucket([(r[0], r) for r in records],
                                                               CALIBRATION_EDGES))]
    return {"type": "score", "n": len(records),
            "exact_accuracy": mean([1.0 if r[1] else 0.0 for r in records]),
            "within_one_accuracy": mean([1.0 if r[2] else 0.0 for r in records]),
            "mae": mean([r[3] for r in records]),
            "by_confidence": by_bucket,
            "confidence_tracks_accuracy": confidence_tracks_accuracy([(r[0], r[1]) for r in records])}


def eval_metrics(items, labels, rows, template, target):
    """Per-question metrics for an eval run."""
    metrics = {}
    for question_id, question in template["questions"].items():
        cases = []
        for item in items:
            expected = labels.get(item.id_key, {}).get(question_id)
            row = rows.get(item.id_key) or {}
            answer = (row.get("answers") or {}).get(question_id)
            if expected is None or answer is None:
                continue
            if question["type"] == "noul":
                cases.append((float(answer.get("noul", 0.5)), expected))
            else:
                cases.append((answer, expected))
        if not cases:
            metrics[question_id] = {"type": question["type"], "n": 0}
        elif question["type"] == "noul":
            metrics[question_id] = noul_metrics(cases, target)
        elif question["type"] == "choice":
            metrics[question_id] = choice_metrics(cases, target)
        else:
            metrics[question_id] = score_metrics(cases)
    return metrics


def round_floats(value, digits=4):
    """Round every float inside a JSON value."""
    if isinstance(value, float):
        return round(value, digits)
    if isinstance(value, dict):
        return {key: round_floats(child, digits) for key, child in value.items()}
    if isinstance(value, list):
        return [round_floats(child, digits) for child in value]
    return value


def fmt(value, digits=2):
    """Number or '-' for None."""
    return "-" if value is None else f"{value:.{digits}f}"


def print_eval_report(report):
    """Human-readable eval tables on stdout."""
    print(f"cases {report['cases']}  answered {report['answered']}  errors {report['errors']}  "
          f"target {report['target']:.2f}")
    for question_id, m in report["questions"].items():
        print(f"\n== {question_id} ({m['type']})  n={m['n']}")
        if not m["n"]:
            print("  no labeled answers")
            continue
        if m["type"] == "noul":
            print(f"  accuracy at 0.5: {fmt(m['accuracy'])}")
            print(f"  {'p bucket':<11} {'n':>5}  {'mean p':>6}  {'yes rate':>8}")
            for row in m["calibration"]:
                print(f"  {row['bucket']:<11} {row['n']:>5}  {fmt(row['mean_p']):>6}  "
                      f"{fmt(row['yes_rate']):>8}")
            bands = m["bands"]
            print(f"  bands: YES n={bands['YES']['n']} precision={fmt(bands['YES']['precision'])}  "
                  f"NO n={bands['NO']['n']} precision={fmt(bands['NO']['precision'])}  "
                  f"UNCERTAIN {bands['UNCERTAIN']['n']}")
            for side, sign in (("yes", ">="), ("no", "<=")):
                s = m["suggested"][side]
                if s:
                    print(f"  suggested {side}: p {sign} {s['threshold']:.2f} "
                          f"(precision {fmt(s['precision'])}, "
                          f"coverage {fmt(s['coverage'])})")
                else:
                    print(f"  suggested {side}: no threshold reaches the target")
        elif m["type"] == "choice":
            print(f"  accuracy: {fmt(m['accuracy'])}")
            print(f"  {'p_max bucket':<12} {'n':>5}  {'accuracy':>8}")
            for row in m["by_p_max"]:
                print(f"  {row['bucket']:<12} {row['n']:>5}  {fmt(row['accuracy']):>8}")
            print("  bands: " + "  ".join(f"{band} n={v['n']} accuracy={fmt(v['accuracy'])}"
                                          for band, v in m["bands"].items()))
            s = m["suggested"]
            if s:
                print(f"  suggested: act when p_max >= {s['threshold']:.2f} (accuracy {fmt(s['accuracy'])}, "
                      f"coverage {fmt(s['coverage'])})")
            else:
                print("  suggested: no p_max threshold reaches the target")
        else:
            print(f"  exact accuracy {fmt(m['exact_accuracy'])}  within one level "
                  f"{fmt(m['within_one_accuracy'])}  MAE {fmt(m['mae'])}")
            print(f"  {'conf bucket':<11} {'n':>5}  {'exact':>6}")
            for row in m["by_confidence"]:
                print(f"  {row['bucket']:<11} {row['n']:>5}  {fmt(row['exact_accuracy']):>6}")


def build_eval_parser():
    """Parser for `jev.py eval`."""
    parser = argparse.ArgumentParser(
        prog="jev.py eval", description="Measure accuracy and calibration of a template on labeled cases.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="cases: same format as batch items, each with \"expect\": {\"<qid>\": value} (never sent).\n"
               "  noul: true/false (also yes/no, 1/0); choice: an option key; score: a 0-based level\n"
               "  index or the exact level text. Cases without a label for a question are skipped.\n"
               "exit codes: 0 all answered, 5 some error rows, 2 bad input or lint error, 3 auth/credit")
    parser.add_argument("--cases", required=True, metavar="F",
                        help="labeled cases: JSON array or JSONL file, '-' for stdin")
    parser.add_argument("--template", required=True, metavar="F", help="template JSON, as for batch")
    parser.add_argument("--target", type=float, default=EVAL_TARGET, metavar="P",
                        help=f"precision/accuracy a suggested threshold must reach (default {EVAL_TARGET})")
    parser.add_argument("--json", action="store_true", help="print metrics as JSON instead of tables")
    add_engine_flags(parser, "keyed")
    add_common_flags(parser, with_cache=True)
    return parser


def run_eval(argv):
    """`jev.py eval`."""
    args = build_eval_parser().parse_args(argv)
    try:
        resolve_provider(args)
        check_engine_args(args)
        if not 0.0 < args.target <= 1.0:
            raise InputError("--target must be in (0, 1]")
        if args.cases == "-" and args.template == "-":
            raise InputError("--cases and --template can't both read stdin")
        template = load_template(args.template)
        items = load_items(args.cases, parse_fields(args.fields), is_cases=True)
        labels = read_expectations(items, template)
        outcome = run_batch_engine(args, template, items, "eval")
    except InputError as error:
        fail(str(error), 2)
    except ApiError as error:
        fail(error.message, error.exit_code)
    if outcome["dry_run"]:
        return 0
    rows = outcome["rows"]
    report = {
        "cases": len(items),
        "answered": sum(1 for item in items if "answers" in rows.get(item.id_key, {})),
        "errors": sum(1 for item in items if "error" in rows.get(item.id_key, {})),
        "target": args.target,
        "questions": eval_metrics(items, labels, rows, template, args.target),
    }
    if args.json:
        print(json.dumps(round_floats(report), indent=2, ensure_ascii=False))
    else:
        print_eval_report(report)
    for question_id, m in report["questions"].items():
        if m.get("confidence_tracks_accuracy") is False:
            warn(f"'{question_id}': confidence is not tracking accuracy here; rewrite the question "
                 f"before trusting thresholds")
    print_summary(outcome, template, items)
    return outcome["exit_code"]


# ---------------------------------------------------------------- doctor

def fetch_openrouter_credit(api_key):
    """'usage $x, limit remaining $y' for an OpenRouter key, or None."""
    request = urllib.request.Request(OPENROUTER_KEY_INFO_URL, headers={
        "Authorization": f"Bearer {api_key}", "Accept": "application/json", "User-Agent": USER_AGENT})
    try:
        with http_open(request, timeout=10) as response:
            if response.status != 200:
                return None
            data = json.loads(read_capped(response).decode("utf-8")).get("data") or {}
        usage, remaining = data.get("usage"), data.get("limit_remaining")
    except (OSError, ValueError, AttributeError, http.client.HTTPException, ApiError):
        return None

    def money(value):
        """Dollar amount, or the raw value when it is not a number."""
        return f"${value:.4f}" if isinstance(value, (int, float)) else str(value)

    return f"usage {money(usage)}, limit remaining {'no limit' if remaining is None else money(remaining)}"


def build_doctor_parser():
    """Parser for `jev.py doctor`."""
    parser = argparse.ArgumentParser(
        prog="jev.py doctor",
        description="Check provider, key, credit, endpoint and model with one tiny call.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="exit codes: 0 ok, 3 auth/credit, 4 network/API, 2 404 or bad model slug")
    parser.add_argument("--provider", choices=sorted(PROVIDERS),
                        help="API route: openrouter (default) or typesafe; env JEV_PROVIDER")
    parser.add_argument("--model", help="model id to test (default as for other commands)")
    parser.add_argument("--mock", action="store_true", help="run the checks offline with a fake answer")
    return parser


def run_doctor(argv):
    """`jev.py doctor`."""
    args = build_doctor_parser().parse_args(argv)
    try:
        provider = resolve_provider(args)
    except InputError as error:
        fail(str(error), 2)
    api_key = os.environ.get(provider["key_env"])
    ledger_note = " (disabled by JEV_NO_LEDGER)" if ledger_disabled() else ""
    print(f"provider  {args.provider}")
    print(f"endpoint  {provider['url']}")
    print(f"model     {args.model}")
    print(f"key       {provider['key_env']} set: {'yes' if api_key else 'no'}")
    print(f"ledger    {ledger_path()}{ledger_note}")
    print(f"cache     {cache_path()}")
    sys.stdout.flush()
    if not args.mock and not api_key:
        print(f"jev: error: {provider['key_env']} is not set (get one at {provider['key_help']})",
              file=sys.stderr)
        return 3
    if args.mock:
        print("credit    skipped (--mock)")
    elif args.provider == "openrouter":
        print(f"credit    {fetch_openrouter_credit(api_key) or 'credit info unavailable'}")
    else:
        print("credit    no balance endpoint on this provider")

    body = {"state": "The sky is blue.", "model": args.model,
            "questions": {"sky": {"type": "noul", "instructions": "Does the text say the sky is blue?"}}}
    if args.mock:
        started = time.monotonic()
        response, status, latency = mock_response(body), 200, elapsed_ms(started)
    else:
        try:
            response, status, latency = post_with_retries(
                provider["url"], body, build_headers(args.provider, api_key), provider["key_env"],
                ledger_recorder("doctor", args, 1, None))
        except ApiError as error:
            print(f"call      failed: {error.message}")
            return error.exit_code
    answer = (response.get("answers") or {}).get("sky") or {}
    cost, cost_source, input_tokens = cost_from_response(response)
    print(f"call      HTTP {status}, {latency} ms, model {response.get('model')}, "
          f"noul {answer.get('noul')}, input_tokens {input_tokens}, {format_cost(cost, cost_source)}")
    if not isinstance(answer.get("noul"), (int, float)):
        sys.stdout.flush()
        print("jev: error: the response has no noul answer", file=sys.stderr)
        return 4
    print("ok")
    return 0


# ---------------------------------------------------------------- usage

def build_usage_parser():
    """Parser for `jev.py usage`."""
    parser = argparse.ArgumentParser(
        prog="jev.py usage", description="Totals from the local usage ledger ($JEV_LEDGER or "
                                         "~/.config/jev/usage.jsonl).")
    parser.add_argument("--since", metavar="YYYY-MM-DD", help="only calls on or after this UTC date")
    parser.add_argument("--label", metavar="L", help="only calls made with --label L")
    parser.add_argument("--by", choices=("day", "label", "model"), default="day",
                        help="group rows by day (default), label or model")
    return parser


def run_usage(argv):
    """`jev.py usage`."""
    args = build_usage_parser().parse_args(argv)
    if args.since:
        try:
            datetime.datetime.strptime(args.since, "%Y-%m-%d")
        except ValueError:
            fail("--since must look like YYYY-MM-DD", 2)
    path = ledger_path()
    if not os.path.exists(path):
        print(f"no usage recorded yet (ledger: {path})")
        return 0
    groups = collections.OrderedDict()
    try:
        with open(path, "r", encoding="utf-8") as handle:
            lines = handle.readlines()
    except OSError as error:
        fail(f"cannot read {path}: {error}", 2)
    for line in lines:
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if not isinstance(row, dict):
            continue
        day = str(row.get("ts", ""))[:10]
        if args.since and day < args.since:
            continue
        if args.label is not None and row.get("label") != args.label:
            continue
        key = {"day": day, "label": row.get("label"), "model": row.get("model")}[args.by]
        key = "(none)" if key in (None, "") else str(key)
        group = groups.setdefault(
            key, {"calls": 0, "errors": 0, "input_tokens": 0, "cost": 0.0, "estimated": 0.0})
        group["calls"] += 1
        group["errors"] += 0 if row.get("status") == "ok" else 1
        group["input_tokens"] += int(row.get("input_tokens") or 0)
        cost = float(row.get("cost_usd") or 0.0)
        group["cost"] += cost
        if row.get("cost_source") == "estimated":
            group["estimated"] += cost
    if not groups:
        print(f"no matching calls in {path}")
        return 0
    width = max(12, max(len(key) for key in groups) + 2)
    print(f"{args.by:<{width}}{'calls':>7}{'errors':>8}{'input_tokens':>14}{'cost':>13}")
    total = {"calls": 0, "errors": 0, "input_tokens": 0, "cost": 0.0, "estimated": 0.0}
    for key in sorted(groups):
        group = groups[key]
        for field in total:
            total[field] += group[field]
        print(f"{key:<{width}}{group['calls']:>7}{group['errors']:>8}{group['input_tokens']:>14,}"
              f"{'$' + format(group['cost'], '.6f'):>13}")
    print(f"{'total':<{width}}{total['calls']:>7}{total['errors']:>8}{total['input_tokens']:>14,}"
          f"{'$' + format(total['cost'], '.6f'):>13}")
    if total["estimated"]:
        print(f"(${total['estimated']:.6f} of the cost is estimated from the list price)")
    return 0


# ---------------------------------------------------------------- main

def main(argv=None):
    """Dispatch to a subcommand, or run a single request."""
    argv = sys.argv[1:] if argv is None else argv
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    handlers = {"batch": run_batch, "rank": run_rank, "eval": run_eval,
                "doctor": run_doctor, "usage": run_usage}
    try:
        if argv and argv[0] in SUBCOMMANDS:
            return handlers[argv[0]](argv[1:])
        return run_ask(argv)
    except KeyboardInterrupt:
        print("jev: interrupted (rerun batch with the same --out to resume)", file=sys.stderr)
        return 130
    except BrokenPipeError:
        sys.stdout = open(os.devnull, "w")
        return 0


if __name__ == "__main__":
    sys.exit(main())
