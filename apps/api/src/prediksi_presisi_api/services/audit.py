"""Penulisan audit trail (TASK 053).

Audit bersifat **append-only** (CLAUDE.md §29): modul ini hanya menulis, tidak pernah
mengubah maupun menghapus.

Yang membedakan audit ini dari sekadar log: penolakan otorisasi ikut dicatat dengan
`result = DENIED`. Audit yang hanya memuat keberhasilan tidak dapat dipakai menilai
kepatuhan RBAC — justru penolakanlah buktinya.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from ..models import AuditLog

RESULT_SUCCESS = "SUCCESS"
RESULT_DENIED = "DENIED"
RESULT_FAILED = "FAILED"


def record(
    session: Session,
    *,
    action: str,
    resource_type: str,
    result: str,
    user_id: uuid.UUID | None = None,
    resource_id: str | None = None,
    detail: dict[str, Any] | None = None,
) -> None:
    """Mencatat satu peristiwa. Pemanggil yang menentukan kapan transaksi ditutup."""
    session.add(
        AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            result=result,
            detail=detail,
        )
    )


def record_denied(
    session: Session,
    *,
    action: str,
    resource_type: str,
    user_id: uuid.UUID | None,
    reason: str,
    resource_id: str | None = None,
) -> None:
    """Mencatat penolakan otorisasi beserta alasannya."""
    record(
        session,
        action=action,
        resource_type=resource_type,
        result=RESULT_DENIED,
        user_id=user_id,
        resource_id=resource_id,
        detail={"reason": reason},
    )
