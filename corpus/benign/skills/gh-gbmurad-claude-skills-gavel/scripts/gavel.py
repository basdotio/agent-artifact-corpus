#!/usr/bin/env python3
"""gavel.py: the parts of a Gavel case that should never be left to judgment. Standard library only.

    python3 gavel.py new "<motion>" [setup flags]  open a case folder with its setup; print the path and the plan
    python3 gavel.py settings [--dir DIR]          the setup saved from the last case (for "use my last settings")
    python3 gavel.py pretrial CASE                 check the judge's pretrial.json against the setup
    python3 gavel.py record CASE [--seed N]       assemble record.md for the jury (checks word limits)
    python3 gavel.py tally CASE [--seed N]        check every ballot, write tally.json and jury-packet.md
    python3 gavel.py close CASE                   check ruling.md and add a line to the docket
    python3 gavel.py list [--dir DIR]             past cases and their verdicts

Exit codes: 0 ok, 1 the case needs a fix (each problem is printed on its own line), 2 bad usage.
"""
import argparse
import datetime
import json
import os
import random
import re
import statistics
import sys

VERDICTS = ["adopt", "adopt_with_conditions", "redesign", "reject", "insufficient"]
LABELS = {"adopt": "Adopt", "adopt_with_conditions": "Adopt with conditions", "redesign": "Redesign",
          "reject": "Reject", "insufficient": "Insufficient evidence"}
SIDE = {"adopt": "for", "adopt_with_conditions": "for", "redesign": "against", "reject": "against",
        "insufficient": "neither"}
CONFIDENCE = {"low": 0.5, "medium": 1.0, "high": 1.5}
GRADES = {"verified", "plausible", "assumption"}
FAVORS = {"for", "against", "neither"}
STANDARDS = {"preponderance", "clear_and_convincing"}
CAPS = {"opening-for.md": 500, "opening-against.md": 500, "rebuttal-for.md": 250, "rebuttal-against.md": 250}
SLACK = 1.10  # a speech may run 10% over its cap before the record refuses it
MOVE = 15     # probability points a juror may drift in round 2 without giving a reason
RULING_SECTIONS = ["## Ruling", "## From my prior", "## Decisive evidence", "## Dissent", "## Conditions",
                   "## What would flip this", "## What to watch", "## The vote"]
MODELS = ("opus", "fable", "sonnet", "haiku", "inherit")  # what the Agent tool accepts; inherit = this chat's model
LEVELS = ("fair", "tough", "ruthless")                   # how hard the prosecution pushes
ROLES = ("judge", "defense", "prosecution", "jury")
DEFAULT_SETUP = {"opposition": "tough", "jurors": 5, "seats": None, "quick": False, "deliberate": False,
                 "research": False,
                 "models": {"judge": "opus", "defense": "sonnet", "prosecution": "sonnet", "jury": "sonnet"}}


class CaseError(Exception):
    """A problem in the case files that a role must fix. Carries every problem found, not just the first."""

    def __init__(self, problems):
        self.problems = problems if isinstance(problems, list) else [problems]
        super().__init__("; ".join(self.problems))


# ---------- helpers ----------

def slug(text, limit=48):
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    if len(s) > limit:
        s = s[:limit + 1]
        s = s[:s.rfind("-")] if "-" in s else s[:limit]  # cut at a word boundary, never mid word
    return s or "case"


def words(text):
    return len(re.findall(r"\S+", text))


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def load_json(path):
    try:
        return json.loads(read(path))
    except FileNotFoundError:
        raise CaseError(f"{os.path.basename(path)}: missing")
    except json.JSONDecodeError as e:
        raise CaseError(f"{os.path.basename(path)}: not valid JSON ({e.msg}, line {e.lineno})")


def seat_file(seat):
    return slug(seat, 32) + ".json"


# ---------- setup ----------

