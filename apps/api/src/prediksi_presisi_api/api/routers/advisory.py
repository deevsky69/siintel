"""Imbauan bulanan untuk grup WhatsApp warga — endpoint bot (kunci bersama MESSAGING_API_KEY).

```text
POST /messaging/groups                     daftarkan grup (chat id) ke satu kelurahan   kunci bot
GET  /messaging/groups?channel=&chat_id=   kelurahan yang terdaftar untuk grup itu
GET  /messaging/advisory?kelurahan=&month= teks imbauan satu kelurahan (untuk /rekomendasi)
GET  /messaging/advisories/pending         grup terdaftar yang belum menerima imbauan bulan ini
POST /messaging/advisories/sent            hasil pengiriman; menandai bulan terkirim
```

Keputusan pemilik proyek 4 November 2026: grup berisi perwakilan RT/RW dan Babin; pengiriman
awal bulan. DIREVISI 6 November 2026 (3A, dokumen mekanisme): imbauan bulan tertentu hanya
terkirim — dan hanya dapat diminta lewat /rekomendasi — setelah **disetujui Pimpinan**
(`advisory_approvals`, `POST /advisories/approvals`, `bulletin:approve`).
Isinya imbauan warga (`services/citizen_advisory.py`), bukan rekomendasi operasional.
"""

from __future__ import annotations

import re
from typing import Any

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ...models import AdvisoryApproval, Babinkamtibmas, Location
from ...services import audit, citizen_advisory, clock
from ..deps import CurrentUser, get_db, require_permission
from ..errors import ApiError
from .messaging import require_messaging_key

router = APIRouter(tags=["imbauan-warga"])

MONTH_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


def _parse_month(value: str | None, *, default: tuple[int, int]) -> tuple[int, int]:
    if not value:
        return default
    if not MONTH_RE.match(value):
        raise ApiError(status.HTTP_400_BAD_REQUEST, "Bulan harus berbentuk YYYY-MM.")
    return int(value[:4]), int(value[5:7])


def _kelurahan_row(session: Session, kelurahan: str) -> tuple[str, str, str] | None:
    area = session.execute(
        select(Location.kelurahan, Location.kecamatan, Location.polsek)
        .where(func.lower(Location.kelurahan) == kelurahan.strip().lower())
        .limit(1)
    ).first()
    return None if area is None else (str(area[0]), str(area[1]), str(area[2]))


def _digits(value: str | None) -> str:
    return "".join(ch for ch in (value or "") if ch.isdigit())


def _sender_is_babin(row: Babinkamtibmas, sender: str | None) -> bool:
    """`sender` berbentuk `628…@c.us`; cocok bila digitnya sama dengan nomor Babin tercatat."""
    number = _digits(row.whatsapp_number)
    return bool(number) and _digits(sender.split("@", 1)[0] if sender else None) == number


class GroupRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    channel: str = Field(description="WHATSAPP")
    chat_id: str = Field(min_length=3, max_length=64, description="mis. 1203…@g.us")
    kelurahan: str = Field(min_length=2, max_length=100)
    #: Pengirim perintah di grup (participant), untuk mencocokkan dengan nomor Babin.
    sender: str | None = Field(default=None, max_length=64)


@router.post(
    "/messaging/groups",
    summary="Mendaftarkan grup warga ke satu kelurahan",
    dependencies=[Depends(require_messaging_key)],
)
def register_group(payload: GroupRequest, session: Session = Depends(get_db)) -> dict[str, Any]:
    if payload.channel.upper() != "WHATSAPP":
        raise ApiError(status.HTTP_400_BAD_REQUEST, "Pendaftaran grup hanya untuk WHATSAPP.")
    if not payload.chat_id.endswith("@g.us"):
        raise ApiError(status.HTTP_400_BAD_REQUEST, "Perintah ini hanya berlaku di dalam grup.")
    area = _kelurahan_row(session, payload.kelurahan)
    if area is None:
        raise ApiError(status.HTTP_404_NOT_FOUND, "Kelurahan tidak dikenal pada master lokasi.")
    row = session.scalar(select(Babinkamtibmas).where(Babinkamtibmas.kelurahan == area[0]))
    if row is None:
        raise ApiError(
            status.HTTP_404_NOT_FOUND,
            f"Kelurahan {area[0]} belum punya kontak Babinkamtibmas. Minta Administrator "
            "mengisinya di menu Laporan → Babinkamtibmas, lalu ulangi /daftar.",
        )
    # Kelurahan yang sudah punya grup tidak dapat dibajak dari grup lain (tinjauan keamanan
    # 4 November 2026): hanya Babin kelurahan itu (nomor WhatsApp tercatat) yang boleh
    # memindahkannya lewat /daftar; selain itu perubahan lewat Administrator di /ops/babin.
    current = row.whatsapp_group_chat_id
    if current and current != payload.chat_id and not _sender_is_babin(row, payload.sender):
        raise ApiError(
            status.HTTP_409_CONFLICT,
            f"Kelurahan {row.kelurahan} sudah terdaftar pada grup lain. Perubahan hanya oleh "
            "Babinkamtibmas kelurahan itu, atau Administrator di menu Laporan → Babinkamtibmas.",
        )
    # Satu grup hanya untuk satu kelurahan: pendaftaran di kelurahan lain dilepas.
    for other in session.scalars(
        select(Babinkamtibmas).where(
            Babinkamtibmas.whatsapp_group_chat_id == payload.chat_id,
            Babinkamtibmas.kelurahan != row.kelurahan,
        )
    ).all():
        other.whatsapp_group_chat_id = None
    previous = row.whatsapp_group_chat_id
    row.whatsapp_group_chat_id = payload.chat_id
    audit.record(
        session,
        action="REGISTER_CITIZEN_GROUP",
        resource_type="babinkamtibmas",
        result=audit.RESULT_SUCCESS,
        user_id=None,
        resource_id=row.kelurahan,
        detail={"channel": "WHATSAPP", "replaced": previous is not None},
    )
    session.commit()
    return {"kelurahan": row.kelurahan, "kecamatan": row.kecamatan, "polsek": row.polsek}


