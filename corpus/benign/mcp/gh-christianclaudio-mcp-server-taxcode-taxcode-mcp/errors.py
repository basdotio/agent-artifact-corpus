"""Error structures and automated credential redaction."""

import json
import re
from typing import Any

from fastmcp.exceptions import ToolError

# Credential keys whose whole value is a secret.
_KEYS = r"(?:api[_-]?key|client[_-]?secret|private[_-]?key|password)"
# Credential keys whose bracketed or bare (number, ``None``, ``True``) value is masked whole,
# whether the key is quoted or not: ``_KEYS`` plus the token names the token rules cover. The
# lookbehind keeps ``next_token``, ``page_token`` and ``max_tokens`` untouched.
_VALUE_KEYS = (
    r"(?:" + _KEYS + r"|(?:api|access|refresh|auth|id|session)[_-]?token|(?<![A-Za-z0-9_])token)"
)
# A closing quote after a key (``'api_key':``, ``"password":``, ``\"token\":``).
_KEY_CLOSE = r"(?:\\?[\"'])?"
# The fixed mask: the same string whatever the secret's length (template #67).
MASK = "[REDACTED]"

# The value of an escaped quote one level down (``\"...\"`` inside a serialized string).
_ESCAPED_VALUE = r"(?:\\\\\\\"|\\\\\\\\|\\\\[^\\\"]|[^\\\"])*"


def _token_patterns(
    key: str, sep: str, unquoted_stop: str | None = r"\s\"'\\&,;}"
) -> list[re.Pattern[str]]:
    """Escaped-quoted, quoted and (unless ``unquoted_stop`` is None) unquoted forms of a key.

    A quoted value is masked to its closing unescaped quote, spaces and escapes included;
    the quotes stay. An unquoted value stops at whitespace or ``unquoted_stop`` punctuation.
    """
    head = r"(?i)(" + key + r"\s*" + sep + r"\s*"
    patterns = [
        re.compile(head + r"\\\")" + _ESCAPED_VALUE, re.IGNORECASE),
        re.compile(head + r"([\"']))(?:\\.|(?!\2)[^\\\n])*", re.IGNORECASE),
    ]
    if unquoted_stop is not None:
        patterns.append(
            re.compile(head + r")(?![\"'\\]|\[REDACTED\])[^" + unquoted_stop + "]+", re.IGNORECASE)
        )
    return patterns


