"""MCP server exposed over Server-Sent Events (SSE).

Every tool requires an ``auth_token`` (a JWT). The token is decoded to find the
owning user so tools only ever touch that user's data.
"""
import json
import os

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from sqlalchemy.orm import Session

from ..auth import decode_access_token, get_user_by_mcp_token
from ..db import SessionLocal
from ..models import Task, User
from ..services import task_service
from ..services.task_service import advance_deadline, cycle_log, regenerate_cycle

mcp = FastMCP("OmniTask")


def _session() -> Session:
    return SessionLocal()


def get_user_from_token(token: str) -> User | None:
    """Resolve a user from either a JWT or a long-lived MCP API key."""
    # Standard JWT first (short-lived, stored statelessly).
    payload = decode_access_token(token)
    if payload and payload.get("sub"):
        db = _session()
        try:
            return db.query(User).filter(User.username == payload["sub"]).first()
        finally:
            db.close()
    # Fall back to the long-lived MCP API key (stored hashed on the user).
    db = _session()
    try:
        return get_user_by_mcp_token(db, token)
    finally:
        db.close()


def _extract_args(kwargs: dict) -> dict:
    """Helper to handle FastMCP's inconsistent argument wrapping.
    If arguments are wrapped in an 'args' key, unwrap them.
    """
    if "args" in kwargs and isinstance(kwargs["args"], dict):
        return kwargs["args"]
    return kwargs


def _parse_dt(value):
    """Normalize an incoming date/datetime (MCP tools receive plain JSON
    strings, e.g. '2026-10-12' or '2026-10-12T18:00:00Z') into a Python
    date/datetime object — SQLite DateTime columns reject raw strings."""
    if value is None or not isinstance(value, str):
        return value
    from datetime import date as _date, datetime as _datetime

    s = value.strip()
    if not s:
        return None
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        return _datetime.fromisoformat(s)
    except ValueError:
        pass
    try:
        return _date.fromisoformat(s)
    except ValueError:
        raise ValueError(
            f"Неправильный формат даты: {value!r} "
            "(ожидается ГГГГ-ММ-ДД или ISO 8601)"
        ) from None


def _parse_task_dates(data: dict) -> dict:
    """Parse date fields in an MCP task payload in place."""
    for key in ("start_date", "deadline"):
        if key in data:
            data[key] = _parse_dt(data[key])
    return data


@mcp.tool()
def get_my_profile(auth_token: str) -> str:
    """Get information about the current authenticated user (ID, role)."""
    user = get_user_from_token(auth_token)
    if not user:
        return "Error: Invalid or missing authentication token"
    return f"User: {user.username}, ID: {user.id}, Role: {user.role}"


@mcp.tool()
def list_boards(auth_token: str) -> str:
    """List the user's boards (workspaces). Every other tool requires a
    board_id from this list — tasks, lists and tags are strictly per-board."""
    from ..models import Board

    user = get_user_from_token(auth_token)
    if not user:
        return "Error: Invalid or missing authentication token"
    db = _session()
    try:
        boards = (
            db.query(Board)
            .filter(Board.user_id == user.id)
            .order_by(Board.position, Board.id)
            .all()
        )
        result = [
            {"id": b.id, "name": b.name, "color": b.color, "description": b.description}
            for b in boards
        ]
        return json.dumps(result)
    finally:
        db.close()


@mcp.tool()
def list_all_lists(auth_token: str, board_id: int) -> str:
    """List all available task lists (categories) of the given board and their corresponding statuses."""
    from ..board import status_for_kind
    from ..models import Board, TaskList

    user = get_user_from_token(auth_token)
    if not user:
        return "Error: Invalid or missing authentication token"
    db = _session()
    try:
        board = (
            db.query(Board)
            .filter(Board.id == board_id, Board.user_id == user.id)
            .first()
        )
        if not board:
            return "Error: Board not found"
        rows = (
            db.query(TaskList)
            .filter(TaskList.user_id == user.id, TaskList.board_id == board_id)
            .order_by(TaskList.position)
            .all()
        )
        lists_str = "\n".join(
            [
                f"- {lst.name} (kind: {lst.kind or 'todo'}, status: {status_for_kind(lst.kind)})"
                for lst in rows
            ]
        )
        return f"Available lists on board '{board.name}':\n{lists_str}"
    finally:
        db.close()


