"""Kontak Babinkamtibmas (tahap 3, 2 November 2026).

```text
GET  /public/babin?kelurahan=       warga: nama, pangkat, nomor dinas, tautan grup   —
GET  /babin                          daftar lengkap                                  babin:read
PUT  /babin/{kelurahan}              buat/ubah kontak kelurahan                      babin:manage
```
Nomor yang ditampilkan adalah nomor DINAS (keputusan pemilik proyek). Baris dummy berlabel.
Nomor WhatsApp Babin dan chat id grup Telegram tidak pernah keluar ke kanal publik: keduanya
tujuan pengiriman buletin, bukan informasi untuk warga.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Path, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ...models import Babinkamtibmas, Location
from ...services import audit
from ..deps import CurrentUser, get_db, require_permission
from ..errors import ApiError

router = APIRouter(tags=["babinkamtibmas"])

PUBLIC_BASIS = (
    "Kontak Babinkamtibmas kelurahan: nomor dinas yang ditetapkan satuan. Baris berlabel DUMMY "
    "adalah data peragaan. Untuk keadaan darurat hubungi 110."
)


def _public(row: Babinkamtibmas) -> dict[str, Any]:
    return {
        "kelurahan": row.kelurahan,
        "kecamatan": row.kecamatan,
        "polsek": row.polsek,
        "rank": row.rank,
        "name": row.name,
        "phone_display": row.phone_display,
        "whatsapp_group_link": row.whatsapp_group_link,
        "is_dummy": row.is_dummy,
    }


def _full(row: Babinkamtibmas) -> dict[str, Any]:
    return {
        **_public(row),
        "telegram_chat_id": row.telegram_chat_id,
        "whatsapp_number": row.whatsapp_number,
        "updated_at": row.updated_at,
    }


@router.get("/public/babin", summary="Kontak Babinkamtibmas satu kelurahan (publik)")
def public_babin(
    kelurahan: str = Query(max_length=100), session: Session = Depends(get_db)
) -> dict[str, Any]:
    row = session.scalar(
        select(Babinkamtibmas).where(
            func.lower(Babinkamtibmas.kelurahan) == kelurahan.strip().lower()
        )
    )
    return {"data": _public(row) if row else None, "basis": PUBLIC_BASIS}


@router.get("/babin", summary="Daftar kontak Babinkamtibmas")
def list_babin(
    session: Session = Depends(get_db),
    current: CurrentUser = require_permission("babin:read"),
) -> dict[str, Any]:
    rows = session.scalars(
        select(Babinkamtibmas).order_by(Babinkamtibmas.kecamatan, Babinkamtibmas.kelurahan)
    ).all()
    return {"data": [_full(row) for row in rows], "total": len(rows)}


class BabinRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=2, max_length=120)
    rank: str | None = Field(default=None, max_length=40)
    phone_display: str = Field(
        min_length=6, max_length=32, description="Nomor dinas, bentuk tampil"
    )
    telegram_chat_id: str | None = Field(default=None, max_length=32)
    whatsapp_group_link: str | None = Field(default=None, max_length=200)
    whatsapp_number: str | None = Field(
        default=None, max_length=20, description="Internasional tanpa +"
    )
    is_dummy: bool = False


@router.put("/babin/{kelurahan}", summary="Membuat atau mengubah kontak Babin satu kelurahan")
def upsert_babin(
    payload: BabinRequest,
    kelurahan: str = Path(max_length=100),
    session: Session = Depends(get_db),
    current: CurrentUser = require_permission("babin:manage"),
) -> dict[str, Any]:
    area = session.execute(
        select(Location.kelurahan, Location.kecamatan, Location.polsek)
        .where(func.lower(Location.kelurahan) == kelurahan.strip().lower())
        .limit(1)
    ).first()
    if area is None:
        raise ApiError(status.HTTP_400_BAD_REQUEST, "Kelurahan tidak dikenal pada master lokasi.")
    row = session.scalar(select(Babinkamtibmas).where(Babinkamtibmas.kelurahan == str(area[0])))
    created = row is None
    if row is None:
        row = Babinkamtibmas(
            kelurahan=str(area[0]),
            kecamatan=str(area[1]),
            polsek=str(area[2]),
            name="",
            phone_display="",
        )
        session.add(row)
    row.name = payload.name.strip()
    row.rank = (payload.rank or "").strip() or None
    row.phone_display = payload.phone_display.strip()
    row.telegram_chat_id = (payload.telegram_chat_id or "").strip() or None
    row.whatsapp_group_link = (payload.whatsapp_group_link or "").strip() or None
    row.whatsapp_number = (
        "".join(ch for ch in (payload.whatsapp_number or "") if ch.isdigit()) or None
    )
    row.is_dummy = payload.is_dummy
    session.flush()
    audit.record(
        session,
        action="CREATE_BABIN" if created else "UPDATE_BABIN",
        resource_type="babinkamtibmas",
        result=audit.RESULT_SUCCESS,
        user_id=current.user.user_id,
        resource_id=row.kelurahan,
        detail={"is_dummy": row.is_dummy, "has_telegram_group": row.telegram_chat_id is not None},
    )
    session.commit()
    session.refresh(row)
    return _full(row)
