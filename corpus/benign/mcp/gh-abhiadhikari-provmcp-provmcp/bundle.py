"""Export a ledger as a W3C PROV bundle.

The point is portability: a bundle should attach to an ELN entry, a methods
section, or a supplementary file and still be verifiable by someone who has never
run provmcp.

PROV mapping (PROV-DM, serialized as PROV-JSON):
  Entity     a result, identified by its content hash; the arguments of a call;
             a data-source release
  Activity   a tool call, with start/end time, tool name, sequence number
  Agent      the client that made the call, the downstream server that answered,
             and provmcp itself
  used / wasGeneratedBy / wasAssociatedWith / wasAttributedTo / wasInformedBy
             the obvious edges, plus wasInformedBy linking each call to the
             previous one so the ledger order survives in the graph

Bundle contents:
  provenance.jsonl   the ledger, verbatim
  provenance.json    PROV-JSON; loads with the `prov` library, converts to PROV-N,
                     PROV-O (RDF), PROV-XML from there
  manifest.json      chain head, entry count, file hashes, provmcp version
  PUBKEY.pem         the Ed25519 public key, if the ledger was signed
"""

from __future__ import annotations

import json
import re
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path

from . import __version__
from .keys import load_public, public_pem
from .ledger import Entry, Ledger, canonical, sha256_hex

NS = "https://github.com/AbhiAdhikari/provmcp/ns#"
LEDGER_NAME = "provenance.jsonl"
PROV_NAME = "provenance.json"
MANIFEST_NAME = "manifest.json"
PUBKEY_NAME = "PUBKEY.pem"