@mcp.tool()
def list_tasks(auth_token: str, board_id: int, status: str | None = None, cyclic: bool | None = None) -> str:
    """List tasks of the given board. Optional status filter and cyclic filter (True = only cyclic tasks, False = only non-cyclic)."""
    user = get_user_from_token(auth_token)
    if not user:
        return "Error: Invalid or missing authentication token"
    db = _session()
    try:
        from ..models import Board

        if not db.query(Board).filter(Board.id == board_id, Board.user_id == user.id).first():
            return "Error: Board not found"
        tasks = task_service.list_tasks(db, user, status=status, board_id=board_id)
        if cyclic is not None:
            tasks = [t for t in tasks if bool(t.is_cyclic) == cyclic]
        result = []
        for t in tasks:
            result.append(
                {
                    "id": t.id,
                    "board_id": t.board_id,
                    "title": t.title,
                    "description": t.description,
                    "status": t.status,
                    "priority": t.priority,
                    "start_date": str(t.start_date) if t.start_date else None,
                    "deadline": str(t.deadline) if t.deadline else None,
                    "list": t.list,
                    "amount": float(t.amount or 0),
                    "tags": [tg.name for tg in t.tags],
                    "blocked_by": t.blocked_by,
                    "is_cyclic": bool(t.is_cyclic),
                    "cycle_period": t.cycle_period,
                    "cycle_interval": t.cycle_interval,
                    "cycle_group_id": t.cycle_group_id,
                    "reminder_days": t.reminder_days,
                    "cycle_dormant": t.cycle_dormant,
                }
            )
        return json.dumps(result)
    finally:
        db.close()


@mcp.tool()
def create_task(
    auth_token: str,
    board_id: int,
    title: str,
    description: str | None = None,
    start_date: str | None = None,
    deadline: str | None = None,
    priority: int = 2,
    tags: list[str] | None = None,
    list: str = "Не начато",
    blocked_by: list[int] | None = None,
    is_cyclic: bool = False,
    cycle_period: str = "monthly",
    cycle_interval: int = 1,
    reminder_days: int = 0,
    amount: float = 0.0,
) -> str:
    """Create a new task on the given board. Priority scale: 1 = Low, 2 = Medium, 3 = High.
    Dates (start_date, deadline) accept 'YYYY-MM-DD' or ISO 8601 strings.
    Cyclic tasks: cycle_period is daily|weekly|monthly|yearly, cycle_interval = every N periods,
    reminder_days = days before deadline when the task becomes visible in the main lists."""
    data = _extract_args(locals())
    _parse_task_dates(data)

    token = data.get("auth_token")
    t_title = data.get("title")
    t_desc = data.get("description")
    t_start = data.get("start_date")
    t_dead = data.get("deadline")
    t_prio = data.get("priority", 2)
    t_tags = data.get("tags")
    t_list = data.get("list", "Не начато")
    t_blocked = data.get("blocked_by")

    if not token or not t_title or data.get("board_id") is None:
        return "Error: Missing required parameters (auth_token, board_id, title)"

    user = get_user_from_token(token)
    if not user:
        return "Error: Invalid or missing authentication token"
    db = _session()
    try:
        try:
            task = task_service.create_task(db, user, data)
        except task_service.TaskError as e:
            return f"Error: {e.message}"
        return f"Task created with ID {task.id}"
    finally:
        db.close()


