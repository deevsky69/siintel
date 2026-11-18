"""Mutu data — Modul 1 "Pembakuan data" (naskah Taskap Bab IV 4.1; 18 November 2026).

TIGA PEKERJAAN

1. KELENGKAPAN. Berapa persen laporan 3C yang kelurahan, jam, koordinat, objek sasaran,
   modus, dan tempat kejadiannya terisi — indikator Tabel 25 naskah (garis dasar kelurahan
   94,97% dan jam 78,1%).

2. PENANDAAN isian kosong atau tidak konsisten, untuk diperiksa petugas terhadap sumbernya.
   Naskah menyebutnya "AI menandai"; yang berjalan di sini adalah ATURAN yang tertulis di
   bawah, bukan model — dinyatakan apa adanya pada `basis` (CLAUDE.md §27). Yang ditandai
   tidak diubah: koreksi tetap lewat petugas dan tercatat di riwayat koreksi.

3. PENCOCOKAN ANTARKANAL. Laporan warga yang sudah diverifikasi disandingkan dengan kejadian
   resmi yang mungkin merujuk peristiwa yang sama (wilayah sama, waktu berdekatan). Sistem
   hanya MENGUSULKAN; petugas memutuskan cocok atau tidak, dengan alasan. Yang cocok
   ditautkan sehingga satu peristiwa terhitung sekali; yang terverifikasi tetapi tanpa
   padanan resmi dihitung terpisah sebagai KEJADIAN TAMBAHAN TERVERIFIKASI; yang belum
   diverifikasi berstatus MENUNGGU PEMERIKSAAN dan tidak dihitung.

Laporan warga tidak memuat identitas pelapor; yang dipakai hanya waktu, wilayah, kategori.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.orm import Session

from ..models import CitizenReport, CrimeIncident, Location, User
from . import clock
from .monthly_ranking import THREATS

#: Jarak hari antara laporan warga dan kejadian resmi yang masih diusulkan sebagai pasangan.
MATCH_WINDOW = timedelta(days=3)
MAX_CANDIDATES = 5
#: Laporan warga yang sudah diperiksa petugas (bukan lagi RECEIVED).
VERIFIED_STATUSES = ("VERIFIED", "FORWARDED", "IN_PROGRESS", "CLOSED")
PENDING_STATUS = "RECEIVED"

BASIS = (
    "Kelengkapan dihitung atas seluruh laporan curat, curas, dan curanmor. Penandaan isian "
    "kosong atau tidak konsisten memakai aturan tertulis (bukan model): jam kosong, objek "
    "sasaran kosong, tempat kejadian kosong, label curanmor dengan objek bukan kendaraan "
    "bermotor, dan tanggal laporan mendahului tanggal kejadian. Usulan pasangan laporan warga "
    "dengan kejadian resmi disusun dari wilayah yang sama dan selisih waktu paling lama 3 hari; "
    "petugas yang memutuskan cocok atau tidak, dengan alasan. Yang ditandai tidak pernah "
    "diubah otomatis."
)

FLAGS: dict[str, str] = {
    "NO_TIME": "Jam kejadian kosong",
    "NO_TARGET": "Objek sasaran kosong",
    "NO_PLACE": "Tempat kejadian kosong",
    "LABEL_OBJECT": "Berlabel curanmor, objek bukan kendaraan bermotor",
    "REPORT_BEFORE_INCIDENT": "Tanggal laporan mendahului tanggal kejadian",
}


class QualityError(ValueError):
    def __init__(self, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.status = status


def _empty(column: Any) -> Any:
    return or_(column.is_(None), func.btrim(column) == "")


def _flag_clause(kind: str) -> Any:
    if kind == "NO_TIME":
        return CrimeIncident.incident_time.is_(None)
    if kind == "NO_TARGET":
        return _empty(CrimeIncident.target_type)
    if kind == "NO_PLACE":
        return _empty(CrimeIncident.location_type)
    if kind == "LABEL_OBJECT":
        return and_(
            CrimeIncident.incident_type == "CURANMOR", CrimeIncident.vehicle_object.is_(False)
        )
    if kind == "REPORT_BEFORE_INCIDENT":
        return func.date(func.timezone("Asia/Jakarta", CrimeIncident.reported_at)) < (
            CrimeIncident.incident_date
        )
    raise QualityError(f"Tanda {kind} tidak dikenal.")


def _incidents(polsek: str | None) -> Select[Any]:
    query = (
        select(func.count())
        .select_from(CrimeIncident)
        .join(Location, Location.location_id == CrimeIncident.location_id)
        .where(CrimeIncident.incident_type.in_(THREATS))
    )
    return query if polsek is None else query.where(Location.polsek == polsek)


def _reports(polsek: str | None) -> Select[Any]:
    query = select(func.count()).select_from(CitizenReport)
    if polsek is None:
        return query
    return query.join(Location, Location.location_id == CitizenReport.location_id).where(
        Location.polsek == polsek
    )


def _pct(part: int, total: int) -> float | None:
    return round(part / total * 100, 2) if total else None


def summary(session: Session, polsek: str | None = None) -> dict[str, Any]:
    def count(query: Select[Any]) -> int:
        return int(session.scalar(query) or 0)

    total = count(_incidents(polsek))
    filled = {
        "kelurahan": count(
            _incidents(polsek).where(
                Location.kelurahan.is_not(None), CrimeIncident.area_pending.is_(False)
            )
        ),
        "jam": count(_incidents(polsek).where(CrimeIncident.incident_time.is_not(None))),
        "koordinat": count(
            _incidents(polsek).where(
                CrimeIncident.latitude.is_not(None), CrimeIncident.longitude.is_not(None)
            )
        ),
        "objek_sasaran": total - count(_incidents(polsek).where(_flag_clause("NO_TARGET"))),
        "tempat_kejadian": total - count(_incidents(polsek).where(_flag_clause("NO_PLACE"))),
    }
    labels = {
        "kelurahan": "Kelurahan",
        "jam": "Jam kejadian",
        "koordinat": "Koordinat",
        "objek_sasaran": "Objek sasaran",
        "tempat_kejadian": "Tempat kejadian",
    }
    verified = CitizenReport.status.in_(VERIFIED_STATUSES)
    return {
        "incidents": total,
        "completeness": [
            {"field": key, "label": labels[key], "filled": value, "pct": _pct(value, total)}
            for key, value in filled.items()
        ],
        "flags": [
            {
                "kind": kind,
                "label": label,
                "total": count(_incidents(polsek).where(_flag_clause(kind))),
            }
            for kind, label in FLAGS.items()
        ],
        "counting": {
            # Satu peristiwa terhitung sekali: laporan warga yang ditautkan tidak menambah.
            "official": total,
            "linked_reports": count(
                _reports(polsek).where(CitizenReport.match_decision == "MATCHED")
            ),
            "additional_verified": count(
                _reports(polsek).where(verified, CitizenReport.match_decision == "NOT_MATCHED")
            ),
            "awaiting_match": count(
                _reports(polsek).where(verified, CitizenReport.match_decision.is_(None))
            ),
            "awaiting_verification": count(
                _reports(polsek).where(CitizenReport.status == PENDING_STATUS)
            ),
        },
        "basis": BASIS,
    }


def flagged(
    session: Session, kind: str, polsek: str | None = None, limit: int = 50
) -> dict[str, Any]:
    if kind not in FLAGS:
        raise QualityError(f"Tanda {kind} tidak dikenal.")
    query = (
        select(CrimeIncident, Location)
        .join(Location, Location.location_id == CrimeIncident.location_id)
        .where(CrimeIncident.incident_type.in_(THREATS), _flag_clause(kind))
    )
    if polsek is not None:
        query = query.where(Location.polsek == polsek)
    rows = session.execute(query.order_by(CrimeIncident.incident_date.desc()).limit(limit)).all()
    return {
        "kind": kind,
        "label": FLAGS[kind],
        "total": int(session.scalar(_incidents(polsek).where(_flag_clause(kind))) or 0),
        "data": [
            {
                "code": incident.code,
                "incident_type": incident.incident_type,
                "incident_date": incident.incident_date,
                "kecamatan": location.kecamatan,
                "kelurahan": location.kelurahan,
                "target_type": incident.target_type,
                "location_type": incident.location_type,
                "data_source": incident.data_source,
            }
            for incident, location in rows
        ],
    }


def _report_day(report: CitizenReport) -> date:
    moment = report.incident_time or report.reported_at
    return moment.astimezone(clock.JAKARTA).date()


def candidates(session: Session, report: CitizenReport) -> list[dict[str, Any]]:
    """Kejadian resmi yang mungkin merujuk peristiwa yang sama — usulan, bukan keputusan."""
    place = report.location
    if place is None:
        return []
    day = _report_day(report)
    query = (
        select(CrimeIncident, Location)
        .join(Location, Location.location_id == CrimeIncident.location_id)
        .where(
            CrimeIncident.incident_type.in_(THREATS),
            CrimeIncident.incident_date >= day - MATCH_WINDOW,
            CrimeIncident.incident_date <= day + MATCH_WINDOW,
            Location.kecamatan == place.kecamatan,
        )
    )
    if place.kelurahan:
        # Kelurahan yang sama, atau kejadian yang kelurahannya sendiri belum pasti.
        query = query.where(
            or_(Location.kelurahan == place.kelurahan, Location.kelurahan.is_(None))
        )
    rows = sorted(
        session.execute(query).all(),
        key=lambda row: (abs((row[0].incident_date - day).days), row[0].code),
    )
    return [
        {
            "code": incident.code,
            "incident_type": incident.incident_type,
            "incident_date": incident.incident_date,
            "kelurahan": location.kelurahan,
            "kecamatan": location.kecamatan,
            "location_type": incident.location_type,
            "target_type": incident.target_type,
            "days_apart": abs((incident.incident_date - day).days),
            "same_kelurahan": bool(place.kelurahan and location.kelurahan == place.kelurahan),
        }
        for incident, location in rows[:MAX_CANDIDATES]
    ]


def _report_row(session: Session, report: CitizenReport, *, propose: bool) -> dict[str, Any]:
    place = report.location
    linked = (
        session.scalar(
            select(CrimeIncident.code).where(
                CrimeIncident.incident_id == report.matched_incident_id
            )
        )
        if report.matched_incident_id
        else None
    )
    return {
        "code": report.code,
        "category": report.category,
        "status": report.status,
        "reported_at": report.reported_at,
        "incident_time": report.incident_time,
        "kecamatan": place.kecamatan if place else None,
        "kelurahan": place.kelurahan if place else None,
        "description": report.description,
        "match_decision": report.match_decision,
        "match_reason": report.match_reason,
        "matched_incident": linked,
        "candidates": candidates(session, report) if propose else [],
    }


def match_queue(session: Session, polsek: str | None = None, limit: int = 30) -> dict[str, Any]:
    """Laporan warga terverifikasi yang belum diputuskan kecocokannya, dengan usulannya."""
    query = select(CitizenReport).where(
        CitizenReport.status.in_(VERIFIED_STATUSES), CitizenReport.match_decision.is_(None)
    )
    if polsek is not None:
        query = query.join(Location, Location.location_id == CitizenReport.location_id).where(
            Location.polsek == polsek
        )
    rows = session.scalars(query.order_by(CitizenReport.reported_at.desc()).limit(limit)).all()
    return {
        "total": int(
            session.scalar(
                _reports(polsek).where(
                    CitizenReport.status.in_(VERIFIED_STATUSES),
                    CitizenReport.match_decision.is_(None),
                )
            )
            or 0
        ),
        "data": [_report_row(session, report, propose=True) for report in rows],
        "window_days": MATCH_WINDOW.days,
    }


def decide_match(
    session: Session,
    report: CitizenReport,
    decision: str,
    incident_code: str | None,
    reason: str | None,
    user: User,
    polsek: str | None = None,
) -> dict[str, Any]:
    """`polsek` adalah cakupan wilayah pemutus: kejadian di luar wilayahnya tidak dapat
    ditautkan, dan dijawab sama seperti kejadian yang tidak ada."""
    decision = decision.upper()
    if decision not in ("MATCHED", "NOT_MATCHED"):
        raise QualityError("Keputusan harus MATCHED atau NOT_MATCHED.")
    if not (reason or "").strip():
        raise QualityError("Alasan keputusan wajib diisi.")
    if report.status not in VERIFIED_STATUSES:
        raise QualityError(
            "Laporan ini masih menunggu pemeriksaan; verifikasi dulu sebelum dicocokkan.", 409
        )
    incident_id = None
    if decision == "MATCHED":
        if not incident_code:
            raise QualityError("Sebutkan kode kejadian resmi yang cocok.")
        lookup = (
            select(CrimeIncident)
            .join(Location, Location.location_id == CrimeIncident.location_id)
            .where(CrimeIncident.code == incident_code.strip())
        )
        if polsek is not None:
            lookup = lookup.where(Location.polsek == polsek)
        incident = session.scalar(lookup)
        if incident is None:
            raise QualityError(f"Kejadian {incident_code} tidak dikenal.")
        incident_id = incident.incident_id
    report.match_decision = decision
    report.matched_incident_id = incident_id
    report.match_reason = (reason or "").strip()
    report.matched_by = user.user_id
    report.matched_at = clock.citizen_now()
    session.flush()
    return _report_row(session, report, propose=False)
