"""Board CRUD: a user's workspaces. Tasks, lists and tags are strictly
board-scoped (spec §1). Max 20 boards per user."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import schemas
from ..auth import get_current_user
from ..board import BOARD_PALETTE, MAX_BOARDS_PER_USER, ensure_default_lists
from ..db import get_db
from ..models import Board, Tag, Task, TaskList, User, Webhook
from ..services import notification_service
from ..services.notification_service import EVENTS

router = APIRouter(prefix="/boards", tags=["boards"])

MAX_NAME_LEN = 20


def get_own_board(db: Session, user: User, board_id: int) -> Board:
    """Return the board if it belongs to the user, else 404 (isolation)."""
    board = db.query(Board).filter(Board.id == board_id, Board.user_id == user.id).first()
    if not board:
        raise HTTPException(status_code=404, detail="Доска не найдена")
    return board


@router.get("", response_model=list[schemas.BoardResponse])
def get_boards(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(Board)
        .filter(Board.user_id == current_user.id)
        .order_by(Board.position, Board.id)
        .all()
    )


@router.post("", response_model=schemas.BoardResponse, status_code=201)
def create_board(
    data: schemas.BoardCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    name = (data.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Укажите название доски")
    from ..services import server_stats

    if server_stats.db_size_exceeded(db):
        raise HTTPException(status_code=400, detail=server_stats.quota_error_message())
    if len(name) > MAX_NAME_LEN:
        raise HTTPException(
            status_code=400, detail=f"Название доски не длиннее {MAX_NAME_LEN} символов"
        )
    if (
        db.query(Board)
        .filter(Board.user_id == current_user.id, Board.name == name)
        .first()
    ):
        raise HTTPException(status_code=400, detail="Доска с таким именем уже есть")
    owned = db.query(Board).filter(Board.user_id == current_user.id)
    if owned.count() >= MAX_BOARDS_PER_USER:
        raise HTTPException(
            status_code=400,
            detail=f"Максимальное количество досок — {MAX_BOARDS_PER_USER}",
        )
    if data.color not in BOARD_PALETTE:
        raise HTTPException(status_code=400, detail="Цвет должен быть из палитры досок")
    pos = (
        db.query(Board)
        .filter(Board.user_id == current_user.id)
        .order_by(Board.position.desc())
        .first()
    )
    board = Board(
        user_id=current_user.id,
        name=name,
        description=data.description,
        color=data.color,
        position=(pos.position + 1) if pos else 0,
    )
    db.add(board)
    db.commit()
    db.refresh(board)
    # A new board gets its own copy of the protected default lists.
    ensure_default_lists(db, current_user.id, board.id)
    return board


@router.put("/{board_id}", response_model=schemas.BoardResponse)
def update_board(
    board_id: int,
    data: schemas.BoardUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    board = get_own_board(db, current_user, board_id)
    if data.name is not None and data.name.strip():
        name = data.name.strip()
        if len(name) > MAX_NAME_LEN:
            raise HTTPException(
                status_code=400,
                detail=f"Название доски не длиннее {MAX_NAME_LEN} символов",
            )
        if name != board.name and (
            db.query(Board)
            .filter(Board.user_id == current_user.id, Board.name == name)
            .first()
        ):
            raise HTTPException(status_code=400, detail="Доска с таким именем уже есть")
        board.name = name
    if data.description is not None:
        board.description = data.description
    if data.color is not None:
        if data.color not in BOARD_PALETTE:
            raise HTTPException(status_code=400, detail="Цвет должен быть из палитры досок")
        board.color = data.color
    if data.position is not None:
        board.position = data.position
    db.commit()
    db.refresh(board)
    return board


@router.delete("/{board_id}")
def delete_board(
    board_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    board = get_own_board(db, current_user, board_id)
    if db.query(Board).filter(Board.user_id == current_user.id).count() <= 1:
        raise HTTPException(status_code=400, detail="Нельзя удалить последнюю доску")
    # Cascade: a board owns its tasks, tags, lists and webhooks entirely.
    db.query(Webhook).filter(Webhook.board_id == board.id).delete()
    db.query(Task).filter(Task.board_id == board.id).delete(synchronize_session=False)
    db.query(Tag).filter(Tag.board_id == board.id).delete(synchronize_session=False)
    db.query(TaskList).filter(TaskList.board_id == board.id).delete(
        synchronize_session=False
    )
    db.delete(board)
    db.commit()
    return {"ok": True}


# --- Board webhook (one per board) ------------------------------------------

# The board editor's «Веб-хуки» tab edits the single webhook of this board.
# The admin can revoke the right per user; a revoked user sees no tab, has
# their webhooks wiped and no events are dispatched (notification_service
# also checks the flag).


def _own_webhook(db: Session, user: User, board_id: int) -> Webhook:
    """The board's single webhook or 404; ownership via get_own_board."""
    get_own_board(db, user, board_id)
    return (
        db.query(Webhook)
        .filter(Webhook.board_id == board_id)
        .first()
    )


