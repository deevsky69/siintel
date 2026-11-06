"""Peringkat bulanan 65 kelurahan (Modul 2–3 mekanisme, migration 0020).

Satu `MonthlyRanking` per (bulan sasaran, metode, cakupan) — dibekukan SEBELUM bulan
berjalan beserta batas data dan versi metode, supaya dapat dievaluasi apa adanya setelah
bulan berakhir. Barisnya seluruh kelurahan, berurutan; seri diurutkan menurut nama.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db import Base
from .base import TimestampMixin, uuid_pk

METHODS = ("HISTORY_3M", "HISTORY_12M", "MODEL")
SCOPES = ("ALL_3C", "VEHICLE")


class MonthlyRanking(TimestampMixin, Base):
    __tablename__ = "monthly_rankings"

    ranking_id: Mapped[uuid.UUID] = uuid_pk()
    #: Hari pertama bulan sasaran.
    target_month: Mapped[date] = mapped_column(Date, nullable=False)
    method: Mapped[str] = mapped_column(String(20), nullable=False)
    scope: Mapped[str] = mapped_column(String(20), nullable=False)
    #: Kejadian yang DILAPORKAN sampai tanggal ini saja yang dipakai (dokumen: "batas data").
    data_cutoff: Mapped[date] = mapped_column(Date, nullable=False)
    model_version: Mapped[str] = mapped_column(String(60), nullable=False)
    basis_from: Mapped[date] = mapped_column(Date, nullable=False)
    basis_to: Mapped[date] = mapped_column(Date, nullable=False)
    #: Jumlah laporan yang masih memerlukan konfirmasi kelurahan saat dibekukan.
    pending_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    generated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="SET NULL")
    )

    rows: Mapped[list[MonthlyRankingRow]] = relationship(
        back_populates="ranking", cascade="all, delete-orphan", order_by="MonthlyRankingRow.rank"
    )

    __table_args__ = (
        UniqueConstraint(
            "target_month", "method", "scope", name="uq_monthly_rankings_month_method_scope"
        ),
        CheckConstraint("method IN " + str(METHODS), name="monthly_ranking_method_allowed"),
        CheckConstraint("scope IN " + str(SCOPES), name="monthly_ranking_scope_allowed"),
        Index("ix_monthly_rankings_target_month", "target_month"),
        Index("ix_monthly_rankings_generated_by", "generated_by"),
    )


class MonthlyRankingRow(Base):
    __tablename__ = "monthly_ranking_rows"

    row_id: Mapped[uuid.UUID] = uuid_pk()
    ranking_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("monthly_rankings.ranking_id", ondelete="CASCADE"),
        nullable=False,
    )
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    kelurahan: Mapped[str] = mapped_column(String(100), nullable=False)
    kecamatan: Mapped[str] = mapped_column(String(100), nullable=False)
    polsek: Mapped[str] = mapped_column(String(100), nullable=False)
    #: Perkiraan jumlah kejadian pada bulan sasaran (rata-rata bulanan pada peta historis).
    predicted_count: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    ikw: Mapped[float | None] = mapped_column(Numeric(5, 1))
    ikw_category: Mapped[str | None] = mapped_column(String(10))
    #: Angka dasarnya: jumlah per bulan, tren, konsistensi — supaya dapat dihitung ulang.
    basis: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    ranking: Mapped[MonthlyRanking] = relationship(back_populates="rows")

    __table_args__ = (
        UniqueConstraint("ranking_id", "kelurahan", name="uq_monthly_ranking_rows_kelurahan"),
        UniqueConstraint("ranking_id", "rank", name="uq_monthly_ranking_rows_rank"),
        Index("ix_monthly_ranking_rows_ranking", "ranking_id", "rank"),
    )
