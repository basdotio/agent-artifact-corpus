"""Tag management. A tag's color must not equal any list's color."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import schemas
from ..auth import get_current_user
from ..board import PALETTE, list_colors
from ..db import get_db
from ..models import Tag, User
from .boards import get_own_board

router = APIRouter(prefix="/tags", tags=["tags"])


def _tag_names(db: Session, user_id: int, board_id: int | None = None) -> set:
    q = db.query(Tag.name).filter(Tag.user_id == user_id)
    if board_id is not None:
        q = q.filter(Tag.board_id == board_id)
    return {r[0] for r in q.all()}


def cleanup_orphan_tags(db: Session, user_id: int | None = None) -> int:
    """Delete tags that are not assigned to any task.
    When user_id is given, only that user's tags are cleaned up.
    Returns the number of removed tags."""
    from ..models import task_tags

    # Flush pending changes first: a just-created tag may already be linked to
    # a task via a dirty relationship — without the flush it looks like an
    # orphan and gets deleted (the "tag appears only on the second save" bug).
    db.flush()

    q = (
        db.query(Tag)
        .outerjoin(task_tags, Tag.id == task_tags.c.tag_id)
        .filter(task_tags.c.task_id.is_(None))
    )
    if user_id is not None:
        q = q.filter(Tag.user_id == user_id)
    orphans = q.all()
    for tag in orphans:
        db.delete(tag)
    if orphans:
        db.commit()
    return len(orphans)


@router.get("", response_model=list[schemas.TagResponse])
def get_tags(
    board_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Tags are strictly per-board.
    get_own_board(db, current_user, board_id)
    return (
        db.query(Tag)
        .filter(Tag.user_id == current_user.id, Tag.board_id == board_id)
        .order_by(Tag.name)
        .all()
    )


@router.post("", response_model=schemas.TagResponse, status_code=201)
def create_tag(
    board_id: int,
    data: schemas.TagCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_own_board(db, current_user, board_id)
    name = (data.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Укажите название тега")
    if name in _tag_names(db, current_user.id, board_id):
        raise HTTPException(status_code=400, detail="Тег с таким именем уже есть")
    if data.color not in PALETTE:
        raise HTTPException(status_code=400, detail="Цвет должен быть из палитры")
    if data.color in list_colors(db, current_user.id, board_id=board_id):
        raise HTTPException(
            status_code=400,
            detail="Цвет тега не должен совпадать с цветом списка",
        )
    tag = Tag(name=name, color=data.color, user_id=current_user.id, board_id=board_id)
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return tag


@router.put("/{board_id}/{tag_id}", response_model=schemas.TagResponse)
def update_tag(
    board_id: int,
    tag_id: int,
    data: schemas.TagUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_own_board(db, current_user, board_id)
    tag = (
        db.query(Tag)
        .filter(
            Tag.id == tag_id,
            Tag.user_id == current_user.id,
            Tag.board_id == board_id,
        )
        .first()
    )
    if not tag:
        raise HTTPException(status_code=404, detail="Тег не найден")
    if data.name is not None and data.name.strip():
        new = data.name.strip()
        if new != tag.name and new in _tag_names(db, current_user.id, board_id):
            raise HTTPException(status_code=400, detail="Имя тега занято")
        tag.name = new
    if data.color is not None:
        if data.color not in PALETTE:
            raise HTTPException(status_code=400, detail="Цвет должен быть из палитры")
        if data.color in list_colors(db, current_user.id, board_id=board_id):
            raise HTTPException(
                status_code=400,
                detail="Цвет тега не должен совпадать с цветом списка",
            )
        tag.color = data.color
    db.commit()
    db.refresh(tag)
    return tag


@router.delete("/{board_id}/{tag_id}")
def delete_tag(
    board_id: int,
    tag_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_own_board(db, current_user, board_id)
    tag = (
        db.query(Tag)
        .filter(
            Tag.id == tag_id,
            Tag.user_id == current_user.id,
            Tag.board_id == board_id,
        )
        .first()
    )
    if not tag:
        raise HTTPException(status_code=404, detail="Тег не найден")
    # Detach the tag from tasks.
    from ..models import Task

    db.query(Task).filter(Task.tag == tag.name).update(
        {Task.tag: None}, synchronize_session=False
    )
    db.delete(tag)
    db.commit()
    return {"ok": True}
