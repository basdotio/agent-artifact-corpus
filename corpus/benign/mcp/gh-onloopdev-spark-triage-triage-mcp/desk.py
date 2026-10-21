"""Triage desk operations. Plain functions so they can be tested without MCP.

The model never sets a colour. It registers a card, asks for the TEWS, and
names discriminators with a quote from the card. This module computes the
colour from those inputs and stores it as *pending* until a named clinician
confirms or overrides it.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone

from . import sats, store


class DeskError(ValueError):
    """An error the agent is expected to read and recover from."""


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").lower()).strip()


def register_patient(card: dict) -> dict:
    pid = str(card.get("patient_id") or "").strip()
    if not pid:
        raise DeskError("card has no patient_id")
    age = card.get("age_years")
    if age is None:
        raise DeskError("card has no age_years; the adult scale cannot be chosen without an age")
    vitals = card.get("vitals") or {}
    existing = store.get_patient(pid)
    if existing is None:
        with store.connect() as c:
            c.execute(
                "INSERT INTO patients (id, card_json, arrived_at, registered_at) VALUES (?,?,?,?)",
                (pid, json.dumps(card), card.get("arrived_at") or store.now(), store.now()),
            )
        store.add_vitals(pid, vitals, source=f"intake card {pid}")
    result = {
        "patient_id": pid,
        "already_registered": existing is not None,
        "scale": "adult" if float(age) >= sats.ADULT_MIN_AGE else "none",
        "missing_vitals": sats.missing_vitals(vitals),
        "vital_problems": sats.validate_vitals(vitals),
    }
    if result["scale"] == "none":
        result["next_step"] = (
            f"Patient is {age} years old. The adult SATS chart applies from age {sats.ADULT_MIN_AGE}. "
            "Do not score. Raise a nurse_review flag."
        )
    elif result["vital_problems"]:
        result["next_step"] = "Vitals incomplete or implausible. Do not score. Raise a missing_vitals flag."
    else:
        result["next_step"] = "Call compute_tews, then list_discriminators, then propose_priority."
    return result


def _require_patient(pid: str) -> dict:
    p = store.get_patient(pid)
    if p is None:
        raise DeskError(f"unknown patient_id {pid}; call register_patient first")
    return p


def compute_tews(patient_id: str) -> dict:
    p = _require_patient(patient_id)
    if float(p["card"]["age_years"]) < sats.ADULT_MIN_AGE:
        raise DeskError("adult TEWS does not apply to this patient's age; raise a nurse_review flag")
    v = store.latest_vitals(patient_id)
    try:
        result = sats.tews(v["vitals"])
    except ValueError as e:
        raise DeskError(f"cannot score: {e}. Raise a missing_vitals flag.") from e
    result["vitals_entry"] = {"id": v["id"], "source": v["source"], "recorded_at": v["recorded_at"]}
    result["measured_discriminators"] = sats.measured_discriminators(v["vitals"])
    return result


def list_discriminators() -> dict:
    return {
        "ruleset": sats.RULESET,
        "how_to_use": (
            "Pick only discriminators the card supports. For each, pass evidence_quote: an exact "
            "phrase copied from the card's complaint or nurse_notes. Measured ones (glucose) are "
            "added by the server automatically; do not pass them."
        ),
        # One short line each keeps this small enough for a 3B model's context window.
        "discriminators": [
            f"{k} ({d['colour']}): {d['label']}"
            for k, d in sats.DISCRIMINATORS.items() if d["kind"] == "symptom"
        ],
    }


def _card_text(card: dict) -> str:
    return _norm(" ".join(str(card.get(k) or "") for k in ("complaint", "nurse_notes")))


def _build_sources(t: dict, chosen: list[dict]) -> list[dict]:
    sources = [{
        "type": "tews_total", "tews": t["tews"], "colour": t["colour"], "rule_id": "SATS-TEWS-BANDS",
        "entry": t["vitals_entry"]["source"], "recorded_at": t["vitals_entry"]["recorded_at"],
    }]
    for comp in t["components"]:
        if comp["points"]:
            sources.append({
                "type": "vital", "param": comp["param"], "value": comp["value"],
                "points": comp["points"], "rule_id": comp["rule_id"],
                "entry": t["vitals_entry"]["source"],
            })
    for d in t["measured_discriminators"]:
        sources.append({"type": "measured_discriminator", **d})
    sources.extend(chosen)
    return sources


def propose_priority(patient_id: str, discriminators: list[dict] | None, rationale: str) -> dict:
    p = _require_patient(patient_id)
    if store.pending_for(patient_id):
        raise DeskError("a proposal is already awaiting nurse confirmation for this patient")
    t = compute_tews(patient_id)
    text = _card_text(p["card"])
    chosen, errors = [], []
    for item in discriminators or []:
        code = str(item.get("code", "")).upper()
        quote = str(item.get("evidence_quote", ""))
        d = sats.DISCRIMINATORS.get(code)
        if d is None:
            errors.append(f"{code}: not a SATS discriminator code (see list_discriminators)")
        elif d["kind"] != "symptom":
            errors.append(f"{code}: measured discriminator, added by the server; remove it")
        elif len(_norm(quote)) < 3 or _norm(quote) not in text:
            errors.append(f"{code}: evidence_quote {quote!r} is not an exact phrase from the card")
        else:
            chosen.append({"type": "symptom_discriminator", "code": code, "colour": d["colour"],
                           "rule_id": d["rule_id"], "evidence": quote,
                           "evidence_source": f"intake card {patient_id}"})
    if errors:
        # Unsourced flags are worse than no flag: reject the whole proposal.
        raise DeskError("proposal rejected, nothing stored: " + " | ".join(errors))
    colours = [t["colour"]] + [d["colour"] for d in t["measured_discriminators"]] + [d["colour"] for d in chosen]
    colour = sats.most_urgent(colours)
    sources = _build_sources(t, chosen)
    with store.connect() as c:
        cur = c.execute(
            "INSERT INTO proposals (patient_id, kind, colour, tews, sources_json, rationale, created_at) "
            "VALUES (?,?,?,?,?,?,?)",
            (patient_id, "initial" if not store.current_confirmed(patient_id) else "retriage",
             colour, t["tews"], json.dumps(sources), rationale, store.now()),
        )
        pid = cur.lastrowid
    return {
        "proposal_id": pid, "patient_id": patient_id, "proposed_colour": colour,
        "tews": t["tews"], "tews_colour": t["colour"],
        "target_minutes": sats.TARGET_MINUTES[colour], "sources": sources,
        "status": "PENDING - a triage nurse must confirm or override before this affects the queue",
    }


FLAG_KINDS = {"missing_vitals", "deterioration", "nurse_review"}


def raise_recheck_flag(patient_id: str, kind: str, reason: str, new_vitals: dict | None = None) -> dict:
    _require_patient(patient_id)
    if kind not in FLAG_KINDS:
        raise DeskError(f"kind must be one of {sorted(FLAG_KINDS)}")
    if len(_norm(reason)) < 5:
        raise DeskError("reason is required and must say what changed or what is missing")
    result: dict = {"patient_id": patient_id, "kind": kind}
    if not new_vitals:
        same = [f for f in store.open_flags(patient_id) if f["kind"] == kind]
        if same:  # idempotent: a second sweep must not stack duplicate flags on the nurse
            return {**result, "flag_id": same[0]["id"], "duplicate": True,
                    "status": "ALREADY OPEN - the nurse already has this flag; nothing new was created"}
    proposal_id = None
    if new_vitals:
        merged = {**(store.latest_vitals(patient_id) or {}).get("vitals", {}), **new_vitals}
        problems = sats.validate_vitals(merged)
        if problems:
            raise DeskError("re-check vitals cannot be scored: " + "; ".join(problems))
        store.add_vitals(patient_id, merged, source=f"re-check entry {store.now()}")
        t = sats.tews(merged)
        conf = store.current_confirmed(patient_id)
        current = conf["final_colour"] if conf else None
        result.update({"new_tews": t["tews"], "new_tews_colour": t["colour"], "current_confirmed": current})
        if current is None or sats.RANK[t["colour"]] > sats.RANK[current]:
            if not store.pending_for(patient_id):
                prop = propose_priority(patient_id, [], f"Re-check: {reason}")
                proposal_id = prop["proposal_id"]
                result["retriage_proposal"] = prop
    with store.connect() as c:
        cur = c.execute(
            "INSERT INTO flags (patient_id, kind, reason, created_at, proposal_id) VALUES (?,?,?,?,?)",
            (patient_id, kind, reason, store.now(), proposal_id),
        )
        result["flag_id"] = cur.lastrowid
    result["status"] = "OPEN - shown to the triage nurse for a second look; the agent takes no further action"
    return result


def _minutes_since(iso: str) -> float:
    try:
        t = datetime.fromisoformat(iso)
        if t.tzinfo is None:
            t = t.replace(tzinfo=timezone.utc)
        return round((datetime.now(timezone.utc) - t).total_seconds() / 60, 1)
    except ValueError:
        return 0.0


def get_queue() -> dict:
    with store.connect() as c:  # patients already sent to a bay have left the queue
        patients = [dict(r) for r in c.execute("SELECT * FROM patients WHERE seen_at IS NULL").fetchall()]
    confirmed, awaiting, untriaged = [], [], []
    for p in patients:
        pid = p["id"]
        waited = _minutes_since(p["arrived_at"])
        conf = store.current_confirmed(pid)
        pend = store.pending_for(pid)
        flags = store.open_flags(pid)
        row = {"patient_id": pid, "arrived_at": p["arrived_at"], "waited_min": waited,
               "open_flags": [{"id": f["id"], "kind": f["kind"], "reason": f["reason"]} for f in flags]}
        if pend:
            awaiting.append({**row, "proposal_id": pend[0]["id"], "proposed_colour": pend[0]["colour"]})
        if conf:
            target = sats.TARGET_MINUTES[conf["final_colour"]]
            confirmed.append({**row, "colour": conf["final_colour"], "confirmed_by": conf["clinician"],
                              "target_min": target, "overdue": waited > target})
        elif not pend:
            untriaged.append(row)
    confirmed.sort(key=lambda r: (-sats.RANK[r["colour"]], r["arrived_at"]))
    for i, r in enumerate(confirmed, 1):
        r["position"] = i
    untriaged.sort(key=lambda r: r["arrived_at"])
    return {"queue": confirmed, "awaiting_nurse": awaiting, "untriaged": untriaged}


def record_clinician_decision(proposal_id: int, clinician_name: str, decision: str,
                              override_colour: str | None = None, note: str = "") -> dict:
    """The human gate. Not exposed to the model's toolset; called by the desk UI."""
    if len(_norm(clinician_name)) < 2:
        raise DeskError("a named clinician is required")
    if decision not in {"approve", "override", "reject"}:
        raise DeskError("decision must be approve, override or reject")
    with store.connect() as c:
        row = c.execute("SELECT * FROM proposals WHERE id=?", (proposal_id,)).fetchone()
        if row is None:
            raise DeskError(f"no proposal {proposal_id}")
        if row["status"] != "pending":
            raise DeskError(f"proposal {proposal_id} is already {row['status']}")
        if decision != "reject" and blind_mode() and not store.blind_call(proposal_id):
            raise DeskError("blind mode is on: record your own priority for this patient before deciding")
        if decision == "override":
            if override_colour not in sats.RANK:
                raise DeskError("override needs override_colour: red, orange, yellow or green")
            if len(_norm(note)) < 3:
                raise DeskError("an override needs a note (senior clinician discretion)")
            final, status = override_colour, "overridden"
        elif decision == "approve":
            final, status = row["colour"], "approved"
        else:
            final, status = None, "rejected"
        c.execute(
            "UPDATE proposals SET status=?, decided_at=?, clinician=?, final_colour=?, note=? WHERE id=?",
            (status, store.now(), clinician_name, final, note, proposal_id),
        )
        c.execute("UPDATE flags SET status='closed', closed_at=?, closed_by=? WHERE proposal_id=? AND status='open'",
                  (store.now(), clinician_name, proposal_id))
        if final:  # a confirmed priority resolves an earlier "vitals missing" flag
            c.execute("UPDATE flags SET status='closed', closed_at=?, closed_by=? "
                      "WHERE patient_id=? AND kind='missing_vitals' AND status='open'",
                      (store.now(), clinician_name, row["patient_id"]))
    return {"proposal_id": proposal_id, "patient_id": row["patient_id"], "status": status,
            "final_colour": final, "clinician": clinician_name}


