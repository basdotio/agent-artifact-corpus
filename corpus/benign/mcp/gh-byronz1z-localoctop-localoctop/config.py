"""Environment-driven configuration and the split-token auth model.

Tokens bind an Octop user to their bridge session. 任务书 v1.1 §七评审补遗
splits the former single token into two independent namespaces (see
tokens.py):

  * mcp_token    — Octop connector Bearer auth on /mcp/localoctop/
  * bridge_token — client WSS auth on /mcp/localoctop/ws

Each direction verifies only its own kind; either can be revoked on its own.
Only SHA-256 hashes are retained — plaintexts are shown exactly once by the
issuing admin endpoint.

Bootstrap (dev / single-tenant) via environment:
  * LOCALOCTOP_MCP_TOKENS="userA:tokA,..."          seeds MCP tokens
  * LOCALOCTOP_CLIENT_TOKENS="userA:btokA,..."  seeds bridge tokens
    (when unset, LOCALOCTOP_MCP_TOKENS also seeds bridge tokens so existing
    single-token deployments keep working until they rotate)

v0.6.1 严格一对一配对: entries sharing the **same user id** across the two
env vars form one pair (the .env lines byron.mcp=yyy / byron.bridge=xxx);
a second user id (byron2) is a second pair for the same human. The
single-token back-compat mode self-pairs each user. MCP calls route by
pair, not by user name — see TokenStore.pair_of and Settings.pair_route.

Everything is read once at startup into a Settings dataclass; tests build a
Settings directly and inject it.

v0.6.0: the token env vars are additionally re-read on demand —
`reload_tokens_from_env()` (wired to the background poller in app.py and to
`POST /admin/tokens/reload`) reconciles the env-derived tokens into the live
store; runtime-issued tokens for users absent from the env are preserved.
"""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field

from .errors import BridgeProtocolError, CODE_AUTH_FAILED, CODE_MCP_UNPAIRED
from .tokens import KIND_BRIDGE, KIND_MCP, TokenStore

DEFAULT_MAX_READ_BYTES = 20 * 1024 * 1024   # 20 MB
DEFAULT_MAX_WRITE_BYTES = 10 * 1024 * 1024  # 10 MB
# 超时预算（任务书 v1.1 §七）：客户端单工具执行 ≤15s、桥往返 ≤18s、
# 适配器整体响应 ≤20s。适配器侧的桥等待取 18s。
DEFAULT_BRIDGE_TIMEOUT = 18.0               # A→B request/response budget
DEFAULT_IDLE_TIMEOUT = 120.0                # drop a bridge with no traffic
# v0.6.0: how often the background task re-reads the token env vars
# (covers k8s/direct-process deployments where the process env can change
# without a container rebuild; see T3-SERVER-HOTRELOAD).
DEFAULT_TOKEN_POLL_INTERVAL = 30.0


