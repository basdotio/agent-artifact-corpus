#!/usr/bin/env python3
"""Find and run other assistants' command-line tools, so the host can fill Seats B and C itself.

Usage:
  python3 seats.py detect [--exclude VENDOR]         # list usable seats as JSON
  python3 seats.py models SEAT                       # list a seat's models, where the tool can
  python3 seats.py run SEAT prompt.txt reply.md [--model NAME] [--effort LEVEL]
  python3 seats.py run custom --cmd "mytool --print" prompt.txt reply.md   # any tool that reads stdin
  python3 seats.py run custom --cmd "mytool -p 'Read {prompt_file}'" prompt.txt reply.md  # or a file
  python3 seats.py --self-test

Each seat runs with the user's existing login for that tool. This script sends the prompt
file to that tool and nothing else: no API keys, no other network calls. Standard library only.
The built-in seats run read-only in an empty folder. `run custom` runs
the command exactly as given, so keeping that tool read-only is up to whoever writes it.
"""
import argparse
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile

# name: (vendor, command). Every seat runs read-only with its tools off or sandboxed, because
# the prompt carries text from outside (a job posting) that could contain instructions.
# The prompt goes in on stdin, or as a private file in the seat's folder where {prompt_file}
# appears. It never goes on the command line, where other local users could see it.
# Earlier entries win when one company has two tools installed.
# MODEL_FLAGS: where --model and --effort go for each tool (inserted after the first N words).
MODEL_FLAGS = {
    "claude": (1, ["--model", "{m}"], ["--effort", "{e}"]),
    "codex": (2, ["-m", "{m}"], ["-c", "model_reasoning_effort={e}"]),
    "agy": (1, ["--model", "{m}"], ["--effort", "{e}"]),
}
LIST_MODELS = {"agy": ["agy", "models"]}
# Each seat runs only its own company's models: Antigravity also lists Claude and GPT models, and picking one would
# send the text to Google while the user was told another company, and quietly undo the independence.
OWN_MODELS = {"claude": ("claude", "opus", "sonnet", "haiku"), "codex": ("gpt-", "o1", "o3", "o4", "codex"), "agy": ("gemini",)}
CLAUDE_MODELS = "opus\tAnthropic's most capable model\nsonnet\tAnthropic's balanced model\nhaiku\tAnthropic's fastest model"


def own_model(seat, model):
    return not model or seat not in OWN_MODELS or model.lower().startswith(OWN_MODELS[seat])
CODEX_MODELS = os.path.expanduser("~/.codex/models_cache.json")  # the models this account can use
SEATS = {
    # --safe-mode keeps the user's own memory, hooks, plugins and MCP servers out of the seat's context.
    "claude": ("anthropic", ["claude", "-p", "--safe-mode", "--tools", "", "--no-session-persistence"]),
    "codex": ("openai", ["codex", "exec", "--sandbox", "read-only", "--ephemeral", "--skip-git-repo-check", "-"]),
    "agy": ("google", ["agy", "--sandbox", "--mode", "plan", "--print-timeout", "10m",
                       "-p", "Open the file {prompt_file} in this folder with your file-reading tool. Run no shell "
                             "commands. Then reply to it exactly as it asks."]),
}


def detect(exclude):
    """One seat per vendor, so two tools from the same company never count as two opinions."""
    found, seen = [], set(exclude)
    for name, (vendor, cmd) in SEATS.items():
        if vendor not in seen and shutil.which(cmd[0]):
            found.append({"seat": name, "vendor": vendor})
            seen.add(vendor)
    return found


def blocked(reply):
    """True only for the tool's own one-line error, never for a reply that merely quotes it."""
    text = reply.strip()
    return text.startswith("jetski: no output produced") and "\n" not in text


PHONE_LABEL = re.compile(r"(?i)\b(?:phone|mobile|cell|tel|telephone|whatsapp|fax)(?:\s*(?:no\.?|number|#))?\s*[:.]?\s*$")


