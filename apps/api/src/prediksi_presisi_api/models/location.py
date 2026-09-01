"""Master wilayah/grid — `locations` (docs/02 §1).

`locations` adalah referensi lokasi kanonik untuk seluruh tabel transaksi (CLAUDE.md §19).
Data import yang hanya membawa `grid_id` dipetakan ke `location_id` melalui tabel ini.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from geoalchemy2 import Geometry
from sqlalchemy import CheckConstraint, Index, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db import Base
from .base import TimestampMixin, uuid_pk

if TYPE_CHECKING:
    from .citizen_report import CitizenReport
    from .crime_incident import CrimeIncident
    from .early_warning import EarlyWarning
    from .intelligence_report import IntelligenceReport
    from .operational_action import OperationalAction
    from .patrol_activity import PatrolActivity
    from .prediction import Prediction
    from .risk_score import RiskScore


class Location(TimestampMixin, Base):
    """Wilayah/grid tempat kejadian, patroli, dan penilaian risiko dilekatkan."""

    __tablename__ = "locations"

    location_id: Mapped[uuid.UUID] = uuid_pk()

    #: ID pada dataset dummy, mis. "LOC-001" (docs/02 K-2)
    code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)

    #: Kunci alami wilayah/grid, mis. "JKS-001" — dipakai saat import
    grid_id: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)

    polsek: Mapped[str] = mapped_column(String(100), nullable=False)
    kecamatan: Mapped[str] = mapped_column(String(100), nullable=False)
    kelurahan: Mapped[str | None] = mapped_column(String(100))

    #: Ukuran grid dalam meter. Besarannya belum final (U-04), tetapi kolomnya wajib (docs/02 §1).
    grid_size_m: Mapped[int] = mapped_column(Integer, nullable=False)

    latitude: Mapped[float] = mapped_column(Numeric(9, 6), nullable=False)
    longitude: Mapped[float] = mapped_column(Numeric(9, 6), nullable=False)

    #: Titik pusat wilayah/grid. Geometri poligon belum ditambahkan — menunggu U-04.
    #: `spatial_index=False` — index GIST dideklarasikan eksplisit di __table_args__
    #: agar tidak ada dua index yang sama (GeoAlchemy2 membuatnya otomatis secara default).
    geom: Mapped[object] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326, spatial_index=False), nullable=False
    )

    #: Kategori TKP. Nilai taksonomi belum final (U-16) sehingga disimpan sebagai teks.
    location_type: Mapped[str | None] = mapped_column(String(100))

    crime_incidents: Mapped[list[CrimeIncident]] = relationship(back_populates="location")
    intelligence_reports: Mapped[list[IntelligenceReport]] = relationship(back_populates="location")
    patrol_activities: Mapped[list[PatrolActivity]] = relationship(back_populates="location")
    citizen_reports: Mapped[list[CitizenReport]] = relationship(back_populates="location")
    risk_scores: Mapped[list[RiskScore]] = relationship(back_populates="location")
    predictions: Mapped[list[Prediction]] = relationship(back_populates="location")
    early_warnings: Mapped[list[EarlyWarning]] = relationship(back_populates="location")
    operational_actions: Mapped[list[OperationalAction]] = relationship(
        back_populates="location", foreign_keys="OperationalAction.location_id"
    )

    __table_args__ = (
        CheckConstraint("latitude BETWEEN -90 AND 90", name="latitude_range"),
        CheckConstraint("longitude BETWEEN -180 AND 180", name="longitude_range"),
        Index("ix_locations_polsek", "polsek"),
        Index("ix_locations_kecamatan", "kecamatan"),
        Index("ix_locations_geom", "geom", postgresql_using="gist"),
    )
