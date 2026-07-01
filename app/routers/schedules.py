from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..database import get_db
from ..models import PluckingSchedule, ScheduleWorker, Field, Worker
from ..schemas.schedule import ScheduleCreate, ScheduleUpdate, ScheduleResponse

router = APIRouter(prefix="/schedules", tags=["Plucking Schedules"])


@router.get("", response_model=list[ScheduleResponse])
def list_schedules(field_id: UUID | None = None, db: Session = Depends(get_db)):
    stmt = select(PluckingSchedule).options(
        selectinload(PluckingSchedule.schedule_workers)
    ).order_by(PluckingSchedule.scheduled_date.desc())
    if field_id:
        stmt = stmt.where(PluckingSchedule.field_id == field_id)
    return db.scalars(stmt).all()


@router.post("", response_model=ScheduleResponse, status_code=status.HTTP_201_CREATED)
def create_schedule(data: ScheduleCreate, db: Session = Depends(get_db)):
    field = db.get(Field, data.field_id)
    if not field:
        raise HTTPException(status_code=404, detail="Field not found")

    sched = PluckingSchedule(
        field_id=data.field_id,
        scheduled_date=data.scheduled_date,
        shift_start=data.shift_start,
        shift_end=data.shift_end,
        recommended_workers=data.recommended_workers,
        notes=data.notes,
    )
    db.add(sched)
    db.flush()

    for w_id in data.assigned_worker_ids:
        if db.get(Worker, w_id):
            sw = ScheduleWorker(schedule_id=sched.id, worker_id=w_id)
            db.add(sw)

    db.commit()
    db.refresh(sched)
    return sched


@router.put("/{schedule_id}", response_model=ScheduleResponse)
def update_schedule(
    schedule_id: UUID, data: ScheduleUpdate, db: Session = Depends(get_db)
):
    sched = db.get(PluckingSchedule, schedule_id)
    if not sched:
        raise HTTPException(status_code=404, detail="Schedule not found")

    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(sched, key, val)

    db.commit()
    db.refresh(sched)
    return sched


@router.post("/{schedule_id}/workers", response_model=ScheduleResponse)
def assign_schedule_workers(
    schedule_id: UUID, worker_ids: list[UUID], db: Session = Depends(get_db)
):
    stmt = select(PluckingSchedule).where(PluckingSchedule.id == schedule_id).options(
        selectinload(PluckingSchedule.schedule_workers)
    )
    sched = db.scalar(stmt)
    if not sched:
        raise HTTPException(status_code=404, detail="Schedule not found")

    # Clear old assignments
    sched.schedule_workers.clear()

    for w_id in set(worker_ids):
        if db.get(Worker, w_id):
            sw = ScheduleWorker(schedule_id=sched.id, worker_id=w_id)
            db.add(sw)

    db.commit()
    db.refresh(sched)
    return sched
