"""Imbauan bulanan untuk grup WhatsApp warga — endpoint bot (kunci bersama MESSAGING_API_KEY).

```text
POST /messaging/groups                     daftarkan grup (chat id) ke satu kelurahan   kunci bot
GET  /messaging/groups?channel=&chat_id=   kelurahan yang terdaftar untuk grup itu
GET  /messaging/advisory?kelurahan=&month= teks imbauan satu kelurahan (untuk /info)
GET  /messaging/advisories/pending         grup terdaftar yang belum menerima imbauan bulan ini
POST /messaging/advisories/sent            hasil pengiriman; menandai bulan terkirim
GET  /advisories/preview?month=            (sesi, bulletin:read) contoh teks + jumlah grup

POST   /messaging/subscriptions            warga berlangganan imbauan satu kelurahan
GET    /messaging/subscriptions?channel=&chat_id=   langganan percakapan itu
DELETE /messaging/subscriptions?channel=&chat_id=   berhenti; barisnya DIHAPUS
GET    /messaging/subscriptions/pending    pelanggan yang belum menerima imbauan bulan ini
POST   /messaging/subscriptions/sent       hasil pengiriman ke satu pelanggan
```

17 November 2026 (naskah Taskap 4.7 b): selain grup, WARGA dapat berlangganan sendiri dari
percakapan pribadinya (`/langganan <kelurahan>`, berhenti dengan `/berhenti`). Yang disimpan
hanya kanal, pengenal percakapan, dan kelurahan (`models/area_subscription.py`).

Keputusan pemilik proyek 4 November 2026: grup berisi perwakilan RT/RW dan Babin; pengiriman
awal bulan, otomatis. 6 November 2026 (3A) sempat menuntut persetujuan Pimpinan per bulan;
**10 November 2026 pemilik proyek mencabutnya**: imbauan kembali otomatis tanpa persetujuan,
dan perintah botnya `/info`. Tabel `advisory_approvals` (0022) dibiarkan — tidak dibaca lagi.
Isinya imbauan warga (`services/citizen_advisory.py`), bukan rekomendasi operasional.
"""

from __future__ import annotations

import re
import uuid
from typing import Any

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ...models import AreaSubscription, Babinkamtibmas, Location
from ...models.area_subscription import CHANNELS
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
    return {"month": key, "data": data}


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
# Langganan warga (percakapan pribadi) — naskah Taskap 4.7 b "Pemberitahuan wilayah".
# ---------------------------------------------------------------------------------------


class SubscriptionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    channel: str = Field(description="WHATSAPP atau TELEGRAM")
    chat_id: str = Field(min_length=3, max_length=64)
    kelurahan: str = Field(min_length=2, max_length=100)


def _channel(value: str) -> str:
    channel = value.upper()
    if channel not in CHANNELS:
        raise ApiError(status.HTTP_400_BAD_REQUEST, "Kanal harus WHATSAPP atau TELEGRAM.")
    return channel


def _subscription(session: Session, channel: str, chat_id: str) -> AreaSubscription | None:
    return session.scalar(
        select(AreaSubscription).where(
            AreaSubscription.channel == channel, AreaSubscription.chat_id == chat_id
        )
    )


def _subscription_row(row: AreaSubscription, area: tuple[str, str, str] | None) -> dict[str, Any]:
    return {
        "kelurahan": row.kelurahan,
        "kecamatan": area[1] if area else None,
        "polsek": area[2] if area else None,
        "subscribed_at": row.subscribed_at,
    }


@router.post(
    "/messaging/subscriptions",
    summary="Warga berlangganan imbauan satu kelurahan",
    dependencies=[Depends(require_messaging_key)],
)
def subscribe(payload: SubscriptionRequest, session: Session = Depends(get_db)) -> dict[str, Any]:
    channel = _channel(payload.channel)
    if payload.chat_id.endswith("@g.us"):
        raise ApiError(
            status.HTTP_400_BAD_REQUEST,
            "Langganan ini untuk percakapan pribadi. Di grup, pakai /daftar <kelurahan>.",
        )
    area = _kelurahan_row(session, payload.kelurahan)
    if area is None:
        raise ApiError(status.HTTP_404_NOT_FOUND, "Kelurahan tidak dikenal pada master lokasi.")
    row = _subscription(session, channel, payload.chat_id)
    changed = row is not None and row.kelurahan != area[0]
    if row is None:
        row = AreaSubscription(
            channel=channel,
            chat_id=payload.chat_id,
            kelurahan=area[0],
            subscribed_at=clock.citizen_now(),
        )
        session.add(row)
    elif changed:
        # Pindah kelurahan: imbauan kelurahan baru bulan ini belum pernah diterima.
        row.kelurahan = area[0]
        row.subscribed_at = clock.citizen_now()
        row.advisory_sent_month = None
    # Jejak tanpa pengenal percakapan: yang perlu diketahui adalah berapa dan di mana.
    audit.record(
        session,
        action="SUBSCRIBE_AREA_ADVISORY",
        resource_type="area_subscription",
        result=audit.RESULT_SUCCESS,
        user_id=None,
        resource_id=area[0],
        detail={"channel": channel, "moved": changed},
    )
    session.commit()
    return _subscription_row(row, area)


@router.get(
    "/messaging/subscriptions",
    summary="Langganan satu percakapan",
    dependencies=[Depends(require_messaging_key)],
)
def subscription_of(
    channel: str = Query(),
    chat_id: str = Query(min_length=3, max_length=64),
    session: Session = Depends(get_db),
) -> dict[str, Any]:
    row = _subscription(session, _channel(channel), chat_id)
    if row is None:
        raise ApiError(status.HTTP_404_NOT_FOUND, "Percakapan ini belum berlangganan.")
    return _subscription_row(row, _kelurahan_row(session, row.kelurahan))


