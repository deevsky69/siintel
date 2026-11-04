"""Kontak Babinkamtibmas (tahap 3, 2 November 2026).

```text
GET  /public/babin?kelurahan=       warga: nama, pangkat, nomor dinas, tautan grup   —
GET  /babin                          daftar lengkap                                  babin:read
PUT  /babin/{kelurahan}              buat/ubah kontak kelurahan                      babin:manage
DELETE /babin/{kelurahan}            hapus kontak kelurahan (4 November 2026)        babin:manage
```
Nomor yang ditampilkan adalah nomor DINAS (keputusan pemilik proyek). Baris dummy berlabel.
Nomor WhatsApp Babin dan chat id grup Telegram tidak pernah keluar ke kanal publik: keduanya
tujuan pengiriman buletin, bukan informasi untuk warga.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, Path, Query, Response, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
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
        "whatsapp_group_chat_id": row.whatsapp_group_chat_id,
        "advisory_sent_month": row.advisory_sent_month,
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
    #: Chat id grup WhatsApp warga (…@g.us); biasanya terisi otomatis lewat /daftar di grup.
    whatsapp_group_chat_id: str | None = Field(default=None, max_length=64)

    @field_validator("whatsapp_group_link")
    @classmethod
    def _only_whatsapp_invite_links(cls, value: str | None) -> str | None:
        """Tautan ini dirender sebagai href di halaman publik: hanya undangan grup WhatsApp
        resmi (https://chat.whatsapp.com/…) yang diterima — bukan skema lain (tinjauan
        keamanan 2 November 2026)."""
        if value is None or not value.strip():
            return None
        parsed = urlparse(value.strip())
        if parsed.scheme != "https" or (parsed.hostname or "").lower() != "chat.whatsapp.com":
            raise ValueError("Tautan grup harus berbentuk https://chat.whatsapp.com/…")
        return value.strip()


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
    row.whatsapp_group_chat_id = (payload.whatsapp_group_chat_id or "").strip() or None
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


@router.delete(
    "/babin/{kelurahan}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Menghapus kontak Babin satu kelurahan",
)
def delete_babin(
    kelurahan: str = Path(max_length=100),
    session: Session = Depends(get_db),
    current: CurrentUser = require_permission("babin:manage"),
) -> Response:
    """Kelurahan tanpa kontak kembali tampil "belum terisi" di layar petugas dan tanpa
    kontak Babin di peta warga. Penghapusannya tercatat di jejak audit."""
    row = session.scalar(
        select(Babinkamtibmas).where(
            func.lower(Babinkamtibmas.kelurahan) == kelurahan.strip().lower()
        )
    )
    if row is None:
        raise ApiError(status.HTTP_404_NOT_FOUND, "Kontak Babin kelurahan ini tidak ada.")
    detail = {"name": row.name, "is_dummy": row.is_dummy}
    resource_id = row.kelurahan
    session.delete(row)
    audit.record(
        session,
        action="DELETE_BABIN",
        resource_type="babinkamtibmas",
        result=audit.RESULT_SUCCESS,
        user_id=current.user.user_id,
        resource_id=resource_id,
        detail=detail,
    )
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
