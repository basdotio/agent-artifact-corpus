#!/usr/bin/env python3
"""Fetch the configured user's ClickUp tasks and write normalized JSON.

Read-only: every call is a GET. The token never appears in the output.

Step 0 - see what can be chosen (prints JSON, writes nothing):
  python fetch_tasks.py --discover                  # sprints, spaces, folders, lists, tags

Scope (pick ONE place, or only a period):
  --sprint latest | --sprint "Sprint 7"             # a sprint list, by dates / name / id
  --list "Backlog"                                  # any list, by name or id
  --folder "Mobile"                                 # every list in a folder
  --space "Development"                             # every list in a space
  --tag "laravel dashboard"                         # every task with this tag
  --days 7 | --since 2026-09-01 [--until ...]       # a date period. Alone, or with --list /
                                                    # --folder / --space / --tag to keep only
                                                    # the done tasks closed in the period.
With none of these, the saved default_scope is used ("latest-sprint"), if any.

Status columns:
  --peek                     print the status columns in the scope, with the user's task count
                             in each, and stop (no comments, no file). Use it to ask the user.
  --statuses "to do,qa"      keep only these columns (names as ClickUp shows them, any case)

Sprint scope: a sprint is any list with a start and a due date. "latest" is
the one with the most recent start date that has already started (a sprint
created in advance is skipped). Every task of the user in that list is
included, whatever its close date. The latest sprint of each OTHER space is
reported in scope.other_latest_sprints, so the agent can mention it.

Period scope:
  - every OPEN task assigned to the user (any age; open work is always relevant)
  - every task CLOSED/DONE inside the period
Every scope reads the latest comments of the most relevant tasks (to spot blockers).

Each task gets a bucket (done / in_progress / todo) and risk flags
(overdue, blocked, stale, over_estimate, no_due_date).
Tracked time = the user's time entries inside the period.

Exit codes: 0 ok, 2 not configured, 3 API error, 4 bad arguments.
"""
import argparse
import json
import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from clickup_client import ClickUpError, emit, get, load_config, resolve_token, utf8_stdout  # noqa: E402

DONE_TYPES = {"closed", "done"}
# Some workspaces use a status named "done" whose type is "custom"; the name decides then.
DONE_NAME_RE = re.compile(r"^(done|completed?|finished|resolved|shipped|released|deployed)$", re.I)
BLOCK_RE = re.compile(
    r"\b(blocked|blocker|blocking|on hold|waiting (on|for)(?! (qa|review|testing)\b)|stuck|depends on|not working|doesn't work"
    r"|(can ?not|cannot|can't|unable to) (be )?(test|tested|proceed|continue|deploy))\b", re.I)
STALE_DAYS = 14
PAGE_SIZE = 100
HALF_DAY_MS = 12 * 3_600_000


def local_ms(day_, end=False):
    dt = datetime(day_.year, day_.month, day_.day)
    if end:
        dt += timedelta(days=1) - timedelta(milliseconds=1)
    return int(dt.astimezone().timestamp() * 1000)


def ms_to_date(ms):
    if not ms:
        return None
    return datetime.fromtimestamp(int(ms) / 1000).astimezone().strftime("%Y-%m-%d")


def day(ms):
    # Sprint bounds are midnight / end of day in the workspace's time zone, which may differ
    # from this machine's. Moving 12 hours into the day gives the right calendar date in any zone.
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")


def one_line(text, limit):
    text = re.sub(r"\s+", " ", text or "").strip()
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def fetch_pages(path, token, params):
    tasks, page = [], 0
    while True:
        data = get(path, token, {**params, "page": page})
        batch = data.get("tasks", [])
        tasks.extend(batch)
        last = data.get("last_page")
        if not batch or last is True or (last is None and len(batch) < PAGE_SIZE) or page >= 200:
            return tasks
        page += 1


