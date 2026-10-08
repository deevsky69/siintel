"""Tombol darurat warga — kanal publik `POST /public/panic` dan antrean petugas `/panic`.

Keputusan pemilik proyek 8 Oktober 2026: aplikasi Android warga mendapat tombol darurat
yang otomatis memberi tahu Administrator, Polsek wilayah itu, dan Pimpinan.

APA ARTI "MEMBERI TAHU" DI SINI, DINYATAKAN TERBUKA

    Sistem ini tidak memiliki notifikasi dorong (tidak ada Firebase/Play Services — lihat
    catatan di `LaporActivity`). Pemberitahuan berarti: peristiwa muncul PALING ATAS pada
    antrean `GET /notifications` ketiga peran itu dan pada spanduk merah di setiap halaman
    web mereka; aplikasi petugas di ponsel memeriksa antrean secara berkala selama terbuka
    dan membunyikan notifikasi sistem bila ada yang baru. Yang BELUM ada: dering ke ponsel
    yang aplikasinya tertutup. Itu menuntut layanan dorong pihak ketiga dan keputusan
    tersendiri.

YANG TETAP TERBUKA SEBAGAI KEBIJAKAN (docs/01 §19.2)

    Waktu tanggap dan eskalasi bila tidak ada yang menerima. Karena itu respons kanal ini
    dan layar warga menyebut 110 sebagai jalur resmi, bukan menggantikannya.

Tanpa identitas, seperti laporan masyarakat; dibatasi laju per alamat (lebih ketat dari
laporan, karena satu tombol lebih mudah ditekan berulang); setiap penekanan dan setiap
penerimaan/penutupan tercatat di audit.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, Path, Query, Request, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from ...models import Location, PanicEvent
from ...models.panic_event import STATUS_ACKNOWLEDGED, STATUS_CLOSED, STATUS_OPEN, STATUSES
from ...services import audit
from ..deps import CurrentUser, get_db, jurisdiction_filter, not_found, require_permission
from ..errors import ApiError
from .public_intake import _client_key, _RateLimiter

router = APIRouter(tags=["tombol darurat"])

#: Lebih ketat daripada laporan masyarakat: satu alamat paling banyak 5 penekanan per jam.
limiter = _RateLimiter(5, 3600)

CHANNEL_BASIS = (
    "Permintaan bantuan darurat dari aplikasi warga, tanpa identitas. Pemberitahuan berarti "
    "muncul paling atas pada antrean Administrator, Polsek wilayah itu, dan Pimpinan — bukan "
    "dering ke ponsel yang aplikasinya tertutup. Waktu tanggap dan eskalasi belum ditetapkan "
    "(PROPOSED); 110 tetap jalur resmi."
)


class PanicRequest(BaseModel):
    """Isi penekanan tombol. Field yang tidak dikenal ditolak, seperti laporan masyarakat."""

    model_config = ConfigDict(extra="forbid")

    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    accuracy_m: float | None = Field(default=None, ge=0, le=100_000)
    note: str | None = Field(default=None, max_length=300)


def _next_code(session: Session) -> str:
    latest = session.scalar(select(func.max(PanicEvent.code)))
    if latest is None:
        return "PNC-0001"
    prefix, _, number = str(latest).rpartition("-")
    return f"{prefix}-{int(number) + 1:04d}"


def _serialize(event: PanicEvent) -> dict[str, Any]:
    location = event.location
    return {
        "code": event.code,
        "pressed_at": event.pressed_at,
        "status": event.status,
        "latitude": float(event.latitude) if event.latitude is not None else None,
        "longitude": float(event.longitude) if event.longitude is not None else None,
        "accuracy_m": float(event.accuracy_m) if event.accuracy_m is not None else None,
        "kecamatan": location.kecamatan if location else None,
        "kelurahan": location.kelurahan if location else None,
        "polsek": location.polsek if location else None,
        "note": event.note,
        "acknowledged_at": event.acknowledged_at,
        "acknowledged_by": event.acknowledger.username if event.acknowledger else None,
        "closed_at": event.closed_at,
        "closed_by": event.closer.username if event.closer else None,
        "closing_note": event.closing_note,
    }


# ---------------------------------------------------------------------------
# Kanal publik
# ---------------------------------------------------------------------------


@router.post(
    "/public/panic",
    status_code=status.HTTP_201_CREATED,
    summary="Menekan tombol darurat (tanpa akun)",
)
def press_panic(
    payload: PanicRequest, request: Request, session: Session = Depends(get_db)
) -> dict[str, Any]:
    if not limiter.allow(_client_key(request)):
        raise ApiError(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Terlalu banyak penekanan dari alamat ini. Untuk keadaan darurat hubungi 110.",
        )
    if (payload.latitude is None) != (payload.longitude is None):
        raise ApiError(status.HTTP_400_BAD_REQUEST, "Lintang dan bujur harus dikirim berpasangan.")

    location: Location | None = None
    if payload.latitude is not None and payload.longitude is not None:
        # Kelurahan terdekat dari titik peranti — di seluruh Polres, karena warga yang
        # menekan tombol tidak memilih kecamatan.
        location = session.scalar(
            select(Location)
            .where(Location.kelurahan.is_not(None))
            .order_by(
                func.ST_Distance(
                    Location.geom,
                    func.ST_SetSRID(
                        func.ST_MakePoint(float(payload.longitude), float(payload.latitude)),
                        4326,
                    ),
                )
            )
            .limit(1)
        )

    event = PanicEvent(
        code=_next_code(session),
        pressed_at=datetime.now(UTC),
        latitude=payload.latitude,
        longitude=payload.longitude,
        geom=(
            func.ST_SetSRID(func.ST_MakePoint(payload.longitude, payload.latitude), 4326)
            if payload.latitude is not None
            else None
        ),
        accuracy_m=payload.accuracy_m if payload.latitude is not None else None,
        location_id=location.location_id if location else None,
        note=(payload.note or "").strip() or None,
        status=STATUS_OPEN,
    )
    session.add(event)
    session.flush()
    audit.record(
        session,
        action="PRESS_PANIC",
        resource_type="panic_event",
        result=audit.RESULT_SUCCESS,
        user_id=None,
        resource_id=event.code,
        detail={
            "has_location": payload.latitude is not None,
            "kecamatan": location.kecamatan if location else None,
            "kelurahan": location.kelurahan if location else None,
            "channel": "PUBLIC",
        },
    )
    session.commit()
    return {
        "code": event.code,
        "status": event.status,
        "kecamatan": location.kecamatan if location else None,
        "kelurahan": location.kelurahan if location else None,
        "message": (
            "Permintaan bantuan Anda tercatat dan diteruskan ke petugas. "
            "Bila keadaan mengancam jiwa, tetap hubungi 110."
        ),
        "basis": CHANNEL_BASIS,
    }


# ---------------------------------------------------------------------------
# Antrean petugas
# ---------------------------------------------------------------------------


def _scoped(query: Select[Any], polsek: str | None) -> Select[Any]:
    """Akun berwilayah hanya melihat peristiwa di kelurahan polseknya. Peristiwa tanpa titik
    (tanpa kelurahan) hanya terlihat oleh akun lingkup seluruh Polres — yang berwilayah tidak
    dapat ditentukan untuk siapa ia."""
    if polsek is None:
        return query
    return query.join(Location, Location.location_id == PanicEvent.location_id).where(
        Location.polsek == polsek
    )


@router.get("/panic", summary="Antrean permintaan bantuan darurat")
def list_panic(
    session: Session = Depends(get_db),
    current: CurrentUser = require_permission("panic:read"),
    status_filter: str | None = Query(
        None, alias="status", description="OPEN, ACKNOWLEDGED, CLOSED"
    ),
    limit: int = Query(100, ge=1, le=500),
) -> dict[str, Any]:
    polsek = jurisdiction_filter(current, "panic:read")
    query = _scoped(select(PanicEvent), polsek)
    if status_filter:
        wanted = status_filter.upper()
        if wanted not in STATUSES:
            raise ApiError(status.HTTP_400_BAD_REQUEST, "Status tidak dikenal.")
        query = query.where(PanicEvent.status == wanted)
    # Yang masih terbuka paling atas, lalu yang terbaru.
    rows = session.scalars(
        query.order_by(
            (PanicEvent.status == STATUS_OPEN).desc(),
            (PanicEvent.status == STATUS_ACKNOWLEDGED).desc(),
            PanicEvent.pressed_at.desc(),
        ).limit(limit)
    ).all()
    open_total = session.scalar(
        _scoped(select(func.count()).select_from(PanicEvent), polsek).where(
            PanicEvent.status == STATUS_OPEN
        )
    )
    return {
        "data": [_serialize(row) for row in rows],
        "open_total": int(open_total or 0),
        "basis": CHANNEL_BASIS,
    }


def _load(session: Session, code: str, polsek: str | None) -> PanicEvent:
    event: PanicEvent | None = session.scalar(
        _scoped(select(PanicEvent), polsek).where(PanicEvent.code == code)
    )
    if event is None:
        raise not_found()
    return event


class CloseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    note: str | None = Field(default=None, max_length=2000)


@router.post("/panic/{code}/acknowledge", summary="Menerima permintaan bantuan darurat")
def acknowledge(
    code: str = Path(description="Kode, mis. PNC-0001"),
    session: Session = Depends(get_db),
    current: CurrentUser = require_permission("panic:acknowledge"),
) -> dict[str, Any]:
    polsek = jurisdiction_filter(current, "panic:acknowledge")
    event = _load(session, code, polsek)
    if event.status != STATUS_OPEN:
        raise ApiError(status.HTTP_409_CONFLICT, f"Permintaan ini sudah berstatus {event.status}.")
    event.status = STATUS_ACKNOWLEDGED
    event.acknowledged_by = current.user.user_id
    event.acknowledged_at = datetime.now(UTC)
    audit.record(
        session,
        action="ACK_PANIC",
        resource_type="panic_event",
        result=audit.RESULT_SUCCESS,
        user_id=current.user.user_id,
        resource_id=event.code,
    )
    session.commit()
    session.refresh(event)
    return _serialize(event)


@router.post("/panic/{code}/close", summary="Menutup permintaan bantuan darurat")
def close(
    payload: CloseRequest,
    code: str = Path(description="Kode, mis. PNC-0001"),
    session: Session = Depends(get_db),
    current: CurrentUser = require_permission("panic:acknowledge"),
) -> dict[str, Any]:
    polsek = jurisdiction_filter(current, "panic:acknowledge")
    event = _load(session, code, polsek)
    if event.status == STATUS_CLOSED:
        raise ApiError(status.HTTP_409_CONFLICT, "Permintaan ini sudah ditutup.")
    event.status = STATUS_CLOSED
    event.closed_by = current.user.user_id
    event.closed_at = datetime.now(UTC)
    event.closing_note = (payload.note or "").strip() or None
    audit.record(
        session,
        action="CLOSE_PANIC",
        resource_type="panic_event",
        result=audit.RESULT_SUCCESS,
        user_id=current.user.user_id,
        resource_id=event.code,
        detail={"has_note": event.closing_note is not None},
    )
    session.commit()
    session.refresh(event)
    return _serialize(event)