# Regex patterns for sensitive tokens, bearer headers, and keys. Every match is replaced by
# ``MASK``. A secret is redacted whole; no part of it is left behind.
SECRET_PATTERNS = [
    # A PEM block, from ``-----BEGIN ...-----`` to ``-----END ...-----``, across lines or
    # with ``\n`` escapes inside a serialized JSON string. A BEGIN with no END is masked to
    # the end of the text (fail closed), which also keeps the scan linear: a lazy search for
    # an END that never comes re-read the rest of the text from every BEGIN. The END must
    # carry the BEGIN's label (any case): a ``-----END CERTIFICATE-----`` inside a PRIVATE
    # KEY block does not end it.
    re.compile(
        r"()-----BEGIN ([A-Z0-9 ]+)-----(?:(?!-----END \2-----).)*"
        r"(?:-----END \2-----|\Z)",
        re.DOTALL | re.IGNORECASE,
    ),
    # Bearer value: base64url and base64 characters (``~``, ``+``, ``/``) plus ``=`` padding.
    re.compile(r"(?i)(bearer\s+)[a-z0-9_\-\.~+/]{8,}=*", re.IGNORECASE),
    # ``Authorization: Bearer <value>`` of any length. A bare short ``Bearer abc`` is left
    # alone so prose such as "Bearer of bad news" is not redacted.
    re.compile(
        r"(?i)(authorization(?:\\?[\"'])?\s*[:=]\s*(?:\\?[\"'])?bearer\s+)[a-z0-9_\-\.~+/]+=*",
        re.IGNORECASE,
    ),
    # Quoted value (``"password": "..."``, ``{'api_key': '...'}``, ``password="..."``): the
    # whole string up to its closing unescaped quote, escapes included; the quotes stay.
    re.compile(
        r"(?i)([\"']?" + _KEYS + r"[\"']?\s*[:=]\s*([\"']))(?:\\.|(?!\2)[^\\\n])*",
        re.IGNORECASE,
    ),
    # Quoted key with a bare value: a Python ``repr`` or JSON number, ``None``, ``True`` or
    # word (``{'password': 12345}``). The value stops at whitespace, ``,`` or a closing
    # bracket, so the rest of the dict keeps its shape. ``None``/``null`` stays, as in
    # ``redact_payload``. Quoted and bracketed values have their own rules.
    re.compile(
        r"(?i)(\\?[\"']" + _VALUE_KEYS + r"\\?[\"']\s*[:=]\s*)"
        r"(?![\"'\\\[{]|\[REDACTED\]|(?:null|None)(?![^\s,}\])]))[^\s,}\])]+",
        re.IGNORECASE,
    ),
    # The same inside an already-serialized JSON string (``\"password\": \"...\"``, template
    # #68): the value ends at the escaped quote that closed it one level down.
    re.compile(
        r"(?i)(\\\"" + _KEYS + r"\\\"\s*:\s*\\\")"
        r"(?:\\\\\\\"|\\\\\\\\|\\\\[^\\\"]|[^\\\"])*",
        re.IGNORECASE,
    ),
    # Unquoted ``key=value`` or ``key: value`` of any length: the value runs to the end of
    # the line, spaces and punctuation included, so ``password=pass word`` leaves nothing
    # behind (template #69). A ``{...}`` / ``[...]`` value is masked first, to its balanced
    # bracket (``_mask_bracket_values``). Structured payloads are redacted value by value
    # before serialization (``redact_payload``), so this never runs on JSON that parses.
    re.compile(
        r"(?i)(" + _KEYS + r"[ \t]*[:=][ \t]*)(?![\"'\\]|\[REDACTED\])[^\s][^\n]*",
        re.IGNORECASE,
    ),
    # Whitespace-separated older forms keep a minimum, so prose stays untouched.
    re.compile(r"(?i)(password\s+)(?!\[REDACTED\])[^\s\"']\S{3,}", re.IGNORECASE),
    re.compile(
        r"(?i)((?:api[_-]?key|client[_-]?secret)\s+)(?!\[REDACTED\])[a-z0-9_\-\.]{8,}",
        re.IGNORECASE,
    ),
    # api/access/refresh/auth/id/session tokens as key=value, key: value, an
    # ``X-Auth-Token:`` header and JSON ("key": "value", also backslash-escaped inside an
    # already-serialized JSON string). A quoted value runs to its closing unescaped quote,
    # spaces included (template #69); an unquoted one stops at whitespace or punctuation.
    *_token_patterns(r"(?:api|access|refresh|auth|id|session)[_-]?token(?:\\?[\"'])?", "[:=]"),
    # The same keys URL-encoded (``access_token%3D...``); the value stops at an encoded
    # ``%26`` (&) or ``%23`` (#), so the parameters after it survive.
    re.compile(
        r"(?i)((?:api|access|refresh|auth|id|session)[_-]?token%3D)"
        r"(?:[^\s\"'\\&,;#%]|%(?!26|23))+",
        re.IGNORECASE,
    ),
    # ``Authorization: Token <value>`` scheme, also as a quoted JSON or dict entry.
    re.compile(
        r"(?i)(authorization(?:\\?[\"'])?\s*[:=]\s*(?:\\?[\"'])?token\s+)[^\s\"'\\&,;}]+",
        re.IGNORECASE,
    ),
    # JSON ``"token": "value"``; the opening quote right before ``token`` keeps keys such
    # as ``"next_token"`` and ``"page_token"`` untouched.
    *_token_patterns(r"\\?[\"']token\\?[\"']", ":", unquoted_stop=None),
    # Bare ``token`` key with ``:`` or ``=``, optional spaces and an optional opening quote
    # (``token=``, ``token: x``, ``token = x``, ``token: "x y"``); the lookbehind keeps
    # ``page_token``, ``next_token``, ``csrf_token`` and ``max_tokens`` untouched.
    *_token_patterns(r"(?<![A-Za-z0-9_])token", "[:=]", unquoted_stop=r"\s\"'\\&#,;}"),
]


# A credential key followed by ``{``, ``[`` or ``(``: the start of a bracketed value. The
# key may be quoted, as in a Python ``repr`` (``{'api_key': ['a', 'b']}`` or a tuple
# ``{'api_key': ('a', 'b')}``) or JSON that does not parse.
_KEYED_BRACKET = re.compile(
    r"(?i)(" + _VALUE_KEYS + _KEY_CLOSE + r"[ \t]*[:=][ \t]*)(?=[\[{(])(?!\[REDACTED\])",
    re.IGNORECASE,
)
_CLOSERS = {"{": "}", "[": "]", "(": ")"}


