"""Token akses dan penyegaran (TASK 050, keputusan SDL-06).

Access token berumur pendek dikirim pada body dan dipakai lewat header `Authorization`.
Refresh token berumur lebih panjang dan hanya ditaruh pada cookie `httpOnly`, sehingga
tidak dapat dibaca JavaScript (CLAUDE.md §23: frontend tidak menyimpan secret).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import jwt

ALGORITHM = "HS256"

TokenType = Literal["access", "refresh"]


class TokenError(Exception):
    """Token tidak sah, kedaluwarsa, atau bukan jenis yang diharapkan."""


def _create(
    subject: str, secret: str, token_type: TokenType, lifetime: timedelta
) -> tuple[str, datetime]:
    now = datetime.now(UTC)
    expires_at = now + lifetime
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(payload, secret, algorithm=ALGORITHM), expires_at


def create_access_token(subject: str, secret: str, minutes: int) -> tuple[str, datetime]:
    return _create(subject, secret, "access", timedelta(minutes=minutes))


def create_refresh_token(subject: str, secret: str, days: int) -> tuple[str, datetime]:
    return _create(subject, secret, "refresh", timedelta(days=days))


def decode_token(token: str, secret: str, expected_type: TokenType) -> dict[str, Any]:
    try:
        payload: dict[str, Any] = jwt.decode(token, secret, algorithms=[ALGORITHM])
    except jwt.PyJWTError as error:
        message = "token tidak sah atau kedaluwarsa"
        raise TokenError(message) from error

    if payload.get("type") != expected_type:
        # Menukar refresh token menjadi access token harus ditolak tegas.
        message = f"token bukan jenis {expected_type}"
        raise TokenError(message)

    return payload