def parse_seats(text):
    """'engineer, designer: opus, a retired airline pilot' -> [{'seat': ..., 'model': ...}]; premortem always seated."""
    seats = []
    for item in (t.strip() for t in text.split(",")):
        if not item:
            continue
        name, model = item, None
        if ":" in item:
            head, tail = item.rsplit(":", 1)
            if tail.strip().lower() in MODELS:
                name, model = head.strip(), tail.strip().lower()
        seat = {"seat": name}
        if model:
            seat["model"] = model
        seats.append(seat)
    if not any(s["seat"].lower() == "premortem" for s in seats):
        seats.append({"seat": "premortem"})
    return seats


def build_setup(motion, saved=None, **choices):
    """Merge defaults, the saved settings and this case's choices; check every value; return the setup."""
    setup = json.loads(json.dumps(DEFAULT_SETUP))
    for layer in (saved or {}, {k: v for k, v in choices.items() if v is not None}):
        for key, value in layer.items():
            if key == "models":
                setup["models"].update({r: m for r, m in value.items() if m})
            elif key in setup:
                setup[key] = value
    setup["motion"] = motion.strip()
    if setup["quick"] and not setup["seats"]:
        setup["jurors"] = 3
    bad = []
    if not setup["motion"]:
        bad.append("setup: the question is empty")
    if setup["opposition"] not in LEVELS:
        bad.append(f"setup: opposition must be one of {list(LEVELS)}")
    for role in ROLES:
        if setup["models"].get(role) not in MODELS:
            bad.append(f"setup: model for {role} must be one of {list(MODELS)}")
    if setup["seats"]:
        names = [s["seat"] for s in setup["seats"]]
        if not 3 <= len(names) <= 8:
            bad.append(f"setup: the jury needs 3 to 8 seats including the premortem, got {len(names)}")
        if len({seat_file(n) for n in names}) != len(names):
            bad.append("setup: two seats share a name")
        bad += [f"setup: model for seat {s['seat']} must be one of {list(MODELS)}"
                for s in setup["seats"] if s.get("model", "sonnet") not in MODELS]
        setup["jurors"] = len(names)
    elif not isinstance(setup["jurors"], int) or not 3 <= setup["jurors"] <= 8:
        bad.append("setup: jurors must be a whole number from 3 to 8")
    if bad:
        raise CaseError(bad)
    return setup


def load_setup(case):
    path = os.path.join(case, "setup.json")
    return load_json(path) if os.path.exists(path) else None


def seat_model(setup, seat):
    for s in (setup or {}).get("seats") or []:
        if s["seat"].lower() == seat.lower() and s.get("model"):
            return s["model"]
    return (setup or DEFAULT_SETUP)["models"]["jury"]


def open_case(base, setup):
    day = datetime.date.today().isoformat()
    case = os.path.join(base, f"{day}-{slug(setup['motion'])}")
    k = 2
    while os.path.exists(case):
        case = os.path.join(base, f"{day}-{slug(setup['motion'])}-{k}")
        k += 1
    os.makedirs(os.path.join(case, "ballots", "round1"))
    write(os.path.join(case, "setup.json"), json.dumps(setup, indent=2) + "\n")
    write(os.path.join(case, "case.md"),
          f"# Case\n\n**Motion.** {setup['motion']}\n\n## Facts\n\n## Constraints\n\n## Stakes\n")
    remembered = {k: v for k, v in setup.items() if k != "motion"}
    write(os.path.join(base, "settings.json"), json.dumps(remembered, indent=2) + "\n")
    return case


def describe(setup):
    m = setup["models"]
    jury = (", ".join(f"{s['seat']} ({seat_model(setup, s['seat'])})" for s in setup["seats"])
            if setup["seats"] else f"{setup['jurors']} seats picked by the judge ({m['jury']})")
    flags = [f for f in ("quick", "deliberate", "research") if setup.get(f)]
    return (f"judge {m['judge']} · defense {m['defense']} · prosecution {m['prosecution']} "
            f"({setup['opposition']}) · jury: {jury}" + (f" · {', '.join(flags)}" if flags else ""))


# ---------- pretrial ----------

