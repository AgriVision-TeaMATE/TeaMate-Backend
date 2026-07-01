from datetime import datetime, timezone
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..database import get_db
from ..models import HarvestRound, Field
from ..models.harvest_round import RoundStatus
from ..schemas.harvest_round import (
    HarvestRoundCreate,
    HarvestRoundUpdate,
    HarvestRoundResponse,
)

router = APIRouter(tags=["Harvest Rounds"])


@router.get("/fields/{field_id}/rounds", response_model=list[HarvestRoundResponse])
def list_field_rounds(field_id: UUID, db: Session = Depends(get_db)):
    stmt = (
        select(HarvestRound)
        .where(HarvestRound.field_id == field_id)
        .options(
            selectinload(HarvestRound.analysis_images),
            selectinload(HarvestRound.weather_log),
        )
        .order_by(HarvestRound.round_date.desc())
    )
    return db.scalars(stmt).all()


@router.get("/rounds/{round_id}", response_model=HarvestRoundResponse)
def get_round(round_id: UUID, db: Session = Depends(get_db)):
    stmt = select(HarvestRound).where(HarvestRound.id == round_id).options(
        selectinload(HarvestRound.analysis_images),
        selectinload(HarvestRound.weather_log),
    )
    round_obj = db.scalar(stmt)
    if not round_obj:
        raise HTTPException(status_code=404, detail="Harvest round not found")
    return round_obj


@router.post(
    "/fields/{field_id}/rounds",
    response_model=HarvestRoundResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_field_round(
    field_id: UUID, data: HarvestRoundCreate, db: Session = Depends(get_db)
):
    field = db.get(Field, field_id)
    if not field:
        raise HTTPException(status_code=404, detail="Field not found")

    new_round = HarvestRound(
        field_id=field.id,
        round_date=data.round_date or datetime.now(timezone.utc),
        field_area_hectares=field.area_hectares,
        status=RoundStatus.draft,
    )
    db.add(new_round)
    db.commit()
    db.refresh(new_round)
    return new_round


@router.put("/rounds/{round_id}", response_model=HarvestRoundResponse)
def update_round(
    round_id: UUID, data: HarvestRoundUpdate, db: Session = Depends(get_db)
):
    stmt = select(HarvestRound).where(HarvestRound.id == round_id).options(
        selectinload(HarvestRound.analysis_images),
        selectinload(HarvestRound.weather_log),
    )
    round_obj = db.scalar(stmt)
    if not round_obj:
        raise HTTPException(status_code=404, detail="Harvest round not found")

    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(round_obj, key, val)

    db.commit()
    db.refresh(round_obj)
    return round_obj


@router.put("/rounds/{round_id}/complete", response_model=HarvestRoundResponse)
def complete_round(round_id: UUID, db: Session = Depends(get_db)):
    stmt = select(HarvestRound).where(HarvestRound.id == round_id).options(
        selectinload(HarvestRound.analysis_images),
        selectinload(HarvestRound.weather_log),
    )
    round_obj = db.scalar(stmt)
    if not round_obj:
        raise HTTPException(status_code=404, detail="Harvest round not found")

    round_obj.status = RoundStatus.completed
    db.commit()
    db.refresh(round_obj)
    return round_obj


@router.delete("/rounds/{round_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_round(round_id: UUID, db: Session = Depends(get_db)):
    round_obj = db.get(HarvestRound, round_id)
    if not round_obj:
        raise HTTPException(status_code=404, detail="Harvest round not found")
    db.delete(round_obj)
    db.commit()