@dataclass
class Settings:
    # --- auth ---
    # Split-token store: mcp_tokens (Octop Bearer) and bridge_tokens (client
    # WSS), held as SHA-256 hashes. Seeded from LOCALOCTOP_MCP_TOKENS /
    # LOCALOCTOP_CLIENT_TOKENS at startup; extended at runtime via the admin
    # issuing endpoint.
    token_store: TokenStore = field(default_factory=TokenStore)
    # Legacy static map, kept only as the source the store is seeded from
    # (and for the admin-endpoint guard "__admin__").
    static_tokens: dict[str, str] = field(default_factory=dict)

    # --- behavior switches ---
    # Master switch for the write tools. User ruling 2026-09-29: write is
    # enabled BY DEFAULT (checkbox pre-ticked on the employee console);
    # the flag exists to allow opting out. The dataclass default stays
    # False for explicit test construction; load_settings (the production
    # path) defaults ON.
    allow_write: bool = False
    # Per-user override: user ids allowed to write even when allow_write is
    # globally off (escape hatch; kept for staged rollout or per-user lock).
    write_allowlist: set[str] = field(default_factory=set)
    # Admin kill-switch: when True, every tools/call is refused. Models the
    # product-layer "管理员可整体停用" control.
    disabled: bool = False

    # --- limits / timeouts ---
    max_read_bytes: int = DEFAULT_MAX_READ_BYTES
    max_write_bytes: int = DEFAULT_MAX_WRITE_BYTES
    bridge_timeout: float = DEFAULT_BRIDGE_TIMEOUT
    idle_timeout: float = DEFAULT_IDLE_TIMEOUT

    # --- logging ---
    audit_log_path: str = "logs/calls.jsonl"
    log_level: str = "INFO"
    # Service-owned state directory (transfer ledger lives here, one file
    # per user — never inside the users' own folders).
    state_dir: str = "state"
    # v0.6.0 热加载: background env-poll interval (0 disables the poller).
    token_poll_interval: float = DEFAULT_TOKEN_POLL_INTERVAL

    # --- server ---
    host: str = "0.0.0.0"  # noqa: S104 — container bind, fronted by a proxy
    port: int = 8080
    # Optional second listener: TLS-terminated public port for employee
    # bridges dialing in over wss:// (no reverse proxy required). When
    # ssl_port is 0 / cert / key unset, only the plain listener runs and
    # behaviour is identical to pre-1.1 deployments.
    ssl_port: int = 0
    ssl_certfile: str = ""
    ssl_keyfile: str = ""
    # Public base path prefix, kept configurable for reverse-proxy mounting.
    mcp_path: str = "/mcp/localoctop/"
    ws_path: str = "/mcp/localoctop/ws"

    # ------------------------------------------------------------------ auth
    def authenticate_mcp(self, token: str | None) -> str:
        """Validate an Octop connector Bearer token (mcp_token) and return
        the user_id. A bridge_token never passes here."""
        return self.token_store.authenticate(KIND_MCP, token)

    def authenticate_bridge(self, token: str | None) -> str:
        """Validate a client WSS token (bridge_token) and return the
        user_id. An mcp_token never passes here."""
        return self.token_store.authenticate(KIND_BRIDGE, token)

    # --------------------------------------------------- v0.6.1 pair routing
    def pair_route_mcp(self, token: str | None) -> tuple[str, str]:
        """Resolve an MCP Bearer token to its strict pair's routing target.

        Returns (user_id, pair_id) — the tools/call must be served ONLY by
        the bridge session that registered with `pair_id`. Raises:
          * CODE_AUTH_FAILED  — unknown/revoked token (not an mcp token);
          * CODE_MCP_UNPAIRED — the token is valid but belongs to no pair
            (e.g. a runtime-issued single mcp token), so there is no routing
            target: no fallback to "any online bridge of this user name".
        """
        # authenticate first: unknown/wrong-kind tokens are auth failures,
        # not pairing failures.
        user_id = self.authenticate_mcp(token)
        pair = self.token_store.pair_of(KIND_MCP, token) if token else None
        if not pair or not pair.get(KIND_BRIDGE):
            raise BridgeProtocolError(
                CODE_MCP_UNPAIRED,
                "mcp-token-unpaired: this mcp token has no live paired bridge "
                "token (unpaired, or the paired bridge token was revoked); "
                "issue a token pair (kind='pair') instead",
            )
        return user_id, pair["pair_id"]

    def pair_route_bridge(self, token: str | None) -> tuple[str, str]:
        """Resolve a bridge WSS token to (user_id, pair_id) at registration.
        Unpaired bridge tokens still authenticate (the bridge may dial in
        for liveness) — pair_id is "" then, and such a session is never a
        routing target for MCP calls."""
        user_id = self.authenticate_bridge(token)
        pair = self.token_store.pair_of(KIND_BRIDGE, token) if token else None
        return user_id, (pair["pair_id"] if pair else "")

    # ------------------------------------------------------- write decisions
    def user_can_write(self, user_id: str) -> bool:
        """Whether write tools are enabled for this user right now."""
        if self.disabled:
            return False
        return self.allow_write or user_id in self.write_allowlist