@router.get(
    "/messaging/groups",
    summary="Kelurahan yang terdaftar untuk satu grup",
    dependencies=[Depends(require_messaging_key)],
)
def group_of(
    channel: str = Query(),
    chat_id: str = Query(min_length=3, max_length=64),
    session: Session = Depends(get_db),
) -> dict[str, Any]:
    if channel.upper() != "WHATSAPP":
        raise ApiError(status.HTTP_400_BAD_REQUEST, "Grup hanya untuk WHATSAPP.")
    row = session.scalar(
        select(Babinkamtibmas).where(Babinkamtibmas.whatsapp_group_chat_id == chat_id)
    )
    if row is None:
        raise ApiError(status.HTTP_404_NOT_FOUND, "Grup ini belum didaftarkan.")
    return {"kelurahan": row.kelurahan, "kecamatan": row.kecamatan, "polsek": row.polsek}


@router.get(
    "/messaging/advisory",
    summary="Teks imbauan satu kelurahan untuk satu bulan",
    dependencies=[Depends(require_messaging_key)],
)
def advisory_text(
    kelurahan: str = Query(min_length=2, max_length=100),
    month: str | None = Query(default=None, description="YYYY-MM; bawaan bulan depan"),
    session: Session = Depends(get_db),
) -> dict[str, Any]:
    area = _kelurahan_row(session, kelurahan)
    if area is None:
        raise ApiError(status.HTTP_404_NOT_FOUND, "Kelurahan tidak dikenal pada master lokasi.")
    today = clock.citizen_now().astimezone(clock.JAKARTA).date()
    year, month_number = _parse_month(month, default=citizen_advisory.month_after(today))
    _require_approved(session, f"{year:04d}-{month_number:02d}")
    advisory = citizen_advisory.build_advisory(session, year, month_number, area[0])
    return {**advisory, "text": citizen_advisory.render_text(advisory)}


@router.get(
    "/messaging/advisories/pending",
    summary="Grup yang belum menerima imbauan bulan berjalan",
    dependencies=[Depends(require_messaging_key)],
)
def pending_advisories(session: Session = Depends(get_db)) -> dict[str, Any]:
    year, month_number = citizen_advisory.current_month()
    key = f"{year:04d}-{month_number:02d}"
    if _approval(session, key) is None:
        # Belum disetujui Pimpinan: tidak ada yang dikirim bulan ini (3A).
        return {"month": key, "approved": False, "data": []}
    rows = session.scalars(
        select(Babinkamtibmas)
        .where(
            Babinkamtibmas.whatsapp_group_chat_id.is_not(None),
            (Babinkamtibmas.advisory_sent_month.is_(None))
            | (Babinkamtibmas.advisory_sent_month != key),
        )
        .order_by(Babinkamtibmas.kecamatan, Babinkamtibmas.kelurahan)
        .limit(200)
    ).all()
    data = []
    for row in rows:
        advisory = citizen_advisory.build_advisory(session, year, month_number, row.kelurahan)
        data.append(
            {
                "kelurahan": row.kelurahan,
                "chat_id": row.whatsapp_group_chat_id,
                "month": key,
                "text": citizen_advisory.render_text(advisory),
            }
        )
    return {"month": key, "approved": True, "data": data}


class SentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kelurahan: str = Field(max_length=100)
    month: str = Field(pattern=r"^\d{4}-\d{2}$")
    delivery: dict[str, str] = Field(description='mis. {"whatsapp": "ok"}')


@router.post(
    "/messaging/advisories/sent",
    summary="Imbauan bulanan sudah dikirim ke grup",
    dependencies=[Depends(require_messaging_key)],
)
def advisory_sent(payload: SentRequest, session: Session = Depends(get_db)) -> dict[str, Any]:
    row = session.scalar(
        select(Babinkamtibmas).where(Babinkamtibmas.kelurahan == payload.kelurahan.strip())
    )
    if row is None:
        raise ApiError(status.HTTP_404_NOT_FOUND, "Kelurahan tidak punya kontak Babinkamtibmas.")
    ok = any(value == "ok" for value in payload.delivery.values())
    if ok:
        row.advisory_sent_month = payload.month
    audit.record(
        session,
        action="SEND_CITIZEN_ADVISORY",
        resource_type="babinkamtibmas",
        result=audit.RESULT_SUCCESS if ok else audit.RESULT_FAILED,
        user_id=None,
        resource_id=row.kelurahan,
        detail={"month": payload.month, "delivery": payload.delivery},
    )
    session.commit()
    return {"kelurahan": row.kelurahan, "advisory_sent_month": row.advisory_sent_month}


# ---------------------------------------------------------------------------------------
# Persetujuan Pimpinan (keputusan 3A, 6 November 2026) — endpoint berkunci sesi, bukan bot.
# ---------------------------------------------------------------------------------------


def _approval(session: Session, month: str) -> AdvisoryApproval | None:
    return session.scalar(select(AdvisoryApproval).where(AdvisoryApproval.month == month))


def _require_approved(session: Session, month: str) -> None:
    if _approval(session, month) is None:
        raise ApiError(
            status.HTTP_409_CONFLICT,
            f"Imbauan bulan {month} belum disetujui Pimpinan; belum dapat dibagikan.",
        )


class ApprovalRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    month: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    note: str | None = Field(default=None, max_length=500)


@router.get("/advisories/approvals", summary="Status persetujuan imbauan bulanan + contoh teks")
def approval_status(
    session: Session = Depends(get_db),
    _: CurrentUser = require_permission("bulletin:read"),
    month: str | None = Query(default=None, description="YYYY-MM; bawaan bulan berjalan"),
) -> dict[str, Any]:
    year, month_number = _parse_month(month, default=citizen_advisory.current_month())
    key = f"{year:04d}-{month_number:02d}"
    row = _approval(session, key)
    groups = int(
        session.scalar(
            select(func.count())
            .select_from(Babinkamtibmas)
            .where(Babinkamtibmas.whatsapp_group_chat_id.is_not(None))
        )
        or 0
    )
    sample_area = session.scalar(
        select(Babinkamtibmas.kelurahan)
        .where(Babinkamtibmas.whatsapp_group_chat_id.is_not(None))
        .order_by(Babinkamtibmas.kelurahan)
    ) or session.scalar(
        select(Location.kelurahan)
        .where(Location.kelurahan.is_not(None))
        .order_by(Location.kelurahan)
    )
    sample = None
    if sample_area:
        advisory = citizen_advisory.build_advisory(session, year, month_number, str(sample_area))
        sample = {"kelurahan": sample_area, "text": citizen_advisory.render_text(advisory)}
    return {
        "month": key,
        "approved": row is not None,
        "approved_at": row.approved_at if row else None,
        "note": row.note if row else None,
        "groups_registered": groups,
        "sample": sample,
    }


@router.post(
    "/advisories/approvals",
    status_code=status.HTTP_201_CREATED,
    summary="Menyetujui imbauan bulanan untuk dibagikan ke grup warga",
)
def approve_advisory(
    payload: ApprovalRequest,
    session: Session = Depends(get_db),
    current: CurrentUser = require_permission("bulletin:approve"),
) -> dict[str, Any]:
    if _approval(session, payload.month) is not None:
        raise ApiError(status.HTTP_409_CONFLICT, f"Imbauan {payload.month} sudah disetujui.")
    row = AdvisoryApproval(
        month=payload.month,
        approved_by=current.user.user_id,
        note=(payload.note or "").strip() or None,
    )
    session.add(row)
    audit.record(
        session,
        action="APPROVE_CITIZEN_ADVISORY",
        resource_type="advisory",
        result=audit.RESULT_SUCCESS,
        user_id=current.user.user_id,
        resource_id=payload.month,
        detail={"note": row.note},
    )
    session.commit()
    session.refresh(row)
    return {"month": row.month, "approved": True, "approved_at": row.approved_at, "note": row.note}
