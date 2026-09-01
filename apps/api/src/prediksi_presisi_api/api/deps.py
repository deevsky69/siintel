"""Dependency bersama: session, pengguna aktif, dan pemeriksaan permission (TASK 052).

Otorisasi ditegakkan **di sini**, bukan di frontend (CLAUDE.md §15, §21). Setiap endpoint
sensitif menyatakan permission yang dibutuhkannya, dan penolakan ikut tercatat di audit.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

from fastapi import Depends, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from ..config import Settings, get_settings
from ..db import get_session_factory
from ..models import User
from ..security import TokenError, decode_token
from ..services import audit
from ..services.permissions import (
    SCOPE_ALL,
    SCOPE_OWN_FUNCTION,
    SCOPE_OWN_JURISDICTION,
    EffectivePermissions,
    load_effective_permissions,
)
from .errors import ApiError

BEARER_PREFIX = "Bearer "


def get_db() -> Iterator[Session]:
    """Satu session per permintaan."""
    with get_session_factory()() as session:
        yield session


def settings_dependency() -> Settings:
    return get_settings()


@dataclass(frozen=True)
class CurrentUser:
    """Pengguna yang sedang masuk beserta permission efektifnya."""

    user: User
    permissions: EffectivePermissions

    @property
    def scope_filters(self) -> dict[str, str | None]:
        return {"polsek": self.user.polsek, "function": self.user.function}


def _unauthenticated(message: str = "Diperlukan autentikasi.") -> ApiError:
    return ApiError(status.HTTP_401_UNAUTHORIZED, message)


def get_current_user(
    request: Request,
    session: Session = Depends(get_db),
    settings: Settings = Depends(settings_dependency),
) -> CurrentUser:
    header = request.headers.get("Authorization", "")
    if not header.startswith(BEARER_PREFIX):
        raise _unauthenticated()

    try:
        payload = decode_token(header[len(BEARER_PREFIX) :], settings.jwt_secret, "access")
    except TokenError as error:
        raise _unauthenticated(str(error)) from error

    user = session.scalar(
        select(User).options(joinedload(User.role)).where(User.code == payload.get("sub"))
    )
    if user is None:
        raise _unauthenticated("Pengguna tidak dikenal.")

    if user.status != "ACTIVE":
        # Akun nonaktif ditolak di sini, bukan hanya disembunyikan dari daftar.
        raise ApiError(status.HTTP_403_FORBIDDEN, "Akun tidak aktif.")

    return CurrentUser(user=user, permissions=load_effective_permissions(session, user))


def require_permission(permission: str) -> object:
    """Menghasilkan dependency yang mensyaratkan satu `resource:action`.

    Penolakan dicatat ke audit dengan `result = DENIED` sebelum kesalahan dilempar,
    sehingga percobaan akses tanpa kewenangan meninggalkan jejak.
    """
    resource, _, action = permission.partition(":")

    def guard(
        current: CurrentUser = Depends(get_current_user),
        session: Session = Depends(get_db),
    ) -> CurrentUser:
        if not current.permissions.allows(permission):
            audit.record_denied(
                session,
                action=f"{action.upper()}_{resource.upper()}",
                resource_type=resource,
                user_id=current.user.user_id,
                reason=(
                    f"permission '{permission}' tidak dimiliki role {current.permissions.role_name}"
                ),
            )
            session.commit()
            raise ApiError(status.HTTP_403_FORBIDDEN, "Tidak memiliki kewenangan.")

        return current

    return Depends(guard)


def scope_of(current: CurrentUser, permission: str) -> str:
    """Cakupan yang berlaku bagi pengguna atas satu permission."""
    return current.permissions.scope_for(permission) or SCOPE_ALL


def jurisdiction_filter(current: CurrentUser, permission: str) -> str | None:
    """Polsek yang boleh dilihat, atau `None` bila tidak dibatasi wilayah.

    Dipakai endpoint daftar untuk menyaring di **query**, bukan setelah data terambil.
    """
    if scope_of(current, permission) != SCOPE_OWN_JURISDICTION:
        return None

    if current.user.polsek is None:
        # Scope terbatas tanpa wilayah berarti tidak ada data yang boleh dilihat —
        # lebih aman daripada diam-diam berubah menjadi akses penuh.
        raise ApiError(
            status.HTTP_403_FORBIDDEN,
            "Akun dibatasi wilayah tetapi belum memiliki penetapan Polsek.",
        )

    return current.user.polsek


def function_filter(current: CurrentUser, permission: str) -> str | None:
    """Fungsi yang boleh dilihat, atau `None` bila tidak dibatasi fungsi."""
    if scope_of(current, permission) != SCOPE_OWN_FUNCTION:
        return None

    if current.user.function is None:
        raise ApiError(
            status.HTTP_403_FORBIDDEN,
            "Akun dibatasi fungsi tetapi belum memiliki penetapan fungsi.",
        )

    return current.user.function


def not_found() -> ApiError:
    """404 dipakai juga untuk data di luar cakupan pengguna.

    Menjawab 403 akan membocorkan bahwa datanya ada di wilayah lain (docs/05 §1).
    """
    return ApiError(status.HTTP_404_NOT_FOUND, "Data tidak ditemukan.")