def _parse_token_pairs(raw: str) -> dict[str, str]:
    """Parse "userA:tokA,userB:tokB" into {user_id: plaintext}.
    Empty/malformed segments are skipped."""
    out: dict[str, str] = {}
    for pair in raw.split(","):
        pair = pair.strip()
        if not pair or ":" not in pair:
            continue
        user_id, _, tok = pair.partition(":")
        user_id, tok = user_id.strip(), tok.strip()
        if user_id and tok:
            out[user_id] = tok
    return out


def _env_token_entries(e) -> tuple[dict[str, str], dict[str, str]]:
    """Read the token env vars. Returns (mcp_entries, bridge_entries) where
    the bridge side falls back to the MCP entries when
    LOCALOCTOP_CLIENT_TOKENS is unset/empty (single-token back-compat)."""
    mcp_entries = _parse_token_pairs(e.get("LOCALOCTOP_MCP_TOKENS", ""))
    bridge_entries = _parse_token_pairs(e.get("LOCALOCTOP_CLIENT_TOKENS", ""))
    if not bridge_entries:
        bridge_entries = dict(mcp_entries)
    return mcp_entries, bridge_entries


def _env_pairs(mcp_entries: dict[str, str], bridge_entries: dict[str, str]) -> dict[str, dict[str, str]]:
    """v0.6.1: map the env entries to strict one-to-one pairs.

    The .env two-line form byron.mcp=yyy / byron.bridge=xxx arrives here as
    mcp_entries["byron"] / bridge_entries["byron"] — same user id, so they
    are one pair. A second machine (byron2) is simply another user id, i.e.
    another pair; a user present in only one var has that side unpaired
    (the pair entry keeps only the side that exists)."""
    pairs: dict[str, dict[str, str]] = {}
    for user_id in set(mcp_entries) | set(bridge_entries):
        # v0.6.1 hotfix: the pair_id MUST be deterministic in the token
        # contents. The hot-reload poller calls this every interval; a random
        # id here would churn every reload and instantly orphan every live
        # bridge session (its registration carried the previous pair_id) —
        # every MCP call would fail with pair-bridge-offline. Deriving the
        # id from user+tokens means: same tokens → same pair_id across
        # reloads/restarts; rotating a token → a new pair (intended).
        material = "\x00".join((
            user_id,
            mcp_entries.get(user_id, ""),
            bridge_entries.get(user_id, ""),
        ))
        pair_id = "pair-" + hashlib.sha256(material.encode()).hexdigest()[:16]
        pairs[user_id] = {
            "pair_id": pair_id,
            "mcp": mcp_entries.get(user_id, ""),
            "bridge": bridge_entries.get(user_id, ""),
        }
    return pairs


def _seed_pairs(store: TokenStore, pairs: dict[str, dict[str, str]]) -> None:
    """Seed the env-derived pairs into the store (startup path)."""
    for user_id, p in pairs.items():
        store.seed_pair(user_id, p["mcp"], p["bridge"], pair_id=p["pair_id"])