class _Brackets:
    """Balanced-bracket ends in one text, with every scan's findings cached.

    A scan from an opener records where each opener it pushed was closed, or that it was
    never closed. A later scan from one of those openers (outside a string in the earlier
    scan) would see exactly the same characters above it, so its answer is read from the
    cache instead of re-scanning to the end of the text. Many unbalanced keyed brackets
    (``password={`` on every line) then cost one pass instead of one pass each.
    """

    def __init__(self, text: str) -> None:
        self.text = text
        self.closes: dict[int, int] = {}
        self.unclosed: set[int] = set()

    def _line_end(self, start: int) -> int:
        newline = self.text.find("\n", start)
        return len(self.text) if newline == -1 else newline

    def end(self, start: int) -> int:
        """Return the index just past the bracket balancing ``text[start]``.

        Brackets inside double- or single-quoted strings (with backslash escapes) do not
        count, so a Python ``repr`` value such as ``['a]b']`` balances correctly. A
        single-quoted string also ends at a newline (a ``repr`` string never spans lines),
        so a stray apostrophe cannot hide the rest of the text. When
        the value never balances, the end of the line is returned instead, so an
        unparseable value is still masked whole.
        """
        if start in self.closes:
            return self.closes[start]
        if start in self.unclosed:
            return self._line_end(start)
        text = self.text
        stack: list[tuple[str, int]] = []
        quote = ""
        i = start
        size = len(text)
        while i < size:
            ch = text[i]
            if quote:
                if ch == "\\":
                    i += 1
                elif ch == quote or (ch == "\n" and quote == "'"):
                    quote = ""
            elif ch in "\"'":
                quote = ch
            elif ch in _CLOSERS:
                stack.append((_CLOSERS[ch], i))
            elif stack and ch == stack[-1][0]:
                self.closes[stack.pop()[1]] = i + 1
                if not stack:
                    return i + 1
            i += 1
        self.unclosed.update(pos for _, pos in stack)
        return self._line_end(start)


def _mask_bracket_values(text: str) -> str:
    """Mask a ``{...}``, ``[...]`` or ``(...)`` value after a credential key to its balance."""
    parts: list[str] = []
    pos = 0
    brackets = _Brackets(text)
    for match in _KEYED_BRACKET.finditer(text):
        if match.start() < pos:
            continue
        parts.append(text[pos : match.end()] + MASK)
        pos = brackets.end(match.end())
    parts.append(text[pos:])
    return "".join(parts)


def redact_secrets(text: str) -> str:
    """Scrub sensitive credentials, tokens, and authorization headers from text."""
    if not text:
        return ""
    sanitized = _mask_bracket_values(text)
    for pattern in SECRET_PATTERNS:
        sanitized = pattern.sub(lambda m: m.group(1) + MASK, sanitized)
    return sanitized


def tool_error(exc: Exception) -> ToolError:
    """Return a FastMCP ``ToolError`` that carries the redacted message of ``exc``.

    A tool handler raises it for a failed call, so the client receives a ``tools/call``
    result with ``isError: true``. The original exception keeps its unredacted message, so
    it must not ride along on the error: build the error inside the ``except`` block and
    raise it ``from None`` after the block ends. Raised inside the block, ``from None``
    still leaves the original on ``__context__``, where chain-walking reporters find it::

        except Exception as exc:
            failure = tool_error(exc)
        raise failure from None

    Batch tools process every item; partial success returns a normal result listing each
    item's status, and when every item fails they raise the redacted ``batch_failed`` error
    (``tool_failure``).
    """
    return ToolError(redact_message(str(exc)))


def _keyed_before(text: str, floor: int, sep: int) -> bool:
    """Return whether ``text[floor : sep + 1]`` ends with a credential key and ``:`` or ``=``."""
    window = text[floor : sep + 1] + "("
    return any(m.end() == len(window) - 1 for m in _KEYED_BRACKET.finditer(window))


_DECODER = json.JSONDecoder()
# Failed bracket tries per message before ``redact_message`` masks the rest (fail closed).
_MAX_BRACKET_TRIES = 64


