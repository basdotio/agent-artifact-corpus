"""Render scrub results as tables: box-drawn for a terminal, pipe tables for markdown.

Everything rendered here comes from findings that never held a secret: kind, length,
public prefix, and a context snippet cut from the already-redacted text.
"""
from __future__ import annotations

import re
from collections import Counter, defaultdict
from pathlib import Path

# Known vendor formats: if one of these turns up, it is a real credential.
CERTAIN = {
    "private_key", "anthropic_key", "openai_key", "github_token", "gitlab_token",
    "aws_access_key_id", "google_api_key", "google_oauth_token", "google_client_secret",
    "slack_token", "slack_webhook", "discord_webhook", "stripe_key", "stripe_webhook_secret",
    "telegram_bot_token", "huggingface_token", "npm_token", "pypi_token", "sendgrid_key",
    "twilio_key", "digitalocean_token", "mailgun_key", "url_password", "literal",
}
CONFIDENCE = {
    "password": "likely", "secret_assignment": "likely", "auth_header": "likely",
    "bearer_token": "likely", "jwt": "likely", "url_token": "link token",
    "high_entropy": "guess",
}
ROLE = {
    "user": "you", "tool_result": "tool output", "assistant": "Claude",
    "meta": "session data", "file": "file", "unparsed": "damaged line",
}
UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


def confidence(kind: str) -> str:
    return "certain" if kind in CERTAIN else CONFIDENCE.get(kind, "likely")


def where(path: str) -> str:
    p = Path(path)
    stem = p.stem[:8] + "…" if UUID_RE.match(p.stem) else p.stem[:22]
    parent = p.parent.name
    if parent == "subagents" and UUID_RE.match(p.parent.parent.name):  # "<session>/subagents/agent-x"
        parent = p.parent.parent.name[:8] + "…/sub"
    if parent.startswith("-"):  # Claude project dirs: "-Users-sam-webapp" -> "webapp"
        parent = re.sub(r"^-(Users|home)-[^-]+-?", "", parent) or "~"
    return f"{parent}/{stem}{p.suffix}"


def duration(seconds: float) -> str:
    m, s = divmod(int(round(seconds)), 60)
    return f"{m}m {s:02d}s" if m else f"{seconds:.1f}s"


def _cut(s: str, n: int) -> str:
    s = s.replace("|", "¦")
    return s if len(s) <= n else s[: n - 1] + "…"


def table(headers, rows, right=(), md=False, widths=None) -> str:
    widths = widths or [60] * len(headers)
    rows = [[_cut(str(c), widths[i]) for i, c in enumerate(r)] for r in rows]
    if md:
        out = ["| " + " | ".join(headers) + " |",
               "|" + "|".join("---:" if i in right else "---" for i in range(len(headers))) + "|"]
        out += ["| " + " | ".join(r) + " |" for r in rows]
        return "\n".join(out)
    w = [max(len(str(h)), *(len(r[i]) for r in rows)) if rows else len(h) for i, h in enumerate(headers)]
    fmt = lambda r: "│ " + " │ ".join(  # noqa: E731
        (c.rjust(w[i]) if i in right else c.ljust(w[i])) for i, c in enumerate(r)) + " │"
    line = lambda l, m, r: l + m.join("─" * (x + 2) for x in w) + r  # noqa: E731
    return "\n".join([line("┌", "┬", "┐"), fmt(headers), line("├", "┼", "┤"),
                      *[fmt(r) for r in rows], line("└", "┴", "┘")])


def _h(text: str, md: bool) -> str:
    return f"### {text}" if md else text.upper()


def _by_kind(findings):
    g = defaultdict(list)
    for f in findings:
        g[f["kind"]].append(f)
    order = sorted(g, key=lambda k: (confidence(k) != "certain", -len(g[k])))
    return g, order


def _sources(fs) -> str:
    c = Counter(ROLE.get(f["role"], f["role"]) for f in fs)
    return ", ".join(f"{k} {v}" for k, v in c.most_common())


def _label(kind: str, fs) -> str:
    pre = next((f["prefix"] for f in fs if f["prefix"]), "")
    return f"{kind} ({pre}…)" if pre else kind


