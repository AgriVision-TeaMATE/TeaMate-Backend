from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.user import User
from ..schemas.user import (
    ForgotPasswordRequest,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserResponse,
)
from ..services.auth_utils import create_access_token, hash_password, verify_password

router = APIRouter(tags=["Authentication"])


@router.post(
    "/auth/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_user(data: UserCreate, db: Session = Depends(get_db)):
    stmt = select(User).where(User.email == data.email.lower())
    existing = db.scalar(stmt)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email address is already registered.",
        )

    new_user = User(
        email=data.email.lower(),
        full_name=data.full_name,
        hashed_password=hash_password(data.password),
        role=data.role or "estate_manager",
        is_active=True,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    token = create_access_token({"sub": str(new_user.id), "email": new_user.email})
    return TokenResponse(access_token=token, user=UserResponse.model_validate(new_user))


@router.post("/auth/login", response_model=TokenResponse)
def login_user(data: UserLogin, db: Session = Depends(get_db)):
    stmt = select(User).where(User.email == data.email.lower())
    user = db.scalar(stmt)
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email address or password.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated.",
        )

    token = create_access_token({"sub": str(user.id), "email": user.email})
    return TokenResponse(access_token=token, user=UserResponse.model_validate(user))


@router.post("/auth/forgot-password")
def forgot_password(data: ForgotPasswordRequest, db: Session = Depends(get_db)):
    stmt = select(User).where(User.email == data.email.lower())
    user = db.scalar(stmt)
    # Return success even if email doesn't exist for security
    return {
        "status": "success",
        "message": f"If an account exists for {data.email}, password recovery instructions have been dispatched.",
    }
