from datetime import date, time
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..database import get_db
from ..dependencies.auth import get_current_user
from ..models import HarvestRound, Field, User
from ..schemas.harvest_round import (
    HarvestRoundCreate,
    HarvestRoundUpdate,
    HarvestRoundResponse,
)
from ..schemas.planning import RoundPlanRequest, RoundPlanResponse
from ..services.image_storage import delete_round_analysis_files
from ..services.round_planning import build_round_plan

router = APIRouter(tags=["Harvest Rounds"])


@router.get("/fields/{field_id}/rounds", response_model=list[HarvestRoundResponse])
def list_field_rounds(
    field_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = (
        select(HarvestRound)
        .join(Field, HarvestRound.field_id == Field.id)
        .where(HarvestRound.field_id == field_id)
        .where(Field.user_id == current_user.id)
        .options(
            selectinload(HarvestRound.analysis_images),
            selectinload(HarvestRound.weather_log),
        )
        .order_by(HarvestRound.created_at.desc())
    )
    return db.scalars(stmt).all()


@router.get("/rounds/{round_id}", response_model=HarvestRoundResponse)
def get_round(
    round_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(HarvestRound).join(Field, HarvestRound.field_id == Field.id).where(
        HarvestRound.id == round_id, Field.user_id == current_user.id
    ).options(
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
    field_id: UUID,
    data: HarvestRoundCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    field = db.scalar(
        select(Field).where(Field.id == field_id, Field.user_id == current_user.id)
    )
    if not field:
        raise HTTPException(status_code=404, detail="Field not found")

    new_round = HarvestRound(
        field_id=field.id,
        plucking_status="awaiting_analysis",
        is_completed=False,
    )
    db.add(new_round)
    db.commit()
    db.refresh(new_round)
    return new_round


@router.put("/rounds/{round_id}", response_model=HarvestRoundResponse)
def update_round(
    round_id: UUID,
    data: HarvestRoundUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(HarvestRound).join(Field, HarvestRound.field_id == Field.id).where(
        HarvestRound.id == round_id, Field.user_id == current_user.id
    ).options(
        selectinload(HarvestRound.analysis_images),
        selectinload(HarvestRound.weather_log),
    )
    round_obj = db.scalar(stmt)
    if not round_obj:
        raise HTTPException(status_code=404, detail="Harvest round not found")
    if round_obj.is_completed:
        allowed_fields = {"actual_yield"}
        incoming_fields = set(data.model_dump(exclude_unset=True).keys())
        if not incoming_fields.issubset(allowed_fields):
            raise HTTPException(
                status_code=400,
                detail="Completed round can only update actual yield.",
            )

    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(round_obj, key, val)

    db.commit()
    db.refresh(round_obj)
    return round_obj


@router.put("/rounds/{round_id}/complete", response_model=HarvestRoundResponse)
def complete_round(
    round_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(HarvestRound).join(Field, HarvestRound.field_id == Field.id).where(
        HarvestRound.id == round_id, Field.user_id == current_user.id
    ).options(
        selectinload(HarvestRound.analysis_images),
        selectinload(HarvestRound.weather_log),
    )
    round_obj = db.scalar(stmt)
    if not round_obj:
        raise HTTPException(status_code=404, detail="Harvest round not found")

    round_obj.is_completed = True
    if round_obj.plucking_status == "awaiting_analysis":
        round_obj.plucking_status = "completed"
    db.commit()
    db.refresh(round_obj)
    return round_obj


@router.post("/rounds/{round_id}/plan", response_model=RoundPlanResponse)
async def plan_round(
    round_id: UUID,
    data: RoundPlanRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(HarvestRound).join(Field, HarvestRound.field_id == Field.id).where(
        HarvestRound.id == round_id, Field.user_id == current_user.id
    ).options(
        selectinload(HarvestRound.analysis_images),
        selectinload(HarvestRound.weather_log),
    )
    round_obj = db.scalar(stmt)
    if not round_obj:
        raise HTTPException(status_code=404, detail="Harvest round not found")

    scheduled_date = data.scheduled_date or date.today()
    shift_start = data.shift_start or time(hour=6)
    shift_end = data.shift_end or time(hour=14)
    return await build_round_plan(
        round_obj=round_obj,
        db=db,
        kg_per_worker_per_day=data.kg_per_worker_per_day,
        scheduled_date=scheduled_date,
        shift_start=shift_start,
        shift_end=shift_end,
    )


@router.delete("/rounds/{round_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_round(
    round_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    round_obj = db.scalar(
        select(HarvestRound)
        .join(Field, HarvestRound.field_id == Field.id)
        .where(HarvestRound.id == round_id, Field.user_id == current_user.id)
        .options(selectinload(HarvestRound.analysis_images))
    )
    if not round_obj:
        raise HTTPException(status_code=404, detail="Harvest round not found")
    delete_round_analysis_files(round_obj)
    db.delete(round_obj)
    db.commit()
