"""Autentikasi (TASK 050).

- `POST /auth/login`   — access token pada body, refresh token pada cookie `httpOnly`
- `POST /auth/refresh` — menukar refresh token dengan access token baru
- `POST /auth/logout`  — menghapus cookie refresh
- `GET  /auth/me`      — profil, role, permission efektif

Seluruh percobaan masuk dicatat ke audit, baik berhasil maupun gagal — termasuk saat
akun tidak dikenal, sehingga upaya menebak akun ikut meninggalkan jejak.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from ...config import Settings
from ...models import User
from ...security import TokenError, create_access_token, create_refresh_token, decode_token
from ...security.passwords import needs_rehash, verify_password
from ...services import audit
from ...services.permissions import load_effective_permissions
from ..deps import CurrentUser, get_current_user, get_db, settings_dependency
from ..errors import ApiError

router = APIRouter(prefix="/auth", tags=["autentikasi"])

REFRESH_COOKIE = "predpol_refresh"


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=256)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"  # noqa: S105 — jenis token, bukan kredensial
    expires_at: datetime
    must_change_password: bool


class ProfileResponse(BaseModel):
    code: str
    username: str
    full_name: str | None
    role: str
    polsek: str | None
    function: str | None
    permissions: list[str]
    scopes: dict[str, str]


def _set_refresh_cookie(response: Response, token: str, settings: Settings) -> None:
    response.set_cookie(
        REFRESH_COOKIE,
        token,
        httponly=True,
        secure=settings.app_env != "development",
        samesite="lax",
        max_age=settings.jwt_refresh_token_ttl_days * 24 * 3600,
        path="/api/v1/auth",
    )


@router.post("/login", response_model=TokenResponse, summary="Masuk")
def login(
    payload: LoginRequest,
    response: Response,
    session: Session = Depends(get_db),
    settings: Settings = Depends(settings_dependency),
) -> Any:
    user = session.scalar(
        select(User).options(joinedload(User.role)).where(User.username == payload.username)
    )

    # Verifikasi tetap dijalankan meski pengguna tidak ada, supaya lamanya respons
    # tidak membedakan "akun tidak ada" dari "password salah".
    valid = verify_password(payload.password, user.password_hash if user else None)

    if user is None or not valid:
        audit.record(
            session,
            action="LOGIN",
            resource_type="auth",
            result=audit.RESULT_DENIED,
            user_id=user.user_id if user else None,
            resource_id=payload.username,
            detail={"reason": "kredensial tidak cocok"},
        )
        session.commit()
        raise ApiError(status.HTTP_401_UNAUTHORIZED, "Username atau password salah.")

    if user.status != "ACTIVE":
        audit.record(
            session,
            action="LOGIN",
            resource_type="auth",
            result=audit.RESULT_DENIED,
            user_id=user.user_id,
            detail={"reason": "akun tidak aktif"},
        )
        session.commit()
        raise ApiError(status.HTTP_403_FORBIDDEN, "Akun tidak aktif.")

    access_token, expires_at = create_access_token(
        user.code, settings.jwt_secret, settings.jwt_access_token_ttl_minutes
    )
    refresh_token, _ = create_refresh_token(
        user.code, settings.jwt_secret, settings.jwt_refresh_token_ttl_days
    )
    _set_refresh_cookie(response, refresh_token, settings)

    user.last_login_at = datetime.now(UTC)
    if needs_rehash(user.password_hash):
        # Parameter Argon2 berubah; perbarui diam-diam saat pengguna berhasil masuk.
        from ...security.passwords import hash_password

        user.password_hash = hash_password(payload.password)

    audit.record(
        session,
        action="LOGIN",
        resource_type="auth",
        result=audit.RESULT_SUCCESS,
        user_id=user.user_id,
    )
    session.commit()

    return TokenResponse(
        access_token=access_token,
        expires_at=expires_at,
        must_change_password=user.must_change_password,
    )


@router.post("/refresh", response_model=TokenResponse, summary="Perbarui access token")
def refresh(
    request: Request,
    session: Session = Depends(get_db),
    settings: Settings = Depends(settings_dependency),
) -> Any:
    token = request.cookies.get(REFRESH_COOKIE)
    if not token:
        raise ApiError(status.HTTP_401_UNAUTHORIZED, "Sesi tidak ditemukan.")

    try:
        payload = decode_token(token, settings.jwt_secret, "refresh")
    except TokenError as error:
        raise ApiError(status.HTTP_401_UNAUTHORIZED, "Sesi tidak sah.") from error

    user = session.scalar(select(User).where(User.code == payload.get("sub")))
    if user is None or user.status != "ACTIVE":
        raise ApiError(status.HTTP_401_UNAUTHORIZED, "Sesi tidak sah.")

    access_token, expires_at = create_access_token(
        user.code, settings.jwt_secret, settings.jwt_access_token_ttl_minutes
    )
    return TokenResponse(
        access_token=access_token,
        expires_at=expires_at,
        must_change_password=user.must_change_password,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, summary="Keluar")
def logout(response: Response) -> None:
    response.delete_cookie(REFRESH_COOKIE, path="/api/v1/auth")


@router.get("/me", response_model=ProfileResponse, summary="Profil pengguna aktif")
def me(
    current: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> Any:
    permissions = load_effective_permissions(session, current.user)

    return ProfileResponse(
        code=current.user.code,
        username=current.user.username,
        full_name=current.user.full_name,
        role=permissions.role_name,
        polsek=current.user.polsek,
        function=current.user.function,
        permissions=permissions.permissions,
        scopes=permissions.grants,
    )