def close_flag(flag_id: int, clinician_name: str, note: str) -> dict:
    if len(_norm(clinician_name)) < 2:
        raise DeskError("a named clinician is required")
    with store.connect() as c:
        row = c.execute("SELECT * FROM flags WHERE id=?", (flag_id,)).fetchone()
        if row is None:
            raise DeskError(f"no flag {flag_id}")
        if row["status"] != "open":
            raise DeskError(f"flag {flag_id} is already closed")
        c.execute("UPDATE flags SET status='closed', closed_at=?, closed_by=? WHERE id=?",
                  (store.now(), clinician_name, flag_id))
    return {"flag_id": flag_id, "patient_id": row["patient_id"], "closed_by": clinician_name, "note": note}


def nurse_set_priority(patient_id: str, clinician_name: str, colour: str, note: str) -> dict:
    """SATS senior-clinician discretion: the nurse sets or changes a priority herself,
    for a confirmed patient, an untriaged one, or one the adult scale does not cover."""
    _require_patient(patient_id)
    if len(_norm(clinician_name)) < 2:
        raise DeskError("a named clinician is required")
    if colour not in sats.RANK:
        raise DeskError("colour must be red, orange, yellow or green")
    if len(_norm(note)) < 3:
        raise DeskError("say why, in a few words")
    if store.pending_for(patient_id):
        raise DeskError("decide the agent's pending proposal for this patient first")
    try:
        t = compute_tews(patient_id)["tews"]
    except DeskError:
        t = -1  # not scorable on the adult scale (child, missing vitals)
    previous = (store.current_confirmed(patient_id) or {}).get("final_colour")
    source = [{"type": "nurse", "rule_id": "SATS-NURSE-DISCRETION", "colour": colour,
               "evidence": note, "evidence_source": f"nurse {clinician_name}"}]
    now = store.now()
    with store.connect() as c:
        cur = c.execute(
            "INSERT INTO proposals (patient_id, kind, colour, tews, sources_json, rationale, status, created_at, "
            "decided_at, clinician, final_colour, note) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (patient_id, "nurse", colour, t, json.dumps(source), "set by nurse", "nurse_set", now, now,
             clinician_name, colour, note))
        c.execute("UPDATE flags SET status='closed', closed_at=?, closed_by=? WHERE patient_id=? AND status='open'",
                  (now, clinician_name, patient_id))
    return {"proposal_id": cur.lastrowid, "patient_id": patient_id, "status": "nurse_set",
            "final_colour": colour, "previous_colour": previous, "clinician": clinician_name}