def check_pretrial(case):
    p = load_json(os.path.join(case, "pretrial.json"))
    setup = load_setup(case)
    bad = []
    if not str(p.get("motion", "")).strip():
        bad.append("pretrial.json: motion is empty")
    if p.get("standard") not in STANDARDS:
        bad.append(f"pretrial.json: standard must be one of {sorted(STANDARDS)}")
    hyps = p.get("hypotheses", [])
    if not isinstance(hyps, list) or not 3 <= len(hyps) <= 5:
        bad.append("pretrial.json: hypotheses must be a list of 3 to 5")
    elif not all(isinstance(h, dict) and h.get("id") and str(h.get("text", "")).strip() for h in hyps):
        bad.append("pretrial.json: every hypothesis needs an id and text")
    crit = p.get("criteria", [])
    if not isinstance(crit, list) or not 2 <= len(crit) <= 4:
        bad.append("pretrial.json: criteria must be a list of 2 to 4")
    else:
        for c in crit:
            if not isinstance(c, dict) or not c.get("id") or not c.get("name"):
                bad.append("pretrial.json: every criterion needs an id and a name")
            elif c.get("weight") not in (1, 2, 3):
                bad.append(f"pretrial.json: criterion {c.get('id')} weight must be 1, 2 or 3")
    seats = p.get("seats", [])
    if not isinstance(seats, list) or not 3 <= len(seats) <= 8:
        bad.append("pretrial.json: seats must be a list of 3 to 8")
    else:
        names = [str(s.get("seat", "")).strip() for s in seats if isinstance(s, dict)]
        if len(names) != len(seats) or not all(names):
            bad.append("pretrial.json: every seat needs a name")
        if len({seat_file(n) for n in names}) != len(names):
            bad.append("pretrial.json: two seats share a name")
        if sum(1 for s in seats if isinstance(s, dict) and s.get("premortem") is True) != 1:
            bad.append("pretrial.json: exactly one seat must have \"premortem\": true")
        if any(isinstance(s, dict) and not str(s.get("question", "")).strip() for s in seats):
            bad.append("pretrial.json: every seat needs its own question")
        if setup and setup.get("seats"):
            want = sorted(s["seat"].lower() for s in setup["seats"])
            if sorted(n.lower() for n in names) != want:
                bad.append(f"pretrial.json: seats must be exactly the ones the user chose: {want}")
        elif setup and len(seats) != setup.get("jurors"):
            bad.append(f"pretrial.json: the user asked for {setup.get('jurors')} seats, got {len(seats)}")
    if bad:
        raise CaseError(bad)
    return p


# ---------- record ----------

def build_record(case, seed=None):
    p = check_pretrial(case)
    bad, speeches = [], {}
    for name, cap in CAPS.items():
        path = os.path.join(case, name)
        if not os.path.exists(path):
            if name.startswith("opening"):
                bad.append(f"{name}: missing")
            continue
        text = read(path).strip()
        n = words(text)
        if n > cap * SLACK:
            bad.append(f"{name}: {n} words, the limit is {cap}; ask that side to cut it")
        speeches[name] = (text, n)
    if ("rebuttal-for.md" in speeches) != ("rebuttal-against.md" in speeches):
        bad.append("rebuttals: one side filed a rebuttal and the other did not")
    if bad:
        raise CaseError(bad)

    rng = random.Random(seed)
    order = ["for", "against"]
    rng.shuffle(order)  # who speaks first in the record is random, so neither side owns the first word
    title = {"for": "For the motion", "against": "Against the motion"}
    out = [f"# The record\n\n**Motion.** {p['motion']}\n",
           f"**Standard of proof.** {p['standard'].replace('_', ' ')}. The burden is on the side for the motion.\n",
           "## Hypotheses the judge set before any argument\n"]
    out += [f"- **{h['id']}** {h['text']}" for h in p["hypotheses"]]
    out.append("\n## Criteria\n")
    out += [f"- **{c['id']}** {c['name']} (weight {c['weight']}): {c.get('question', '')}" for c in p["criteria"]]
    out.append("\n## The case file\n")
    out.append(read(os.path.join(case, "case.md")).strip() if os.path.exists(os.path.join(case, "case.md"))
               else "_No case file._")
    for stage in ("opening", "rebuttal"):
        if f"{stage}-for.md" not in speeches:
            continue
        out.append(f"\n## {stage.capitalize()}s\n")
        for side in order:
            text, n = speeches[f"{stage}-{side}.md"]
            out.append(f"### {title[side]} ({n} words)\n\n{text}\n")
    out.append(f"\n_Order of sides in this record: {', '.join(title[s] for s in order)} (random)._\n")
    write(os.path.join(case, "record.md"), "\n".join(out))
    return order


