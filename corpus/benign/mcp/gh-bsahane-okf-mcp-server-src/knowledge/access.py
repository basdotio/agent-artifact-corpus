"""Caller identity and document access control.

Identity comes only from a validated token (never from tool arguments). Each
document carries an `access` list of principals, set at ingestion from the
source system or `_okf.yaml`:

    group:<name>   members of a group from the token's groups claim
    user:<id>      a user, matched against subject, email or username
    *              any authenticated user

A document without an `access` list follows `OKF_DEFAULT_ACCESS`
(`deny` by default, so unlabelled content is hidden rather than exposed).
With authentication disabled the local operator is trusted and sees
everything, which is the single-user pilot mode.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, FrozenSet, Iterable, List, Optional

ANY_AUTHENTICATED = "*"


class AccessError(PermissionError):
    """Raised when a caller has no usable identity."""


@dataclass(frozen=True)
class Identity:
    """A validated caller. `trusted` is the local operator (auth disabled)."""

    subject: str
    issuer: str = ""
    email: str = ""
    username: str = ""
    groups: FrozenSet[str] = field(default_factory=frozenset)
    trusted: bool = False

    @property
    def principals(self) -> FrozenSet[str]:
        """Principal strings this caller matches."""
        users = {u for u in (self.subject, self.email, self.username) if u}
        return frozenset(
            {ANY_AUTHENTICATED}
            | {f"user:{u.lower()}" for u in users}
            | {f"group:{g.lower()}" for g in self.groups}
        )

    def audit(self) -> Dict[str, Any]:
        """Identity fields recorded in the audit log."""
        return {
            "sub": self.subject,
            "iss": self.issuer,
            "email": self.email,
            "groups": sorted(self.groups),
            "trusted": self.trusted,
        }


LOCAL_OPERATOR = Identity(subject="local-operator", trusted=True)


def _as_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return value.split() if " " in value else [value]
    return [str(v) for v in value]


def identity_from_claims(
    claims: Dict[str, Any],
    required_audience: str = "",
    required_scope: str = "",
    groups_claim: str = "groups",
) -> Identity:
    """Build an Identity from validated token claims (introspection result).

    Raises:
        AccessError: Without a subject, or when the audience or scope does
            not match what this server requires.
    """
    subject = str(claims.get("sub") or "")
    if not subject:
        raise AccessError("token has no subject")
    # Keycloak marks refresh and ID tokens with `typ`; introspection reports them active too.
    if str(claims.get("typ") or "").lower() in ("refresh", "offline", "id"):
        raise AccessError("not an access token")
    if required_audience:
        # Only `aud`: `azp` names the client that asked, not who the token is for.
        if required_audience not in _as_list(claims.get("aud")):
            raise AccessError(f"token audience does not include {required_audience!r}")
    if required_scope and required_scope not in _as_list(claims.get("scope")):
        raise AccessError(f"token lacks scope {required_scope!r}")
    # Keycloak group paths look like "/finance/payroll" and match
    # `group:finance/payroll` only: a leaf name would also grant a same-named
    # top-level group. A string claim is one group name, never split on spaces.
    raw = claims.get(groups_claim)
    groups = {
        g.strip().strip("/") for g in ([raw] if isinstance(raw, str) else _as_list(raw))
    }
    # An unverified email, or a username shaped like an email, could claim
    # someone else's `user:<email>` grants.
    email = (
        str(claims.get("email") or "") if claims.get("email_verified") is True else ""
    )
    username = str(claims.get("preferred_username") or claims.get("username") or "")
    if "@" in username and username.lower() != email.lower():
        username = ""
    return Identity(
        subject=subject,
        issuer=str(claims.get("iss") or ""),
        email=email,
        username=username,
        groups=frozenset(g for g in groups if g),
    )


def normalize_access(entries: Optional[Iterable[Any]]) -> Optional[List[str]]:
    """Canonical principal list for storage, or None when no rule applies.

    Accepts `group:x`, `user:x`, `*`, and `{groups: [...], users: [...]}`.
    """
    if entries is None:
        return None
    if isinstance(entries, dict):
        entries = [f"group:{g}" for g in entries.get("groups") or []] + [
            f"user:{u}" for u in entries.get("users") or []
        ]
    out = set()
    for entry in entries:
        entry = str(entry).strip()
        if entry == ANY_AUTHENTICATED:
            out.add(entry)
        elif entry.startswith(("group:", "user:")):
            kind, _, name = entry.partition(":")
            name = name.strip().strip("/") if kind == "group" else name.strip()
            if name:
                out.add(f"{kind}:{name.lower()}")
        else:
            raise ValueError(
                f"access entry must be '*', 'group:<name>' or 'user:<id>': {entry!r}"
            )
    return sorted(out)


def allowed(
    identity: Identity, access: Optional[List[str]], default_access: str
) -> bool:
    """Whether `identity` may see a document with this access list."""
    if identity.trusted:
        return True
    if access is None:
        return default_access == "authenticated"
    return bool(identity.principals & set(access))