def mark_seen(patient_id: str, clinician_name: str) -> dict:
    """The nurse sends a confirmed patient to a bay; they leave the queue."""
    p = _require_patient(patient_id)
    if len(_norm(clinician_name)) < 2:
        raise DeskError("a named clinician is required")
    conf = store.current_confirmed(patient_id)
    if not conf:
        raise DeskError("confirm a priority before sending the patient to a bay")
    with store.connect() as c:
        row = c.execute("SELECT seen_at FROM patients WHERE id=?", (patient_id,)).fetchone()
        if row["seen_at"]:
            raise DeskError("this patient has already been sent to a bay")
        now = store.now()
        c.execute("UPDATE patients SET seen_at=?, seen_by=? WHERE id=?", (now, clinician_name, patient_id))
        c.execute("UPDATE flags SET status='closed', closed_at=?, closed_by=? WHERE patient_id=? AND status='open'",
                  (now, clinician_name, patient_id))
    waited = _minutes_between(p["arrived_at"], now)
    target = sats.TARGET_MINUTES[conf["final_colour"]]
    return {"patient_id": patient_id, "colour": conf["final_colour"], "waited_min": waited,
            "target_min": target, "within_target": waited <= target, "seen_by": clinician_name}


def _minutes_between(a: str, b: str) -> float:
    try:
        ta, tb = datetime.fromisoformat(a), datetime.fromisoformat(b)
        ta = ta if ta.tzinfo else ta.replace(tzinfo=timezone.utc)
        tb = tb if tb.tzinfo else tb.replace(tzinfo=timezone.utc)
        return round((tb - ta).total_seconds() / 60, 1)
    except (TypeError, ValueError):
        return 0.0


