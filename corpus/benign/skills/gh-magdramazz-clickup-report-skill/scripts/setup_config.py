#!/usr/bin/env python3
"""Create, check, or update the clickup-report config.

Modes (all print one JSON object):
  --status      Is the skill configured? The token is shown masked.
                Exit 0 = configured, 2 = not configured.
  --discover    With a token: who owns it, and which workspaces it can see
                (with member ids). Saves nothing. Helps a user who does not
                know their ids.
  (default)     Validate and save. Needs --user-id, --team-id and a token,
                except values already saved (so preferences can be changed
                alone, e.g. --language Arabic).
  --reset       Delete the saved config.

Token input, most private first:
  1. Run with no flags in your OWN terminal: you get a hidden prompt.
  2. --token-stdin   read the token from standard input.
  3. --token VALUE   ends up in shell history; avoid.

Validation problems (unknown workspace, user not in workspace, user id is not
the token owner) block the save and are listed in "problems". Re-run with
--force only after the user has confirmed the values are right.
"""
import argparse
import getpass
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from clickup_client import (ClickUpError, config_path, emit, get, load_config,  # noqa: E402
                            mask, save_config, utf8_stdout)

GROUP_CHOICES = ("list", "folder", "space", "tag", "status")
DEFAULTS = {
    "report_dir": str(Path.home() / "clickup-reports"),
    "language": "Arabic",
    "group_by": "list",
    "default_scope": "ask",
}


def public_view(cfg):
    view = {k: v for k, v in cfg.items() if k != "token"}
    view["token"] = mask(cfg.get("token", ""))
    return view


def discover(token):
    owner = get("/user", token).get("user", {})
    teams = get("/team", token).get("teams", [])
    return {
        "token_owner": {"id": str(owner.get("id")), "username": owner.get("username"),
                        "email": owner.get("email")},
        "workspaces": [{
            "team_id": str(t.get("id")),
            "name": t.get("name"),
            "members": [{"id": str((m.get("user") or {}).get("id")),
                         "username": (m.get("user") or {}).get("username")}
                        for m in t.get("members", [])],
        } for t in teams],
    }


def validate(token, user_id, team_id):
    info = discover(token)
    problems = []
    team = next((t for t in info["workspaces"] if t["team_id"] == team_id), None)
    user_name = None
    if team is None:
        visible = ", ".join(f"{t['team_id']} ({t['name']})" for t in info["workspaces"]) or "none"
        problems.append(f"Workspace {team_id} is not visible to this token. Visible: {visible}.")
    else:
        member = next((m for m in team["members"] if m["id"] == user_id), None)
        if member is None:
            problems.append(f"User {user_id} is not a member of workspace {team_id} ({team['name']}).")
        else:
            user_name = member["username"]
    owner = info["token_owner"]
    if owner["id"] != user_id:
        problems.append(f"User id {user_id} is not the token owner ({owner['id']}, {owner['username']}). "
                        "The report would list another person's tasks.")
    return problems, (team or {}).get("name"), user_name or (owner["username"] if owner["id"] == user_id else None)


def read_token(args, interactive):
    if args.token_stdin:
        return sys.stdin.readline().strip()
    if args.token:
        return args.token.strip()
    if interactive:
        return getpass.getpass("ClickUp API token (hidden): ").strip()
    return ""


def main():
    utf8_stdout()
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--status", action="store_true")
    p.add_argument("--discover", action="store_true")
    p.add_argument("--reset", action="store_true")
    p.add_argument("--user-id")
    p.add_argument("--team-id", help="workspace id (the number in app.clickup.com/<id>/...)")
    p.add_argument("--token")
    p.add_argument("--token-stdin", action="store_true")
    p.add_argument("--report-dir")
    p.add_argument("--language")
    p.add_argument("--group-by", choices=GROUP_CHOICES)
    p.add_argument("--default-scope", choices=("latest-sprint", "ask"),
                   help="what a report covers when the user names no period")
    p.add_argument("--force", action="store_true", help="save despite validation problems")
    args = p.parse_args()

    existing = load_config() or {}

    if args.status:
        if not existing:
            emit({"configured": False, "config_path": str(config_path())})
            return 2
        emit({"configured": True, "config_path": str(config_path()), **public_view(existing)})
        return 0

    if args.reset:
        path = config_path()
        if path.exists():
            path.unlink()
        emit({"reset": True, "config_path": str(path)})
        return 0

    interactive = sys.stdin.isatty() and len(sys.argv) == 1
    if interactive:
        print("clickup-report setup. Press Enter to keep a saved value.")
        args.user_id = input(f"ClickUp user id [{existing.get('user_id', '')}]: ").strip() or None
        args.team_id = input(f"Workspace (team) id [{existing.get('team_id', '')}]: ").strip() or None

    token = read_token(args, interactive)

    if args.discover:
        token = token or existing.get("token", "")
        if not token:
            emit({"ok": False, "error": "no token given (use --token-stdin)"})
            return 4
        try:
            emit({"ok": True, **discover(token)})
        except ClickUpError as err:
            emit({"ok": False, "error": str(err)})
            return 3
        return 0

    cfg = dict(existing)
    for key, value in (("user_id", args.user_id), ("team_id", args.team_id), ("token", token)):
        if value:
            cfg[key] = str(value).strip()
    for key, value in (("report_dir", args.report_dir), ("language", args.language), ("group_by", args.group_by),
                       ("default_scope", args.default_scope)):
        if value:
            cfg[key] = value
    for key, value in DEFAULTS.items():
        cfg.setdefault(key, value)

    missing = [k for k in ("user_id", "team_id", "token") if not cfg.get(k)]
    if missing:
        emit({"ok": False, "missing": missing})
        return 4

    identity_changed = any(cfg.get(k) != existing.get(k) for k in ("user_id", "team_id", "token"))
    if identity_changed:
        try:
            problems, team_name, user_name = validate(cfg["token"], cfg["user_id"], cfg["team_id"])
        except ClickUpError as err:
            emit({"ok": False, "saved": False, "error": str(err)})
            return 3
        if problems and not args.force:
            emit({"ok": False, "saved": False, "problems": problems})
            return 5
        cfg["team_name"] = team_name or cfg.get("team_name")
        cfg["user_name"] = user_name or cfg.get("user_name")

    cfg["version"] = 1
    cfg["saved_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
    path = save_config(cfg)
    emit({"ok": True, "saved": True, "config_path": str(path), **public_view(cfg)})
    return 0


if __name__ == "__main__":
    sys.exit(main())
