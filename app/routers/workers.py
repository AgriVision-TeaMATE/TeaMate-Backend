from datetime import datetime, timezone
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..database import get_db
from ..models import Worker, WorkerFieldAssignment, Field
from ..models.worker import WorkerStatus
from ..schemas.worker import (
    WorkerCreate,
    WorkerUpdate,
    WorkerResponse,
    WorkerDetailResponse,
    AssignWorkerRequest,
    WorkerStatusUpdate,
)

router = APIRouter(prefix="/workers", tags=["Workers"])


def _format_worker_detail(worker: Worker) -> WorkerDetailResponse:
    active = next(
        (wa for wa in worker.field_assignments if wa.is_active), None
    )
    resp = WorkerDetailResponse.model_validate(worker)
    if active and active.field:
        resp.assigned_field_id = active.field.id
        resp.assigned_field_name = active.field.name
    return resp


@router.get("", response_model=list[WorkerDetailResponse])
def list_workers(
    status_filter: str | None = None, db: Session = Depends(get_db)
):
    stmt = select(Worker).options(
        selectinload(Worker.field_assignments).selectinload(
            WorkerFieldAssignment.field
        )
    ).order_by(Worker.name)
    if status_filter:
        stmt = stmt.where(Worker.status == status_filter)
    workers = db.scalars(stmt).all()
    return [_format_worker_detail(w) for w in workers]


@router.get("/{worker_id}", response_model=WorkerDetailResponse)
def get_worker(worker_id: UUID, db: Session = Depends(get_db)):
    stmt = select(Worker).where(Worker.id == worker_id).options(
        selectinload(Worker.field_assignments).selectinload(
            WorkerFieldAssignment.field
        )
    )
    worker = db.scalar(stmt)
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    return _format_worker_detail(worker)


@router.post("", response_model=WorkerResponse, status_code=status.HTTP_201_CREATED)
def create_worker(data: WorkerCreate, db: Session = Depends(get_db)):
    existing = db.scalar(select(Worker).where(Worker.phone == data.phone))
    if existing:
        raise HTTPException(status_code=400, detail="Phone number already registered")
    worker = Worker(**data.model_dump())
    db.add(worker)
    db.commit()
    db.refresh(worker)
    return worker


@router.put("/{worker_id}", response_model=WorkerResponse)
def update_worker(worker_id: UUID, data: WorkerUpdate, db: Session = Depends(get_db)):
    worker = db.get(Worker, worker_id)
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    if data.phone and data.phone != worker.phone:
        if db.scalar(select(Worker).where(Worker.phone == data.phone)):
            raise HTTPException(status_code=400, detail="Phone number already in use")

    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(worker, key, val)
    db.commit()
    db.refresh(worker)
    return worker


@router.delete("/{worker_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_worker(worker_id: UUID, db: Session = Depends(get_db)):
    worker = db.get(Worker, worker_id)
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    db.delete(worker)
    db.commit()


@router.post("/{worker_id}/assign", response_model=WorkerDetailResponse)
def assign_worker_to_field(
    worker_id: UUID, data: AssignWorkerRequest, db: Session = Depends(get_db)
):
    stmt = select(Worker).where(Worker.id == worker_id).options(
        selectinload(Worker.field_assignments).selectinload(
            WorkerFieldAssignment.field
        )
    )
    worker = db.scalar(stmt)
    field = db.get(Field, data.field_id)
    if not worker or not field:
        raise HTTPException(status_code=404, detail="Worker or Field not found")

    # Deactivate current assignments
    for wa in worker.field_assignments:
        if wa.is_active:
            wa.is_active = False
            wa.unassigned_at = datetime.now(timezone.utc)

    # Create new assignment
    new_assignment = WorkerFieldAssignment(
        worker_id=worker.id, field_id=field.id, is_active=True
    )
    worker.status = WorkerStatus.assigned
    db.add(new_assignment)
    db.commit()
    db.refresh(worker)
    return _format_worker_detail(worker)


@router.post("/{worker_id}/unassign", response_model=WorkerDetailResponse)
def unassign_worker(worker_id: UUID, db: Session = Depends(get_db)):
    stmt = select(Worker).where(Worker.id == worker_id).options(
        selectinload(Worker.field_assignments).selectinload(
            WorkerFieldAssignment.field
        )
    )
    worker = db.scalar(stmt)
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")

    for wa in worker.field_assignments:
        if wa.is_active:
            wa.is_active = False
            wa.unassigned_at = datetime.now(timezone.utc)

    worker.status = WorkerStatus.available
    db.commit()
    db.refresh(worker)
    return _format_worker_detail(worker)


@router.put("/{worker_id}/status", response_model=WorkerDetailResponse)
def update_worker_status(
    worker_id: UUID, data: WorkerStatusUpdate, db: Session = Depends(get_db)
):
    stmt = select(Worker).where(Worker.id == worker_id).options(
        selectinload(Worker.field_assignments).selectinload(
            WorkerFieldAssignment.field
        )
    )
    worker = db.scalar(stmt)
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")

    worker.status = data.status
    if data.status == WorkerStatus.on_leave.value:
        for wa in worker.field_assignments:
            if wa.is_active:
                wa.is_active = False
                wa.unassigned_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(worker)
    return _format_worker_detail(worker)
