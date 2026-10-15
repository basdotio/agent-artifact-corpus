"""Split bearer tokens + the v0.6.1 strict one-to-one pairing model.

任务书 v1.1 §七评审补遗 split the single shared token into two kinds:

  * **mcp_token**    — presented by Octop's connector as `Authorization:
                       Bearer` on the /mcp/localoctop/ endpoint.
  * **bridge_token** — presented by the employee's client on the outbound
                       WSS bridge (?token= or Authorization header).

The two namespaces are fully separate: an mcp_token never authenticates a
bridge connection and a bridge_token never passes the MCP Bearer check.

v0.6.1 严格一对一配对 ([用户裁定] 2026-09-30): one mcp_token ↔ one
bridge_token. Pairs are issued, live, and revoked together; one user may
hold several pairs (byron2 = byron's second machine). The pair — not the
user name — is the routing key: a tools/call authenticated with an mcp
token is served **only** by the bridge session that registered with that
pair's bridge token. Same-name, cross-pair routing ("找该用户名在线的桥")
is gone: a paired bridge offline returns an explicit error, never a
fallback. An mcp token without a pair (runtime-issued alone, e.g. a temp
token) has no routing target and is rejected with CODE_MCP_UNPAIRED —
revoking such strays is an ops action, not a code special case.

Env pairing rule: the "user:token" entries in LOCALOCTOP_MCP_TOKENS and
LOCALOCTOP_CLIENT_TOKENS with the **same user id** form one pair
(byron.bridge=xxx / byron.mcp=yyy is how this looks in .env lines);
byron2 entries form the second pair naturally. The single-token back-compat
mode (only LOCALOCTOP_MCP_TOKENS set) self-pairs each user: that one token
is both the mcp and the bridge token of its pair.

Only SHA-256 hashes are kept in memory/on disk — the plaintext is returned
exactly once, from the issuing admin endpoint, and never stored.
"""

from __future__ import annotations

import hashlib
import secrets
import threading
import time
from dataclasses import dataclass, field

from .errors import BridgeProtocolError, CODE_AUTH_FAILED

KIND_MCP = "mcp"
KIND_BRIDGE = "bridge"
KIND_PAIR = "pair"
_KINDS = (KIND_MCP, KIND_BRIDGE)

# Plaintext prefixes make the kind obvious at a glance in configs/logs and
# rule out "is this the WSS token or the connector token?" confusion.
_PREFIX = {KIND_MCP: "lfs-mcp-", KIND_BRIDGE: "lfs-bridge-"}


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@dataclass
class TokenRecord:
    user_id: str
    created_at: float
    revoked: bool = False
    # First characters of the plaintext, so ops can tell tokens apart in
    # listings without ever storing the secret itself.
    hint: str = ""
    # v0.6.0 热加载: True for records derived from the token env vars
    # (seeded at startup or reconciled by a reload). These follow the env
    # strictly — the user disappearing from the env removes the token.
    # Runtime-issued tokens (from the admin issuing endpoint) are False and
    # survive env reloads as long as their user is not governed by the env.
    from_env: bool = False
    # v0.6.1 配对模型: identifier of the pair this token belongs to. A
    # strict one-to-one pair shares one pair_id across its mcp and bridge
    # tokens; a token issued alone has pair_id="" (unpaired — an mcp token
    # like that cannot route anywhere and is refused with CODE_MCP_UNPAIRED).
    pair_id: str = ""


def new_pair_id() -> str:
    """Fresh unique pair identifier (opaque; never derived from a secret)."""
    return "pair-" + secrets.token_hex(8)


