from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies.auth import get_current_user
from ..models import User, YieldSettings
from ..schemas.yield_settings import YieldSettingsResponse, YieldSettingsUpdate

router = APIRouter(prefix="/settings", tags=["Settings"])


def _build_response(settings: YieldSettings | None) -> YieldSettingsResponse:
    if settings is None:
        return YieldSettingsResponse(
            tea_variant="TRI 2025",
            pluckable_100_bud_weight_g=None,
            arimbu_100_bud_weight_g=None,
            is_configured=False,
        )

    return YieldSettingsResponse(
        id=settings.id,
        tea_variant=settings.tea_variant,
        pluckable_100_bud_weight_g=float(settings.pluckable_100_bud_weight_g)
        if settings.pluckable_100_bud_weight_g is not None
        else None,
        arimbu_100_bud_weight_g=float(settings.arimbu_100_bud_weight_g)
        if settings.arimbu_100_bud_weight_g is not None
        else None,
        is_configured=(
            settings.pluckable_100_bud_weight_g is not None
            and settings.arimbu_100_bud_weight_g is not None
        ),
        created_at=settings.created_at,
        updated_at=settings.updated_at,
    )


@router.get("/yield", response_model=YieldSettingsResponse)
def get_yield_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _build_response(current_user.yield_settings)


@router.put("/yield", response_model=YieldSettingsResponse)
def update_yield_settings(
    data: YieldSettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    settings = current_user.yield_settings
    if settings is None:
        settings = YieldSettings(user_id=current_user.id)
        db.add(settings)

    settings.tea_variant = data.tea_variant
    settings.pluckable_100_bud_weight_g = data.pluckable_100_bud_weight_g
    settings.arimbu_100_bud_weight_g = data.arimbu_100_bud_weight_g

    db.commit()
    db.refresh(settings)
    return _build_response(settings)
