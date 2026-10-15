#!/usr/bin/env python3
"""Seen red, for real (SKILL.md R6): run one test command and say RED, GREEN or NOT RUN — from the
reports THIS run wrote, never from what was already on disk.

    redcheck.py --expect red   --test PaneBackStackTest -- ./gradlew :feature:ui:testDebugUnitTest --tests '*PaneBackStackTest' --rerun --no-build-cache
    redcheck.py --expect green --test PaneBackStackTest -- ./gradlew :feature:ui:testDebugUnitTest --tests '*PaneBackStackTest' --rerun --no-build-cache

    redcheck.py --expect red --test PaneBackStackTest \
        --break feature/ui/src/commonMain/kotlin/PaneBackStack.kt 'if (popped) return' 'if (false) return' \
        -- ./gradlew :feature:ui:testDebugUnitTest --tests '*PaneBackStackTest' --rerun --no-build-cache

Exit 0 when the result is the one you expected, 1 when it is the other colour, 2 when the test did not
run at all (a build failure, a timeout, only skipped tests, no report newer than the run, or a `--test`
that named more than one class), 3 when a `--break` could not be put back (the message says where the
original is).

`--test` is an identity, not a search: it matches the class, its last segment, or `Class.method`, and
every report file it was counted from is printed. Two different classes answering to it is a NOT RUN,
because the colour would be a mix of both; so is the same class answering red in one report file and
green in another. The full identity of a regression test is **task + report file + class + method**:
`--test` gives the last two and the printed path gives the first two, and `--reports <dir>` narrows the
search to one task or source set when a name is shared.

A report is this run's only if the command changed it **and** its own timestamp is not older than the
run (runners write one; Gradle does). That catches a file this run *touched* rather than wrote — a
restore, a sync, an editor save. It cannot catch another runner writing a fresh report for the same test
at the same time: for that, every report file counted has to agree on the colour, which is checked, and
anything else written during the run is named.

`--break FILE OLD NEW` makes the break for this run and undoes it afterwards: OLD must appear exactly
once in FILE, and the file is written back byte for byte and checked — after this script's own
`--timeout`, after Ctrl-C, and after a SIGTERM or SIGHUP. A copy of every original is written **before
the first byte changes** and its path is printed, so even a kill no handler survives (SIGKILL, or the
tool that launched this one timing out) leaves the original somewhere. Give the caller a timeout above
`--timeout`, or run this in the background: whoever kills this process wins. Repeat it for a break that spans several places. Breaking and restoring by hand is where it goes
wrong: a shell loop that didn't split its file list left four files broken after a correct red, and
only a failed `cp` gave it away (measured).

Why it exists: a break that did not compile left the previous run's report on disk, and only its
unchanged time showed the "red" was never run (measured); a break re-applied after a restore came back
UP-TO-DATE twice in a row. Reading the report by hand is care; this makes it a rule.

Reports: JUnit XML (Gradle, Maven, most runners) under --reports (default: every `test-results` folder
below the working directory, and every `outputs/androidTest-results`, where tests on a device write
theirs). Only report files the command created or changed count.
"""
import argparse
import datetime
import glob
import hashlib
import re
import os
import signal
import subprocess
import sys
import time
import tempfile
import xml.etree.ElementTree as ET


def keep_path(path):
    return os.path.join(tempfile.gettempdir(),
                        "redcheck-" + hashlib.sha256(os.path.abspath(path).encode()).hexdigest()[:12]
                        + "-" + os.path.basename(path))