@dataclass
class TokenStore:
    """Holds both token namespaces, keyed by SHA-256 hash of the plaintext,
    plus the pairing table that binds mcp ↔ bridge tokens 1:1.

    v0.6.0 hot-reload: all mutating methods replace the per-kind table with a
    fresh dict under `_lock` (write-lock, read-copy), and `authenticate` grabs
    the lock only to take a reference — verification itself runs on the
    immutable snapshot outside the lock. Readers therefore never iterate a
    dict that is being mutated ("禁止边遍历边改"), and a concurrent reload
    swaps the whole table atomically.
    """

    _mcp: dict[str, TokenRecord] = field(default_factory=dict)
    _bridge: dict[str, TokenRecord] = field(default_factory=dict)
    # v0.6.1: pair_id -> {"mcp": hash, "bridge": hash}. Invariant: the hash
    # on each side is also that table's record's pair_id. Kept in sync under
    # the same `_lock` as the tables, so a reader never sees a torn pair.
    _pairs: dict[str, dict[str, str]] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def _table(self, kind: str) -> dict[str, TokenRecord]:
        if kind == KIND_MCP:
            return self._mcp
        if kind == KIND_BRIDGE:
            return self._bridge
        raise ValueError(f"unknown token kind: {kind}")

    def _table_locked(self, kind: str) -> dict[str, TokenRecord]:
        """Snapshot of the current table under the lock; the caller mutates
        the copy freely (it is private after the swap in apply_env)."""
        with self._lock:
            return dict(self._table(kind))

    # -------------------------------------------------------------- issuing
    def issue(self, kind: str, user_id: str) -> str:
        """Mint a fresh token. Returns the plaintext — the only time it is
        ever available; only its hash is kept."""
        token = _PREFIX[kind] + secrets.token_hex(24)
        rec = TokenRecord(
            user_id=user_id,
            created_at=time.time(),
            hint=token[: len(_PREFIX[kind]) + 8],
        )
        with self._lock:
            old = dict(self._table(kind))
            old[_hash(token)] = rec
            self._set_table(kind, old)
        return token

    def issue_pair(self, user_id: str) -> tuple[str, str]:
        """v0.6.1 成对签发 ([用户裁定]): mint one mcp + one bridge token as a
        single strict pair. Returns (mcp_plaintext, bridge_plaintext) — the
        only time either is available; only hashes are kept."""
        mcp_token = _PREFIX[KIND_MCP] + secrets.token_hex(24)
        bridge_token = _PREFIX[KIND_BRIDGE] + secrets.token_hex(24)
        now = time.time()
        pair_id = new_pair_id()
        mcp_rec = TokenRecord(
            user_id=user_id, created_at=now,
            hint=mcp_token[: len(_PREFIX[KIND_MCP]) + 8], pair_id=pair_id,
        )
        bridge_rec = TokenRecord(
            user_id=user_id, created_at=now,
            hint=bridge_token[: len(_PREFIX[KIND_BRIDGE]) + 8], pair_id=pair_id,
        )
        with self._lock:
            mcp_old = dict(self._mcp)
            mcp_old[_hash(mcp_token)] = mcp_rec
            bridge_old = dict(self._bridge)
            bridge_old[_hash(bridge_token)] = bridge_rec
            pairs_old = dict(self._pairs)
            pairs_old[pair_id] = {"mcp": _hash(mcp_token), "bridge": _hash(bridge_token)}
            self._mcp = mcp_old
            self._bridge = bridge_old
            self._pairs = pairs_old
        return mcp_token, bridge_token

    def seed(self, kind: str, user_id: str, plaintext: str, pair_id: str = "") -> None:
        """Register a pre-existing plaintext (dev/test bootstrap from env
        vars; marks the record env-sourced so reloads can govern it).
        Production deployments issue via the admin endpoint instead."""
        if not plaintext:
            return
        rec = TokenRecord(
            user_id=user_id,
            created_at=time.time(),
            hint=plaintext[:16],
            from_env=True,
            pair_id=pair_id,
        )
        with self._lock:
            old = dict(self._table(kind))
            old[_hash(plaintext)] = rec
            self._set_table(kind, old)

    def seed_pair(self, user_id: str, mcp_plaintext: str, bridge_plaintext: str,
                  pair_id: str = "") -> None:
        """Env bootstrap: register the user's mcp and bridge tokens as one
        strict pair. This is how the .env two-line form maps to the pairing
        model; an explicit pair_id is honored when the caller already minted
        one (config.py does, so both records and the table share it)."""
        if not mcp_plaintext and not bridge_plaintext:
            return
        pair_id = pair_id or new_pair_id()
        if mcp_plaintext:
            self.seed(KIND_MCP, user_id, mcp_plaintext, pair_id=pair_id)
        if bridge_plaintext:
            self.seed(KIND_BRIDGE, user_id, bridge_plaintext, pair_id=pair_id)
        with self._lock:
            pairs_old = dict(self._pairs)
            entry: dict[str, str | None] = {}
            if mcp_plaintext:
                entry["mcp"] = _hash(mcp_plaintext)
            if bridge_plaintext:
                entry["bridge"] = _hash(bridge_plaintext)
            pairs_old[pair_id] = entry  # type: ignore[assignment]
            self._pairs = pairs_old

    def _set_table(self, kind: str, table: dict[str, TokenRecord]) -> None:
        """Replace the whole table for `kind` with `table` (caller holds
        `_lock`). Authentication never sees a half-updated store: it reads
        either the old or the new table in full."""
        if kind == KIND_MCP:
            self._mcp = table
        elif kind == KIND_BRIDGE:
            self._bridge = table
        else:
            raise ValueError(f"unknown token kind: {kind}")

    # ------------------------------------------------------------ env reload
    def apply_env(self, kind: str, entries: dict[str, str],
                  pairs: dict[str, dict[str, str]] | None = None) -> dict[str, list[str]]:
        """Reconcile env-sourced tokens of `kind` against the current table.

        v0.6.0 热加载 semantics:
          * env 用户/令牌新增 → 插入
          * env 中消失的用户/令牌 → 移除（旧令牌随即使鉴权失败）
          * 运行时经 /admin/tokens/issue 签发、且用户不在 env 中的令牌
            **保留**（动态签发不受 env 轮询影响）；用户在 env 中的动态
            签发令牌按移除处理（运维以 env 为该用户的最终权威）。
        `entries` maps user_id -> plaintext as parsed from the env var.
        `pairs` (v0.6.1) maps user_id -> {"pair_id":..., "mcp":..., "bridge":...}
        for the users this env pairs; passing it rebuilds the pairing table
        for those users (single-token back-compat users self-pair; runtime
        pair tokens survive because their user is absent from env pairs).
        Returns {"added": [user_ids], "removed": [user_ids]} (no plaintext).
        The swap is atomic per kind.
        """
        env_hash_user: dict[str, str] = {}   # hash -> user_id (from env)
        env_users: set[str] = set()
        for user_id, plaintext in entries.items():
            h = _hash(plaintext)
            env_hash_user[h] = user_id
            env_users.add(user_id)

        old = self._table_locked(kind)
        # v0.6.1: the pair_id each env user's token must carry after this
        # reload; users absent from `pairs` keep their existing pair binding.
        env_pair_by_user: dict[str, str] = {}
        if pairs is not None:
            for user_id, p in pairs.items():
                if p.get(kind):
                    env_pair_by_user[user_id] = p["pair_id"]

        new: dict[str, TokenRecord] = {}
        added: set[str] = set()
        removed: set[str] = set()

        # keep env tokens (re-seeded so a changed plaintext refreshes the record)
        for h, user_id in env_hash_user.items():
            rec = old.get(h)
            if rec is None:
                added.add(user_id)
            pair_id = env_pair_by_user.get(user_id) or (rec.pair_id if rec is not None else "")
            new[h] = TokenRecord(
                user_id=user_id,
                created_at=rec.created_at if rec is not None else time.time(),
                revoked=rec.revoked if rec is not None else False,
                hint=rec.hint if rec is not None else "",
                from_env=True,
                pair_id=pair_id,
            )
        # drop stale entries: a user whose env token is gone (rotated away or
        # removed from the env var) loses every record that is not the current
        # env hash — 移除即拒绝. Users absent from env keep their runtime-issued
        # tokens (dynamic issuance is untouched by env polling).
        env_plaintext_hashes = set(env_hash_user)
        for h, rec in old.items():
            if h in env_plaintext_hashes:
                continue
            if rec.user_id in env_users or rec.from_env:
                removed.add(rec.user_id)
                continue
            new[h] = rec

        with self._lock:
            self._set_table(kind, new)
            if pairs is not None:
                self._rebuild_pairs_locked(env_users)
        return {"added": sorted(added), "removed": sorted(removed)}

    def _rebuild_pairs_locked(self, env_users: set[str]) -> None:
        """Rebuild the pairing table (caller holds `_lock`): drop pairs whose
        side-hash is no longer live, keep runtime-issued pairs whose user is
        not governed by env, and re-add the env-derived pairs from the token
        records themselves (both records carry the same pair_id)."""
        new_pairs: dict[str, dict[str, str]] = {}
        mcp_live = self._mcp
        bridge_live = self._bridge
        # Re-derive env pairs: any live env record with a pair_id rebuilds the
        # binding from the tables (records are the source of truth).
        for table, side in ((mcp_live, KIND_MCP), (bridge_live, KIND_BRIDGE)):
            for h, rec in table.items():
                if not rec.pair_id or not rec.from_env:
                    continue
                entry = new_pairs.setdefault(rec.pair_id, {})
                if not entry.get(side):
                    entry[side] = h
        # Keep runtime-issued (non-env) pairs whose user is not governed by
        # the env — dynamic issuance is untouched by env polling.
        for pair_id, entry in self._pairs.items():
            mcp_h = entry.get("mcp")
            br_h = entry.get("bridge")
            mcp_rec = mcp_live.get(mcp_h) if mcp_h else None
            br_rec = bridge_live.get(br_h) if br_h else None
            if mcp_rec is None and br_rec is None:
                continue
            rec = mcp_rec or br_rec
            if rec.user_id in env_users and rec.from_env:
                continue
            new_pairs.setdefault(pair_id, dict(entry))
        self._pairs = new_pairs

    # ---------------------------------------------------------- verification
    def authenticate(self, kind: str, token: str | None) -> str:
        """Return the user_id behind a valid token of `kind`, or raise
        CODE_AUTH_FAILED. Tokens of the *other* kind are just unknown here —
        this is what makes the two directions mutually exclusive."""
        if not token:
            raise BridgeProtocolError(CODE_AUTH_FAILED, "missing bearer token")
        with self._lock:
            table = self._table(kind)
        rec = table.get(_hash(token))
        if rec is None or rec.revoked:
            raise BridgeProtocolError(CODE_AUTH_FAILED, "invalid token")
        return rec.user_id

    def pair_of(self, kind: str, token: str) -> dict | None:
        """v0.6.1: resolve the strict pair a token belongs to.

        Returns {"pair_id", "user_id", "mcp", "bridge"} (side keys present
        only when that side is live and non-revoked — a revoked half makes
        the pair one-sided, which callers treat as unpaired), or None when
        the token is unknown/revoked/unpaired."""
        h = _hash(token)
        with self._lock:
            # All three structures snapshotted under one lock acquisition so
            # the pair view is never torn by a concurrent reload/issue.
            mcp_t, bridge_t = dict(self._mcp), dict(self._bridge)
            pairs = dict(self._pairs)
        table = mcp_t if kind == KIND_MCP else bridge_t
        rec = table.get(h)
        if rec is None or rec.revoked or not rec.pair_id:
            return None
        pair_id = rec.pair_id
        entry = pairs.get(pair_id)
        if not entry:
            # The record carries a pair_id but no table entry — can only happen
            # for hand-seeded dev/test stores; treat as unpaired.
            return None
        out: dict = {"pair_id": pair_id, "user_id": rec.user_id}
        for side, tbl in ((KIND_MCP, mcp_t), (KIND_BRIDGE, bridge_t)):
            side_h = entry.get(side)
            side_rec = tbl.get(side_h) if side_h else None
            if side_rec is not None and not side_rec.revoked:
                out[side] = side_h
        return out

    # ------------------------------------------------------------- revocation
    def revoke_pair(self, pair_id: str) -> bool:
        """v0.6.1 成对吊销 ([用户裁定]): revoke both halves of a pair at once.
        Returns True if the pair was known and either half was still live."""
        with self._lock:
            entry = self._pairs.get(pair_id)
            if not entry:
                return False
            old_mcp, old_bridge = dict(self._mcp), dict(self._bridge)
            changed = False
            for table, side_h in ((old_mcp, entry.get("mcp")),
                                  (old_bridge, entry.get("bridge"))):
                if not side_h:
                    continue
                rec = table.get(side_h)
                if rec is not None and not rec.revoked:
                    table[side_h] = TokenRecord(
                        user_id=rec.user_id, created_at=rec.created_at,
                        revoked=True, hint=rec.hint, pair_id=rec.pair_id,
                    )
                    changed = True
            if changed:
                self._mcp = old_mcp
                self._bridge = old_bridge
                pairs_old = dict(self._pairs)
                pairs_old.pop(pair_id, None)
                self._pairs = pairs_old
            return changed

    def revoke_user(self, kind: str, user_id: str) -> int:
        """Revoke every token of `kind` belonging to `user_id`. Returns how
        many were revoked. The other kind is untouched (independent
        revocation per direction)."""
        n = 0
        old = self._table_locked(kind)
        new = {h: rec for h, rec in old.items()}
        for h, rec in new.items():
            if rec.user_id == user_id and not rec.revoked:
                # TokenRecord is shared with the immutable snapshot readers may
                # still hold — replace instead of mutating in place.
                new[h] = TokenRecord(
                    user_id=rec.user_id, created_at=rec.created_at,
                    revoked=True, hint=rec.hint, pair_id=rec.pair_id,
                )
                n += 1
        if n:
            with self._lock:
                self._set_table(kind, new)
        return n

    def revoke_token(self, kind: str, token: str) -> bool:
        """Revoke one specific token. Returns True if it was known and live."""
        h = _hash(token)
        old = self._table_locked(kind)
        rec = old.get(h)
        if rec is None or rec.revoked:
            return False
        new = dict(old)
        new[h] = TokenRecord(
            user_id=rec.user_id, created_at=rec.created_at,
            revoked=True, hint=rec.hint, pair_id=rec.pair_id,
        )
        with self._lock:
            self._set_table(kind, new)
        return True

    # ------------------------------------------------------------------ ops
    def list_pairs(self) -> list[dict]:
        """Pairing table for the admin views (v0.6.1): pair_id, user, and
        per-side {hint, revoked} resolved from the live tables — no
        plaintext, no full hashes. `complete` marks a full live pair; a
        pair whose other half was revoked independently appears one-sided
        (and MCP routing through it behaves as unpaired)."""
        with self._lock:
            mcp_t, bridge_t = dict(self._mcp), dict(self._bridge)
            pairs = dict(self._pairs)
        out: list[dict] = []
        for pair_id, entry in pairs.items():
            mcp_rec = mcp_t.get(entry.get("mcp")) if entry.get("mcp") else None
            br_rec = bridge_t.get(entry.get("bridge")) if entry.get("bridge") else None
            user = (mcp_rec or br_rec).user_id if (mcp_rec or br_rec) else ""
            out.append({
                "pair_id": pair_id,
                "user_id": user,
                "complete": bool(mcp_rec and br_rec
                                 and not mcp_rec.revoked and not br_rec.revoked),
                "mcp": {"hint": mcp_rec.hint, "revoked": bool(mcp_rec and mcp_rec.revoked)}
                       if mcp_rec else None,
                "bridge": {"hint": br_rec.hint, "revoked": bool(br_rec and br_rec.revoked)}
                         if br_rec else None,
            })
        out.sort(key=lambda p: (p["user_id"], p["pair_id"]))
        return out

    def list_user(self, kind: str, user_id: str) -> list[dict]:
        """Metadata for a user's tokens (no plaintext, no full hashes)."""
        table = self._table_locked(kind)
        return [
            {
                "kind": kind,
                "user_id": rec.user_id,
                "hint": rec.hint,
                "created_at": rec.created_at,
                "revoked": rec.revoked,
                "pair_id": rec.pair_id or None,
                "paired": bool(rec.pair_id),
            }
            for rec in table.values()
            if not user_id or rec.user_id == user_id
        ]
