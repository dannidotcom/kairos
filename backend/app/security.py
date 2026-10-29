from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID, uuid4

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import RefreshToken, User
from app.schemas import TokenPair

password_hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4, hash_len=32, salt_len=16)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, encoded: str) -> bool:
    try:
        return password_hasher.verify(encoded, password)
    except (VerifyMismatchError, InvalidHashError, ValueError):
        return False


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def hash_api_key(raw_key: str) -> str:
    return hmac.new(settings.api_key_pepper.encode(), raw_key.encode(), hashlib.sha256).hexdigest()


def generate_api_key() -> tuple[str, str, str]:
    raw = f"kairos_mcp_{secrets.token_urlsafe(32)}"
    prefix = raw[:18]
    return raw, prefix, hash_api_key(raw)


def constant_time_equal(left: str, right: str) -> bool:
    return hmac.compare_digest(left.encode(), right.encode())


def _encode(payload: dict[str, Any], expires_delta: timedelta) -> str:
    now = utcnow()
    payload = {
        **payload,
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
        "iss": "kairos",
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_access_token(user_id: UUID) -> str:
    return _encode(
        {"sub": str(user_id), "type": "access", "jti": str(uuid4())},
        timedelta(minutes=settings.access_token_expire_minutes),
    )


def create_refresh_token(user_id: UUID) -> tuple[str, datetime]:
    expires_at = utcnow() + timedelta(days=settings.refresh_token_expire_days)
    token = _encode(
        {"sub": str(user_id), "type": "refresh", "jti": str(uuid4())},
        timedelta(days=settings.refresh_token_expire_days),
    )
    return token, expires_at


def decode_token(token: str, expected_type: str) -> dict[str, Any] | None:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            issuer="kairos",
        )
    except jwt.PyJWTError:
        return None
    if payload.get("type") != expected_type:
        return None
    return payload


async def issue_token_pair(
    session: AsyncSession,
    user: User,
    user_agent: str | None = None,
) -> TokenPair:
    access = create_access_token(user.id)
    refresh, refresh_expires = create_refresh_token(user.id)
    session.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_refresh_token(refresh),
            expires_at=refresh_expires,
            user_agent=(user_agent or "")[:500] or None,
        )
    )
    await session.flush()
    return TokenPair(
        access_token=access,
        refresh_token=refresh,
        expires_in=settings.access_token_expire_minutes * 60,
    )
