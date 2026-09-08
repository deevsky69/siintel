"""Lampiran laporan masyarakat — daftar dan pengambilan berkas (revisi 8 September 2026).

Berkas yang dikirim warga memuat wajah, suara, dan tempat. Ia diterima karena verifikasi
membutuhkannya; ia dijaga karena alasan yang sama tidak berlaku bagi siapa pun yang tidak
memverifikasi.

TIGA PENJAGA, DAN MENGAPA KETIGANYA DI SINI DAN BUKAN DI LAYAR

1. **Kewenangan.** Hanya pemegang `citizen_report:write` — peran yang memang bertugas
   memverifikasi — yang dapat membuka lampiran. Membacanya bukan tindakan pasif: ia
   memperlihatkan wajah orang yang tidak pernah menyetujui apa pun.

2. **Cakupan wilayah.** Mengikuti aturan triase pada `data_entry.py`: laporan di luar
   wilayah pengguna dijawab `404`, bukan `403`. Menjawab "ada tetapi tidak boleh"
   memberi tahu keberadaan laporan kepada orang yang tidak berhak mengetahuinya.

3. **Jejak.** Setiap pengambilan berkas dicatat — siapa, kapan, lampiran mana. Melihat
   data pribadi adalah peristiwa yang pantas ditanggungjawabkan (CLAUDE.md §29).

Isi berkas tidak pernah masuk ke jejak audit; yang dicatat adalah bahwa ia dibuka.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...models import CitizenReport, CitizenReportAttachment, Location
from ...services import attachments as attachment_store
from ...services import audit
from ..deps import CurrentUser, get_db, jurisdiction_filter, require_permission
from ..errors import ApiError

router = APIRouter(tags=["laporan masyarakat"])

#: Kewenangan yang membuka lampiran. Sama dengan kewenangan triase: yang boleh memutuskan
#: nasib sebuah laporan adalah yang boleh melihat buktinya, dan tidak seorang pun selain itu.
VIEW_PERMISSION = "citizen_report:write"


def _report_in_scope(session: Session, code: str, current: CurrentUser) -> CitizenReport:
    polsek = jurisdiction_filter(current, VIEW_PERMISSION)
    query = (
        select(CitizenReport)
        .outerjoin(Location, Location.location_id == CitizenReport.location_id)
        .where(CitizenReport.code == code)
    )
    if polsek is not None:
        query = query.where(Location.polsek == polsek)

    report = session.scalar(query)
    if report is None:
        raise ApiError(status.HTTP_404_NOT_FOUND, "Laporan tidak ditemukan.")
    return report


@router.get(
    "/citizen-reports/{code}/attachments",
    summary="Daftar lampiran satu laporan masyarakat",
)
def list_attachments(
    code: str,
    session: Session = Depends(get_db),
    current: CurrentUser = require_permission(VIEW_PERMISSION),
) -> dict[str, Any]:
    """Keterangan lampiran — bukan isinya.

    Lampiran yang berkasnya sudah dihapus karena masa retensi tetap disebutkan, lengkap
    dengan kapan ia dimusnahkan. Menghilangkannya dari daftar akan membuat pemeriksa
    mengira laporan itu memang tidak pernah berlampiran.
    """
    report = _report_in_scope(session, code, current)
    rows = session.scalars(
        select(CitizenReportAttachment)
        .where(CitizenReportAttachment.report_id == report.report_id)
        .order_by(CitizenReportAttachment.created_at)
    ).all()

    return {
        "code": report.code,
        "coordinate_source": report.coordinate_source,
        "gps_accuracy_m": float(report.gps_accuracy_m) if report.gps_accuracy_m else None,
        "data": [
            {
                "attachment_id": str(row.attachment_id),
                "kind": row.kind,
                "media_type": row.media_type,
                "byte_size": row.byte_size,
                "sha256": row.sha256,
                "metadata_stripped_with": row.metadata_stripped_with,
                "created_at": row.created_at,
                "purged_at": row.purged_at,
                "available": row.is_available,
            }
            for row in rows
        ],
        "retention_basis": (
            f"Berkas dihapus {attachment_store.RETENTION_DAYS_AFTER_CLOSED} hari setelah "
            "laporan selesai. Baris lampirannya tetap ada sebagai jejak bahwa penghapusan "
            "itu dijalankan."
        ),
    }


@router.get(
    "/citizen-reports/{code}/attachments/{attachment_id}",
    summary="Mengambil berkas satu lampiran",
    response_class=FileResponse,
)
def download_attachment(
    code: str,
    attachment_id: str,
    session: Session = Depends(get_db),
    current: CurrentUser = require_permission(VIEW_PERMISSION),
) -> FileResponse:
    """Mengirim berkas lampiran. Setiap pengambilan meninggalkan jejak."""
    report = _report_in_scope(session, code, current)
    attachment = session.scalar(
        select(CitizenReportAttachment).where(
            CitizenReportAttachment.report_id == report.report_id,
            CitizenReportAttachment.attachment_id == attachment_id,
        )
    )
    if attachment is None:
        raise ApiError(status.HTTP_404_NOT_FOUND, "Lampiran tidak ditemukan.")

    if not attachment.is_available:
        raise ApiError(
            status.HTTP_410_GONE,
            "Berkas lampiran sudah dihapus sesuai masa retensi.",
        )

    path = attachment_store.path_of(attachment)
    if not path.exists():
        # Baris ada, berkasnya tidak. Ini keadaan yang tidak seharusnya terjadi, dan
        # menyamarkannya sebagai 404 akan menyembunyikan kerusakan penyimpanan.
        audit.record(
            session,
            action="READ_CITIZEN_REPORT_ATTACHMENT",
            resource_type="citizen_report_attachment",
            result=audit.RESULT_FAILED,
            user_id=current.user.user_id,
            resource_id=str(attachment.attachment_id),
            detail={"reason": "berkas tidak ada di penyimpanan", "code": report.code},
        )
        session.commit()
        raise ApiError(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Berkas lampiran tidak ditemukan di penyimpanan.",
        )

    audit.record(
        session,
        action="READ_CITIZEN_REPORT_ATTACHMENT",
        resource_type="citizen_report_attachment",
        result=audit.RESULT_SUCCESS,
        user_id=current.user.user_id,
        resource_id=str(attachment.attachment_id),
        detail={"code": report.code, "kind": attachment.kind},
    )
    session.commit()

    return FileResponse(
        path,
        media_type=attachment.media_type,
        # `inline` supaya foto dan video dapat dilihat langsung di layar triase tanpa
        # diunduh ke cakram petugas — makin sedikit salinan data pribadi, makin baik.
        headers={"Content-Disposition": f'inline; filename="{attachment.storage_key}"'},
    )
