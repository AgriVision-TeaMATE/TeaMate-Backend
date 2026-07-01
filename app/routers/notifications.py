from datetime import datetime, timezone
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Notification
from ..schemas.notification import NotificationResponse

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=list[NotificationResponse])
def list_notifications(
    category: str | None = None,
    unread_only: bool = False,
    db: Session = Depends(get_db),
):
    stmt = select(Notification).order_by(Notification.created_at.desc())
    if category and category.lower() != "all":
        stmt = stmt.where(Notification.category == category.lower())
    if unread_only:
        stmt = stmt.where(Notification.is_read == False) # noqa: E712

    return db.scalars(stmt).all()


@router.put("/{notif_id}/read", response_model=NotificationResponse)
def mark_notification_read(notif_id: UUID, db: Session = Depends(get_db)):
    notif = db.get(Notification, notif_id)
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    notif.is_read = True
    notif.read_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(notif)
    return notif


@router.put("/read-all", response_model=dict)
def mark_all_read(db: Session = Depends(get_db)):
    stmt = select(Notification).where(Notification.is_read == False) # noqa: E712
    unread = db.scalars(stmt).all()
    now = datetime.now(timezone.utc)
    for n in unread:
        n.is_read = True
        n.read_at = now
    db.commit()
    return {"updated_count": len(unread)}
