"""Modul 1 mekanisme — "Membakukan laporan kejadian" (6 November 2026).

Tiga pekerjaan kecil yang dipakai pintu masuk data dan layar pembakuan:

- menandai dugaan laporan ganda saat entri petugas (sejenis, lokasi sama, ±1 hari);
- mencatat riwayat koreksi (`crime_incident_revisions`) — bidang, nilai sebelum/sesudah;
- memberi label sumber pada entri petugas supaya terpisah dari rekaman Pusiknas.

Aturan dugaan ganda adalah pilihan teknis (PROPOSED): dokumen hanya meminta dugaan
ditandai dan dicocokkan sebelum digabung; batas ±1 hari dan "lokasi sama" dipilih karena
itu yang dapat diperiksa tanpa identitas siapa pun.
"""

from __future__ import annotations

import uuid
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import CrimeIncident, CrimeIncidentRevision, User

DUPLICATE_WINDOW = timedelta(days=1)
DUPLICATE_BASIS = (
    "Dugaan ganda: kejadian sejenis pada lokasi yang sama dalam ±1 hari sudah tercatat. "
    "Ditandai, bukan digabung — dicocokkan dulu dengan Satreskrim/Polsek (PROPOSED)."
)


def officer_source(user: User) -> str:
    """Label sumber entri petugas, mis. `ENTRI:Polsek Tebet` atau `ENTRI:Administrator`."""
    unit = user.polsek or user.function or (user.role.role_name if user.role else "PETUGAS")
    return f"ENTRI:{unit}"[:50]


def flag_suspected_duplicate(session: Session, incident: CrimeIncident) -> str | None:
    """Menandai `incident` sebagai dugaan ganda dari kejadian tercatat yang paling mirip."""
    match = session.scalar(
        select(CrimeIncident.code)
        .where(
            CrimeIncident.code != incident.code,
            CrimeIncident.incident_type == incident.incident_type,
            CrimeIncident.location_id == incident.location_id,
            CrimeIncident.occurred_at >= incident.occurred_at - DUPLICATE_WINDOW,
            CrimeIncident.occurred_at <= incident.occurred_at + DUPLICATE_WINDOW,
        )
        .order_by(CrimeIncident.occurred_at.desc())
        .limit(1)
    )
    if match is None:
        return None
    incident.duplicate_of = match
    incident.duplicate_status = "SUSPECTED"
    return match


def record_revision(
    session: Session,
    incident: CrimeIncident,
    user_id: uuid.UUID | None,
    field: str,
    before: object,
    after: object,
    note: str | None = None,
) -> CrimeIncidentRevision:
    row = CrimeIncidentRevision(
        incident_id=incident.incident_id,
        changed_by=user_id,
        field=field,
        value_before=None if before is None else str(before),
        value_after=None if after is None else str(after),
        note=(note or "").strip() or None,
    )
    session.add(row)
    return row
