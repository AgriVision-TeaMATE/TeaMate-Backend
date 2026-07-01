from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..database import get_db
from ..models import Field, WorkerFieldAssignment, HarvestRound
from ..schemas.field import FieldCreate, FieldUpdate, FieldResponse, FieldDetailResponse
from ..schemas.harvest_round import HarvestRoundResponse

router = APIRouter(prefix="/fields", tags=["Fields"])


def _format_field_detail(field: Field) -> FieldDetailResponse:
    active_workers = [
        wa for wa in field.worker_assignments if wa.is_active
    ]
    rounds = sorted(
        field.harvest_rounds, key=lambda r: r.round_date, reverse=True
    )
    latest = HarvestRoundResponse.model_validate(rounds[0]) if rounds else None

    resp = FieldDetailResponse.model_validate(field)
    resp.assigned_worker_count = len(active_workers)
    resp.latest_round = latest
    return resp


@router.get("", response_model=list[FieldDetailResponse])
def list_fields(db: Session = Depends(get_db)):
    stmt = select(Field).options(
        selectinload(Field.worker_assignments),
        selectinload(Field.harvest_rounds).selectinload(
            HarvestRound.analysis_images
        ),
        selectinload(Field.harvest_rounds).selectinload(
            HarvestRound.weather_log
        ),
    ).order_by(Field.name)
    fields = db.scalars(stmt).all()
    return [_format_field_detail(f) for f in fields]


@router.get("/{field_id}", response_model=FieldDetailResponse)
def get_field(field_id: UUID, db: Session = Depends(get_db)):
    stmt = select(Field).where(Field.id == field_id).options(
        selectinload(Field.worker_assignments),
        selectinload(Field.harvest_rounds).selectinload(
            HarvestRound.analysis_images
        ),
        selectinload(Field.harvest_rounds).selectinload(
            HarvestRound.weather_log
        ),
    )
    field = db.scalar(stmt)
    if not field:
        raise HTTPException(status_code=404, detail="Field not found")
    return _format_field_detail(field)


@router.post("", response_model=FieldResponse, status_code=status.HTTP_201_CREATED)
def create_field(data: FieldCreate, db: Session = Depends(get_db)):
    field = Field(**data.model_dump())
    db.add(field)
    db.commit()
    db.refresh(field)
    return field


@router.put("/{field_id}", response_model=FieldResponse)
def update_field(field_id: UUID, data: FieldUpdate, db: Session = Depends(get_db)):
    field = db.get(Field, field_id)
    if not field:
        raise HTTPException(status_code=404, detail="Field not found")

    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(field, key, val)

    db.commit()
    db.refresh(field)
    return field


@router.delete("/{field_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_field(field_id: UUID, db: Session = Depends(get_db)):
    field = db.get(Field, field_id)
    if not field:
        raise HTTPException(status_code=404, detail="Field not found")
    db.delete(field)
    db.commit()
