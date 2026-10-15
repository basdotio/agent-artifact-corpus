"""Board list management: default + user-defined lists (columns of the board)."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import schemas
from ..auth import get_current_user
from ..board import (
    PALETTE,
    ensure_default_lists,
    list_names,
    status_for_kind,
)
from ..db import get_db
from ..models import Board, Task, TaskList, User
from .boards import get_own_board

router = APIRouter(prefix="/lists", tags=["lists"])


@router.get("", response_model=list[schemas.TaskListResponse])
def get_lists(
    board_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Lists are strictly per-board: only the given board's lists are returned.
    get_own_board(db, current_user, board_id)
    return (
        db.query(TaskList)
        .filter(TaskList.user_id == current_user.id, TaskList.board_id == board_id)
        .order_by(TaskList.position)
        .all()
    )


@router.post("", response_model=schemas.TaskListResponse, status_code=201)
def create_list(
    board_id: int,
    data: schemas.TaskListCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_own_board(db, current_user, board_id)
    name = (data.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Укажите название списка")
    if name in list_names(db, current_user.id, board_id=board_id):
        raise HTTPException(status_code=400, detail="Список с таким именем уже есть")
    if data.color not in PALETTE:
        raise HTTPException(status_code=400, detail="Цвет должен быть из палитры")
    pos = data.position
    if pos is None:
        # Новые списки — в конец своей доски (максимум в рамках user+board).
        pos = (
            db.query(func.max(TaskList.position))
            .filter(
                TaskList.user_id == current_user.id,
                TaskList.board_id == board_id,
            )
            .scalar()
            or 0
        ) + 1
    if data.kind not in (None, "todo", "progress", "done"):
        raise HTTPException(status_code=400, detail="Недопустимый статус списка")
    lst = TaskList(
        name=name,
        color=data.color,
        position=pos,
        is_default=False,
        kind=data.kind,
        user_id=current_user.id,
        board_id=board_id,
    )
    db.add(lst)
    db.commit()
    db.refresh(lst)
    return lst


@router.put("/{board_id}/{list_id}", response_model=schemas.TaskListResponse)
def update_list(
    board_id: int,
    list_id: int,
    data: schemas.TaskListUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_own_board(db, current_user, board_id)
    lst = (
        db.query(TaskList)
        .filter(
            TaskList.id == list_id,
            TaskList.user_id == current_user.id,
            TaskList.board_id == board_id,
        )
        .first()
    )
    if not lst:
        raise HTTPException(status_code=404, detail="Список не найден")

    # All lists are editable: no protected/system names (UPDATE ТЗ).
    if data.name is not None and data.name.strip():
        new = data.name.strip()
        if new != lst.name and new in list_names(
            db, current_user.id, board_id=board_id
        ):
            raise HTTPException(status_code=400, detail="Имя списка занято")
        old = lst.name
        lst.name = new
        # Keep the owner's tasks pointing at the renamed list.
        db.query(Task).filter(
            Task.list == old,
            Task.user_id == current_user.id,
            Task.board_id == board_id,
        ).update({Task.list: new}, synchronize_session=False)

    if data.color is not None:
        if data.color not in PALETTE:
            raise HTTPException(status_code=400, detail="Цвет должен быть из палитры")
        lst.color = data.color
    if data.position is not None:
        lst.position = data.position
    if data.kind is not None:
        if data.kind not in ("todo", "progress", "done"):
            raise HTTPException(status_code=400, detail="Недопустимый статус списка")
        lst.kind = data.kind
        # Keep task status consistent with the new list semantics.
        db.query(Task).filter(
            Task.list == lst.name,
            Task.user_id == current_user.id,
            Task.board_id == board_id,
        ).update({Task.status: status_for_kind(data.kind)}, synchronize_session=False)

    db.commit()
    db.refresh(lst)
    return lst


@router.delete("/{board_id}/{list_id}")
def delete_list(
    list_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    lst = (
        db.query(TaskList)
        .filter(TaskList.id == list_id, TaskList.user_id == current_user.id)
        .first()
    )
    if not lst:
        raise HTTPException(status_code=404, detail="Список не найден")
    # Reassign only the owner's tasks to the default "not started" list.
    db.query(Task).filter(
        Task.list == lst.name, Task.user_id == current_user.id
    ).update(
        {Task.list: "Не начато"}, synchronize_session=False
    )
    db.delete(lst)
    db.commit()
    return {"ok": True}
