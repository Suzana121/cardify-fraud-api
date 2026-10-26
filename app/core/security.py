from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from app.core.config import get_settings


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


def create_access_token(user_id: int, expires_minutes: int | None = None) -> str:
    settings = get_settings()
    minutes = expires_minutes if expires_minutes is not None else settings.jwt_expire_minutes
    now = datetime.now(UTC)
    payload = {"sub": str(user_id), "iat": now, "exp": now + timedelta(minutes=minutes)}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> int:
    """Return the user id from a valid token. Raises jwt.PyJWTError if invalid or expired."""
    settings = get_settings()
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    return int(payload["sub"])
