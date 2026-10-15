#!/usr/bin/env python3
"""Track a domain warm-up: today's ramp target, gate progress and the stop rule.

The log is JSON lines, one object per run. Nothing here talks to a mailbox; sending and
measuring are provider specific, and this only does the bookkeeping that is identical
everywhere, so that every run agrees on the run number and the gate.

    warmup_log.py next    --log warmup.jsonl
    warmup_log.py status  --log warmup.jsonl [--provider microsoft]
    warmup_log.py append  --log warmup.jsonl --sent 4 --replied 3 --rescued 2 \
                          --measured-to inbox --provider microsoft
"""
from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

# Run number -> sends per weekday. The gradient is the point, not the totals: a new domain
# that sends steadily and slowly looks like a person, and one that jumps looks like a list.
RAMP = ((3, 2), (7, 4), (14, 6))
RAMP_CEILING = 10

GATE_NEEDED = 2       # consecutive unassisted inbox landings before outreach starts

# A floor under the gate, not a substitute for it. Reputation is built from behaviour
# observed OVER TIME, so a domain four days old with six messages behind it has almost no
# history for a filter to weigh: two inbox landings there are as likely to be luck as
# evidence. Ten sending runs is roughly a fortnight of weekdays, which is the shortest span
# that has produced a durable result. Passing the measurement earlier is encouraging and is
# not the gate.
MIN_RUNS_BEFORE_GATE = 10
STOP_AFTER_RUNS = 15  # keep junking this long and a human needs to hear about it
VALID_PLACEMENTS = ("inbox", "junk", "promotions", "missing", "unknown")

# What the measured message actually contained. A plain-text note landing in the inbox does
# not predict how a message carrying a link to a brand-new domain is treated, and the link
# is what real outreach carries - so the gate is held per content shape, not just per
# provider. "promotions" is Gmail's tab, which is not spam but is not the primary inbox
# either, and a cold prospect rarely looks there.
CONTENT_SHAPES = ("plain", "link", "attachment")


def target_for(run: int) -> int:
    for last_run, sends in RAMP:
        if run <= last_run:
            return sends
    return RAMP_CEILING