def normalize(t, spaces):
    status = t.get("status") or {}
    folder = t.get("folder") or {}
    closed_ms = int(t.get("date_closed") or t.get("date_done") or 0)
    return {
        "id": t.get("id"),
        "custom_id": t.get("custom_id"),
        "name": one_line(t.get("name"), 200),
        "url": t.get("url"),
        "status": status.get("status", ""),
        "status_type": status.get("type", ""),
        "status_color": status.get("color"),  # the column color on the ClickUp board
        "status_order": int(status.get("orderindex") or 0),  # ClickUp's order: to do → … → closed
        "space": spaces.get(str((t.get("space") or {}).get("id"))),
        "folder": None if folder.get("hidden") else folder.get("name"),
        "list": (t.get("list") or {}).get("name"),
        "priority": (t.get("priority") or {}).get("priority"),
        "tags": [x.get("name") for x in t.get("tags") or [] if x.get("name")],
        "is_subtask": bool(t.get("parent")),
        "points": t.get("points"),
        "estimate_ms": int(t.get("time_estimate") or 0),
        "tracked_ms": 0,  # filled from time entries: time the user tracked inside the period
        "created": ms_to_date(t.get("date_created")),
        "updated": ms_to_date(t.get("date_updated")),
        "start": ms_to_date(t.get("start_date")),
        "due": ms_to_date(t.get("due_date")),
        "closed": ms_to_date(closed_ms),
        "description": one_line(t.get("text_content"), 4000),
        "updated_ms": int(t.get("date_updated") or 0),
        "due_ms": int(t.get("due_date") or 0),
        "closed_ms": closed_ms,
    }


def find_structure(team_id, token, with_tags=False):
    """Every space, folder and list. A list with a start and a due date is a sprint."""
    spaces, folders, lists = [], [], []
    for space in get(f"/team/{team_id}/space", token, {"archived": "false"}).get("spaces", []):
        entry = {"id": str(space["id"]), "name": space.get("name")}
        if with_tags:
            try:
                entry["tags"] = [t.get("name") for t in get(f"/space/{space['id']}/tag", token).get("tags", [])]
            except ClickUpError:
                entry["tags"] = []
        spaces.append(entry)
        pairs = []
        for folder in get(f"/space/{space['id']}/folder", token, {"archived": "false"}).get("folders", []):
            folders.append({"id": str(folder["id"]), "name": folder.get("name"), "space": space.get("name")})
            pairs += [(folder, lst) for lst in folder.get("lists", [])]
        pairs += [(None, lst) for lst in get(f"/space/{space['id']}/list", token, {"archived": "false"}).get("lists", [])]
        for folder, lst in pairs:
            lists.append({"id": str(lst["id"]), "name": lst.get("name"),
                          "folder": folder.get("name") if folder else None,
                          "space": space.get("name"),
                          "start_ms": int(lst.get("start_date") or 0), "due_ms": int(lst.get("due_date") or 0),
                          "task_count": lst.get("task_count")})
    return spaces, folders, lists


def is_sprint(lst):
    return bool(lst["start_ms"] and lst["due_ms"])


def match_one(items, wanted, kind):
    """Find one item by id, exact name, then part of the name. Raise ValueError for the user."""
    wanted = wanted.strip()
    matches = [i for i in items if i["id"] == wanted]
    matches = matches or [i for i in items if (i["name"] or "").lower() == wanted.lower()]
    matches = matches or [i for i in items if wanted.lower() in (i["name"] or "").lower()]
    if not matches:
        raise ValueError(f"no {kind} matches {wanted!r}")
    if len(matches) > 1:
        raise ValueError(f"several {kind}s match: " + "; ".join(
            f"{i['id']} {i['name']} ({i.get('space') or ''})" for i in matches[:15]) + ". Use the id.")
    return matches[0]


def public_sprint(s):
    return {"id": s["id"], "name": s["name"], "folder": s["folder"], "space": s["space"],
            "start": day(s["start_ms"] + HALF_DAY_MS), "due": day(s["due_ms"] - HALF_DAY_MS)}


def pick_sprint(sprints, wanted, now_ms):
    """Return (sprint, other_latest_sprints). Raise ValueError with a message for the user."""
    if wanted.lower() == "latest":
        started = [s for s in sprints if s["start_ms"] <= now_ms]
        if not started:
            raise ValueError("no started sprint found (no list has a start date in the past)")
        chosen = max(started, key=lambda s: s["start_ms"])
        latest_per_space = {}
        for s in started:
            best = latest_per_space.get(s["space"])
            if s["space"] != chosen["space"] and (best is None or s["start_ms"] > best["start_ms"]):
                latest_per_space[s["space"]] = s
        return public_sprint(chosen), [public_sprint(s) for s in latest_per_space.values()]
    return public_sprint(match_one(sprints, wanted, "sprint")), []


