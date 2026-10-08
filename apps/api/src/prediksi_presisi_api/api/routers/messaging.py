"""Kanal perpesanan — endpoint untuk layanan bot Telegram / WhatsApp (8 Oktober 2026).

```text
POST /messaging/reports          laporan dari satu percakapan (+ kontak untuk kabar)
POST /messaging/attachments      lampiran dari satu percakapan
GET  /messaging/reports          laporan milik satu percakapan (untuk perintah /status)
GET  /messaging/updates          laporan yang statusnya berubah sejak terakhir dikabarkan
POST /messaging/updates/ack      kabar sudah terkirim ke percakapan itu
```

SIAPA YANG BOLEH MEMANGGIL

    Hanya layanan bot, lewat kunci bersama pada header `X-Messaging-Key`, dibandingkan
    waktu-tetap dengan `MESSAGING_API_KEY`. Bukan endpoint publik: ia menerima dan
    mengembalikan pengenal percakapan (data pribadi pada WhatsApp), sehingga tidak boleh
    terbuka seperti `/public/*`. Kosongnya kunci berarti kanal tidak aktif dan endpoint
    menjawab 503 — bukan menerima semua orang.

MENGAPA BUKAN /public/citizen-reports SAJA

    Bot adalah satu proses di satu alamat jaringan. Pembatas laju kanal publik menghitung
    per alamat, sehingga seluruh pelapor lewat bot akan berbagi satu kuota sepuluh laporan
    per jam. Di sini kuota dihitung per PERCAKAPAN, dengan angka yang sama.

APA YANG DISIMPAN DARI PELAPOR

    Kanal dan pengenal percakapan, pada tabel terpisah `citizen_report_contacts`, untuk satu
    tujuan: mengabari perkembangan laporannya. Lihat `models/citizen_report_contact.py`.
"""

from __future__ import annotations

import secrets
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...config import get_settings
from ...models import CitizenReport, CitizenReportContact
from ...models.citizen_report_contact import CHANNELS
from ...services import attachments as attachment_store
from ...services import audit
from ..deps import get_db
from ..errors import ApiError
from .public_intake import (
    ATTACHMENT_BASIS,
    RATE_LIMIT_PER_HOUR,
    RATE_WINDOW_SECONDS,
    STATUS_LABELS,
    ReportRequest,
    _RateLimiter,
    accept_report,
)

router = APIRouter(prefix="/messaging", tags=["kanal perpesanan"])

KEY_HEADER = "X-Messaging-Key"
MAX_REPORTS_PER_CHAT = 10
MAX_UPDATES = 100

#: Kuota yang sama dengan kanal publik, dihitung per percakapan.
limiter = _RateLimiter(RATE_LIMIT_PER_HOUR, RATE_WINDOW_SECONDS)

CONTACT_BASIS = (
    "Pengenal percakapan disimpan (keputusan pemilik proyek 8 Oktober 2026) hanya untuk "
    "mengabari perkembangan laporan ini ke percakapan yang sama. Ia tidak tampil pada layar "
    "petugas mana pun dan dapat dihapus tanpa menyentuh laporannya."
)


def require_messaging_key(request: Request) -> None:
    configured = get_settings().messaging_api_key
    if not configured:
        raise ApiError(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Kanal perpesanan tidak aktif: MESSAGING_API_KEY belum diisi.",
        )
    supplied = request.headers.get(KEY_HEADER, "")
    if not supplied or not secrets.compare_digest(supplied, configured):
        raise ApiError(status.HTTP_401_UNAUTHORIZED, "Kunci kanal perpesanan tidak sah.")


def _channel(value: str) -> str:
    wanted = value.upper()
    if wanted not in CHANNELS:
        raise ApiError(
            status.HTTP_400_BAD_REQUEST,
            "Kanal tidak dikenal.",
            details=[{"field": "channel", "issue": f"harus salah satu dari {list(CHANNELS)}"}],
        )
    return wanted


def _chat_key(channel: str, chat_id: str) -> str:
    return f"{channel}:{chat_id}"


class MessagingReportRequest(ReportRequest):
    """Isi laporan ditambah percakapan asalnya."""

    model_config = ConfigDict(extra="forbid")

    channel: str = Field(description="TELEGRAM atau WHATSAPP")
    chat_id: str = Field(min_length=1, max_length=64, description="Pengenal percakapan")


@router.post(
    "/reports",
    status_code=status.HTTP_201_CREATED,
    summary="Laporan masyarakat dari satu percakapan bot",
    dependencies=[Depends(require_messaging_key)],
)
def submit_from_chat(
    payload: MessagingReportRequest, session: Session = Depends(get_db)
) -> dict[str, Any]:
    channel = _channel(payload.channel)
    if not limiter.allow(_chat_key(channel, payload.chat_id)):
        raise ApiError(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Terlalu banyak laporan dari percakapan ini dalam satu jam terakhir. "
            "Untuk keadaan mendesak, hubungi 110.",
        )
    body = ReportRequest(**payload.model_dump(exclude={"channel", "chat_id"}))
    report, response = accept_report(session, body, channel=channel)
    # Tiketnya disampaikan bot saat itu juga, jadi status awal sudah "dikabarkan".
    session.add(
        CitizenReportContact(
            report_id=report.report_id,
            channel=channel,
            chat_id=payload.chat_id,
            last_notified_status=report.status,
        )
    )
    session.commit()
    # Token klaim tidak diberikan ke bot: percakapan itulah bukti kepemilikannya, dan bot
    # tidak perlu menyimpan rahasia kedua yang hanya akan bocor bersamanya.
    response.pop("claim_token", None)
    response["contact_basis"] = CONTACT_BASIS
    return response


