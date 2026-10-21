"""TypeDB access: one database per run, schema = core + method.

Connection settings come from qls.toml [typedb] or the environment:
QLS_TYPEDB (address, default 127.0.0.1:1729), QLS_TYPEDB_USER, QLS_TYPEDB_PASSWORD,
QLS_TYPEDB_TLS=1 for TLS with the system's root certificates.
"""

from __future__ import annotations

import os
import re

from .util import QlsError, dumps, sha256_text


class GraphError(QlsError):
    """A write the ontology refused. `message` is written for the agent; `raw` is TypeDB's error."""

    def __init__(self, message: str, raw: str = ""):
        super().__init__(message)
        self.raw = raw


def lit(value) -> str:
    """A TypeQL literal."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    s = str(value)
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t") + '"'


_CARD = re.compile(r"Constraint '@card\((\d+)\.\.(\d*)\)' has been violated: found (\d+) instances")
_ROLE = re.compile(r"of type '([\w-]+)' violated constraint for playing role type '([\w-]+):([\w-]+)'")
_OWNS = re.compile(r"of type '([\w-]+)' has an attribute ownership constraint violation for attribute ownership of type '([\w-]+)'")
_RELATES = re.compile(r"of type '([\w-]+)' violated constraint for relating role type '([\w-]+):([\w-]+)'")
_VALUES = re.compile(r"Constraint '@values\((.*?)\)' has been violated: value '(.*?)'")
_KEY = re.compile(r"@key|unique", re.I)


def _card_text(lo: str, hi: str) -> str:
    if hi == "":
        return f"at least {lo}"
    if lo == hi:
        return f"exactly {lo}"
    if lo == "0":
        return f"at most {hi}"
    return f"between {lo} and {hi}"


def translate(raw: str) -> str:
    """Turn a TypeDB validation error into one sentence an agent can act on."""
    card, role, owns = _CARD.search(raw), _ROLE.search(raw), _OWNS.search(raw)
    if card and role:
        typ, rel, rname = role.groups()
        lo, hi, found = card.groups()
        return (f"The ontology refused this: a {typ} must be the '{rname}' in {_card_text(lo, hi)} "
                f"'{rel}' relation(s); this change would leave {found}.")
    if card and owns:
        typ, attr = owns.groups()
        lo, hi, found = card.groups()
        return f"The ontology refused this: a {typ} needs {_card_text(lo, hi)} '{attr}' (found {found})."
    rel = _RELATES.search(raw)
    if card and rel:
        return f"The ontology refused this: a '{rel.group(1)}' relation needs its '{rel.group(3)}'."
    vals = _VALUES.search(raw)
    if vals:
        return f"The ontology refused this: {vals.group(2)} is not one of {vals.group(1)}."
    if _KEY.search(raw):
        return "The ontology refused this: an id is already in use."
    first = next((ln for ln in raw.splitlines() if ln.strip()), raw)
    return f"The ontology refused this: {first.strip()}"


class Graph:
    def __init__(self, address: str | None = None, user: str | None = None, password: str | None = None,
                 tls: bool | None = None):
        self.address = address or os.environ.get("QLS_TYPEDB", "127.0.0.1:1729")
        self.user = user or os.environ.get("QLS_TYPEDB_USER", "admin")
        self.password = password or os.environ.get("QLS_TYPEDB_PASSWORD", "password")
        self.tls = tls if tls is not None else os.environ.get("QLS_TYPEDB_TLS", "") in ("1", "true", "yes")
        self._driver = None

    @property
    def driver(self):
        if self._driver is None:
            try:
                from typedb.driver import Credentials, DriverOptions, DriverTlsConfig, TypeDB
            except ImportError as exc:
                raise QlsError("pip install 'qual-analysis-mcp-tools[typedb]' (typedb-driver)") from exc
            tls = DriverTlsConfig.enabled_with_native_root_ca() if self.tls else DriverTlsConfig.disabled()
            try:
                self._driver = TypeDB.driver(self.address, Credentials(self.user, self.password), DriverOptions(tls))
            except Exception as exc:
                raise QlsError(f"Cannot reach TypeDB at {self.address}: {str(exc).strip().splitlines()[0]}. "
                               "Start it with `typedb server` (see README, Install) or set QLS_TYPEDB.") from exc
        return self._driver

    def close(self) -> None:
        if self._driver is not None:
            self._driver.close()
            self._driver = None

    # -- databases ----------------------------------------------------------------

    def exists(self, db: str) -> bool:
        return self.driver.databases.contains(db)

    def create(self, db: str, schemas: list[str]) -> None:
        from typedb.driver import TransactionType

        if self.exists(db):
            raise QlsError(f"TypeDB database {db!r} already exists")
        self.driver.databases.create(db)
        try:
            with self.driver.transaction(db, TransactionType.SCHEMA) as tx:
                for s in schemas:
                    tx.query(s).resolve()
                tx.commit()
        except Exception:
            self.drop(db)
            raise

    def drop(self, db: str) -> None:
        if self.exists(db):
            self.driver.databases.get(db).delete()

    # -- queries ------------------------------------------------------------------

    def write(self, db: str, queries: list[str]) -> None:
        """Run queries in one write transaction; all or nothing."""
        from typedb.driver import TransactionType

        if not queries:
            return
        try:
            with self.driver.transaction(db, TransactionType.WRITE) as tx:
                for q in queries:
                    tx.query(q).resolve()
                tx.commit()
        except Exception as exc:
            raw = str(exc).strip()
            raise GraphError(translate(raw), raw) from None

    def rows(self, db: str, query: str) -> list[dict]:
        """Read query -> list of {variable: python value}. Attributes and values become plain values,
        types their label, entities and relations {'type': label, 'iid': iid}."""
        from typedb.driver import TransactionType

        try:
            with self.driver.transaction(db, TransactionType.READ) as tx:
                ans = tx.query(query).resolve()
                if ans.is_concept_documents():
                    return list(ans.as_concept_documents())
                if not ans.is_concept_rows():
                    return []
                out = []
                for row in ans.as_concept_rows():
                    out.append({c: _py(row.get(c)) for c in row.column_names()})
                return out
        except Exception as exc:
            raw = str(exc).strip()
            raise GraphError(next((ln for ln in raw.splitlines() if ln.strip()), raw), raw) from None

    def column(self, db: str, query: str, var: str) -> list:
        return [r[var] for r in self.rows(db, query)]

    def state_hash(self, db: str) -> str:
        """Fingerprint of the graph, independent of internal ids and insertion order."""
        ents: dict[str, list] = {}
        for r in self.rows(db, "match $x isa! $t, has id $i, has $a; $a isa! $at; select $t, $i, $at, $a;"):
            ents.setdefault(f"{r['t']}|{r['i']}", []).append((r["at"], r["a"]))
        rels: dict[str, dict] = {}
        for r in self.rows(db, "match $r isa! $rt, links ($role: $p); $p has id $pid; select $r, $rt, $role, $pid;"):
            d = rels.setdefault(r["r"]["iid"], {"t": r["rt"], "p": [], "a": []})
            d["p"].append((r["role"], r["pid"]))
        for r in self.rows(db, "match $r isa! $rt, links ($role: $p), has $a; $a isa! $at; select $r, $at, $a;"):
            if r["r"]["iid"] in rels:
                rels[r["r"]["iid"]]["a"].append((r["at"], r["a"]))
        e = sorted((k, sorted(set(v))) for k, v in ents.items())
        rr = sorted(dumps([d["t"], sorted(set(d["p"])), sorted(set(d["a"]))]) for d in rels.values())
        return sha256_text(dumps([e, rr]))


def _py(c):
    if c is None:
        return None
    if c.is_attribute():
        return c.get_value()
    if c.is_value():
        return c.get()
    if c.is_type():
        return c.get_label()
    return {"type": c.get_type().get_label(), "iid": c.get_iid()}