# ---------- ballots ----------

def check_ballot(b, seat, criteria, rnd, path):
    tag = os.path.relpath(path)
    bad = []
    if not isinstance(b, dict):
        return [f"{tag}: a ballot must be a JSON object"]
    if str(b.get("seat", "")).strip().lower() != seat.lower():
        bad.append(f"{tag}: seat is {b.get('seat')!r}, expected {seat!r}")
    if b.get("verdict") not in VERDICTS:
        bad.append(f"{tag}: verdict must be one of {VERDICTS}")
    prob = b.get("probability")
    if not isinstance(prob, (int, float)) or isinstance(prob, bool) or not 0 <= prob <= 100:
        bad.append(f"{tag}: probability must be a number from 0 to 100")
    if b.get("confidence") not in CONFIDENCE:
        bad.append(f"{tag}: confidence must be low, medium or high")
    findings = b.get("findings")
    if not isinstance(findings, list) or not 1 <= len(findings) <= 6:
        bad.append(f"{tag}: findings must be a list of 1 to 6")
    else:
        for i, f in enumerate(findings, 1):
            if not isinstance(f, dict) or not str(f.get("text", "")).strip():
                bad.append(f"{tag}: finding {i} needs text")
                continue
            if f.get("grade") not in GRADES:
                bad.append(f"{tag}: finding {i} grade must be verified, plausible or assumption")
            if f.get("favors") not in FAVORS:
                bad.append(f"{tag}: finding {i} favors must be for, against or neither")
            if not re.fullmatch(r"([FA]\d+|case)", str(f.get("claim", ""))):
                bad.append(f"{tag}: finding {i} claim must be a claim id like F2 or A1, or \"case\"")
    scores = b.get("scores")
    if not isinstance(scores, dict) or set(scores) != set(criteria):
        bad.append(f"{tag}: scores must give every criterion exactly once: {sorted(criteria)}")
    elif any(not isinstance(v, int) or isinstance(v, bool) or not 1 <= v <= 5 for v in scores.values()):
        bad.append(f"{tag}: every score must be a whole number from 1 to 5")
    for key in ("decisive", "change_my_mind"):
        if not str(b.get(key, "")).strip():
            bad.append(f"{tag}: {key} is empty")
    if b.get("verdict") == "adopt_with_conditions" and not b.get("conditions"):
        bad.append(f"{tag}: adopt_with_conditions needs at least one condition")
    if rnd == 2 and "flip_reason" not in b:
        bad.append(f"{tag}: round 2 ballots need flip_reason (empty string if nothing changed)")
    return bad


def load_round(case, seats, criteria, rnd):
    folder = os.path.join(case, "ballots", f"round{rnd}")
    ballots, bad = {}, []
    for s in seats:
        path = os.path.join(folder, seat_file(s))
        try:
            b = load_json(path)
        except CaseError as e:
            bad += [f"ballots/round{rnd}/{m}" for m in e.problems]
            continue
        bad += check_ballot(b, s, criteria, rnd, path)
        ballots[s] = b
    if bad:
        raise CaseError(bad)
    return ballots


# ---------- tally ----------

def majority_side(ballots):
    counts = {"for": 0, "against": 0, "neither": 0}
    for b in ballots.values():
        counts[SIDE[b["verdict"]]] += 1
    top = max(counts.values())
    leaders = [s for s, n in counts.items() if n == top]
    return (leaders[0] if len(leaders) == 1 else "tied"), counts