@router.post(
    "/attachments",
    status_code=status.HTTP_201_CREATED,
    summary="Lampiran dari satu percakapan bot",
    dependencies=[Depends(require_messaging_key)],
)
def upload_from_chat(
    channel: Annotated[str, Form()],
    chat_id: Annotated[str, Form(min_length=1, max_length=64)],
    berkas: UploadFile = File(description="Foto, rekaman suara, atau video."),
) -> dict[str, Any]:
    kind = _channel(channel)
    if not limiter.allow(_chat_key(kind, chat_id)):
        raise ApiError(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Terlalu banyak berkas dari percakapan ini dalam satu jam terakhir.",
        )
    try:
        handle, stored = attachment_store.stage(berkas.file)
    except attachment_store.AttachmentError as error:
        raise ApiError(status.HTTP_400_BAD_REQUEST, str(error)) from error
    return {
        "handle": handle,
        "kind": stored.kind,
        "media_type": stored.media_type,
        "byte_size": stored.byte_size,
        "basis": ATTACHMENT_BASIS,
    }


def _status_row(report: CitizenReport) -> dict[str, Any]:
    return {
        "ticket": report.code,
        "status": report.status,
        "status_label": STATUS_LABELS.get(report.status, report.status),
        "reported_at": report.reported_at,
        "category": report.category,
        "attachments": len(report.attachments),
    }


@router.get(
    "/reports",
    summary="Laporan milik satu percakapan",
    dependencies=[Depends(require_messaging_key)],
)
def reports_of_chat(
    channel: str = Query(),
    chat_id: str = Query(min_length=1, max_length=64),
    session: Session = Depends(get_db),
) -> dict[str, Any]:
    """Untuk perintah /status: hanya laporan yang dikirim dari percakapan ini sendiri.
    Isinya sama dengan yang diberikan `GET /public/citizen-reports/{code}` kepada pemegang
    token klaim — tanpa penilaian internal petugas."""
    kind = _channel(channel)
    rows = session.scalars(
        select(CitizenReport)
        .join(CitizenReportContact, CitizenReportContact.report_id == CitizenReport.report_id)
        .where(CitizenReportContact.channel == kind, CitizenReportContact.chat_id == chat_id)
        .order_by(CitizenReport.reported_at.desc())
        .limit(MAX_REPORTS_PER_CHAT)
    ).all()
    return {"data": [_status_row(row) for row in rows]}


@router.get(
    "/updates",
    summary="Laporan yang statusnya berubah sejak terakhir dikabarkan",
    dependencies=[Depends(require_messaging_key)],
)
def pending_updates(channel: str = Query(), session: Session = Depends(get_db)) -> dict[str, Any]:
    kind = _channel(channel)
    rows = session.execute(
        select(CitizenReport, CitizenReportContact)
        .join(CitizenReportContact, CitizenReportContact.report_id == CitizenReport.report_id)
        .where(
            CitizenReportContact.channel == kind,
            CitizenReportContact.last_notified_status != CitizenReport.status,
        )
        .order_by(CitizenReport.updated_at)
        .limit(MAX_UPDATES)
    ).all()
    return {
        "data": [{**_status_row(report), "chat_id": contact.chat_id} for report, contact in rows]
    }


class AckRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ticket: str = Field(max_length=50)
    status: str = Field(max_length=50, description="Status yang baru saja dikabarkan")
    channel: str = Field(description="TELEGRAM atau WHATSAPP")


@router.post(
    "/updates/ack",
    summary="Kabar perkembangan sudah terkirim",
    dependencies=[Depends(require_messaging_key)],
)
def acknowledge_update(payload: AckRequest, session: Session = Depends(get_db)) -> dict[str, Any]:
    kind = _channel(payload.channel)
    row = session.execute(
        select(CitizenReport, CitizenReportContact)
        .join(CitizenReportContact, CitizenReportContact.report_id == CitizenReport.report_id)
        .where(CitizenReport.code == payload.ticket, CitizenReportContact.channel == kind)
    ).first()
    if row is None:
        raise ApiError(status.HTTP_404_NOT_FOUND, "Laporan tidak ditemukan pada kanal itu.")
    report, contact = row
    contact.last_notified_status = payload.status.upper()
    # Kabar kepada pelapor adalah tindakan atas data pribadi; jejaknya dicatat tanpa isi
    # pengenal percakapan.
    audit.record(
        session,
        action="NOTIFY_CITIZEN_REPORTER",
        resource_type="citizen_report",
        result=audit.RESULT_SUCCESS,
        user_id=None,
        resource_id=report.code,
        detail={"channel": kind, "status": contact.last_notified_status},
    )
    session.commit()
    return {"ticket": report.code, "last_notified_status": contact.last_notified_status}
