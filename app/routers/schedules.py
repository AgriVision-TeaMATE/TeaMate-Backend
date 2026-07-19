from datetime import datetime, timezone
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..database import get_db
from ..dependencies.auth import get_current_user
from ..models import (
    Field,
    HarvestRound,
    Notification,
    PluckingSchedule,
    ScheduleWorker,
    User,
    Worker,
    WorkerFieldAssignment,
)
from ..models.notification import AlertSeverity, NotificationCategory
from ..models.worker import WorkerStatus
from ..schemas.schedule import ScheduleCreate, ScheduleUpdate, ScheduleResponse
from ..schemas.planning import SmsDispatchResponse
from ..services.sms_service import send_schedule_sms

router = APIRouter(prefix="/schedules", tags=["Plucking Schedules"])


@router.get("", response_model=list[ScheduleResponse])
def list_schedules(
    field_id: UUID | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(PluckingSchedule).options(
        selectinload(PluckingSchedule.schedule_workers)
    ).join(Field, PluckingSchedule.field_id == Field.id).where(
        Field.user_id == current_user.id
    ).order_by(PluckingSchedule.scheduled_date.desc())
    if field_id:
        stmt = stmt.where(PluckingSchedule.field_id == field_id)
    return db.scalars(stmt).all()


@router.post("", response_model=ScheduleResponse, status_code=status.HTTP_201_CREATED)
def create_schedule(
    data: ScheduleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    field = db.scalar(
        select(Field).where(Field.id == data.field_id, Field.user_id == current_user.id)
    )
    if not field:
        raise HTTPException(status_code=404, detail="Field not found")
    if data.harvest_round_id:
        round_obj = db.scalar(
            select(HarvestRound).where(
                HarvestRound.id == data.harvest_round_id,
                HarvestRound.field_id == field.id,
            )
        )
        if not round_obj:
            raise HTTPException(status_code=404, detail="Harvest round not found")

    sched = PluckingSchedule(
        field_id=data.field_id,
        harvest_round_id=data.harvest_round_id,
        scheduled_date=data.scheduled_date,
        shift_start=data.shift_start,
        shift_end=data.shift_end,
        recommended_workers=data.recommended_workers,
        notes=data.notes,
    )
    db.add(sched)
    db.flush()

    for w_id in data.assigned_worker_ids:
        worker = db.get(Worker, w_id)
        if worker:
            _ensure_worker_available_for_date(db, w_id, data.scheduled_date, sched.id)
            sw = ScheduleWorker(schedule_id=sched.id, worker_id=w_id)
            db.add(sw)
            _set_worker_current_field(db, worker, field.id)

    _create_schedule_notifications(db, sched, field.name)

    db.commit()
    db.refresh(sched)
    return sched


@router.put("/{schedule_id}", response_model=ScheduleResponse)
def update_schedule(
    schedule_id: UUID,
    data: ScheduleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sched = db.scalar(
        select(PluckingSchedule)
        .join(Field, PluckingSchedule.field_id == Field.id)
        .where(PluckingSchedule.id == schedule_id, Field.user_id == current_user.id)
    )
    if not sched:
        raise HTTPException(status_code=404, detail="Schedule not found")

    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(sched, key, val)

    db.commit()
    db.refresh(sched)
    return sched


@router.post("/{schedule_id}/workers", response_model=ScheduleResponse)
def assign_schedule_workers(
    schedule_id: UUID,
    worker_ids: list[UUID],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = (
        select(PluckingSchedule)
        .join(Field, PluckingSchedule.field_id == Field.id)
        .where(PluckingSchedule.id == schedule_id, Field.user_id == current_user.id)
        .options(
        selectinload(PluckingSchedule.schedule_workers)
        )
    )
    sched = db.scalar(stmt)
    if not sched:
        raise HTTPException(status_code=404, detail="Schedule not found")

    old_worker_ids = [sw.worker_id for sw in sched.schedule_workers]

    # Clear old schedule assignments
    sched.schedule_workers.clear()
    db.flush()

    for old_worker_id in old_worker_ids:
        if old_worker_id not in set(worker_ids):
            old_worker = db.get(Worker, old_worker_id)
            if old_worker:
                _clear_worker_current_field(db, old_worker, sched.field_id)

    for w_id in set(worker_ids):
        worker = db.get(Worker, w_id)
        if worker:
            _ensure_worker_available_for_date(db, w_id, sched.scheduled_date, sched.id)
            sw = ScheduleWorker(schedule_id=sched.id, worker_id=w_id)
            db.add(sw)
            _set_worker_current_field(db, worker, sched.field_id)

    field = db.get(Field, sched.field_id)
    _create_schedule_notifications(db, sched, field.name if field else "Field")
    db.commit()
    db.refresh(sched)
    return sched


@router.post("/{schedule_id}/send-sms", response_model=SmsDispatchResponse)
def send_schedule_sms_notifications(
    schedule_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = (
        select(PluckingSchedule)
        .join(Field, PluckingSchedule.field_id == Field.id)
        .where(PluckingSchedule.id == schedule_id, Field.user_id == current_user.id)
        .options(
            selectinload(PluckingSchedule.schedule_workers).selectinload(
                ScheduleWorker.worker
            ),
            selectinload(PluckingSchedule.harvest_round).selectinload(
                HarvestRound.weather_log
            ),
        )
    )
    sched = db.scalar(stmt)
    if not sched:
        raise HTTPException(status_code=404, detail="Schedule not found")

    workers = [sw.worker for sw in sched.schedule_workers if sw.worker]
    field = db.get(Field, sched.field_id)
    sms_result = send_schedule_sms(sched, workers, field.name if field else "Field")
    return SmsDispatchResponse(schedule_id=sched.id, **sms_result)


def _ensure_worker_available_for_date(
    db: Session,
    worker_id: UUID,
    scheduled_date,
    current_schedule_id: UUID,
):
    stmt = (
        select(PluckingSchedule)
        .join(ScheduleWorker, ScheduleWorker.schedule_id == PluckingSchedule.id)
        .where(
            ScheduleWorker.worker_id == worker_id,
            PluckingSchedule.scheduled_date == scheduled_date,
            PluckingSchedule.id != current_schedule_id,
            PluckingSchedule.status != "cancelled",
        )
    )
    if db.scalar(stmt):
        raise HTTPException(
            status_code=400,
            detail="Worker is already allocated to another field on the same day.",
        )


def _create_schedule_notifications(db: Session, schedule: PluckingSchedule, field_name: str):
    db.add(
        Notification(
            field_id=schedule.field_id,
            harvest_round_id=schedule.harvest_round_id,
            title="Labour allocation updated",
            message=(
                f"Plucking schedule for {field_name} has "
                f"{len(schedule.schedule_workers)} assigned workers on {schedule.scheduled_date.isoformat()}."
            ),
            category=NotificationCategory.labor,
            severity=AlertSeverity.info,
        )
    )


def _set_worker_current_field(db: Session, worker: Worker, field_id: UUID) -> None:
    for assignment in worker.field_assignments:
        if assignment.is_active and assignment.field_id != field_id:
            assignment.is_active = False
            assignment.unassigned_at = datetime.now(timezone.utc)

    current = next(
        (
            assignment
            for assignment in worker.field_assignments
            if assignment.field_id == field_id
        ),
        None,
    )
    if current:
        current.is_active = True
        current.unassigned_at = None
    else:
        db.add(
            WorkerFieldAssignment(
                worker_id=worker.id,
                field_id=field_id,
                is_active=True,
            )
        )
    worker.status = WorkerStatus.assigned


def _clear_worker_current_field(db: Session, worker: Worker, field_id: UUID) -> None:
    for assignment in worker.field_assignments:
        if assignment.is_active and assignment.field_id == field_id:
            assignment.is_active = False
            assignment.unassigned_at = datetime.now(timezone.utc)

    has_other_active = db.scalar(
        select(WorkerFieldAssignment).where(
            WorkerFieldAssignment.worker_id == worker.id,
            WorkerFieldAssignment.is_active == True,  # noqa: E712
        )
    )
    if not has_other_active:
        worker.status = WorkerStatus.available