@router.delete(
    "/messaging/subscriptions",
    summary="Berhenti berlangganan; barisnya dihapus",
    dependencies=[Depends(require_messaging_key)],
)
def unsubscribe(
    channel: str = Query(),
    chat_id: str = Query(min_length=3, max_length=64),
    session: Session = Depends(get_db),
) -> dict[str, Any]:
    channel = _channel(channel)
    row = _subscription(session, channel, chat_id)
    if row is None:
        raise ApiError(status.HTTP_404_NOT_FOUND, "Percakapan ini belum berlangganan.")
    kelurahan = row.kelurahan
    session.delete(row)
    audit.record(
        session,
        action="UNSUBSCRIBE_AREA_ADVISORY",
        resource_type="area_subscription",
        result=audit.RESULT_SUCCESS,
        user_id=None,
        resource_id=kelurahan,
        detail={"channel": channel},
    )
    session.commit()
    return {"kelurahan": kelurahan, "unsubscribed": True}


@router.get(
    "/messaging/subscriptions/pending",
    summary="Pelanggan yang belum menerima imbauan bulan berjalan",
    dependencies=[Depends(require_messaging_key)],
)
def pending_subscriptions(session: Session = Depends(get_db)) -> dict[str, Any]:
    year, month_number = citizen_advisory.current_month()
    key = f"{year:04d}-{month_number:02d}"
    rows = session.scalars(
        select(AreaSubscription)
        .where(
            (AreaSubscription.advisory_sent_month.is_(None))
            | (AreaSubscription.advisory_sent_month != key)
        )
        .order_by(AreaSubscription.kelurahan, AreaSubscription.subscribed_at)
        .limit(200)
    ).all()
    texts: dict[str, str] = {}
    data = []
    for row in rows:
        if row.kelurahan not in texts:
            advisory = citizen_advisory.build_advisory(session, year, month_number, row.kelurahan)
            texts[row.kelurahan] = citizen_advisory.render_text(advisory)
        data.append(
            {
                "subscription_id": str(row.subscription_id),
                "channel": row.channel,
                "chat_id": row.chat_id,
                "kelurahan": row.kelurahan,
                "month": key,
                "text": texts[row.kelurahan],
            }
        )
    return {"month": key, "data": data}


class SubscriptionSentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subscription_id: uuid.UUID
    month: str = Field(pattern=r"^\d{4}-\d{2}$")
    delivery: dict[str, str] = Field(description='mis. {"whatsapp": "ok"}')


@router.post(
    "/messaging/subscriptions/sent",
    summary="Imbauan bulanan sudah dikirim ke satu pelanggan",
    dependencies=[Depends(require_messaging_key)],
)
def subscription_sent(
    payload: SubscriptionSentRequest, session: Session = Depends(get_db)
) -> dict[str, Any]:
    row = session.get(AreaSubscription, payload.subscription_id)
    if row is None:
        # Pelanggan berhenti di antara pengambilan dan pengiriman: tidak ada yang ditandai.
        raise ApiError(status.HTTP_404_NOT_FOUND, "Langganan tidak ditemukan.")
    ok = any(value == "ok" for value in payload.delivery.values())
    # Ditandai juga saat gagal: kegagalan dicatat dan TIDAK diulang-ulang tiap dua menit
    # (nomor yang memblokir bot akan gagal selamanya); bulan berikutnya dicoba lagi.
    row.advisory_sent_month = payload.month
    audit.record(
        session,
        action="SEND_SUBSCRIBER_ADVISORY",
        resource_type="area_subscription",
        result=audit.RESULT_SUCCESS if ok else audit.RESULT_FAILED,
        user_id=None,
        resource_id=row.kelurahan,
        detail={"month": payload.month, "channel": row.channel, "delivery": payload.delivery},
    )
    session.commit()
    return {"kelurahan": row.kelurahan, "advisory_sent_month": row.advisory_sent_month}


# ---------------------------------------------------------------------------------------
# Pratinjau untuk layar /ops/buletin — berkunci sesi, hanya membaca.
# ---------------------------------------------------------------------------------------


@router.get("/advisories/preview", summary="Contoh teks imbauan bulanan + jumlah grup terdaftar")
def advisory_preview(
    session: Session = Depends(get_db),
    _: CurrentUser = require_permission("bulletin:read"),
    month: str | None = Query(default=None, description="YYYY-MM; bawaan bulan berjalan"),
) -> dict[str, Any]:
    year, month_number = _parse_month(month, default=citizen_advisory.current_month())
    key = f"{year:04d}-{month_number:02d}"
    groups = int(
        session.scalar(
            select(func.count())
            .select_from(Babinkamtibmas)
            .where(Babinkamtibmas.whatsapp_group_chat_id.is_not(None))
        )
        or 0
    )
    sent = int(
        session.scalar(
            select(func.count())
            .select_from(Babinkamtibmas)
            .where(Babinkamtibmas.advisory_sent_month == key)
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
    subscribers = int(session.scalar(select(func.count()).select_from(AreaSubscription)) or 0)
    subscribers_sent = int(
        session.scalar(
            select(func.count())
            .select_from(AreaSubscription)
            .where(AreaSubscription.advisory_sent_month == key)
        )
        or 0
    )
    return {
        "month": key,
        "automatic": True,
        "groups_registered": groups,
        "groups_sent": sent,
        "subscribers": subscribers,
        "subscribers_sent": subscribers_sent,
        "sample": sample,
    }
