"""Produk bulanan (Modul 4 mekanisme, migration 0021).

Satu `MonthlyProduct` per bulan sasaran, dibangun dari peringkat yang DIBEKUKAN. Isinya
`MonthlyProductItem` per kelurahan teratas (draf usulan sistem), `MonthlyProductStage`
per tahap pemeriksaan (ANALYST → KBO → KASAT → PIMPINAN; alasan wajib bila ditolak atau
diperbaiki), dan `MonthlyAction` — kegiatan nyata yang dicatat fungsi pelaksana.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    false,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db import Base
from .base import TimestampMixin, uuid_pk

# KBO_CHECKED / VALIDATED dan tahap KBO / KASAT adalah tinggalan alur empat tahap
# (6–10 November 2026); dipertahankan agar baris lama tetap sah dan tertelusur. Alur yang
# berjalan: DRAFT → ANALYST_REVIEWED → DECIDED (catatan 177).
STATUSES = ("DRAFT", "ANALYST_REVIEWED", "KBO_CHECKED", "VALIDATED", "DECIDED")
STAGES = ("ANALYST", "KBO", "KASAT", "PIMPINAN")
OUTCOMES = ("ACCEPTED", "REVISED", "REJECTED", "DECIDED")
ANALYST_STATUSES = ("ACCEPTED", "REVISED", "REJECTED")


class MonthlyProduct(TimestampMixin, Base):
    __tablename__ = "monthly_products"

    product_id: Mapped[uuid.UUID] = uuid_pk()
    target_month: Mapped[date] = mapped_column(Date, nullable=False, unique=True)
    ranking_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("monthly_rankings.ranking_id", ondelete="RESTRICT"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="DRAFT")
    facts: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    priority_count: Mapped[int | None] = mapped_column(Integer)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="SET NULL")
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    items: Mapped[list[MonthlyProductItem]] = relationship(
        back_populates="product", cascade="all, delete-orphan", order_by="MonthlyProductItem.rank"
    )
    stages: Mapped[list[MonthlyProductStage]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
        order_by="MonthlyProductStage.acted_at",
    )

    __table_args__ = (
        CheckConstraint("status IN " + str(STATUSES), name="monthly_product_status_allowed"),
        Index("ix_monthly_products_ranking_id", "ranking_id"),
        Index("ix_monthly_products_created_by", "created_by"),
    )


class MonthlyProductItem(Base):
    __tablename__ = "monthly_product_items"

    item_id: Mapped[uuid.UUID] = uuid_pk()
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("monthly_products.product_id", ondelete="CASCADE"),
        nullable=False,
    )
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    kelurahan: Mapped[str] = mapped_column(String(100), nullable=False)
    kecamatan: Mapped[str] = mapped_column(String(100), nullable=False)
    polsek: Mapped[str] = mapped_column(String(100), nullable=False)
    predicted_count: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    #: Pola yang mendasari usulan: jumlah per jenis, jenis dominan, blok jam puncak.
    pattern: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    proposal_text: Mapped[str] = mapped_column(Text, nullable=False)
    proposed_function: Mapped[str] = mapped_column(String(30), nullable=False)
    analyst_status: Mapped[str | None] = mapped_column(String(10))
    analyst_text: Mapped[str | None] = mapped_column(Text)
    analyst_reason: Mapped[str | None] = mapped_column(Text)
    selected: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )
    decided_action: Mapped[str | None] = mapped_column(Text)

    product: Mapped[MonthlyProduct] = relationship(back_populates="items")
    actions: Mapped[list[MonthlyAction]] = relationship(
        back_populates="item", cascade="all, delete-orphan", order_by="MonthlyAction.acted_at"
    )

    __table_args__ = (
        UniqueConstraint("product_id", "kelurahan", name="uq_monthly_product_items_kelurahan"),
        CheckConstraint(
            "analyst_status IS NULL OR analyst_status IN " + str(ANALYST_STATUSES),
            name="monthly_item_analyst_status_allowed",
        ),
        Index("ix_monthly_product_items_product", "product_id", "rank"),
    )


class MonthlyProductStage(Base):
    __tablename__ = "monthly_product_stages"

    stage_id: Mapped[uuid.UUID] = uuid_pk()
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("monthly_products.product_id", ondelete="CASCADE"),
        nullable=False,
    )
    stage: Mapped[str] = mapped_column(String(10), nullable=False)
    outcome: Mapped[str] = mapped_column(String(10), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    note: Mapped[str | None] = mapped_column(Text)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    acted_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="SET NULL")
    )
    acted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    product: Mapped[MonthlyProduct] = relationship(back_populates="stages")

    __table_args__ = (
        CheckConstraint("stage IN " + str(STAGES), name="monthly_stage_allowed"),
        CheckConstraint("outcome IN " + str(OUTCOMES), name="monthly_stage_outcome_allowed"),
        Index("ix_monthly_product_stages_product", "product_id", "acted_at"),
        Index("ix_monthly_product_stages_acted_by", "acted_by"),
    )


class MonthlyAction(Base):
    __tablename__ = "monthly_actions"

    action_id: Mapped[uuid.UUID] = uuid_pk()
    item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("monthly_product_items.item_id", ondelete="CASCADE"),
        nullable=False,
    )
    recorded_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="SET NULL")
    )
    unit: Mapped[str] = mapped_column(String(100), nullable=False)
    acted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    place: Mapped[str] = mapped_column(String(200), nullable=False)
    action: Mapped[str] = mapped_column(Text, nullable=False)
    result: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    item: Mapped[MonthlyProductItem] = relationship(back_populates="actions")

    __table_args__ = (
        Index("ix_monthly_actions_item", "item_id", "acted_at"),
        Index("ix_monthly_actions_recorded_by", "recorded_by"),
    )
