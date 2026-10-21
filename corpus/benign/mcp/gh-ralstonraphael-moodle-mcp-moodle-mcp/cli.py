"""`moodle` command-line front end over the same client the MCP server uses."""

from __future__ import annotations

import argparse
import getpass
import json
import sys

from .client import CONFIG_PATH, DEFAULT_URL, Moodle, MoodleError, clear_config, load_config, parse_token, save_config

AUTH_HELP = """\
Most schools sign you in to Moodle through single sign-on, so there's no password to give this tool.
Instead it uses the same per-user token the official Moodle app gets. Two ways to grab it:

  A) Moodle → your avatar → Preferences → Security keys
     ({url}/user/managetoken.php)
     Click Reset on the "Moodle mobile web service" row; Moodle shows the new key
     once, so copy it then. If that row isn't there, sign in to the Moodle phone
     app once and it will appear.

  B) While logged in, open this in your browser:
     {url}/admin/tool/mobile/launch.php?service=moodle_mobile_app&passport=1&urlscheme=moodlemobile&confirmed=1
     Right-click "Click here to launch the app" → Copy Link Address, and paste that whole link.

The token is stored in {path} (readable only by you).
"""


def cmd_auth(args) -> None:
    cfg = load_config()
    url = (args.url or cfg.get("url") or DEFAULT_URL).rstrip("/")
    print(AUTH_HELP.format(url=url, path=CONFIG_PATH))
    raw = getpass.getpass("Paste token or launch link (hidden): ")
    try:
        token = parse_token(raw)
    except ValueError as e:
        sys.exit(f"✗ {e}")
    try:
        who = Moodle(url=url, token=token).whoami()
    except MoodleError as e:
        sys.exit(f"✗ Moodle rejected that token: {e}")
    save_config({"url": url, "token": token})
    print(f"✓ Signed in as {who['fullname']} ({who['username']}) on {who['site']}. "
          f"{who['functions_available']} web-service functions available.")


def _print(obj) -> None:
    print(json.dumps(obj, indent=2, ensure_ascii=False))


def cmd_due(args, c: Moodle) -> None:
    items = c.deadlines(args.days, args.back)
    if args.json:
        return _print(items)
    if not items:
        print(f"Nothing on the Moodle timeline for the next {args.days} days.")
    for e in items:
        flag = "OVERDUE " if e["overdue"] else ""
        print(f"{flag}{e['due']:<26} {e['course'] or '':<20} {e['name']}\n{'':27}{e['url']}")


def cmd_courses(args, c: Moodle) -> None:
    items = c.courses(args.which)
    if args.json:
        return _print(items)
    for x in items:
        print(f"{x['id']:>6}  {x['shortname']:<22} {x['fullname']}")


def cmd_assignments(args, c: Moodle) -> None:
    items = c.assignments([args.course] if args.course else None, include_status=True)
    if args.json:
        return _print(items)
    for a in items:
        status = a.get("submission", "?")
        grade = f"  grade {a['grade']}" if a.get("grade") else ""
        print(f"{(a['due'] or 'no due date'):<26} {a['course']:<20} [{status}]{grade}  {a['name']}  (assign {a['assign_id']})")


def main() -> None:
    p = argparse.ArgumentParser(prog="moodle", description="Talk to Moodle from the terminal.")
    p.add_argument("--json", action="store_true", help="raw JSON output")
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("auth", help="save your Moodle token")
    a.add_argument("--url", help=f"Moodle site (default {DEFAULT_URL})")
    sub.add_parser("logout", help="delete the saved token from this computer")
    sub.add_parser("whoami", help="check the connection")
    s = sub.add_parser("functions", help="list the web-service functions your token can call")
    s.add_argument("match", nargs="?", help="only names containing this text")
    s = sub.add_parser("courses", help="list courses with ids")
    s.add_argument("which", nargs="?", default="inprogress", choices=["inprogress", "future", "past", "all"])
    s = sub.add_parser("due", help="upcoming (and overdue) deadlines")
    s.add_argument("--days", type=int, default=14)
    s.add_argument("--back", type=int, default=14, help="days of overdue items to include")
    s = sub.add_parser("assignments", help="assignments with submission status")
    s.add_argument("course", type=int, nargs="?")
    s = sub.add_parser("contents", help="course sections and activities")
    s.add_argument("course", type=int)
    s = sub.add_parser("read", help="open an activity by cmid")
    s.add_argument("cmid", type=int)
    s = sub.add_parser("grades", help="grades for a course (or all course totals)")
    s.add_argument("course", type=int, nargs="?")
    s = sub.add_parser("file", help="print the text of a Moodle file URL")
    s.add_argument("fileurl")
    s = sub.add_parser("download", help="save a Moodle file")
    s.add_argument("fileurl")
    s.add_argument("--to", default="~/Downloads/Moodle")
    s = sub.add_parser("news", help="latest announcements")
    s = sub.add_parser("notifications", help="bell notifications")
    s = sub.add_parser("search", help="search course contents")
    s.add_argument("query")
    s = sub.add_parser("call", help="raw web-service call: moodle call fn '{\"courseid\": 1}'")
    s.add_argument("wsfunction")
    s.add_argument("params", nargs="?", default="{}")

    args = p.parse_args()
    if args.cmd == "auth":
        return cmd_auth(args)
    if args.cmd == "logout":
        print(f"✓ Removed {CONFIG_PATH}" if clear_config() else "No saved token to remove.")
        return
    try:
        c = Moodle()
        if args.cmd == "due":
            cmd_due(args, c)
        elif args.cmd == "courses":
            cmd_courses(args, c)
        elif args.cmd == "assignments":
            cmd_assignments(args, c)
        elif args.cmd == "whoami":
            _print(c.whoami())
        elif args.cmd == "functions":
            print("\n".join(c.functions(args.match)))
        elif args.cmd == "contents":
            _print(c.course_contents(args.course))
        elif args.cmd == "read":
            _print(c.read_module(args.cmid))
        elif args.cmd == "grades":
            _print(c.grades(args.course) if args.course else c.course_overview_grades())
        elif args.cmd == "file":
            print(c.file_text(args.fileurl))
        elif args.cmd == "download":
            print(c.download(args.fileurl, args.to))
        elif args.cmd == "news":
            _print(c.announcements())
        elif args.cmd == "notifications":
            _print(c.notifications())
        elif args.cmd == "search":
            _print(c.search(args.query))
        elif args.cmd == "call":
            _print(c.call(args.wsfunction, **json.loads(args.params)))
    except MoodleError as e:
        sys.exit(f"✗ {e}")


if __name__ == "__main__":
    main()