def redact_message(text: str) -> str:
    """Redact a free-text message, keeping any JSON inside it valid where possible.

    Each ``{...}`` or ``[...]`` that ``json.loads`` accepts (the whole message, or one after
    a prefix such as ``HTTP 400: ``) is parsed, redacted value by value (``redact_payload``)
    and re-serialized in place; the text around it goes through ``redact_secrets``. JSON
    that does not parse falls back to ``redact_secrets`` on the raw text: the redaction is
    still whole, but the JSON shape may break. A bracketed value right after a credential
    key (``password={...}``), or a tuple right after one (``{'api_key': ('a', 'b')}``), is
    masked whole to its balanced bracket, or to the end of the line when it never balances,
    whether or not it parses. A ``(`` never counts toward ``_MAX_BRACKET_TRIES``.

    At most ``_MAX_BRACKET_TRIES`` brackets that neither parse nor follow a credential key
    are tried per message. Each try re-reads the text since the last match, so without the
    cap the cost grew with the square of the bracket count (8,000 ``{`` took about 14s).
    Past the cap the message fails closed: everything from the bracket that hit the cap to
    the end is replaced by ``MASK``. Only abusive input (dozens of stray brackets) gets
    there, and full redaction beats a readable tail that might hold a secret.
    """
    if not text:
        return ""
    parts: list[str] = []
    start = 0
    i = 0
    tries = 0
    brackets = _Brackets(text)
    size = len(text)
    while i < size:
        if text[i] == "(":
            # A tuple right after a credential key (``{'api_key': ('a', 'b')}``) is masked
            # whole too. A key needs ``:`` or ``=`` before the ``(``, with only spaces and
            # tabs between, so the 256 characters before that ``:`` or ``=`` are searched
            # only when one is there. The step back over the gap has no bound (a gap of any
            # length is still checked), yet each gap is read once, by the one ``(`` after
            # it, and a ``(`` never counts as a try, so long inputs stay linear.
            j = i - 1
            while j >= start and text[j] in " \t":
                j -= 1
            if j >= start and text[j] in ":=" and _keyed_before(text, max(start, j - 256), j):
                parts.append(redact_secrets(text[start:i]) + MASK)
                start = i = brackets.end(i)
                continue
        elif text[i] in "{[":
            prefix = text[start:i]
            # A value right after a credential key (``password={...}``) is the secret,
            # masked whole to its balanced bracket whether or not it parses.
            if redact_secrets(prefix + "x").endswith(MASK):
                parts.append(redact_secrets(prefix) + MASK)
                start = i = brackets.end(i)
                continue
            try:
                value, end = _DECODER.raw_decode(text, i)
            except (ValueError, RecursionError):
                # Nesting deeper than the decoder's recursion limit (Python 3.10/3.11 raise
                # RecursionError) is treated as JSON that does not parse.
                value, end = None, i
            if isinstance(value, (dict, list)):
                parts.append(redact_secrets(prefix))
                parts.append(json.dumps(redact_payload(value)))
                start = i = end
                continue
            tries += 1
            if tries == _MAX_BRACKET_TRIES:
                return "".join(parts) + redact_secrets(text[start:i]) + MASK
        i += 1
    if not parts:
        return redact_secrets(text)
    parts.append(redact_secrets(text[start:]))
    return "".join(parts)


_SECRET_KEY = re.compile(
    r"(?i)(?:" + _KEYS + r"|(?:api|access|refresh|auth|id|session)?[_-]?token|authorization)"
)


def redact_payload(value: Any) -> Any:
    """Redact a structured payload value by value, before it is serialized.

    Every string is passed through ``redact_secrets`` on its decoded text, so a
    ``password=...`` inside a message is redacted whole and ``json.dumps`` then escapes the
    result: the serialized JSON stays valid. Any non-None value under a credential key
    (``password``, ``api_key``, ``access_token``, ...), whether a string, number, list or
    dict, is replaced by ``MASK`` outright.
    """
    if isinstance(value, dict):
        return {
            k: (
                MASK
                if isinstance(k, str) and v is not None and _SECRET_KEY.fullmatch(k)
                else redact_payload(v)
            )
            for k, v in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [redact_payload(v) for v in value]
    if isinstance(value, str):
        return redact_secrets(value)
    return value


def tool_failure(error_type: str, message: str, **details: Any) -> ToolError:
    """Return a ``ToolError`` for a failure the tool detects itself, such as a failed batch.

    The message is the ``{"error": {"type": ..., "message": ..., **details}}`` JSON. The
    payload is redacted value by value before ``json.dumps`` (``redact_payload``), never as
    serialized text, so the message always parses. Raise it ``from None``, outside any
    ``except`` block, so the client receives ``isError: true`` and no caught exception rides
    along on ``__context__``.
    """
    payload: dict[str, Any] = {"type": error_type, "message": message, **details}
    return ToolError(json.dumps({"error": redact_payload(payload)}, indent=2))


class TemplateError(Exception):
    """Base exception for all template errors with automatic message redaction.

    The message goes through ``redact_message``, so a JSON body inside it (an upstream 401
    response, for example) is redacted value by value and keeps its shape.
    """

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        self.message = redact_message(message)
        self.details = details or {}
        super().__init__(self.message)


class AuthenticationError(TemplateError):
    """Raised on HTTP 401 / 403 authorization failures."""


class ResourceNotFoundError(TemplateError):
    """Raised on HTTP 404 missing resource errors."""


class RateLimitError(TemplateError):
    """Raised on HTTP 429 rate limit exhaustion."""


class SafetyViolationError(TemplateError, ToolError):
    """Raised when an operation violates read-only, single-delete, or bulk-destructive gates.

    Also a FastMCP ``ToolError``, so a refusal raised from middleware reaches the client as
    a ``tools/call`` result with ``isError: true`` instead of a JSON-RPC internal error.
    """
