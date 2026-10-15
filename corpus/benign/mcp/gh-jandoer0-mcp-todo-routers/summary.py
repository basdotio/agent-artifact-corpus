"""Task summary statistics for the authenticated user."""
from datetime import timedelta
from ..clock import utcnow

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import schemas
from ..auth import get_current_user
from ..clock import utcnow
from ..db import get_db
from ..models import Task, User

router = APIRouter(prefix="/summary", tags=["summary"])


@router.get("", response_model=schemas.SummaryResponse)
def get_summary(
    board_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    uid = current_user.id

    # Dormant cyclic tasks (outside their reminder window) are excluded from
    # the headline statistics — they are only counted in 'planned'.
    now = utcnow()
    dormant_q = db.query(Task).filter(
        Task.user_id == uid,
        Task.is_cyclic == True,
    )
    base_q = db.query(Task).filter(Task.user_id == uid)
    if board_id is not None:
        dormant_q = dormant_q.filter(Task.board_id == board_id)
        base_q = base_q.filter(Task.board_id == board_id)
    dormant_ids = set()
    for t in dormant_q.all():
        if t.deadline:
            window = t.deadline - timedelta(days=max(0, t.reminder_days or 0))
            if now < window:
                dormant_ids.add(t.id)

    base = base_q
    if dormant_ids:
        base = base.filter(~Task.id.in_(dormant_ids))

    total = base.count()
    todo = base.filter(Task.status == "todo").count()
    in_progress = base.filter(Task.status == "in_progress").count()
    done = base.filter(Task.status == "done").count()
    overdue = base.filter(
        Task.deadline < now,
        Task.status != "done",
    ).count()
    planned = len(dormant_ids)
    return {
        "total": total,
        "todo": todo,
        "in_progress": in_progress,
        "done": done,
        "overdue": overdue,
        "planned": planned,
    }