def _median(xs: list[float]) -> float | None:
    xs = sorted(xs)
    if not xs:
        return None
    m = len(xs) // 2
    return xs[m] if len(xs) % 2 else round((xs[m - 1] + xs[m]) / 2, 1)


def desk_metrics() -> dict:
    """The brief's own measures: time to a confirmed priority, and who was seen within the SATS target."""
    with store.connect() as c:
        patients = [dict(r) for r in c.execute("SELECT * FROM patients").fetchall()]
        decided = [dict(r) for r in c.execute(
            "SELECT patient_id, colour, final_colour, status, decided_at FROM proposals "
            "WHERE status IN ('approved','overridden','nurse_set') ORDER BY decided_at").fetchall()]
    first = {}
    for d in decided:
        first.setdefault(d["patient_id"], d["decided_at"])
    to_priority = [_minutes_between(p["arrived_at"], first[p["id"]]) for p in patients if p["id"] in first]
    seen = []
    for p in patients:
        if not p.get("seen_at"):
            continue
        conf = store.current_confirmed(p["id"])
        if conf:
            w = _minutes_between(p["arrived_at"], p["seen_at"])
            seen.append(w <= sats.TARGET_MINUTES[conf["final_colour"]])
    lowered = sum(1 for d in decided if d["status"] == "overridden"
                  and sats.RANK[d["final_colour"]] < sats.RANK[d["colour"]])
    raised = sum(1 for d in decided if d["status"] == "overridden"
                 and sats.RANK[d["final_colour"]] > sats.RANK[d["colour"]])
    return {"registered": len(patients), "with_priority": len(first),
            "median_min_to_priority": _median(to_priority),
            "seen": len(seen), "seen_within_target": sum(seen),
            "nurse_lowered": lowered, "nurse_raised": raised}