def apply_breaks(breaks):
    """Apply every --break; return {path: original bytes}. Refuses — putting back what it already
    changed — unless each OLD is found exactly once.

    The copy of each original is written BEFORE anything changes: no handler runs on SIGKILL, and the
    tool that launched this one can time out and kill it — SIGTERM and SIGHUP left the source broken
    with no copy anywhere (measured).
    """
    originals = {}
    for sig in (signal.SIGTERM, signal.SIGHUP):
        signal.signal(sig, lambda *_: sys.exit(2))
    for path, _, _ in breaks or []:
        if os.path.exists(keep_path(path)):
            print(f"note: a copy of {path} from an earlier run is still at {keep_path(path)} — a break may "
                  "have been left in place; compare them before trusting this run.", file=sys.stderr)
    try:
        for path, old, new in breaks or []:
            # One file, one original: `Repo.kt` and `./Repo.kt` kept as two made the second "original"
            # the already-broken text, and the restore wrote that back.
            path = os.path.realpath(path)
            if old == new:
                refuse(f"--break {path}: OLD and NEW are the same — that breaks nothing")
            if re.sub(r"\s+", "", old) == re.sub(r"\s+", "", new):
                # A break that only moves spaces compiles, runs, and leaves the test green — which reads
                # as "the test won't go red" when what happened is that nothing was mutated.
                refuse(f"--break {path}: OLD and NEW differ only in whitespace — that mutates nothing")
            if not os.path.isfile(path):
                refuse(f"--break {path}: no such file")
            data = open(path, "rb").read()
            n = data.count(old.encode())
            if n != 1:
                refuse(f"--break {path}: OLD appears {n} times, not once — make it unique")
            if path not in originals:
                originals[path] = data
                with open(keep_path(path), "wb") as fh:
                    fh.write(data)
                print(f"break: {path} — original kept at {keep_path(path)}", file=sys.stderr)
            with open(path, "wb") as fh:
                fh.write(data.replace(old.encode(), new.encode(), 1))
    except BaseException:
        restore(originals)
        raise
    return originals


def refuse(message):
    """Nothing ran: exit 2, like any other NOT RUN — 1 means "the other colour"."""
    print(f"NOT RUN: {message}", file=sys.stderr)
    raise SystemExit(2)


def restore(originals):
    """Write every broken file back and check it is byte for byte the original. A copy of each
    original is kept in the temp folder until that check passes."""
    failed = []
    for path, data in originals.items():
        keep = keep_path(path)
        try:
            with open(path, "wb") as fh:
                fh.write(data)
            ok = open(path, "rb").read() == data
        except OSError:
            ok = False
        if ok:
            os.remove(keep)
        else:
            failed.append(f"{path} (original kept at {keep})")
    if failed:
        print("BREAK NOT UNDONE — put these back before anything else: " + "; ".join(failed), file=sys.stderr)
        raise SystemExit(3)
    if originals:
        print(f"break undone: {len(originals)} file(s) back byte for byte")


def default_roots():
    """Where JUnit XML lands below here: `test-results` for tests on the JVM, and
    `outputs/androidTest-results` for connectedAndroidTest, which does not write under test-results
    (measured: a campaign had to pass that folder by hand)."""
    found = glob.glob("**/test-results/*", recursive=True) + glob.glob("**/outputs/androidTest-results/*", recursive=True)
    return sorted({os.path.dirname(d) for d in found}) or ["."]


def snapshot(roots):
    """Every report file and its (mtime, size) before the run."""
    seen = {}
    for root in roots:
        for path in glob.glob(os.path.join(root, "**", "*.xml"), recursive=True):
            st = os.stat(path)
            seen[path] = (st.st_mtime_ns, st.st_size)
    return seen


ASSERTION_TYPES = ("assertionerror", "assertionfailederror", "comparisonfailure", "assertionfailure",
                   "multiplefailureserror", "opentest4j")
# A mocking library's verification failure IS the test's own check — "expected this call, it never
# happened". Mockito throws its own types for it (WantedButNotInvoked, TooFewActualInvocations,
# ArgumentsAreDifferent…), none of which ends in "AssertionError", so a real red was reported as a
# crash and the campaign had to read the report by hand (friction log, Shiori campaign 2026-09-24).
# Only `exceptions.verification`: a misuse (unnecessary stubbing) is the test being wrong, not its
# check failing.
VERIFICATION_PACKAGES = ("mockito.exceptions.verification", "mockk.assertion")