def findings_report(summary, findings, next_cmd: str, md: bool) -> str:
    s, out = summary, []
    head = "Dry run, nothing changed" if s["mode"] == "dry-run" else "Applied"
    out.append(f"**scrub-transcripts: {head}**" if md else f"scrub-transcripts: {head}")
    out.append(f"Scanned {s['files_scanned']:,} files in {duration(s['seconds'])}. "
               f"Found {s['findings']:,} secrets in {s['files_with_findings']:,} files.")
    if not findings:
        out.append("Nothing to redact.")
        out += _skipped_note(s, md)
        return "\n\n".join(out) + "\n"

    g, order = _by_kind(findings)
    rows = [(_label(k, g[k]), f"{len(g[k]):,}", f"{len({f['file'] for f in g[k]}):,}",
             confidence(k), _sources(g[k])) for k in order]
    out.append(_h("What was found", md))
    out.append(table(["Secret", "Found", "Files", "Confidence", "Where it came from"],
                     rows, right=(1, 2), md=md))

    ex = []
    for k in order:
        f = next((x for x in g[k] if x["snippet"]), g[k][0])
        ex.append((k, f"{where(f['file'])}:{f['line']}", f["snippet"]))
    out.append(_h("One example of each (already redacted)", md))
    out.append(table(["Secret", "File", "Context"], ex, md=md, widths=[24, 36, 90]))

    steps = []
    certain = [k for k in order if confidence(k) == "certain"]
    likely = [k for k in order if confidence(k) != "certain"]
    steps.append("Skim the table. \"certain\" rows are real credentials. \"likely\" rows are "
                 "labelled values, so a few may be harmless (redacting those costs nothing).")
    steps.append(f"Redact them: `{next_cmd}`" if md else f"Redact them:  {next_cmd}")
    if certain:
        steps.append("Rotate these, because redacting the logs doesn't un-send them: "
                     + ", ".join(certain) + ".")
    if likely:
        steps.append("Check whether any of these are live and rotate the ones that are: "
                     + ", ".join(likely) + ".")
    out.append(_h("Next steps", md))
    out.append("\n".join(f"{i}. {t}" for i, t in enumerate(steps, 1)))
    out += _skipped_note(s, md)
    return "\n\n".join(out) + "\n"


def applied_report(summary, findings, remaining: int, report_path: str | None, md: bool) -> str:
    s, out = summary, []
    out.append("**scrub-transcripts: Done**" if md else "scrub-transcripts: Done")
    out.append(f"Replaced {s['findings']:,} secrets in {s['files_rewritten']:,} files "
               f"({duration(s['seconds'])}). Re-scan of the changed files: "
               + ("0 secrets left." if remaining == 0 else f"{remaining} still found, see below."))
    if not findings:
        out += _skipped_note(s, md)
        return "\n\n".join(out) + "\n"

    g, order = _by_kind(findings)
    out.append(_h("What replaced them", md))
    out.append(table(["Replaced with", "Count", "Files", "Was"],
                     [(f"[REDACTED:{k}]", f"{len(g[k]):,}", f"{len({f['file'] for f in g[k]}):,}",
                       _label(k, g[k]) + f", {confidence(k)}") for k in order],
                     right=(1, 2), md=md))

    per_file = defaultdict(list)
    for f in findings:
        per_file[f["file"]].append(f)
    top = sorted(per_file, key=lambda p: -len(per_file[p]))[:15]
    out.append(_h(f"Files changed (top {len(top)} of {len(per_file):,})", md))
    out.append(table(["File", "Replaced", "Markers"],
                     [(where(p), str(len(per_file[p])),
                       ", ".join(f"{k}×{n}" for k, n in Counter(f["kind"] for f in per_file[p]).most_common()))
                      for p in top], right=(1,), md=md, widths=[40, 8, 70]))

    ex = []
    for k in order:
        f = next((x for x in g[k] if x["snippet"]), g[k][0])
        ex.append((f"{where(f['file'])}:{f['line']}", f["snippet"]))
    out.append(_h("How the lines read now", md))
    out.append(table(["File", "Now reads"], ex, md=md, widths=[36, 100]))

    steps = []
    certain = [k for k in order if confidence(k) == "certain"]
    if certain:
        steps.append("Rotate the real credentials, since they were sent to the API before this ran: "
                     + ", ".join(certain) + ".")
    if s["skipped_active"]:
        steps.append(f"{len(s['skipped_active'])} open session file(s) were skipped. Re-run with "
                     "`--since 1` after closing them.")
    if remaining:
        steps.append(f"{remaining} finding(s) survived the re-scan. Run a dry run on the same scope to see them.")
    if report_path:
        steps.append(f"This report is saved at `{report_path}`." if md else f"This report is saved at {report_path}")
    if steps:
        out.append(_h("Next steps", md))
        out.append("\n".join(f"{i}. {t}" for i, t in enumerate(steps, 1)))
    return "\n\n".join(out) + "\n"


def _skipped_note(s, md):
    notes = []
    if s["skipped_active"]:
        notes.append(f"Skipped {len(s['skipped_active'])} file(s) changed in the last few minutes, "
                     "because a live session may still be writing to them.")
    for e in s["errors"]:
        notes.append(f"Error in {e['file']}: {e['error']}")
    return notes