# --- Blind mode -------------------------------------------------------------
# The nurse records her own priority before the agent's proposal is shown, so
# her confirmation is an independent check and not an anchored rubber stamp.

def blind_mode() -> bool:
    return store.get_setting("blind_mode", "0") == "1"


def set_blind_mode(on: bool, clinician_name: str) -> dict:
    if len(_norm(clinician_name)) < 2:
        raise DeskError("a named clinician is required")
    store.set_setting("blind_mode", "1" if on else "0")
    return {"blind_mode": on, "set_by": clinician_name}


def record_blind_call(proposal_id: int, clinician_name: str, colour: str) -> dict:
    if len(_norm(clinician_name)) < 2:
        raise DeskError("a named clinician is required")
    if colour not in sats.RANK:
        raise DeskError("colour must be red, orange, yellow or green")
    with store.connect() as c:
        row = c.execute("SELECT * FROM proposals WHERE id=?", (proposal_id,)).fetchone()
        if row is None:
            raise DeskError(f"no proposal {proposal_id}")
        if row["status"] != "pending":
            raise DeskError("the blind call must be recorded before the proposal is decided")
        if store.blind_call(proposal_id):
            raise DeskError("a blind call is already recorded for this proposal and cannot be changed")
        c.execute("INSERT INTO blind_calls (proposal_id, patient_id, clinician, colour, recorded_at) "
                  "VALUES (?,?,?,?,?)", (proposal_id, row["patient_id"], clinician_name, colour, store.now()))
    agent = row["colour"]
    gap = sats.RANK[agent] - sats.RANK[colour]
    return {"proposal_id": proposal_id, "patient_id": row["patient_id"], "nurse_colour": colour,
            "agent_colour": agent, "agree": gap == 0,
            "agent_was": "same" if gap == 0 else ("more urgent" if gap > 0 else "less urgent")}


def agreement_stats() -> dict:
    with store.connect() as c:
        rows = c.execute(
            "SELECT b.patient_id, b.colour AS nurse, p.colour AS agent, b.clinician, p.final_colour, p.status "
            "FROM blind_calls b JOIN proposals p ON p.id = b.proposal_id ORDER BY b.recorded_at"
        ).fetchall()
        overrides = c.execute("SELECT COUNT(*) FROM proposals WHERE status='overridden'").fetchone()[0]
        decided = c.execute("SELECT COUNT(*) FROM proposals WHERE status IN ('approved','overridden','rejected')").fetchone()[0]
    pairs = [dict(r) for r in rows]
    more = [p for p in pairs if sats.RANK[p["agent"]] > sats.RANK[p["nurse"]]]
    less = [p for p in pairs if sats.RANK[p["agent"]] < sats.RANK[p["nurse"]]]
    return {
        "blind_calls": len(pairs),
        "agree": len(pairs) - len(more) - len(less),
        "agent_more_urgent": len(more),
        "agent_less_urgent": len(less),
        "disagreements": [{"patient_id": p["patient_id"], "nurse": p["nurse"], "agent": p["agent"],
                           "final": p["final_colour"], "clinician": p["clinician"]} for p in more + less],
        "decided": decided, "overridden": overrides,
    }


# --- Overdue sweep ------------------------------------------------------------

SWEEP_COOLDOWN_MIN = 30