def _slug(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", s).strip("_") or "unknown"


def _iso(ts: str, plus_ms: int = 0) -> str:
    dt = datetime.fromisoformat(ts)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return (dt + timedelta(milliseconds=plus_ms)).isoformat()


def to_prov_json(entries: list[Entry]) -> dict:
    doc: dict = {
        "prefix": {"provmcp": NS, "xsd": "http://www.w3.org/2001/XMLSchema#"},
        "entity": {}, "activity": {}, "agent": {},
        "used": {}, "wasGeneratedBy": {}, "wasAssociatedWith": {},
        "wasAttributedTo": {}, "wasInformedBy": {},
    }
    ent, act, ag = doc["entity"], doc["activity"], doc["agent"]

    ag["provmcp:proxy"] = {
        "prov:type": {"$": "prov:SoftwareAgent", "type": "prov:QUALIFIED_NAME"},
        "provmcp:version": __version__,
    }

    prev_call: str | None = None
    for e in entries:
        call = f"provmcp:call/{e.seq}"
        server = f"provmcp:server/{_slug(e.server_id)}"
        result = f"provmcp:result/{e.result_hash}"
        args = f"provmcp:arguments/{e.seq}"

        ag.setdefault(server, {
            "prov:type": {"$": "prov:SoftwareAgent", "type": "prov:QUALIFIED_NAME"},
            "provmcp:server_id": e.server_id,
        })

        act[call] = {
            "prov:startTime": _iso(e.timestamp),
            "prov:endTime": _iso(e.timestamp, e.duration_ms),
            "provmcp:seq": e.seq,
            "provmcp:tool": e.tool,
            "provmcp:entry_hash": e.entry_hash,
            **({"provmcp:error": e.error} if e.error else {}),
        }

        ent[args] = {"provmcp:json": canonical(e.arguments).decode("utf-8")}
        ent.setdefault(result, {"provmcp:sha256": e.result_hash})
        if e.result is not None:
            ent[result]["provmcp:json"] = canonical(e.result).decode("utf-8")

        doc["used"][f"_:u{e.seq}a"] = {"prov:activity": call, "prov:entity": args}
        doc["wasGeneratedBy"][f"_:g{e.seq}"] = {"prov:entity": result, "prov:activity": call}
        doc["wasAssociatedWith"][f"_:as{e.seq}"] = {"prov:activity": call, "prov:agent": server}
        doc["wasAssociatedWith"][f"_:ap{e.seq}"] = {"prov:activity": call, "prov:agent": "provmcp:proxy"}
        doc["wasAttributedTo"][f"_:at{e.seq}"] = {"prov:entity": result, "prov:agent": server}

        if e.client:
            client = f"provmcp:client/{_slug(e.client)}"
            ag.setdefault(client, {
                "prov:type": {"$": "prov:SoftwareAgent", "type": "prov:QUALIFIED_NAME"},
                "provmcp:client": e.client,
            })
            doc["wasAssociatedWith"][f"_:ac{e.seq}"] = {"prov:activity": call, "prov:agent": client}

        if e.source_release:
            rel = f"provmcp:release/{_slug(e.source_release)}"
            ent.setdefault(rel, {"provmcp:release": e.source_release,
                                 "provmcp:server_id": e.server_id})
            doc["used"][f"_:u{e.seq}r"] = {"prov:activity": call, "prov:entity": rel}

        if prev_call is not None:
            doc["wasInformedBy"][f"_:i{e.seq}"] = {"prov:informed": call, "prov:informant": prev_call}
        prev_call = call

    return {k: v for k, v in doc.items() if v}  # drop empty relation maps


def write_bundle(ledger: Ledger, out_dir: Path) -> Path:
    out_dir = Path(out_dir)
    if out_dir.exists() and any(out_dir.iterdir()):
        raise FileExistsError(f"{out_dir} exists and is not empty; refusing to overwrite a bundle")
    out_dir.mkdir(parents=True, exist_ok=True)

    entries = list(ledger.entries())
    if not ledger.path.exists():
        ledger.path.touch()
    shutil.copyfile(ledger.path, out_dir / LEDGER_NAME)

    prov_bytes = json.dumps(to_prov_json(entries), indent=2, ensure_ascii=False).encode("utf-8")
    (out_dir / PROV_NAME).write_bytes(prov_bytes)

    pub_pem: bytes | None = None
    if ledger._key is not None:
        pub_pem = public_pem(ledger._key.public_key())
        (out_dir / PUBKEY_NAME).write_bytes(pub_pem)

    n, head = ledger.head()
    manifest = {
        "provmcp_version": __version__,
        "exported_at": datetime.now(UTC).isoformat(),
        "entry_count": n,
        "head_hash": head,
        "signed": pub_pem is not None,
        "files": {
            LEDGER_NAME: sha256_hex((out_dir / LEDGER_NAME).read_bytes()),
            PROV_NAME: sha256_hex(prov_bytes),
            **({PUBKEY_NAME: sha256_hex(pub_pem)} if pub_pem else {}),
        },
    }
    (out_dir / MANIFEST_NAME).write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return out_dir


def verify_bundle(bundle_dir: Path) -> list[str]:
    """Check a bundle from a clean checkout: file hashes match the manifest, the
    ledger chain is intact, signatures verify against the bundled public key."""
    bundle_dir = Path(bundle_dir)
    problems: list[str] = []
    try:
        manifest = json.loads((bundle_dir / MANIFEST_NAME).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return [f"no {MANIFEST_NAME} in {bundle_dir}"]

    for name, expected in manifest.get("files", {}).items():
        p = bundle_dir / name
        if not p.exists():
            problems.append(f"{name}: missing")
        elif sha256_hex(p.read_bytes()) != expected:
            problems.append(f"{name}: hash does not match manifest")

    ledger = Ledger(bundle_dir / LEDGER_NAME)
    n, head = ledger.head()
    if n != manifest.get("entry_count"):
        problems.append(f"entry count {n} != manifest {manifest.get('entry_count')}")
    if head != manifest.get("head_hash"):
        problems.append("chain head does not match manifest")

    pub = None
    if manifest.get("signed"):
        try:
            pub = load_public(bundle_dir / PUBKEY_NAME)
        except Exception as exc:
            problems.append(f"{PUBKEY_NAME}: unreadable ({exc})")
    problems.extend(ledger.verify(pub))
    return problems
