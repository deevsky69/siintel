"""Survey Rasa Aman — ulasan warga per kelurahan (keputusan pemilik proyek 2 November 2026).

Seperti ulasan tempat pada peta daring: siapa pun dapat memberi nilai 1–5 dan komentar
singkat untuk kelurahannya, dan semua orang dapat membacanya. Batas-batasnya:

- **Anonim.** Tidak ada nama, nomor, atau pengenal percakapan. Yang disimpan hanya nilai,
  komentar, kelurahan, dan waktu. Pembatas laju per alamat jaringan menahan banjir.
- **Moderasi dulu, baru tayang.** Komentar bebas di ruang publik dapat memuat fitnah,
  identitas orang lain, atau hasutan. Ulasan masuk sebagai PENDING; yang tayang hanya
  PUBLISHED, diputuskan pemegang `review:moderate`. Nilai rata-rata dihitung dari yang
  tayang saja supaya tidak dapat dicurangi oleh ulasan yang belum diperiksa.
- Ulasan tidak menyentuh data kejadian: ia persepsi, bukan fakta kamtibmas, dan layar
  menyebutnya demikian.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, SmallInteger, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db import Base
from .base import TimestampMixin, uuid_pk

if TYPE_CHECKING:
    from .location import Location
    from .rbac import User

STATUS_PENDING = "PENDING"
STATUS_PUBLISHED = "PUBLISHED"
STATUS_REJECTED = "REJECTED"
STATUSES = (STATUS_PENDING, STATUS_PUBLISHED, STATUS_REJECTED)
MAX_COMMENT = 300


class AreaReview(TimestampMixin, Base):
    __tablename__ = "area_reviews"

    review_id: Mapped[uuid.UUID] = uuid_pk()
    code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    #: Master kelurahan (baris `locations` dengan kelurahan terisi).
    location_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("locations.location_id", ondelete="RESTRICT"), nullable=False
    )
    rating: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=STATUS_PENDING)
    moderated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="RESTRICT")
    )
    moderated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    moderation_note: Mapped[str | None] = mapped_column(String(300))

    location: Mapped[Location] = relationship()
    moderator: Mapped[User | None] = relationship()

    __table_args__ = (
        CheckConstraint("rating BETWEEN 1 AND 5", name="review_rating_range"),
        CheckConstraint("status IN " + str(STATUSES), name="review_status_allowed"),
        Index("ix_area_reviews_location_status", "location_id", "status"),
        Index("ix_area_reviews_status_submitted", "status", "submitted_at"),
        Index("ix_area_reviews_moderated_by", "moderated_by"),
    )