def load(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out = []
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            # A corrupt line is worth naming rather than skipping silently: the log is the
            # only evidence the gate is computed from.
            raise SystemExit(f"{path}:{n} is not valid JSON - fix it before continuing")
    return out


def placement_mix(entries: list[dict], provider: str | None = None) -> dict:
    """Where measured messages landed, and whether it is trending the right way.

    Reported as evidence, never as a pass mark. These mailboxes reply and rescue, so their
    placement flatters the domain - which is fine, since that engagement is what builds the
    reputation, but it means this is encouragement rather than proof.
    """
    seen = [e for e in entries if not e.get("blocked")
            and (e.get("measured_to") or "unknown") in ("inbox", "junk", "promotions")
            and (not provider or not e.get("provider") or e["provider"] == provider)]
    mix = {k: sum(1 for e in seen if (e.get("measured_to") or "") == k)
           for k in ("inbox", "junk", "promotions")}
    half = len(seen) // 2 or 1
    first, last = seen[:half], seen[-half:]
    rate = lambda rows: (sum(1 for e in rows if e.get("measured_to") == "inbox") / len(rows)
                         if rows else 0.0)
    mix["measured"] = len(seen)
    mix["inbox_rate_first_half"] = round(rate(first), 2)
    mix["inbox_rate_second_half"] = round(rate(last), 2)
    mix["trend"] = ("improving" if rate(last) > rate(first)
                    else "flat" if rate(last) == rate(first) else "worse")
    return mix


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=("next", "status", "append"))
    ap.add_argument("--log", required=True, type=Path)
    ap.add_argument("--provider", help="only count this provider towards the gate")
    ap.add_argument("--sent", type=int, default=0)
    ap.add_argument("--replied", type=int, default=0)
    ap.add_argument("--rescued", type=int, default=0)
    ap.add_argument("--measured-to", choices=VALID_PLACEMENTS, default="unknown",
                    help="folder the measured message was DELIVERED to, recorded before any rescue")
    ap.add_argument("--content", choices=CONTENT_SHAPES, default="plain",
                    help="what the measured message carried")
    ap.add_argument("--cold-seed", action="store_true",
                    help="measured against a mailbox that never replies or rescues")
    ap.add_argument("--blocked", action="store_true", help="the run could not send; say why in --notes")
    ap.add_argument("--notes", default="")
    args = ap.parse_args()

    entries = load(args.log)
    run = len(entries) + 1

    if args.command == "next":
        print(json.dumps({"run": run, "target_sends": target_for(run)}, indent=2))
        return

    if args.command == "append":
        entry = {
            "date": date.today().isoformat(), "run": run, "sent": args.sent,
            "replied": args.replied, "rescued": args.rescued,
            "measured_to": args.measured_to, "provider": args.provider or "",
            "content": args.content, "cold_seed": args.cold_seed,
            "blocked": args.blocked, "notes": args.notes,
        }
        args.log.parent.mkdir(parents=True, exist_ok=True)
        with args.log.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry) + "\n")
        print(json.dumps(entry, indent=2))
        return

    sending = [e for e in entries if not e.get("blocked")]
    blocked_tail = 0
    for e in reversed(entries):
        if e.get("blocked"):
            blocked_tail += 1
        else:
            break
    # Gaps matter more than totals here: the ramp is a shape, and a machine that was off for
    # three days leaves a hole nobody notices from a run count alone.
    gap_days, last_date = None, ""
    dated = [e.get("date") for e in entries if e.get("date")]
    if dated:
        from datetime import date as _date
        try:
            last_date = max(dated)
            y, m, d = (int(x) for x in last_date.split("-"))
            gap_days = (_date.today() - _date(y, m, d)).days
        except ValueError:
            gap_days = None

    mix = placement_mix(entries, args.provider)
    stop_fired = len(sending) >= STOP_AFTER_RUNS and not any(
        (e.get("measured_to") or "") == "inbox" for e in sending)
    print(json.dumps({
        "runs_logged": len(entries),
        "runs_that_sent": len(sending),
        "consecutive_blocked_runs": blocked_tail,
        "next_run": run,
        "next_target_sends": target_for(run),
        "runs_needed": MIN_RUNS_BEFORE_GATE,
        "last_run_date": last_date,
        "days_since_last_run": gap_days,
        "gap_warning": (
            "" if gap_days is None or gap_days <= 3 else
            f"no run logged for {gap_days} days - if the machine was off, move the schedule "
            "into hours it is reliably awake. Continue the ramp from the next run rather than "
            "sending extra to catch up."
        ),
        "warmup_complete": len(sending) >= MIN_RUNS_BEFORE_GATE,
        "placement": mix,
        # Said this way on purpose: a completed warm-up improves how providers treat the
        # domain, and promises nothing about any individual message.
        "verdict": (
            "not finished - keep going" if len(sending) < MIN_RUNS_BEFORE_GATE
            else "two weeks done and placement is mostly inbox; sending should be in better "
                 "shape, though nothing guarantees placement"
            if mix["measured"] and mix["inbox"] >= mix["junk"]
            else "two weeks done but mail is still mostly going to junk - do not treat this "
                 "as finished; check authentication alignment, blocklists, and the content "
                 "itself before sending anything real"
        ),
        "stop_rule_fired": stop_fired,
        # A fired stop rule is the loudest thing this file can say, so it must set the flag
        # a caller acts on. Reporting stop_rule_fired=true alongside escalate=false invited
        # exactly the outcome the stop rule exists to prevent: a warm-up that is not working
        # continuing quietly because nothing told anyone to look.
        "escalate": bool(blocked_tail >= 3 or stop_fired),
    }, indent=2))


if __name__ == "__main__":
    main()
