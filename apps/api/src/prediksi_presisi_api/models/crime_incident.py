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
    Text,
    Time,
    false,
    func,
    text,
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
#: Nilai `target_type` Pusiknas yang berarti objek sasaran kendaraan bermotor.
VEHICLE_TARGET = "Kendaraan bermotor"
DUPLICATE_STATUSES = ("SUSPECTED", "CONFIRMED", "CLEARED")


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

    # --- Modul 1 mekanisme (migration 0019, 6 November 2026) ---
    #: Objek sasaran kendaraan bermotor pada kolom tersendiri (dokumen mekanisme, Modul 1).
    #: Diturunkan dari `target_type == "Kendaraan bermotor"` — nilai Pusiknas apa adanya.
    vehicle_object: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )
    #: TRUE bila kelurahan belum pasti: lokasinya tingkat kecamatan. Dihitung terpisah
    #: ("masih memerlukan konfirmasi") dan tidak masuk perhitungan per kelurahan.
    area_pending: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )
    #: Kode kejadian yang diduga sama; `duplicate_status` SUSPECTED → CONFIRMED / CLEARED.
    #: Yang CONFIRMED disembunyikan dari seluruh perhitungan (services/visibility.py).
    duplicate_of: Mapped[str | None] = mapped_column(String(50))
    duplicate_status: Mapped[str | None] = mapped_column(String(20))

    location: Mapped[Location] = relationship(back_populates="crime_incidents")
    evaluations: Mapped[list[PredictionActual]] = relationship(back_populates="actual_incident")
    revisions: Mapped[list[CrimeIncidentRevision]] = relationship(
        back_populates="incident",
        cascade="all, delete-orphan",
        order_by="CrimeIncidentRevision.changed_at",
    )

    __table_args__ = (
        # Jam yang tidak tercatat tidak boleh mengaku tercatat, dan sebaliknya.
        CheckConstraint(
            "NOT time_known OR incident_time IS NOT NULL", name="time_known_needs_time"
        ),
        CheckConstraint(
            "data_group IS NULL OR data_group IN " + str(DATA_GROUPS), name="data_group_known"
        ),
        CheckConstraint(
            "duplicate_status IS NULL OR duplicate_status IN " + str(DUPLICATE_STATUSES),
            name="duplicate_status_known",
        ),
        Index("ix_crime_incidents_occurred_at", "occurred_at"),
        Index("ix_crime_incidents_location_occurred", "location_id", "occurred_at"),
        Index("ix_crime_incidents_incident_type", "incident_type"),
        Index("ix_crime_incidents_reported_at", "reported_at"),
        Index("ix_crime_incidents_data_group", "data_group"),
        Index(
            "ix_crime_incidents_area_pending", "area_pending", postgresql_where=text("area_pending")
        ),
        Index(
            "ix_crime_incidents_duplicate_status",
            "duplicate_status",
            postgresql_where=text("duplicate_status IS NOT NULL"),
        ),
    )


class CrimeIncidentRevision(Base):
    """Riwayat koreksi satu kejadian: bidang apa, dari apa menjadi apa, oleh siapa, kapan.

    Dokumen mekanisme (Modul 1): "Simpan rujukan sumber dan riwayat setiap koreksi."
    Audit log mencatat *peristiwa*; tabel ini mencatat *nilai* supaya kejadian dapat
    dibaca ulang sebagaimana adanya pada tanggal mana pun.
    """

    __tablename__ = "crime_incident_revisions"

    revision_id: Mapped[uuid.UUID] = uuid_pk()
    incident_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("crime_incidents.incident_id", ondelete="CASCADE"),
        nullable=False,
    )
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    changed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="SET NULL")
    )
    field: Mapped[str] = mapped_column(String(50), nullable=False)
    value_before: Mapped[str | None] = mapped_column(Text)
    value_after: Mapped[str | None] = mapped_column(Text)
    note: Mapped[str | None] = mapped_column(Text)

    incident: Mapped[CrimeIncident] = relationship(back_populates="revisions")

    __table_args__ = (
        Index("ix_crime_incident_revisions_incident", "incident_id", "changed_at"),
        Index("ix_crime_incident_revisions_changed_by", "changed_by"),
    )
