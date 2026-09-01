"""API kanal masyarakat (TASK 024) — laporan masyarakat dan ringkasan sinyalnya.

Fitur MVP #12 pada spesifikasi (*Community Intelligence*) dan keluaran §8 no. 6
(*community signal dashboard*).

**Yang wajib ikut terbaca bersama angka-angka di sini.** Spesifikasi §4 menyatakan:

> laporan masyarakat tidak langsung dianggap sebagai fakta. Laporan harus melalui
> klasifikasi, deteksi duplikasi, deteksi spam, pengelompokan lokasi, penilaian urgensi,
> dan validasi operator/analis sebelum memengaruhi risk score.

Pada prototipe ini **tidak satu pun** tahapan itu sudah dibangun. Karena itu setiap
respons membawa `basis` yang menyatakan apa adanya bahwa laporan masyarakat **belum
memengaruhi risk score sama sekali**, dan bahwa `urgency_score`/`verification_score`
adalah nilai sintetis berstatus `DEMO`. Menyatakan sebaliknya — atau mendiamkannya —
akan membuat layar tampak memiliki mekanisme yang belum ada (CLAUDE.md §27).

Cakupan wilayah ditegakkan **di query** lewat `location_id → locations.polsek`, seperti
endpoint daftar lain. Laporan yang belum tertaut ke sel grid tidak memiliki wilayah, dan
karena itu **tidak** diberikan kepada pengguna yang dibatasi wilayah: menebak wilayahnya
akan sama saja dengan mengarang lokasi, dan menyertakannya begitu saja akan membocorkan
laporan di luar wilayah pengguna.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from ...models import CitizenReport, CommunityFeedback, Location
from ..deps import CurrentUser, get_db, jurisdiction_filter, require_permission
from ..pagination import PageParams, page_params, paginate

router = APIRouter(tags=["masyarakat"])

#: Penanda mutu data, searah dengan Evaluation Center dan Warning Center.
DATA_STATUS = "DEMO"

#: Jumlah wilayah teratas pada ringkasan.
TOP_AREA_LIMIT = 5

#: Jumlah laporan terbaru pada ringkasan.
RECENT_REPORT_LIMIT = 5

BASIS = (
    "Laporan masyarakat BELUM memengaruhi risk score sama sekali: tidak ada jalur dari "
    "citizen_reports ke risk_scores maupun predictions pada prototipe ini. Spesifikasi §4 "
    "mensyaratkan laporan melewati klasifikasi, deteksi duplikasi, deteksi spam, "
    "pengelompokan lokasi, penilaian urgensi, dan validasi operator/analis sebelum boleh "
    "memengaruhi risiko — tidak satu pun tahapan itu sudah dibangun. `urgency_score` dan "
    "`verification_score` adalah nilai sintetis berstatus DEMO, bukan hasil penilaian "
    "model. Laporan tanpa tautan wilayah tidak diberikan kepada akun yang dibatasi wilayah."
)

#: Laporan tanpa `location_id` memang ada dan sengaja tidak dipetakan paksa (docs/02 §6).
UNMAPPED_BASIS = (
    "Laporan yang koordinatnya belum jatuh pada sel grid mana pun. Lokasinya tidak "
    "ditebak ke sel terdekat, sehingga laporan ini tidak memiliki wilayah dan tidak "
    "muncul pada akun yang dibatasi wilayah."
)


def _scoped_reports(polsek: str | None) -> Select[Any]:
    """Query dasar laporan beserta wilayahnya, sudah tersaring menurut cakupan pengguna."""
    query = select(CitizenReport, Location).outerjoin(
        Location, Location.location_id == CitizenReport.location_id
    )
    return query if polsek is None else query.where(Location.polsek == polsek)


def _report_item(report: CitizenReport, location: Location | None) -> dict[str, Any]:
    return {
        "code": report.code,
        "reported_at": report.reported_at,
        "incident_time": report.incident_time,
        "category": report.category,
        "description": report.description,
        "location_text": report.location_text,
        "urgency_score": report.urgency_score,
        "verification_score": report.verification_score,
        "status": report.status,
        # Kosong bila laporan belum tertaut ke sel grid — dinyatakan, bukan ditebak.
        "kecamatan": location.kecamatan if location else None,
        "kelurahan": location.kelurahan if location else None,
        "polsek": location.polsek if location else None,
        "grid_id": location.grid_id if location else None,
    }


@router.get("/citizen-reports", summary="Daftar laporan masyarakat")
def list_citizen_reports(
    session: Session = Depends(get_db),
    params: PageParams = Depends(page_params),
    current: CurrentUser = require_permission("citizen_report:read"),
    status: str | None = Query(
        None, description="RECEIVED, VERIFIED, FORWARDED, IN_PROGRESS, CLOSED"
    ),
    category: str | None = Query(None, description="Kategori laporan apa adanya"),
) -> dict[str, Any]:
    polsek = jurisdiction_filter(current, "citizen_report:read")

    query = _scoped_reports(polsek).order_by(CitizenReport.reported_at.desc())
    if status:
        query = query.where(CitizenReport.status == status.upper())
    if category:
        query = query.where(CitizenReport.category == category)

    total = session.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = session.execute(query.offset(params.offset).limit(params.page_size)).all()

    return {
        **paginate([_report_item(report, location) for report, location in rows], total, params),
        "status": DATA_STATUS,
        "basis": BASIS,
    }


def _grouped(session: Session, query: Select[Any]) -> dict[str, int]:
    return {str(key): int(total) for key, total in session.execute(query).all()}


def _feedback_block(session: Session, current: CurrentUser) -> dict[str, Any] | None:
    """Umpan balik masyarakat, bila pengguna berwenang membacanya.

    Cakupannya mengikuti permission umpan balik itu sendiri, bukan permission laporan:
    keduanya dideklarasikan terpisah pada `config/rbac/permissions.yaml`.
    """
    if not current.permissions.allows("community_feedback:read"):
        return None

    polsek = jurisdiction_filter(current, "community_feedback:read")
    base = (
        select(CommunityFeedback)
        .join(CitizenReport, CitizenReport.report_id == CommunityFeedback.report_id)
        .outerjoin(Location, Location.location_id == CitizenReport.location_id)
    )
    if polsek is not None:
        base = base.where(Location.polsek == polsek)

    total = session.scalar(select(func.count()).select_from(base.subquery())) or 0
    per_type = _grouped(
        session,
        base.with_only_columns(CommunityFeedback.feedback_type, func.count()).group_by(
            CommunityFeedback.feedback_type
        ),
    )
    per_status = _grouped(
        session,
        base.with_only_columns(CommunityFeedback.status, func.count()).group_by(
            CommunityFeedback.status
        ),
    )

    return {"total": total, "per_type": per_type, "per_status": per_status}


@router.get("/community/summary", summary="Ringkasan sinyal masyarakat")
def community_summary(
    session: Session = Depends(get_db),
    current: CurrentUser = require_permission("citizen_report:read"),
) -> dict[str, Any]:
    """Agregat untuk *community signal dashboard*.

    Seluruh agregat dihitung di atas query yang **sudah** tersaring menurut cakupan
    pengguna, sehingga jumlah total pun tidak membocorkan baris di luar wilayahnya.
    """
    polsek = jurisdiction_filter(current, "citizen_report:read")
    base = _scoped_reports(polsek)

    total = session.scalar(select(func.count()).select_from(base.subquery())) or 0
    per_status = _grouped(
        session,
        base.with_only_columns(CitizenReport.status, func.count()).group_by(CitizenReport.status),
    )
    per_category = _grouped(
        session,
        base.with_only_columns(CitizenReport.category, func.count()).group_by(
            CitizenReport.category
        ),
    )

    area_rows = session.execute(
        base.with_only_columns(Location.kecamatan, Location.polsek, func.count())
        .where(Location.kecamatan.is_not(None))
        .group_by(Location.kecamatan, Location.polsek)
        .order_by(func.count().desc(), Location.kecamatan)
        .limit(TOP_AREA_LIMIT)
    ).all()

    unmapped = (
        session.scalar(
            select(func.count()).select_from(
                base.where(CitizenReport.location_id.is_(None)).subquery()
            )
        )
        or 0
    )

    recent = session.execute(
        base.order_by(CitizenReport.reported_at.desc()).limit(RECENT_REPORT_LIMIT)
    ).all()

    return {
        "total_reports": total,
        "per_status": per_status,
        "per_category": per_category,
        "top_areas": [
            {"kecamatan": kecamatan, "polsek": unit, "total": int(count)}
            for kecamatan, unit, count in area_rows
        ],
        "recent_reports": [_report_item(report, location) for report, location in recent],
        "unmapped_reports": unmapped,
        "unmapped_basis": UNMAPPED_BASIS,
        "feedback": _feedback_block(session, current),
        "status": DATA_STATUS,
        "basis": BASIS,
    }
