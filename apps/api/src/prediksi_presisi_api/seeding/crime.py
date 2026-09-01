"""TASK 021 — Seed data kejadian: crime_incidents, intelligence_reports, patrol_activity.

Dua hal yang benar-benar diuji di sini pada volume nyata (docs/08 PHASE 3):

- **A-2** — setiap `grid_id` pada CSV terpetakan ke `location_id`. Grid yang tidak dikenal
  menghentikan seed, tidak dilewati diam-diam.
- **A-11** — `incident_date` + `incident_time` (waktu lokal WIB) digabung menjadi
  `occurred_at` dalam UTC.

Kolom `modus`, `target_type`, dan `location_type` dipertahankan apa adanya: itu istilah
lapangan, bukan taksonomi berjenjang yang perlu dipetakan (docs/02 §22).
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import CrimeIncident, IntelligenceReport, Location, PatrolActivity, PoliceUnit
from . import csv_source as src
from .errors import SeedError
from .master import SeedSummary
from .taxonomy import Taxonomy, load_taxonomy


def location_index(session: Session) -> dict[str, uuid.UUID]:
    """Peta `grid_id` → `location_id`, sesuai CLAUDE.md §19."""
    index = {
        grid_id: location_id
        for grid_id, location_id in session.execute(
            select(Location.grid_id, Location.location_id)
        ).all()
    }
    if not index:
        message = "tabel locations masih kosong — jalankan `pnpm seed:master` lebih dulu"
        raise SeedError(message)
    return index


def unit_index(session: Session) -> dict[str, uuid.UUID]:
    """Peta `code` unit → `unit_id`."""
    return {
        code: unit_id
        for code, unit_id in session.execute(select(PoliceUnit.code, PoliceUnit.unit_id)).all()
    }


def _resolve_location(index: dict[str, uuid.UUID], grid_id: str | None, where: str) -> uuid.UUID:
    if grid_id is None:
        message = f"{where}: kolom grid_id kosong, lokasi tidak dapat ditentukan"
        raise SeedError(message)

    location_id = index.get(grid_id)
    if location_id is None:
        message = (
            f"{where}: grid_id '{grid_id}' tidak ada pada tabel locations. "
            f"Perbaiki data sumber atau tambahkan lokasinya — jangan dilewati."
        )
        raise SeedError(message)
    return location_id


def seed_crime_incidents(session: Session, taxonomy: Taxonomy, summary: SeedSummary) -> None:
    existing = set(session.scalars(select(CrimeIncident.code)).all())
    locations = location_index(session)
    inserted = 0

    for row in src.read_rows("crime_incidents.csv"):
        code = src.required_text(row, "incident_id", "crime_incidents.csv")
        if code in existing:
            continue

        where = f"crime_incidents.csv:{code}"
        incident_date = src.parse_date(src.required_text(row, "incident_date", where), where)
        incident_time = src.parse_time(src.required_text(row, "incident_time", where), where)

        session.add(
            CrimeIncident(
                code=code,
                incident_type=taxonomy.require("incident_type", src.text(row, "incident_type")),
                occurred_at=src.combine(incident_date, incident_time),
                incident_date=incident_date,
                incident_time=incident_time,
                location_id=_resolve_location(locations, src.text(row, "grid_id"), where),
                location_type=src.text(row, "location_type"),
                modus=src.text(row, "modus"),
                target_type=src.text(row, "target_type"),
                status=taxonomy.map("status_crime", src.text(row, "status")),
            )
        )
        inserted += 1

    summary.record("crime_incidents", inserted, len(existing))


def seed_intelligence_reports(session: Session, taxonomy: Taxonomy, summary: SeedSummary) -> None:
    existing = set(session.scalars(select(IntelligenceReport.code)).all())
    locations = location_index(session)
    inserted = 0

    for row in src.read_rows("intelligence_reports.csv"):
        code = src.required_text(row, "intelligence_id", "intelligence_reports.csv")
        if code in existing:
            continue

        where = f"intelligence_reports.csv:{code}"

        session.add(
            IntelligenceReport(
                code=code,
                report_date=src.parse_date(src.required_text(row, "report_date", where), where),
                category=src.required_text(row, "category", where),
                location_id=_resolve_location(locations, src.text(row, "grid_id"), where),
                reliability=src.text(row, "reliability"),
                confidence=src.integer(row, "confidence"),
                urgency=src.integer(row, "urgency"),
                impact=taxonomy.map("impact", src.text(row, "impact")),
                status=taxonomy.map("status_intelligence", src.text(row, "status")),
            )
        )
        inserted += 1

    summary.record("intelligence_reports", inserted, len(existing))


def seed_patrol_activity(session: Session, summary: SeedSummary) -> None:
    existing = set(session.scalars(select(PatrolActivity.code)).all())
    locations = location_index(session)
    units = unit_index(session)
    inserted = 0

    for row in src.read_rows("patrol_activity.csv"):
        code = src.required_text(row, "patrol_id", "patrol_activity.csv")
        if code in existing:
            continue

        where = f"patrol_activity.csv:{code}"
        unit_code = src.required_text(row, "unit_id", where)
        unit_id = units.get(unit_code)
        if unit_id is None:
            message = f"{where}: unit '{unit_code}' tidak ada pada tabel police_units"
            raise SeedError(message)

        start_raw = src.text(row, "start_time")
        end_raw = src.text(row, "end_time")

        session.add(
            PatrolActivity(
                code=code,
                unit_id=unit_id,
                location_id=_resolve_location(locations, src.text(row, "grid_id"), where),
                patrol_date=src.parse_date(src.required_text(row, "patrol_date", where), where),
                start_time=None if start_raw is None else src.parse_time(start_raw, where),
                end_time=None if end_raw is None else src.parse_time(end_raw, where),
                activity_type=src.text(row, "activity_type"),
                result=src.text(row, "result"),
            )
        )
        inserted += 1

    summary.record("patrol_activity", inserted, len(existing))


def seed_crime_data(session: Session, taxonomy: Taxonomy | None = None) -> SeedSummary:
    """Menjalankan seluruh seed data kejadian TASK 021."""
    resolved = taxonomy or load_taxonomy()
    summary = SeedSummary()

    seed_crime_incidents(session, resolved, summary)
    seed_intelligence_reports(session, resolved, summary)
    seed_patrol_activity(session, summary)

    return summary