def load_settings(env: os._Environ | dict | None = None) -> Settings:
    """Build Settings from the environment (or an injected mapping for tests)."""
    e = env if env is not None else os.environ

    static = _parse_token_pairs(e.get("LOCALOCTOP_MCP_TOKENS", ""))
    mcp_entries, bridge_entries = _env_token_entries(e)
    pairs = _env_pairs(mcp_entries, bridge_entries)

    store = TokenStore()
    _seed_pairs(store, pairs)

    write_allow: set[str] = set()
    for u in e.get("LOCALOCTOP_WRITE_ALLOWLIST", "").split(","):
        u = u.strip()
        if u:
            write_allow.add(u)

    return Settings(
        token_store=store,
        static_tokens=static,
        allow_write=_env_flag(e.get("LOCALOCTOP_ALLOW_WRITE"), True),
        write_allowlist=write_allow,
        disabled=_env_flag(e.get("LOCALOCTOP_DISABLED"), False),
        max_read_bytes=_int(e.get("LOCALOCTOP_MAX_READ_BYTES"), DEFAULT_MAX_READ_BYTES),
        max_write_bytes=_int(e.get("LOCALOCTOP_MAX_WRITE_BYTES"), DEFAULT_MAX_WRITE_BYTES),
        bridge_timeout=_float(e.get("LOCALOCTOP_BRIDGE_TIMEOUT"), DEFAULT_BRIDGE_TIMEOUT),
        idle_timeout=_float(e.get("LOCALOCTOP_IDLE_TIMEOUT"), DEFAULT_IDLE_TIMEOUT),
        audit_log_path=e.get("LOCALOCTOP_AUDIT_LOG", "logs/calls.jsonl"),
        log_level=e.get("LOCALOCTOP_LOG_LEVEL", "INFO"),
        state_dir=e.get("LOCALOCTOP_STATE_DIR", "state"),
        token_poll_interval=_float(e.get("LOCALOCTOP_TOKEN_POLL_INTERVAL"), DEFAULT_TOKEN_POLL_INTERVAL),
        host=e.get("LOCALOCTOP_HOST", "0.0.0.0"),
        port=_int(e.get("LOCALOCTOP_PORT"), 8080),
        ssl_port=_int(e.get("LOCALOCTOP_SSL_PORT"), 0),
        ssl_certfile=e.get("LOCALOCTOP_SSL_CERTFILE", ""),
        ssl_keyfile=e.get("LOCALOCTOP_SSL_KEYFILE", ""),
        mcp_path=e.get("LOCALOCTOP_MCP_PATH", "/mcp/localoctop/"),
        ws_path=e.get("LOCALOCTOP_WS_PATH", "/mcp/localoctop/ws"),
    )


def reload_tokens_from_env(settings: Settings, env: os._Environ | dict | None = None,
                           logger=None) -> dict[str, dict[str, list[str]]]:
    """v0.6.0 热加载: re-read the token env vars and reconcile them into
    `settings.token_store` (atomic swap per kind — see TokenStore.apply_env).

    Returns {"mcp": {"added": [...], "removed": [...]}, "bridge": {...}}
    with user ids only — plaintexts never appear in the result or logs.

    Note: in Docker the process env is fixed at container creation, so a
    changed .env on the host is only visible after `docker compose up -d`;
    this poller covers k8s/direct-process deployments where the env of a
    running process can actually change.
    """
    e = env if env is not None else os.environ
    mcp_entries, bridge_entries = _env_token_entries(e)
    # v0.6.1: the same pairing rule as startup — same user id across the two
    # vars is one pair; reload reconciles the pairing table along with the
    # token tables (runtime-issued pairs for users absent from env survive).
    pairs = _env_pairs(mcp_entries, bridge_entries)
    result = {
        "mcp": settings.token_store.apply_env(KIND_MCP, mcp_entries, pairs),
        "bridge": settings.token_store.apply_env(KIND_BRIDGE, bridge_entries, pairs),
    }
    if logger is not None:
        for kind in ("mcp", "bridge"):
            added = result[kind]["added"]
            removed = result[kind]["removed"]
            if added or removed:
                logger.info("token reload (%s): added users=%s removed users=%s",
                            kind, added, removed)
    return result


def _env_flag(v: str | None, default: bool) -> bool:
    if v is None or v == "":
        return default
    return v.strip().lower() in {"1", "true", "yes", "on"}


def _int(v: str | None, default: int) -> int:
    try:
        return int(v) if v not in (None, "") else default
    except ValueError:
        return default


def _float(v: str | None, default: float) -> float:
    try:
        return float(v) if v not in (None, "") else default
    except ValueError:
        return default
