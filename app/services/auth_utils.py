import base64
import hashlib
import hmac
import json
import os
import secrets
from datetime import datetime, timedelta, timezone

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "teamate-super-secret-key-yield-optimization-2026")
ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    """Hash password using PBKDF2 HMAC SHA256 with a random salt."""
    salt = secrets.token_hex(16)
    hashed = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        100000,
    )
    return f"{salt}${hashed.hex()}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against stored salt$hash."""
    try:
        if "$" not in hashed_password:
            return False
        salt, stored_hash = hashed_password.split("$", 1)
        computed = hashlib.pbkdf2_hmac(
            "sha256",
            plain_password.encode("utf-8"),
            salt.encode("utf-8"),
            100000,
        )
        return hmac.compare_digest(computed.hex(), stored_hash)
    except Exception:
        return False


def create_access_token(data: dict, expires_delta: timedelta = timedelta(days=30)) -> str:
    """Create a standard HMAC SHA256 JWT token."""
    header = {"alg": ALGORITHM, "typ": "JWT"}
    payload = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    payload.update({"exp": int(expire.timestamp())})

    def b64url(val: bytes) -> str:
        return base64.urlsafe_b64encode(val).rstrip(b"=").decode("ascii")

    header_b64 = b64url(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = b64url(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")

    sig = hmac.new(
        SECRET_KEY.encode("utf-8"),
        signing_input,
        hashlib.sha256,
    ).digest()
    sig_b64 = b64url(sig)

    return f"{header_b64}.{payload_b64}.{sig_b64}"
