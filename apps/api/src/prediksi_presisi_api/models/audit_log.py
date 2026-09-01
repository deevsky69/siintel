"""Jejak audit — `audit_logs` (docs/02 §20, CLAUDE.md §29).

Bersifat **append-only**: tidak ada operasi update/delete, dan tidak ada endpoint tulis
pada kontrak API (docs/05 §2.2). Nilai `result` mencakup `DENIED` supaya penolakan
otorisasi ikut terekam — justru itu bukti utama RBAC bekerja.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base
from .base import uuid_pk

#: Hasil sebuah aksi. Nilai teknis yang ditetapkan sistem, bukan taksonomi bisnis.
AUDIT_RESULTS = ("SUCCESS", "DENIED", "FAILED")


class AuditLog(Base):
    """Satu peristiwa penting yang tercatat."""

    __tablename__ = "audit_logs"

    audit_id: Mapped[uuid.UUID] = uuid_pk()
    code: Mapped[str | None] = mapped_column(String(50), unique=True)

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    #: Nullable untuk peristiwa sistem yang tidak dipicu pengguna (docs/02 §20).
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="RESTRICT"),
    )

    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)

    #: Menyimpan UUID maupun `code` resource, sehingga bertipe teks.
    resource_id: Mapped[str | None] = mapped_column(String(100))

    result: Mapped[str] = mapped_column(String(20), nullable=False)

    #: Konteks tambahan, mis. nilai konfigurasi sebelum/sesudah pada CHANGE_CONFIGURATION.
    detail: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    __table_args__ = (
        CheckConstraint(
            "result IN ('SUCCESS', 'DENIED', 'FAILED')",
            name="result_allowed",
        ),
        Index("ix_audit_logs_timestamp", "timestamp"),
        Index("ix_audit_logs_user_timestamp", "user_id", "timestamp"),
        Index("ix_audit_logs_resource", "resource_type", "resource_id"),
        Index("ix_audit_logs_action", "action"),
    )
