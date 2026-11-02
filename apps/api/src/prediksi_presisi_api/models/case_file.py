"""Berkas perkara 3C — lacak laporan dan cek kendaraan untuk warga (keputusan pemilik
proyek 2 November 2026, butir 2, 3, 6).

Data Pusiknas yang dipakai sistem tidak memuat nomor LP, plat, maupun nomor rangka. Entitas
ini DIISI operator (Administrator/Polsek) atau, untuk peragaan, oleh pembangkit data dummy
yang menandai setiap baris `is_dummy = true` — dan label DUMMY itu tampil di setiap layar
yang menampilkannya, sisi warga maupun petugas.

BATAS YANG DIJAGA

- Warga melacak dengan **nomor LP + PIN** (empat digit yang dipegang pelapor), bukan nama
  atau plat: mencari dengan nama/plat saja berarti siapa pun dapat tahu seseorang pernah
  melapor. PIN disimpan sebagai hash.
- Cek kendaraan menjawab hanya **"tercatat sebagai laporan kehilangan" atau "tidak ada
  catatan"** — tanpa nama, tanpa nomor LP, tanpa alamat.
- Tahapan mengikuti istilah SP2HP (Diterima → Penyelidikan → Penyidikan → P21 / SP3 →
  Selesai) sebagai label; urutannya tidak dipaksa oleh sistem (SOP belum ditetapkan —
  PROPOSED), setiap perpindahan tercatat.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db import Base
from .base import TimestampMixin, uuid_pk

if TYPE_CHECKING:
    from .location import Location
    from .rbac import User

STAGES = ("DITERIMA", "LIDIK", "SIDIK", "P21", "SP3", "SELESAI")
STAGE_LABELS = {
    "DITERIMA": "Laporan diterima",
    "LIDIK": "Penyelidikan",
    "SIDIK": "Penyidikan",
    "P21": "Berkas lengkap (P21)",
    "SP3": "Penyidikan dihentikan (SP3)",
    "SELESAI": "Selesai",
}
CRIME_TYPES = ("CURANMOR", "CURAT", "CURAS")


def normalize_plate(plate: str) -> str:
    """'b 1234 abc' -> 'B1234ABC' — satu bentuk untuk dibandingkan."""
    return "".join(ch for ch in plate.upper() if ch.isalnum())


def hash_pin(lp_number: str, pin: str) -> str:
    """PIN digabung nomor LP sebelum di-hash: PIN yang sama pada LP lain menghasilkan hash lain."""
    return hashlib.sha256(f"{lp_number.strip().upper()}:{pin.strip()}".encode()).hexdigest()


class CaseFile(TimestampMixin, Base):
    __tablename__ = "case_files"

    case_id: Mapped[uuid.UUID] = uuid_pk()
    #: Nomor Laporan Polisi, mis. LP/B/123/X/2026/SPKT/POLSEK TEBET.
    lp_number: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    crime_type: Mapped[str] = mapped_column(String(50), nullable=False)
    location_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("locations.location_id", ondelete="RESTRICT"), nullable=False
    )
    reported_on: Mapped[date] = mapped_column(Date, nullable=False)
    stage: Mapped[str] = mapped_column(String(20), nullable=False, default="DITERIMA")
    stage_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    #: Uraian singkat yang boleh dilihat pelapor — tanpa nama siapa pun.
    summary: Mapped[str | None] = mapped_column(Text)
    #: Kendaraan (Curanmor): plat dalam bentuk ternormalisasi, nomor rangka, nomor mesin.
    vehicle_plate: Mapped[str | None] = mapped_column(String(16))
    vehicle_plate_display: Mapped[str | None] = mapped_column(String(20))
    vehicle_vin: Mapped[str | None] = mapped_column(String(30))
    vehicle_engine: Mapped[str | None] = mapped_column(String(30))
    vehicle_desc: Mapped[str | None] = mapped_column(String(120))
    vehicle_recovered: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    #: Hash PIN pelapor (empat digit); tidak pernah disimpan apa adanya.
    reporter_pin_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    #: Hanya untuk peragaan: PIN dummy boleh ditampilkan di layar petugas agar dapat dicoba.
    is_dummy: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    dummy_pin: Mapped[str | None] = mapped_column(String(4))

    location: Mapped[Location] = relationship()
    stages: Mapped[list[CaseStage]] = relationship(
        back_populates="case", cascade="all, delete-orphan", order_by="CaseStage.changed_at"
    )

    __table_args__ = (
        CheckConstraint("stage IN " + str(STAGES), name="case_stage_allowed"),
        CheckConstraint("crime_type IN " + str(CRIME_TYPES), name="case_crime_type_allowed"),
        CheckConstraint("is_dummy OR dummy_pin IS NULL", name="case_dummy_pin_only_for_dummy"),
        Index("ix_case_files_location", "location_id"),
        Index("ix_case_files_plate", "vehicle_plate"),
        Index("ix_case_files_vin", "vehicle_vin"),
        Index("ix_case_files_stage", "stage"),
    )


class CaseStage(Base):
    """Satu perpindahan tahap, dengan waktu dan catatan singkat untuk pelapor."""

    __tablename__ = "case_file_stages"

    stage_id: Mapped[uuid.UUID] = uuid_pk()
    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("case_files.case_id", ondelete="CASCADE"), nullable=False
    )
    stage: Mapped[str] = mapped_column(String(20), nullable=False)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    note: Mapped[str | None] = mapped_column(String(300))
    changed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="RESTRICT")
    )

    case: Mapped[CaseFile] = relationship(back_populates="stages")
    actor: Mapped[User | None] = relationship()

    __table_args__ = (
        CheckConstraint("stage IN " + str(STAGES), name="case_stage_history_allowed"),
        Index("ix_case_file_stages_case", "case_id", "changed_at"),
        Index("ix_case_file_stages_changed_by", "changed_by"),
    )