def audit_flips(r1, r2):
    """Round 2 is trusted only if the jurors who moved say what new point moved them."""
    side1, _ = majority_side(r1)
    flips = []
    for seat, b2 in r2.items():
        b1 = r1[seat]
        moved = b1["verdict"] != b2["verdict"] or abs(b1["probability"] - b2["probability"]) > MOVE
        if not moved:
            continue
        cited_before = {f["claim"] for f in b1["findings"]}
        reason = str(b2.get("flip_reason", "")).strip()
        new_point = bool(re.search(r"\bJuror [A-H]\b", reason)) or any(
            c not in cited_before for c in re.findall(r"\b[FA]\d+\b", reason))
        toward = SIDE[b2["verdict"]] == side1 and SIDE[b1["verdict"]] != side1
        flips.append({"seat": seat, "from": b1["verdict"], "to": b2["verdict"],
                      "probability": [b1["probability"], b2["probability"]],
                      "justified": bool(reason) and new_point, "toward_majority": toward, "reason": reason})
    unjustified = sum(1 for f in flips if not f["justified"])
    herding = bool(flips) and all(f["toward_majority"] for f in flips) and not any(f["justified"] for f in flips)
    if flips and (unjustified * 2 > len(flips) or herding):
        return flips, 1, (f"{unjustified} of {len(flips)} changes named no new point"
                          + ("; every change moved toward the round 1 majority" if herding else ""))
    return flips, 2, "round 2 changes cite new points" if flips else "nobody changed their vote"


def summarize(ballots, criteria):
    probs = sorted(b["probability"] for b in ballots.values())
    weights = [CONFIDENCE[b["confidence"]] for b in ballots.values()]
    side, counts = majority_side(ballots)
    n = len(ballots)
    top = max(counts["for"], counts["against"], counts["neither"])
    spread = "unanimous" if top == n else ("lean" if top * 3 >= n * 2 else "split")
    q = statistics.quantiles(probs, n=4, method="inclusive") if n >= 2 else [probs[0]] * 3
    crit_means = {c: round(statistics.mean(b["scores"][c] for b in ballots.values()), 2) for c in criteria}
    verified = {"for": 0, "against": 0, "neither": 0}
    for b in ballots.values():
        for f in b["findings"]:
            if f["grade"] == "verified":
                verified[f["favors"]] += 1
    minority = []
    for seat, b in ballots.items():
        if side in ("for", "against") and SIDE[b["verdict"]] != side:
            against_majority = [f for f in b["findings"] if f["grade"] == "verified" and f["favors"] not in (side, "neither")]
            minority.append({"seat": seat, "verdict": b["verdict"], "probability": b["probability"],
                             "decisive": b["decisive"], "verified_against_majority": len(against_majority)})
    return {
        "jurors": n,
        "verdicts": {v: sum(1 for b in ballots.values() if b["verdict"] == v) for v in VERDICTS},
        "sides": counts, "majority_side": side, "spread": spread,
        "probability": {"median": statistics.median(probs), "q1": q[0], "q3": q[2], "min": probs[0], "max": probs[-1],
                        "confidence_weighted_mean": round(sum(p * w for p, w in zip(
                            [b["probability"] for b in ballots.values()], weights)) / sum(weights), 1)},
        "criteria_means": crit_means,
        "verified_findings": verified,
        "minority": minority,
        "strong_minority": any(m["verified_against_majority"] for m in minority),
        "objections": [{"seat": s, "objection": b["objection"]} for s, b in ballots.items() if b.get("objection")],
    }


