"""Kejadian kriminal — `crime_incidents` (docs/02 §3).

Tidak menyimpan identitas korban/pelaku/saksi (CLAUDE.md §16, docs/02 K-10).
Kolom wilayah tidak diduplikasi di sini; diperoleh lewat join ke `locations` (docs/02 K-8).
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, time
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Time,
    true,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db import Base
from .base import TimestampMixin, uuid_pk

if TYPE_CHECKING:
    from .location import Location
    from .prediction_actual import PredictionActual


#: Pembagian latih/uji oleh pemilik data (Pusiknas). Sama dengan migration 0010.
DATA_GROUPS = ("TRAIN", "TEST")


class CrimeIncident(TimestampMixin, Base):
    """Satu kejadian yang dilaporkan/ditangani."""

    __tablename__ = "crime_incidents"

    incident_id: Mapped[uuid.UUID] = uuid_pk()

    #: ID anonim pada dataset dummy, mis. "INC-00001"
    code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)

    #: CURANMOR / CURAT / CURAS / TAWURAN / KEJAHATAN_JALANAN — taksonomi final menunggu U-16.
    incident_type: Mapped[str] = mapped_column(String(50), nullable=False)

    #: Waktu kejadian sebagai satu nilai (UTC). Sumber kebenaran untuk query rentang waktu.
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    #: Dipertahankan untuk agregasi harian dan analisis jam rawan (docs/02 §3).
    incident_date: Mapped[date] = mapped_column(Date, nullable=False)
    #: NULL bila jam tidak tercatat pada Laporan Polisi — 21,9% data asli Pusiknas.
    #: Jangan pernah diisi 00:00 sebagai pengganti: itu menumpuk ribuan kejadian ke jendela
    #: dini hari dan merusak pola jam rawan dengan tenang. Lihat `time_known`.
    incident_time: Mapped[time | None] = mapped_column(Time)
    #: FALSE bila jam tidak tercatat; `occurred_at` lalu berisi tengah malam setempat agar
    #: hitungan per HARI tidak kehilangan kejadian. Kode yang membentuk pola JAM wajib
    #: menyaring `time_known` — dijaga `test_unknown_hours_never_shape_the_hour_pattern`.
    time_known: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=true()
    )

    # --- Dibawa Laporan Polisi asli (migration 0010); NULL pada baris tanpa sumber itu ---
    reported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    report_lag_hours: Mapped[float | None] = mapped_column(Numeric(9, 1))
    report_source: Mapped[str | None] = mapped_column(String(50))
    receiving_unit: Mapped[str | None] = mapped_column(String(100))
    #: TRAIN (laporan 2023–2025) atau TEST (2026) — pembagian oleh pemilik data, bukan kami.
    data_group: Mapped[str | None] = mapped_column(String(10))
    #: Nama jalan TKP tanpa nomor rumah, RT, RW — sudah demikian di sumbernya.
    street: Mapped[str | None] = mapped_column(String(255))
    #: Titik kejadian bila tercatat (17%, hampir seluruhnya 2025–2026), dibulatkan 3 desimal
    #: di sumbernya. Titik wilayahnya tetap pada `location`.
    latitude: Mapped[float | None] = mapped_column(Numeric(9, 6))
    longitude: Mapped[float | None] = mapped_column(Numeric(9, 6))
    grid_500m: Mapped[str | None] = mapped_column(String(20))
    data_source: Mapped[str | None] = mapped_column(String(50))

    location_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("locations.location_id", ondelete="RESTRICT"),
        nullable=False,
    )

    location_type: Mapped[str | None] = mapped_column(String(100))
    modus: Mapped[str | None] = mapped_column(String(100))
    target_type: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[str | None] = mapped_column(String(50))

    location: Mapped[Location] = relationship(back_populates="crime_incidents")
    evaluations: Mapped[list[PredictionActual]] = relationship(back_populates="actual_incident")

    __table_args__ = (
        # Jam yang tidak tercatat tidak boleh mengaku tercatat, dan sebaliknya.
        CheckConstraint(
            "NOT time_known OR incident_time IS NOT NULL", name="time_known_needs_time"
        ),
        CheckConstraint(
            "data_group IS NULL OR data_group IN " + str(DATA_GROUPS), name="data_group_known"
        ),
        Index("ix_crime_incidents_occurred_at", "occurred_at"),
        Index("ix_crime_incidents_location_occurred", "location_id", "occurred_at"),
        Index("ix_crime_incidents_incident_type", "incident_type"),
        Index("ix_crime_incidents_reported_at", "reported_at"),
        Index("ix_crime_incidents_data_group", "data_group"),
    )