def is_assertion(kind):
    """Did the test's own check fail, or did something blow up before it? (R6)"""
    whole = (kind or "").lower()
    if any(p in whole for p in VERIFICATION_PACKAGES):
        return True
    last = whole.rsplit(".", 1)[-1]
    return any(t in last for t in ASSERTION_TYPES)


def matches_filter(classname, name, name_filter):
    """`--test Foo` means the class Foo, its last segment, or Foo.method — not any string containing it.

    A plain substring on "classname.name" counted a sibling class and a same-named method in another
    module as the target test (audit).
    """
    if not name_filter:
        return True
    cls = (classname or "").replace("$", ".")
    f = name_filter.replace("$", ".")
    return (f == cls or cls.endswith("." + f) or f == f"{cls}.{name}" or f == f"{cls.rsplit('.', 1)[-1]}.{name}"
            or f == name)


# How far a report's own clock may sit before this run started before it stops counting. Generous on
# purpose: a wrong guess here turns a real red into NOT RUN.
STALE_MARGIN_S = 120


def suite_time(root):
    """The report's own start time, when the runner wrote one (Gradle does).

    The mtime only says the file changed while this run was going: a restore, an rsync, an editor save
    or another build touching an old report all do that, and the result would be read as this run's.
    The suite's own timestamp is the runner's word for when it ran. What this does NOT catch is another
    runner writing a *fresh* report for the same test at the same time — for that, the per-file colours
    below have to agree, and `--reports` scopes the search to one task.
    """
    raw = (root.get("timestamp") or "").strip()
    if not raw:
        return None
    try:
        when = datetime.datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if when.tzinfo is None:
        # No zone marker says nothing about the zone: Gradle up to 8.x (Ant's DateUtils) writes GMT,
        # other runners write local time. Read as local only, a report written seconds ago looked
        # hours old east of Greenwich and a real red came back NOT RUN. Take the later reading: a
        # report is stale only when it is stale either way.
        return max(when.timestamp(), when.replace(tzinfo=datetime.timezone.utc).timestamp())
    return when.timestamp()


def reports_written_since(roots, before, name_filter, started):
    tests = failures = skipped = 0
    messages, crashes, counted, per_path, stale, others = [], [], {}, {}, [], []
    for root in roots:
        for path in glob.glob(os.path.join(root, "**", "*.xml"), recursive=True):
            st = os.stat(path)
            # Written by THIS run: new, or changed since the snapshot. A time margin instead let a red from
            # the previous run, under a second old, count for a run that never compiled (measured here).
            if before.get(path) == (st.st_mtime_ns, st.st_size):
                continue
            try:
                tree = ET.parse(path)
            except ET.ParseError:
                continue
            when = suite_time(tree.getroot())
            if when is not None and when < started - STALE_MARGIN_S:
                stale.append((path, when))
                continue
            here = [0, 0, 0, 0]                       # tests, failures, skipped, crashes in THIS file
            for case in tree.iter("testcase"):
                cls, name = case.get("classname", ""), case.get("name", "")
                if not matches_filter(cls, name, name_filter):
                    continue
                tests += 1
                here[0] += 1
                # Every report the class was counted from, not just the first: the same class name in two
                # modules, or one class run on two devices, look identical in the totals otherwise.
                if path not in counted.setdefault(cls, []):
                    counted[cls].append(path)
                bad = case.find("failure")
                if bad is None:
                    bad = case.find("error")
                if bad is not None:
                    first = (bad.get("message") or (bad.text or "")).strip().splitlines()
                    line = f"{name}: {first[0][:160] if first else '(no message)'}"
                    # An Android connected-test report has no `type`: the class is the message's first word.
                    # A Compose assertion read as a crash there, and two real reds were read by hand (measured).
                    kind = bad.get("type") or (re.match(r"\s*([\w.$]+)", bad.get("message") or bad.text or "") or [None, None])[1]
                    if is_assertion(kind):
                        failures += 1
                        here[1] += 1
                        messages.append(line)
                    else:
                        # R6: a crash before the check is not the test saying "expected this, got that".
                        crashes.append(f"{line}  [{kind or 'no type'}]")
                        here[3] += 1
                elif case.find("skipped") is not None:
                    skipped += 1
                    here[2] += 1
            if here[0]:
                per_path[path] = tuple(here)
            elif next(tree.iter("testcase"), None) is not None:
                # A report written during this run that holds none of the test you named: something else
                # is running tests here, and the next one it writes could be for the same class.
                others.append(path)
    return tests, failures, skipped, messages, crashes, counted, per_path, stale, others


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--expect", choices=["red", "green"], required=True)
    p.add_argument("--test", help="the one test to judge: its class, the class's last segment, or Class.method — an identity, not a substring")
    p.add_argument("--reports", action="append", help="folder with JUnit XML, repeatable; default: every test-results and outputs/androidTest-results folder below .")
    p.add_argument("--timeout", type=float, default=900, help="seconds; a test that never ends is not red (R6)")
    p.add_argument("--break", dest="breaks", nargs=3, action="append", metavar=("FILE", "OLD", "NEW"),
                   help="make this break for the run and undo it after, checked byte for byte; OLD must appear once")
    p.add_argument("command", nargs=argparse.REMAINDER)
    a = p.parse_args()
    cmd = a.command[1:] if a.command[:1] == ["--"] else a.command
    if not cmd:
        p.error("give the test command after --")
    if "gradle" in os.path.basename(cmd[0]) and "--rerun" not in cmd:
        print("note: no --rerun — Gradle may call the task up to date and write no report (it will say NOT RUN)",
              file=sys.stderr)

    originals = apply_breaks(a.breaks)
    try:
        judge(a, cmd)
    finally:
        restore(originals)


