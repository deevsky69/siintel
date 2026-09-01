"""Imbauan untuk publik — `public_alerts` (docs/02 §7).

Sengaja **tidak** menyimpan `location_id`: alert publik memakai `area_text` agar grid internal
dan detail sensitif tidak terekspos ke luar (docs/02 §7, CLAUDE.md §24).

`warning_id` menunjuk `early_warnings` yang dibuat pada TASK 013; foreign key-nya
ditambahkan pada migration TASK 013, bukan di sini (lihat catatan pada migration 0003).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base
from .base import TimestampMixin, uuid_pk


class PublicAlert(TimestampMixin, Base):
    """Imbauan kewaspadaan yang dipublikasikan ke masyarakat."""

    __tablename__ = "public_alerts"

    public_alert_id: Mapped[uuid.UUID] = uuid_pk()
    code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)

    #: Peringatan internal yang menjadi dasar. Nullable — imbauan dapat terbit tanpa warning.
    #: FK ditambahkan pada TASK 013 setelah tabel `early_warnings` ada.
    warning_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))

    severity: Mapped[str] = mapped_column(String(50), nullable=False)
    threat_type: Mapped[str] = mapped_column(String(50), nullable=False)

    #: Deskripsi wilayah untuk publik (mis. "Kebayoran Baru"), bukan grid internal.
    area_text: Mapped[str] = mapped_column(String(255), nullable=False)

    #: Label jendela waktu untuk tampilan; batasnya ada pada window_start/window_end.
    time_window: Mapped[str | None] = mapped_column(String(50))
    window_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    window_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    status: Mapped[str] = mapped_column(String(50), nullable=False)
    public_message: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "window_end IS NULL OR window_start IS NULL OR window_end > window_start",
            name="window_order",
        ),
        Index("ix_public_alerts_status", "status"),
        Index("ix_public_alerts_warning", "warning_id"),
        Index("ix_public_alerts_window_start", "window_start"),
    )