@mcp.tool()
def update_task(
    auth_token: str,
    task_id: int,
    board_id: int,
    title: str | None = None,
    description: str | None = None,
    status: str | None = None,
    priority: int | None = None,
    tags: list[str] | None = None,
    start_date: str | None = None,
    deadline: str | None = None,
    list: str | None = None,
    blocked_by: list[int] | None = None,
    is_cyclic: bool | None = None,
    cycle_period: str | None = None,
    cycle_interval: int | None = None,
    reminder_days: int | None = None,
    amount: float | None = None,
) -> str:
    """Update an existing task (must belong to the given board). Priority scale: 1 = Low, 2 = Medium, 3 = High.
    Setting status='done' on a cyclic task completes the cycle: logs history and spawns the next iteration."""
    data = _extract_args(locals())
    
    token = data.get("auth_token")
    t_id = data.get("task_id")
    
    if not token or t_id is None:
        return "Error: Missing required parameters (auth_token, task_id)"
    board_id = data.get("board_id")

    user = get_user_from_token(token)
    if not user:
        return "Error: Invalid or missing authentication token"
    db = _session()
    try:
        update_data = {
            k: v
            for k, v in data.items()
            if k not in ("auth_token", "task_id", "board_id") and v is not None
        }
        _parse_task_dates(update_data)
        # The task must belong to the given board (no cross-board moves).
        from ..models import Board

        board = db.query(Board).filter(Board.id == board_id, Board.user_id == user.id).first()
        if not board:
            return "Error: Board not found"
        existing = (
            db.query(Task)
            .filter(Task.id == t_id, Task.user_id == user.id)
            .first()
        )
        if not existing:
            return "Task not found"
        if existing.board_id != board_id:
            return "Error: Task not found on this board"
        # `list` is a builtin name in the tool signature; map it through.
        try:
            task = task_service.update_task(db, user, t_id, update_data)
        except LookupError:
            return "Task not found"
        except task_service.TaskError as e:
            return f"Error: {e.message}"
        # Cyclic completion via MCP: service already spawned the next iteration.
        if task.is_cyclic and task.status == "done":
            return (
                f"Cycle iteration completed. Next iteration created with ID "
                f"{task.id}, deadline {task.deadline}"
            )
        return f"Task {task.id} updated"
    finally:
        db.close()


@mcp.tool()
def delete_task(auth_token: str, board_id: int, task_id: int) -> str:
    """Delete a task of the given board. For a cyclic task, the whole iteration chain is deleted."""
    user = get_user_from_token(auth_token)
    if not user:
        return "Error: Invalid or missing authentication token"
    db = _session()
    try:
        try:
            cyclic = (
                db.query(Task)
                .filter(Task.id == task_id, Task.user_id == user.id, Task.is_cyclic == True)
                .first()
            )
            group_id = cyclic.cycle_group_id if cyclic else None
            task_service.delete_task(db, user, task_id)
        except LookupError:
            return "Task not found"
        if group_id:
            return "Cyclic task chain deleted"
        return f"Task {task_id} deleted"
    finally:
        db.close()


@mcp.tool()
def manage_cycle(auth_token: str, board_id: int, task_id: int, action: str) -> str:
    """Manage a cyclic task of the given board. action: 'skip' (shift deadline to next cycle, no history),
    'stop' (break the cycle, logged), 'history' (list completed iterations),
    'complete' (mark done: logs history and creates the next iteration)."""
    user = get_user_from_token(auth_token)
    if not user:
        return "Error: Invalid or missing authentication token"
    db = _session()
    try:
        task = (
            db.query(Task)
            .filter(Task.id == task_id, Task.user_id == user.id)
            .first()
        )
        if not task:
            return "Task not found"
        if not task.is_cyclic:
            return "Error: Task is not cyclic"
        action = (action or "").lower()
        if action in ("done", "complete"):  # 'done' kept for backwards compat
            action = "complete"
        if action == "skip":
            if not task.deadline:
                return "Error: Task has no deadline to shift"
            task.deadline = advance_deadline(
                task.deadline, task.cycle_period, task.cycle_interval
            )
            db.commit()
            return f"Deadline shifted to next cycle: {task.deadline}"
        if action == "stop":
            task.is_cyclic = False
            cycle_log(db, task.user_id, task.cycle_group_id, task, "stopped")
            db.commit()
            return "Cycle stopped. No new iterations will be created."
        if action == "complete":
            next_task = regenerate_cycle(db, task)
            return f"Cycle iteration completed. Next iteration created with ID {next_task.id}, deadline {next_task.deadline}"
        if action == "history":
            from ..models import TaskCycleLog
            logs = (
                db.query(TaskCycleLog)
                .filter(
                    TaskCycleLog.user_id == user.id,
                    TaskCycleLog.cycle_group_id == task.cycle_group_id,
                )
                .order_by(TaskCycleLog.logged_at.desc())
                .all()
            )
            return json.dumps(
                [
                    {
                        "task_title": l.task_title,
                        "action": l.action,
                        "deadline": str(l.deadline) if l.deadline else None,
                        "logged_at": str(l.logged_at),
                    }
                    for l in logs
                ]
            )
        return "Error: Unknown action. Use skip | stop | complete | history"
    finally:
        db.close()