def discover(team_id, token, now_ms):
    """What the user can choose from: sprints (newest first), spaces with tags, folders, lists."""
    spaces, folders, lists = find_structure(team_id, token, with_tags=True)
    sprints = sorted((l for l in lists if is_sprint(l)), key=lambda l: -l["start_ms"])
    started = [s for s in sprints if s["start_ms"] <= now_ms]
    return {
        "ok": True,
        "latest_sprint": public_sprint(started[0]) if started else None,
        "sprints": [{**public_sprint(s), "started": s["start_ms"] <= now_ms} for s in sprints[:12]],
        "spaces": spaces,
        "folders": folders,
        "lists": [{"id": l["id"], "name": l["name"], "space": l["space"], "folder": l["folder"],
                   "task_count": l["task_count"]} for l in lists if not is_sprint(l)],
    }


def classify(task, since_ms, until_ms, now_ms):
    """Return the bucket, or None when the task is outside the report."""
    if task["status_type"] in DONE_TYPES or DONE_NAME_RE.match(task["status"].strip()):
        ref = task["closed_ms"] or task["updated_ms"]
        return "done" if since_ms <= ref <= until_ms else None
    return "todo" if task["status_type"] == "open" else "in_progress"


def flag(task, now_ms):
    flags = []
    open_task = task["bucket"] != "done"
    if open_task and task["due_ms"] and task["due_ms"] < now_ms:
        flags.append("overdue")
    if open_task and not task["due_ms"]:
        flags.append("no_due_date")
    if open_task and BLOCK_RE.search(task["status"]):
        flags.append("blocked")
    if task["bucket"] == "in_progress" and task["updated_ms"] < now_ms - STALE_DAYS * 86_400_000:
        flags.append("stale")
    return flags


def add_tracked_time(tasks, team_id, user_id, token, since_ms, until_ms, warnings):
    """Task objects carry no tracked time, so sum the user's time entries in the period."""
    try:
        entries = get(f"/team/{team_id}/time_entries", token, {
            "start_date": since_ms, "end_date": until_ms, "assignee": user_id}).get("data", [])
    except ClickUpError as err:
        warnings.append(f"tracked time unavailable: {err}")
        return
    per_task = {}
    for entry in entries:
        task_id = (entry.get("task") or {}).get("id") if isinstance(entry.get("task"), dict) else None
        duration = int(entry.get("duration") or 0)
        if task_id and duration > 0:  # a running timer has a negative duration
            per_task[task_id] = per_task.get(task_id, 0) + duration
    for task in tasks:
        task["tracked_ms"] = per_task.get(task["id"], 0)
    if not entries:
        warnings.append("no time entries in this period (time tracking not used, so tracked time shows —)")


def add_comments(tasks, token, limit, warnings):
    order = {"in_progress": 0, "todo": 1, "done": 2}
    picked = sorted(tasks, key=lambda t: (order[t["bucket"]], -t["updated_ms"]))[:limit]
    for task in picked:
        try:
            comments = get(f"/task/{task['id']}/comment", token).get("comments", [])
        except ClickUpError as err:
            warnings.append(f"comments skipped for {task['id']}: {err}")
            continue
        comments = sorted(comments, key=lambda c: int(c.get("date") or 0), reverse=True)[:5]
        task["recent_comments"] = [{
            "by": (c.get("user") or {}).get("username"),
            "date": ms_to_date(c.get("date")),
            "text": one_line(c.get("comment_text"), 600),
        } for c in comments]
        if task["bucket"] != "done" and "blocked" not in task["flags"] and any(
                BLOCK_RE.search(c["text"]) for c in task["recent_comments"]):
            task["flags"].append("blocked_in_comment")
    if len(tasks) > limit:
        warnings.append(f"comments read for {limit} of {len(tasks)} tasks (raise --max-comment-tasks for more)")