def contact_details(prompt, keep=()):
    """Emails, profile links and phone numbers that should have been swapped for stand-ins.
    keep: values the user checked are not contact details (a requisition number), from standins.md."""
    found = re.findall(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+|linkedin\.com/in/[\w-]+", prompt)
    for m in re.finditer(r"(?<![$€£¥₹\d])\+?\d[\d ().-]{5,}\d", prompt):  # after a currency sign it is money
        s = m.group(0)
        before = prompt[max(0, m.start() - 30):m.start()]
        digits = sum(c.isdigit() for c in s)
        # A number right after a phone label ("Phone: +44 20 2018-2022") is a phone, whatever it looks like.
        if digits >= 7 and PHONE_LABEL.search(before):
            found.append(s)
        elif (digits >= (7 if re.search(r"\D", s) else 10)
                # A year range inside ("10 2018 - 2022", a GPA scale then dates) means dates, not a phone.
                and not re.search(r"(?:19|20)\d\d\s*[-–]\s*(?:19|20)\d\d", s)
                # Dates such as 2026-09-15 or 15.09.2026 (a saved profile dates its entries) are not phones.
                and not re.fullmatch(r"(?:19|20)\d\d-\d\d-\d\d|\d\d?[.-]\d\d?[.-](?:19|20)\d\d", s)
                and not labelled_id(before)):
            found.append(s)
    # keep only ever excuses a number; an email or a profile link is always caught.
    keep = {k.lower() for k in keep if not re.search(r"@|linkedin|[a-z]", k.lower())}
    return [f for f in found if f.lower() not in keep]


def labelled_id(before):
    """True when the text just before a number labels it as a posting or order ID ("Req. ID:", "Job #").
    Any phone word nearby ("Phone No.", "contact number", "call") means it is a phone, whatever follows."""
    if re.search(r"(?i)\b(?:phone|mobile|cell|tel|telephone|contact|call|whatsapp|fax)\b", before):
        return False
    return bool(re.search(r"(?i)\b(?:req(?:uisition)?|job|ref(?:erence)?|order|invoice|case|ticket)\b[\W]{0,4}(?:id|no|number|#)?\W{0,3}$"
                          r"|\bid\W{0,3}$", before))


def run(cmd, prompt_path, reply_path, timeout, allow_contact=False):
    with open(prompt_path, encoding="utf-8") as f:
        prompt = f.read()
    # Values the user checked are not contact details sit in standins.md as <<KEEP>> lines, next to the prompt.
    path = os.path.join(os.path.dirname(os.path.abspath(prompt_path)), "standins.md")
    keep = re.findall(r"^<<KEEP\w*>> = (.+?)\s*$", open(path, encoding="utf-8").read(), re.M) if os.path.exists(path) else []
    found = contact_details(prompt, keep)
    # Backstop for every pattern above: any value already hidden at setup, found again anywhere, stops the send.
    if os.path.exists(path):
        hidden = re.findall(r"^<<(?!KEEP)\w+>> = (.+?)\s*$", open(path, encoding="utf-8").read(), re.M)
        found += [v for v in hidden if len(v) >= 3 and re.search(rf"(?<![\w-]){re.escape(v)}(?![\w-])", prompt, re.I)]
    if found and not allow_contact:
        sys.exit(f"not sent: the prompt still holds personal details ({', '.join(found[:3])}). Run prompt.py hide and build "
                 "the prompt again, or pass --allow-contact if the user agreed to send them. A large figure that is not a phone "
                 "passes once written with commas: 1,000,000,000.")
    # Fail early if the reply cannot be saved, and clear any earlier reply so a failed run leaves nothing stale.
    open(reply_path, "w", encoding="utf-8").close()
    # These tools are agents that can read files. Run each one in an empty folder so it
    # cannot see the other drafts, the label log or anything else in the project.
    uses_file = any("{prompt_file}" in part for part in cmd)
    with tempfile.TemporaryDirectory() as empty:  # created readable by this user only
        if uses_file:
            fd = os.open(os.path.join(empty, "prompt.md"), os.O_WRONLY | os.O_CREAT, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(prompt)
        cmd = [part.replace("{prompt_file}", "prompt.md") for part in cmd]
        stdin = None if uses_file else prompt
        for attempt in (1, 2):  # a read-only seat sometimes reaches for a blocked tool; one retry clears it
            try:
                r = subprocess.run(cmd, input=stdin, capture_output=True, text=True, encoding="utf-8",
                                   timeout=timeout, cwd=empty)
            except (OSError, subprocess.TimeoutExpired) as e:
                sys.exit(f"seat failed: {e}")
            if r.returncode == 0 and r.stdout.strip() and not blocked(r.stdout):
                break
    if r.returncode != 0 or not r.stdout.strip() or blocked(r.stdout):
        sys.exit(f"seat failed (exit {r.returncode}): {(r.stderr.strip() or r.stdout.strip())[:500] or 'empty reply'}")
    with open(reply_path, "w", encoding="utf-8") as f:
        f.write(r.stdout)
    print(f"saved {len(r.stdout)} characters to {reply_path}")


def with_model(seat, cmd, model, effort):
    at, mflag, eflag = MODEL_FLAGS[seat]
    extra = ([f.format(m=model) for f in mflag] if model else []) + \
            ([f.format(e=effort) for f in eflag] if effort else [])
    return cmd[:at] + extra + cmd[at:]


def self_test():
    assert blocked("jetski: no output produced\n") and not blocked("# Resume\njetski: no output produced")
    assert with_model("codex", SEATS["codex"][1], "m1", "high")[:6] == ["codex", "exec", "-m", "m1", "-c", "model_reasoning_effort=high"]
    assert with_model("claude", SEATS["claude"][1], None, None) == SEATS["claude"][1]
    assert all(d["vendor"] != "openai" for d in detect(["openai"]))
    assert contact_details("Mail sam@example.com or call +1 (555) 010-2030") == ["sam@example.com", "+1 (555) 010-2030"]
    assert contact_details("<<EMAIL>> | <<PHONE>> | Jan 2019 - Mar 2021 | 2019 - 2021 | cut 1200 to 300 | 5000000") == []
    assert contact_details("call 555-0117") == ["555-0117"]
    assert contact_details("Send it to hr@corp.example.") == ["hr@corp.example"]  # not the full stop
    assert contact_details("GPA: 8.2 / 10 2018 - 2022. Req. ID: 1273383451. Job #4471234567") == []  # dates and IDs
    assert contact_details("call 5551234567", keep=["5551234567"]) == []
    # Phone words always mean a phone, whatever label follows; keep never excuses an email.
    assert contact_details("Phone No. 5551234567, contact number: 555-123-4567, Mobile #: 5551234567") == ["5551234567", "555-123-4567", "5551234567"]
    assert contact_details("Cell no 5551234567") == ["5551234567"] and contact_details("No. 5551234567") == ["5551234567"]
    assert contact_details("mail a@b.co", keep=["a@b.co"]) == ["a@b.co"]
    # Backstop: a value hidden at setup that turns up again stops the send; a word that merely contains it does not.
    with tempfile.TemporaryDirectory() as d:
        open(os.path.join(d, "standins.md"), "w").write("<<NAME>> = Jordan Ellis\n<<PERSONAL>> = Ruth\n")
        for text, refused in (("Jordan Ellis wrote it.", True), ("The truth is ruthless.", False)):
            open(os.path.join(d, "p.txt"), "w").write(text)
            try:
                run(["echo", "ok"], os.path.join(d, "p.txt"), os.path.join(d, "r.md"), 5)
                assert not refused, text
            except SystemExit as e:
                assert refused and "not sent" in str(e), (text, e)
    assert contact_details("call 5551234567") == ["5551234567"]
    assert contact_details("## 2026-09-15\nconfirmed 15.09.2026 and 1-9-2026") == []  # dated profile entries
    assert contact_details("call 0161-555-0199") == ["0161-555-0199"]
    assert contact_details("Annual budget $1000000000, £25000000 and €4000000.") == []  # money, not phones
    assert contact_details("call +44 7700 900123") == ["+44 7700 900123"]
    # A phone label wins over the date-range exemption; a bullet's own dates stay dates.
    assert contact_details("Phone: +44 20 2018-2022") == ["+44 20 2018-2022"] and contact_details("Tel: 020-2018-2022") == ["020-2018-2022"]
    assert contact_details("Ran the contact center 2018-2022") == []
    assert own_model("agy", "gemini-3.8-flash-high") and not own_model("agy", "claude-opus-4-6-thinking")
    assert own_model("claude", "opus") and own_model("codex", "gpt-6-luna") and not own_model("codex", "opus") and own_model("agy", None)
    print("self-test passed")


def main():
    if sys.argv[1:] == ["--self-test"]:
        return self_test()
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="action", required=True)
    d = sub.add_parser("detect")
    d.add_argument("--exclude", action="append", default=[], type=str.lower,
                   choices=sorted({v for v, _ in SEATS.values()}), help="the host's own vendor")
    m = sub.add_parser("models")
    m.add_argument("seat", choices=sorted(SEATS))
    r = sub.add_parser("run")
    r.add_argument("seat", choices=sorted(SEATS) + ["custom"], help="a seat name, or custom with --cmd")
    r.add_argument("--cmd", help="custom command that reads the prompt on stdin")
    r.add_argument("prompt")
    r.add_argument("reply")
    r.add_argument("--timeout", type=int, default=540, help="seconds; kept under a ten-minute shell limit")
    r.add_argument("--model", help="the seat company's own model, matched to the host's tier")
    r.add_argument("--effort", help="reasoning effort, such as low, medium or high")
    r.add_argument("--allow-contact", action="store_true", help="send even if the prompt holds an email, phone or profile link")
    a = p.parse_args()
    if a.action == "detect":
        print(json.dumps(detect(a.exclude)))
    elif a.action == "models" and a.seat == "codex" and os.path.exists(CODEX_MODELS):
        for m in json.load(open(CODEX_MODELS, encoding="utf-8")).get("models", []):
            if m.get("visibility") == "list":
                print(f"{m['slug']}\t{m.get('description', '')}")
    elif a.action == "models" and a.seat == "claude":
        print(CLAUDE_MODELS)  # Claude Code's own names for its current models
    elif a.action == "models":
        if a.seat not in LIST_MODELS:
            sys.exit(f"{a.seat} cannot list its models here; use the names in its documentation")
        r = subprocess.run(LIST_MODELS[a.seat], capture_output=True, text=True, encoding="utf-8")
        mine = [l for l in (r.stdout or "").splitlines() if own_model(a.seat, l.split()[0] if l.split() else "")]
        print("\n".join(mine) if r.stdout else r.stderr)
    elif a.seat == "custom":
        if not a.cmd:
            p.error("custom needs --cmd")
        run(shlex.split(a.cmd), a.prompt, a.reply, a.timeout, a.allow_contact)
    else:
        if not own_model(a.seat, a.model):
            sys.exit(f"{a.seat} runs only its own company's models here, not {a.model}: choose one from seats.py models {a.seat}")
        run(with_model(a.seat, SEATS[a.seat][1], a.model, a.effort), a.prompt, a.reply, a.timeout, a.allow_contact)


if __name__ == "__main__":
    main()