@mcp.tool()
def search_tasks(auth_token: str, board_id: int, query_str: str) -> str:
    """Search tasks by title or description on the given board."""
    user = get_user_from_token(auth_token)
    if not user:
        return "Error: Invalid or missing authentication token"
    db = _session()
    try:
        tasks = (
            db.query(Task)
            .filter(
                Task.user_id == user.id,
                Task.board_id == board_id,
                (Task.title.ilike(f"%{query_str}%"))
                | (Task.description.ilike(f"%{query_str}%")),
            )
            .all()
        )
        return json.dumps(
            [{"id": t.id, "title": t.title, "status": t.status} for t in tasks]
        )
    finally:
        db.close()


@mcp.tool()
def get_board_budget(auth_token: str, board_id: int) -> str:
    """Read the board's budget (property-based): ПЛАН = amounts in lists with
    property 'К выполнению'/'В работе' (kind todo/progress), ФАКТ = in lists
    with property 'Завершено' (kind done), ИТОГО = all amounts of the board.
    Returns totals and the list of entries (title, list, signed amount:
    income positive, expense negative)."""
    user = get_user_from_token(auth_token)
    if not user:
        return "Error: Invalid or missing authentication token"
    db = _session()
    try:
        try:
            b = task_service.board_budget(db, user, board_id)
        except LookupError:
            return "Error: Board not found"
        lines = [
            f"Budget of board '{b['board_name']}' (id {b['board_id']}):",
            f"ПЛАН: {b['plan']:+g}",
            f"ФАКТ: {b['fact']:+g}",
            f"ИТОГО: {b['total']:+g}",
            f"ВСЕГО ДОХОД: {b['income']:+g}",
            f"ВСЕГО РАСХОД: {b['expense']:+g}",
            "Entries:",
        ]
        lines += [
            f"- {e['title']} [{e['list']}]: {e['amount']:+g}"
            for e in b["entries"]
        ] or ["- (нет задач с ненулевой суммой)"]
        return "\n".join(lines)
    finally:
        db.close()


@mcp.tool()
def get_project_summary(auth_token: str, board_id: int) -> str:
    """Return a summary of the given board's tasks."""
    user = get_user_from_token(auth_token)
    if not user:
        return "Error: Invalid or missing authentication token"
    db = _session()
    try:
        import json as _json

        from ..models import Board

        if not db.query(Board).filter(Board.id == board_id, Board.user_id == user.id).first():
            return "Error: Board not found"
        return _json.dumps(task_service.count_tasks(db, user, board_id=board_id))
    finally:
        db.close()


# --- SSE transport wiring -------------------------------------------------
# We deliberately disable DNS-rebinding protection (or restrict it via the
# MCP_ALLOWED_HOSTS env var) so the server is reachable behind a reverse proxy
# or from any host. The original hand-rolled transport did not enforce it, and
# the FastMCP default would otherwise reject every request whose Host header is
# not localhost/127.0.0.1 with HTTP 421 -- which is exactly what broke tool
# discovery. The constructor auto-enables the protection for host=127.0.0.1, so
# we override it here.
_allowed_hosts = [h.strip() for h in os.getenv("MCP_ALLOWED_HOSTS", "").split(",") if h.strip()]
if _allowed_hosts:
    mcp.settings.transport_security = TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=_allowed_hosts,
        allowed_origins=[f"http://{h}" for h in _allowed_hosts],
    )
else:
    mcp.settings.transport_security = TransportSecuritySettings(
        enable_dns_rebinding_protection=False
    )


def _build_mcp_routes():
    """Build the SSE routes from FastMCP's official ``sse_app()``.

    Using the library's own SSE app guarantees the handshake
    (initialize / tools/list / tools/call) is implemented correctly, so all
    registered tools are discoverable by standard MCP clients.
    """
    sse_app = mcp.sse_app()
    return list(sse_app.routes)


# Routes mounted by the application factory in main.py.
mcp_routes = _build_mcp_routes()