def status_columns(tasks):
    """The status columns seen in the scope, in ClickUp's order, with the user's task count in each."""
    columns = {}
    for t in tasks:
        col = columns.setdefault(t["status"], {"name": t["status"], "type": t["status_type"],
                                               "color": t["status_color"], "order": t["status_order"], "count": 0})
        col["count"] += 1
        col["order"] = min(col["order"], t["status_order"])
    return sorted(columns.values(), key=lambda c: (c["order"], c["name"].lower()))


def main():
    utf8_stdout()
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--discover", action="store_true", help="print sprints, spaces, folders, lists and tags; stop")
    p.add_argument("--sprint", help='"latest" or a sprint (list) name or id')
    p.add_argument("--list", dest="list_", help="any list, by name or id")
    p.add_argument("--folder", help="a folder, by name or id (all of its lists)")
    p.add_argument("--space", help="a space, by name or id")
    p.add_argument("--tag", help="a tag name")
    p.add_argument("--days", type=int, help="period = the last N days, today included")
    p.add_argument("--since", help="YYYY-MM-DD (local time)")
    p.add_argument("--until", help="YYYY-MM-DD (local time, default today)")
    p.add_argument("--statuses", help="comma-separated status columns to keep (default: all)")
    p.add_argument("--peek", action="store_true", help="print the status columns in the scope and stop")
    p.add_argument("--out", help="where to write the JSON (required unless --discover or --peek)")
    p.add_argument("--max-comment-tasks", type=int, default=40, help="0 turns comments off")
    args = p.parse_args()

    cfg = load_config()
    token = resolve_token(cfg)
    if not cfg or not token or not cfg.get("user_id") or not cfg.get("team_id"):
        emit({"ok": False, "error": "NOT_CONFIGURED", "hint": "run setup_config.py first"})
        return 2

    now_ms = int(datetime.now().timestamp() * 1000)
    team_id, user_id = cfg["team_id"], cfg["user_id"]

    if args.discover:
        try:
            emit(discover(team_id, token, now_ms))
        except ClickUpError as err:
            emit({"ok": False, "error": str(err)})
            return 3
        return 0

    places = [x for x in (args.sprint, args.list_, args.folder, args.space, args.tag) if x]
    if len(places) > 1:
        emit({"ok": False, "error": "bad scope: give only one of --sprint, --list, --folder, --space, --tag"})
        return 4
    if not args.out and not args.peek:
        emit({"ok": False, "error": "bad arguments: --out is required (or use --peek)"})
        return 4
    has_period = bool(args.days or args.since)
    sprint_arg = args.sprint
    if not (places or has_period):
        if cfg.get("default_scope") == "latest-sprint":
            sprint_arg = "latest"
        else:
            emit({"ok": False, "error": "bad scope: give --sprint, --list, --folder, --space, --tag, --days or --since"})
            return 4

    warnings = []
    since = until = None
    if has_period:
        try:
            until = date.fromisoformat(args.until) if args.until else date.today()
            since = date.fromisoformat(args.since) if args.since else until - timedelta(days=args.days - 1)
            if since > until:
                raise ValueError("--since is after --until")
        except ValueError as err:
            emit({"ok": False, "error": f"bad period: {err}"})
            return 4

    scope = {"type": "period"}
    try:
        spaces = {}
        try:
            spaces = {str(s["id"]): s.get("name") for s in get(f"/team/{team_id}/space", token).get("spaces", [])}
        except ClickUpError as err:
            warnings.append(f"space names unavailable: {err}")
        base = {"assignees[]": [user_id], "subtasks": "true"}

        if sprint_arg:
            try:
                sprint, others = pick_sprint([l for l in find_structure(team_id, token)[2] if is_sprint(l)],
                                             sprint_arg, now_ms)
            except ValueError as err:
                emit({"ok": False, "error": f"bad sprint: {err}"})
                return 4
            scope = {"type": "sprint", "sprint": sprint, "other_latest_sprints": others}
            since, until = date.fromisoformat(sprint["start"]), date.fromisoformat(sprint["due"])
            raw = fetch_pages(f"/list/{sprint['id']}/task", token, {**base, "include_closed": "true"})
            # Everything in the sprint list belongs to the sprint, whatever its close date.
            classify_since, classify_until = float("-inf"), float("inf")
        elif places:
            kind = "list" if args.list_ else "folder" if args.folder else "space" if args.space else "tag"
            if kind == "tag":
                target, params = {"name": args.tag}, {"tags[]": [args.tag]}
            else:
                space_list, folder_list, list_list = find_structure(team_id, token)
                pool = {"list": list_list, "folder": folder_list, "space": space_list}[kind]
                try:
                    found = match_one(pool, args.list_ or args.folder or args.space, kind)
                except ValueError as err:
                    emit({"ok": False, "error": f"bad {kind}: {err}"})
                    return 4
                target = {k: found.get(k) for k in ("id", "name", "space", "folder")}
                param = {"list": "list_ids[]", "folder": "project_ids[]", "space": "space_ids[]"}[kind]
                params = {param: [found["id"]]}
            scope = {"type": kind, "target": target}
            raw = fetch_pages(f"/team/{team_id}/task", token, {**base, **params, "include_closed": "true"})
            if has_period:
                scope["period_filter"] = True
                classify_since, classify_until = local_ms(since), local_ms(until, end=True)
            else:
                # No period: the whole place. The period only bounds the tracked-time lookup.
                classify_since, classify_until = float("-inf"), float("inf")
                created = [int(t["date_created"]) for t in raw if t.get("date_created")]
                until = date.today()
                since = datetime.fromtimestamp(min(created) / 1000).date() if created else until - timedelta(days=29)
        else:
            classify_since, classify_until = local_ms(since), local_ms(until, end=True)
            raw = fetch_pages(f"/team/{team_id}/task", token, {**base, "include_closed": "false"})
            # Closed tasks: only those touched since the period start; classify() filters by close date.
            raw += fetch_pages(f"/team/{team_id}/task", token,
                               {**base, "include_closed": "true", "date_updated_gt": classify_since})
    except ClickUpError as err:
        emit({"ok": False, "error": str(err)})
        return 3
    since_ms, until_ms = local_ms(since), local_ms(until, end=True)

    tasks, seen = [], set()
    for t in raw:
        if t.get("id") in seen or t.get("archived"):
            continue
        seen.add(t.get("id"))
        task = normalize(t, spaces)
        task["bucket"] = classify(task, classify_since, classify_until, now_ms)
        if task["bucket"]:
            task["flags"] = flag(task, now_ms)
            tasks.append(task)

    columns = status_columns(tasks)
    period = {"since": since.isoformat(), "until": until.isoformat()}
    if args.peek:
        emit({"ok": True, "peek": True, "scope": scope, "period": period, "total": len(tasks),
              "status_columns": columns, "warnings": warnings})
        return 0

    if args.statuses:
        status_filter = [s.strip() for s in args.statuses.split(",") if s.strip()]
        known = {c["name"].lower() for c in columns}
        for s in status_filter:
            if s.lower() not in known:
                warnings.append(f"no task of the user in status column {s!r} in this scope")
        wanted = {s.lower() for s in status_filter}
        tasks = [t for t in tasks if t["status"].lower() in wanted]
        scope["status_filter"] = status_filter

    add_tracked_time(tasks, team_id, user_id, token, since_ms, until_ms, warnings)
    for task in tasks:
        if task["estimate_ms"] and task["tracked_ms"] > task["estimate_ms"]:
            task["flags"].append("over_estimate")

    if args.max_comment_tasks > 0:
        add_comments(tasks, token, args.max_comment_tasks, warnings)

    counts = {b: sum(1 for t in tasks if t["bucket"] == b) for b in ("done", "in_progress", "todo")}
    result = {
        "meta": {
            "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "period": period,
            "scope": scope,
            "user": {"id": user_id, "name": cfg.get("user_name")},
            "workspace": {"id": team_id, "name": cfg.get("team_name")},
            "language": cfg.get("language", "Arabic"),
            "group_by": cfg.get("group_by", "list"),
            "report_dir": cfg.get("report_dir"),
            "counts": counts,
            "warnings": warnings,
        },
        "tasks": tasks,
    }
    out = Path(args.out).expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    emit({"ok": True, "out": str(out), "scope": scope, "period": period, "counts": counts,
          "task_ids": [t["id"] for t in tasks], "warnings": warnings})
    return 0


if __name__ == "__main__":
    sys.exit(main())