def tally(case, seed=None):
    p = check_pretrial(case)
    seats = [s["seat"] for s in p["seats"]]
    criteria = [c["id"] for c in p["criteria"]]
    r1 = load_round(case, seats, criteria, 1)
    used, rounds, flips, note = r1, 1, [], "blind vote only"
    if os.path.isdir(os.path.join(case, "ballots", "round2")):
        r2 = load_round(case, seats, criteria, 2)
        flips, rounds, note = audit_flips(r1, r2)
        used = r2 if rounds == 2 else r1
    result = summarize(used, criteria)
    setup = load_setup(case)
    juror_models = {seat: seat_model(setup, seat) for seat in seats}
    distinct = sorted(set(juror_models.values()))
    result.update({
        "round_used": rounds, "round_note": note, "flips": flips, "juror_models": juror_models,
        "correlation_note": (f"Every juror ran on the same model ({distinct[0]}), so their errors are likely "
                             "correlated; agreement is weaker evidence than the count suggests.")
                            if len(distinct) == 1 else
                            (f"Jurors ran on {len(distinct)} models ({', '.join(distinct)}), all from one family; "
                             "that spreads the errors a little, not fully."),
    })

    rng = random.Random(seed)
    order = list(used)
    rng.shuffle(order)  # the judge reads ballots in a random order under letters, never in seating order
    letters = {seat: f"Juror {chr(65 + i)}" for i, seat in enumerate(order)}
    result["packet_order"] = [letters[s] for s in order]
    write(os.path.join(case, "tally.json"), json.dumps(result, indent=2) + "\n")

    lines = [f"# Jury packet\n\nBallots from round {rounds} ({note}), in random order. "
             "Each juror voted alone before seeing any other ballot.\n"]
    for seat in order:
        b = used[seat]
        lines.append(f"## {letters[seat]}: {seat}\n")
        lines.append(f"**Verdict** {LABELS[b['verdict']]} · **probability** {b['probability']} · "
                     f"**confidence** {b['confidence']}\n")
        lines.append("**Findings**")
        lines += [f"- [{f['claim']}, {f['grade']}, favors {f['favors']}] {f['text']}" for f in b["findings"]]
        lines.append(f"\n**Scores** " + ", ".join(f"{k} {v}" for k, v in b["scores"].items()))
        lines.append(f"\n**Decisive** {b['decisive']}\n\n**Would change my mind** {b['change_my_mind']}")
        if b.get("conditions"):
            lines.append("\n**Conditions**")
            lines += [f"- {c}" for c in b["conditions"]]
        if b.get("objection"):
            lines.append(f"\n**Objection to the motion** {b['objection']}")
        if rounds == 2 and b.get("flip_reason"):
            lines.append(f"\n**Why I moved** {b['flip_reason']}")
        lines.append("")
    write(os.path.join(case, "jury-packet.md"), "\n".join(lines))
    return result, letters


# ---------- close and list ----------

def check_ruling(case):
    path = os.path.join(case, "ruling.md")
    if not os.path.exists(path):
        raise CaseError("ruling.md: missing")
    text = read(path)
    bad = []
    first = text.strip().splitlines()[0] if text.strip() else ""
    m = re.fullmatch(r"VERDICT: (Adopt|Adopt with conditions|Redesign|Reject|Insufficient evidence) "
                     r"\(confidence (low|medium|high)\)", first.strip())
    if not m:
        bad.append("ruling.md: first line must read 'VERDICT: <Adopt | Adopt with conditions | Redesign | Reject | "
                   "Insufficient evidence> (confidence <low|medium|high>)'")
    bad += [f"ruling.md: missing section '{s}'" for s in RULING_SECTIONS if s not in text]
    if words(text) > 600 * SLACK:
        bad.append(f"ruling.md: {words(text)} words, the limit is 600")
    if bad:
        raise CaseError(bad)
    return m.group(1), m.group(2)


def close(case):
    verdict, conf = check_ruling(case)
    motion = check_pretrial(case)["motion"]
    docket = os.path.join(os.path.dirname(os.path.abspath(case)), "docket.md")
    line = f"- {os.path.basename(os.path.abspath(case))} · {verdict} ({conf}) · {motion}\n"
    existing = read(docket) if os.path.exists(docket) else "# Docket\n\n"
    if line not in existing:
        write(docket, existing + line)
    return verdict, conf