def _require_webhooks_allowed(user: User) -> None:
    if not user.webhooks_enabled:
        raise HTTPException(status_code=403, detail="Веб-хуки запрещены для этого пользователя")


@router.get("/{board_id}/webhook", response_model=schemas.WebhookResponse | None)
def get_board_webhook(
    board_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_webhooks_allowed(current_user)
    return _own_webhook(db, current_user, board_id)


@router.put("/{board_id}/webhook", response_model=schemas.WebhookResponse)
def put_board_webhook(
    board_id: int,
    data: schemas.WebhookPut,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create or update the board's single webhook (one per board).
    On update only the provided fields are replaced; on creation the
    required fields (url, chat_id) must be present."""
    _require_webhooks_allowed(current_user)
    board = get_own_board(db, current_user, board_id)
    unknown = [
        e
        for e in (*(data.events or []), *(data.excluded_events or []))
        if e not in EVENTS
    ]
    if unknown:
        raise HTTPException(
            status_code=400, detail=f"Неизвестные события: {', '.join(unknown)}"
        )
    webhook = _own_webhook(db, current_user, board_id)
    if webhook is None:
        if not data.url or not data.chat_id:
            raise HTTPException(
                status_code=400,
                detail="Укажите URL и Telegram Chat ID веб-хука",
            )
        webhook = Webhook(
            user_id=current_user.id, board_id=board.id, events=[], excluded_events=[]
        )
        db.add(webhook)
        for key, value in data.model_dump().items():
            setattr(webhook, key, value)
        webhook.events = data.events or []
        webhook.excluded_events = data.excluded_events or []
    else:
        payload = data.model_dump(exclude_unset=True, exclude_none=True)
        for key, value in payload.items():
            setattr(webhook, key, value)
    webhook.name = (webhook.name or "").strip() or f"Доска «{board.name}»"
    db.commit()
    db.refresh(webhook)
    return webhook


@router.delete("/{board_id}/webhook")
def delete_board_webhook(
    board_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_webhooks_allowed(current_user)
    webhook = _own_webhook(db, current_user, board_id)
    if webhook:
        db.delete(webhook)
        db.commit()
    return {"ok": True}


@router.post("/{board_id}/webhook/test")
async def test_board_webhook(
    board_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Send a test notification synchronously so the user immediately sees
    whether the receiving endpoint is reachable."""
    import httpx

    _require_webhooks_allowed(current_user)
    webhook = _own_webhook(db, current_user, board_id)
    if not webhook:
        raise HTTPException(status_code=404, detail="Веб-хук не настроен")
    body, headers = notification_service.build_request(
        webhook, notification_service.send_test(webhook)
    )
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(webhook.url, content=body, headers=headers)
        ok = resp.status_code < 400
        return {
            "ok": ok,
            "status_code": resp.status_code,
            "error": None if ok else f"HTTP {resp.status_code}",
        }
    except Exception as exc:
        return {"ok": False, "status_code": None, "error": str(exc)}