def overdue_unflagged(cooldown_min: int = SWEEP_COOLDOWN_MIN) -> list[dict]:
    """Confirmed patients past their SATS target with no open nurse_review or
    deterioration flag, and none closed by a nurse in the last cooldown_min."""
    out = []
    with store.connect() as c:
        recent = {r["patient_id"] for r in c.execute(
            "SELECT patient_id, closed_at FROM flags WHERE status='closed' AND closed_at IS NOT NULL "
            "AND kind IN ('nurse_review','deterioration')").fetchall()
            if _minutes_since(r["closed_at"]) < cooldown_min}
    for r in get_queue()["queue"]:
        if not r["overdue"] or r["patient_id"] in recent:
            continue
        if any(f["kind"] in ("nurse_review", "deterioration") for f in r["open_flags"]):
            continue
        out.append({"patient_id": r["patient_id"], "colour": r["colour"], "waited_min": r["waited_min"],
                    "target_min": r["target_min"]})
    return out


# --- Audit timeline -----------------------------------------------------------

def _j(text: str):
    try:
        return json.loads(text)
    except (TypeError, ValueError):
        return text


def _say(tool: str, actor: str, inp, out, ok: bool) -> str:
    who = actor.split(":", 1)[1] if actor.startswith("clinician:") else ("Agent" if actor == "agent" else actor)
    out = out if isinstance(out, dict) else {"text": out}
    inp = inp if isinstance(inp, dict) else {}
    if not ok:
        return f"{who}: {tool.replace('_', ' ')} failed. {out.get('error', '')}".strip()
    if tool.startswith("filesystem."):
        return f"{who} read the intake card file"
    if tool == "register_patient":
        miss = out.get("missing_vitals") or []
        return f"{who} registered the card ({'adult scale' if out.get('scale') == 'adult' else 'adult scale does not apply'})" + (
            f", missing: {', '.join(miss)}" if miss else "")
    if tool == "compute_tews":
        return f"{who} computed the early warning score: {out.get('tews')} ({out.get('colour')})"
    if tool == "list_discriminators":
        return f"{who} looked up the SATS discriminator list"
    if tool == "propose_priority":
        cited = [f"{s['code'].replace('_', ' ').lower()} \"{s['evidence']}\"" for s in out.get("sources", [])
                 if s.get("type") == "symptom_discriminator"]
        return f"{who} proposed {out.get('proposed_colour')} (score {out.get('tews')})" + (
            f", citing {'; '.join(cited)}" if cited else ", from vitals only")
    if tool == "raise_recheck_flag":
        if out.get("duplicate"):
            return f"{who} checked: a {inp.get('kind', '').replace('_', ' ')} flag was already open"
        extra = f", new score {out['new_tews']} ({out['new_tews_colour']})" if "new_tews" in out else ""
        return f"{who} raised a {inp.get('kind', '').replace('_', ' ')} flag: {inp.get('reason', '')}{extra}"
    if tool == "get_queue":
        return f"{who} checked the queue"
    if tool == "record_blind_call":
        return f"{who} made a blind call: {out.get('nurse_colour')} (agent had {out.get('agent_colour')})"
    if tool == "record_clinician_decision":
        st = out.get("status")
        if st == "approved":
            return f"{who} approved {out.get('final_colour')}"
        if st == "overridden":
            return f"{who} changed the priority to {out.get('final_colour')}: {inp.get('note', '')}"
        return f"{who} rejected the proposal: {inp.get('note', '')}"
    if tool == "nurse_set_priority":
        prev = out.get("previous_colour")
        return f"{who} set the priority to {out.get('final_colour')}" + (f" (was {prev})" if prev else "") + f": {inp.get('note', '')}"
    if tool == "mark_seen":
        return (f"{who} sent the patient to a bay after {out.get('waited_min')} min "
                f"({'within' if out.get('within_target') else 'past'} the {out.get('target_min')}-min target)")
    if tool == "close_flag":
        return f"{who} marked the flag as handled: {inp.get('note', '')}"
    return f"{who}: {tool.replace('_', ' ')}"


def audit_timeline(patient_id: str) -> list[dict]:
    rows = store.audit_for(patient_id)
    return [{"ts": r["ts"], "actor": r["actor"], "tool": r["tool"], "ok": bool(r["ok"]),
             "summary": _say(r["tool"], r["actor"], _j(r["input_json"]), _j(r["output_json"]), bool(r["ok"]))}
            for r in rows]