def list_cases(base):
    if not os.path.isdir(base):
        return []
    rows = []
    for name in sorted(os.listdir(base)):
        case = os.path.join(base, name)
        if not os.path.isdir(case):
            continue
        try:
            verdict = check_ruling(case)[0]
        except CaseError:
            verdict = "open"
        try:
            motion = load_json(os.path.join(case, "pretrial.json")).get("motion", "")
        except CaseError:
            motion = ""
        rows.append((name, verdict, motion))
    return rows


# ---------- command line ----------

def main(argv=None):
    home = os.environ.get("GAVEL_DIR", ".gavel")
    ap = argparse.ArgumentParser(prog="gavel.py", description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    new = sub.add_parser("new", help="open a case folder with its setup")
    new.add_argument("motion")
    new.add_argument("--dir", default=home)
    new.add_argument("--last", action="store_true", help="start from the settings saved by the last case")
    new.add_argument("--opposition", choices=LEVELS)
    new.add_argument("--seats", help='comma separated, e.g. "engineer, designer: opus, a retired pilot"')
    new.add_argument("--jurors", type=int, help="3 to 8 seats for the judge to pick (ignored with --seats)")
    for role in ROLES:
        new.add_argument(f"--{role}", choices=MODELS, help=f"model for the {role}")
    for flag in ("quick", "deliberate", "research"):
        new.add_argument(f"--{flag}", action="store_true", default=None)
    sub.add_parser("settings", help="the setup saved by the last case").add_argument("--dir", default=home)
    for name in ("pretrial", "record", "tally", "close"):
        cmd = sub.add_parser(name)
        cmd.add_argument("case")
        if name in ("record", "tally"):
            cmd.add_argument("--seed", type=int, help="fix the random order (for tests and appeals)")
    sub.add_parser("list", help="past cases").add_argument("--dir", default=home)
    a = ap.parse_args(argv)

    try:
        if a.cmd == "new":
            saved_path = os.path.join(a.dir, "settings.json")
            saved = load_json(saved_path) if a.last and os.path.exists(saved_path) else None
            setup = build_setup(
                a.motion, saved, opposition=a.opposition, jurors=a.jurors,
                seats=parse_seats(a.seats) if a.seats else None,
                models={r: getattr(a, r) for r in ROLES},
                quick=a.quick, deliberate=a.deliberate, research=a.research)
            print(open_case(a.dir, setup))
            print(describe(setup))
        elif a.cmd == "settings":
            path = os.path.join(a.dir, "settings.json")
            if not os.path.exists(path):
                print("no saved settings")
            else:
                print(describe(dict(load_json(path), motion="")))
        elif a.cmd == "pretrial":
            p = check_pretrial(a.case)
            setup = load_setup(a.case)
            print(f"pretrial ok: {len(p['seats'])} seats, standard {p['standard']}")
            for s in p["seats"]:
                print(f"seat {s['seat']} -> ballots/round1/{seat_file(s['seat'])} model {seat_model(setup, s['seat'])}"
                      + ("  (premortem)" if s.get("premortem") else ""))
        elif a.cmd == "record":
            order = build_record(a.case, a.seed)
            print(f"record ok: {os.path.join(a.case, 'record.md')} (first side: {order[0]})")
        elif a.cmd == "tally":
            r, letters = tally(a.case, a.seed)
            pr = r["probability"]
            print(f"tally ok: round {r['round_used']} ({r['round_note']}); {r['jurors']} jurors; "
                  f"majority {r['majority_side']}, {r['spread']}; median {pr['median']} (q1 {pr['q1']}, q3 {pr['q3']})"
                  + ("; STRONG MINORITY" if r["strong_minority"] else ""))
        elif a.cmd == "close":
            verdict, conf = close(a.case)
            print(f"closed: {verdict} ({conf})")
        elif a.cmd == "list":
            rows = list_cases(a.dir)
            if not rows:
                print("no cases")
            for name, verdict, motion in rows:
                print(f"{name} | {verdict} | {motion}")
    except CaseError as e:
        for msg in e.problems:
            print(f"FIX {msg}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