def kill_tree(proc):
    """The command and everything it started (it runs in its own session)."""
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        proc.kill()


def judge(a, cmd):
    roots = a.reports or default_roots()
    before = snapshot(roots)
    started = time.time()
    # Its own session, so the whole tree can be stopped: killing only the command left its children
    # running — a test still spinning, able to write a report after the break was undone.
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                            errors="replace", start_new_session=True)
    try:
        out, err = proc.communicate(timeout=a.timeout)
        output, code = out + err, proc.returncode
    except subprocess.TimeoutExpired:
        kill_tree(proc)
        try:
            tail = (proc.communicate(timeout=5)[0] or "")[-300:].strip()
        except subprocess.TimeoutExpired:
            tail = ""
        print(f"NOT RUN: no end after {a.timeout:.0f} s — a hang is a finding, not a red (R6). Last output: {tail or '(none)'}")
        sys.exit(2)
    except BaseException:                  # Ctrl-C, SIGTERM: the break is undone next, so stop the run first
        kill_tree(proc)
        raise
    if not a.reports:
        roots = default_roots()

    (tests, failures, skipped, messages, crashes, counted,
     per_path, stale, others) = reports_written_since(roots, before, a.test, started)
    for path, when in stale:
        print(f"   ignored {path}: the report says it ran at "
              f"{time.strftime('%H:%M:%S', time.localtime(when))}, before this run started — this run "
              "touched the file, it did not write it")
    if others:
        print(f"   note: {len(others)} report file(s) changed during this run with no test matching "
              f"{a.test!r} ({os.path.basename(others[0])}…) — something else is writing reports here "
              "(another Gradle, the IDE, a watcher). Scope with --reports if a colour looks wrong.",
              file=sys.stderr)
    for cls, paths in sorted(counted.items()):
        for path in paths:
            print(f"   counted {cls} from {path}")
        if len(paths) > 1:
            print(f"   note: {cls} counted from {len(paths)} report files — two variants, two source sets or two "
                  "devices. The colour below is all of them together.")
    if not a.test and len(counted) > 1:
        # Without --test, any report the command touched counts: an unrelated module's tests turned an
        # up-to-date target into GREEN (audit). Name what was counted instead of hiding it.
        print(f"   ⚠️ {len(counted)} test classes counted and no --test: this colour is the whole run's, "
              "not one test's", file=sys.stderr)
    cached = [l for l in output.splitlines() if "FROM-CACHE" in l and "> Task" in l]
    if cached:
        print(f"NOT RUN: the task came FROM-CACHE, so the report on disk is a restored one, not this run's "
              f"({cached[0].strip()[:120]}). Re-run with --rerun --no-build-cache.")
        sys.exit(2)
    reds = sorted(p for p, (t, f, s, c) in per_path.items() if f)
    greens = sorted(p for p, (t, f, s, c) in per_path.items() if not f and t > s)
    if a.test and reds and greens:
        # The same test, two report files, two different answers — two variants, two source sets or two
        # devices. Summing them gives whichever colour was asked for; neither file is the test's verdict.
        print(f"NOT RUN: two report files for --test {a.test!r} disagree — red in {reds[0]}, green in "
              f"{greens[0]}. Name the one task you mean with --reports, and look at why they differ.")
        sys.exit(2)
    if a.test and len(counted) > 1:
        # `--test Foo` names ONE test. Two classes answering to it are two different tests — sibling
        # classes, or the same name in another module — and the colour would be a mix of both (audit).
        print(f"NOT RUN: --test {a.test!r} matched {len(counted)} different classes: " + ", ".join(sorted(counted))
              + ". Name the class with its package, or point --reports at the one module.")
        sys.exit(2)
    if tests == 0:
        # Only when the command actually failed: `error:` appears in plenty of successful output, and an
        # up-to-date run was reported as a failed build because of it (audit).
        compile_lines = [l for l in output.splitlines() if l.startswith("e: ") or "Compilation error" in l
                         or "compilation failed" in l.lower() or re.search(r"\.(java|kt):\d+: error:", l)] if code != 0 else []
        if compile_lines:
            print(f"NOT RUN: the build failed before the test — {compile_lines[0][:200]}")
        else:
            tasks = [l.strip()[:120] for l in output.splitlines()
                     if "> Task" in l and ("UP-TO-DATE" in l or "FROM-CACHE" in l or "NO-SOURCE" in l)]
            print(f"NOT RUN: no report from this run{' for ' + repr(a.test) if a.test else ''} (exit {code}). "
                  "Up to date or cached? Rerun with --rerun --no-build-cache and name the test task."
                  + ("\n   " + "\n   ".join(tasks[:3]) if tasks else ""))
        sys.exit(2)
    if crashes and not failures:
        print(f"NOT RED: {len(crashes)} of {tests} ended before their check — a crash, not the test's own "
              "verdict (R6). Fix the crash, then look again:")
        for m in crashes[:5]:
            print(f"   {m}")
        sys.exit(2)
    if crashes:
        print(f"   note: {len(crashes)} more ended in a crash rather than a failed check: {crashes[0][:120]}")
    if failures:
        result = "red"
        print(f"RED: {failures} of {tests} failed, from reports this run wrote")
        for m in messages[:5]:
            print(f"   {m}")
        print("   Read the message: it must be the test's own check (R6), not a crash before it.")
    elif tests == skipped:
        print(f"NOT RUN: all {tests} test cases were skipped")
        sys.exit(2)
    else:
        result = "green"
        print(f"GREEN: {tests - skipped} passed{f', {skipped} skipped' if skipped else ''}, from reports this run wrote")
        print("   A green is the runner's verdict, not proof the test exercised the behaviour: an early `return`, a "
              "swallowed exception or a missing assertion all pass. The red you saw first is what proves it (R6).")
        if a.breaks:
            # "I broke it and it stayed green" is read as "this test won't go red". It means one of two
            # things, and neither is the code being right: the mutation missed what the test checks, or
            # the test does not cover it. Applied is not validated.
            print("   ⚠️ MUTATION NOT VALIDATED: the break was applied, it compiled, the test ran — and "
                  "nothing failed. That is not evidence the code is right: either the mutation did not "
                  "touch what this test asserts, or the test does not cover it. Break the line its own "
                  "assertion depends on, and if it still passes, the test is the finding.")
    sys.exit(0 if result == a.expect else 1)


if __name__ == "__main__":
    main()
