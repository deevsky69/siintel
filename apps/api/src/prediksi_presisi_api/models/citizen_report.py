"""Laporan masyarakat — `citizen_reports` (docs/02 §6).

Laporan masyarakat **tidak otomatis dianggap fakta**; wajib melewati verifikasi
(`verification_score`, `status`) sebelum dipakai sebagai dasar tindakan.

Identitas/kontak pelapor dan lampiran bukti **tidak** disimpan pada PoC
(CLAUDE.md §16, U-13 — menunggu keputusan kebijakan).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from geoalchemy2 import Geometry
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    SmallInteger,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db import Base
from .base import TimestampMixin, uuid_pk

if TYPE_CHECKING:
    from .community_feedback import CommunityFeedback
    from .location import Location


class CitizenReport(TimestampMixin, Base):
    """Satu laporan dari masyarakat."""

    __tablename__ = "citizen_reports"

    report_id: Mapped[uuid.UUID] = uuid_pk()
    code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)

    #: Kapan laporan masuk.
    reported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    #: Kapan kejadian menurut pelapor. Boleh kosong bila pelapor tidak mengetahuinya.
    incident_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    category: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    latitude: Mapped[float] = mapped_column(Numeric(9, 6), nullable=False)
    longitude: Mapped[float] = mapped_column(Numeric(9, 6), nullable=False)
    geom: Mapped[object] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326, spatial_index=False), nullable=False
    )

    #: Nullable: laporan masuk dengan koordinat bebas dan baru dipetakan ke grid
    #: setelah geo-processing (docs/02 §6).
    location_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("locations.location_id", ondelete="RESTRICT"),
    )

    location_text: Mapped[str | None] = mapped_column(String(255))

    urgency_score: Mapped[int | None] = mapped_column(SmallInteger)
    verification_score: Mapped[int | None] = mapped_column(SmallInteger)

    status: Mapped[str] = mapped_column(String(50), nullable=False)

    location: Mapped[Location | None] = relationship(back_populates="citizen_reports")
    feedback: Mapped[list[CommunityFeedback]] = relationship(back_populates="report")

    __table_args__ = (
        CheckConstraint(
            "urgency_score IS NULL OR (urgency_score BETWEEN 0 AND 100)",
            name="urgency_score_range",
        ),
        CheckConstraint(
            "verification_score IS NULL OR (verification_score BETWEEN 0 AND 100)",
            name="verification_score_range",
        ),
        CheckConstraint("latitude BETWEEN -90 AND 90", name="latitude_range"),
        CheckConstraint("longitude BETWEEN -180 AND 180", name="longitude_range"),
        Index("ix_citizen_reports_reported_at", "reported_at"),
        Index("ix_citizen_reports_status", "status"),
        Index("ix_citizen_reports_location", "location_id"),
        Index("ix_citizen_reports_geom", "geom", postgresql_using="gist"),
    )
