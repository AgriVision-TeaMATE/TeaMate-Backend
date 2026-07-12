import base64
import hashlib
import hmac
import json
from datetime import datetime, timezone
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.user import User
from ..services.auth_utils import SECRET_KEY


def _decode_token(token: str) -> dict:
    try:
        header_b64, payload_b64, signature_b64 = token.split(".")
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token.",
        ) from exc

    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    expected_signature = hmac.new(
        SECRET_KEY.encode("utf-8"),
        signing_input,
        hashlib.sha256,
    ).digest()
    actual_signature = base64.urlsafe_b64decode(
        signature_b64 + "=" * (-len(signature_b64) % 4)
    )

    if not hmac.compare_digest(expected_signature, actual_signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token.",
        )

    payload_bytes = base64.urlsafe_b64decode(
        payload_b64 + "=" * (-len(payload_b64) % 4)
    )
    payload = json.loads(payload_bytes.decode("utf-8"))
    expires_at = payload.get("exp")
    if not isinstance(expires_at, int) or expires_at < int(
        datetime.now(timezone.utc).timestamp()
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token has expired.",
        )
    return payload


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )

    payload = _decode_token(authorization.removeprefix("Bearer ").strip())
    user_id = payload.get("sub")
    try:
        parsed_user_id = UUID(user_id)
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token.",
        ) from exc

    user = db.get(User, parsed_user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is not available.",
        )
    return user
