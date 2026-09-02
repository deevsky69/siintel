"""Penelusuran jejak audit (TASK 142).

Audit bersifat **append-only** (CLAUDE.md §29). Modul ini karena itu **hanya membaca** —
tidak ada `POST`, `PATCH`, maupun `DELETE`, dan ketiadaannya bukan kebetulan melainkan
sifat yang dijaga `test_the_audit_trail_offers_no_way_to_write`.

Yang membuat jejak ini bernilai bukan catatan keberhasilannya, melainkan **penolakannya**.
Audit yang hanya memuat `SUCCESS` tidak dapat dipakai menilai apakah pembatasan kewenangan
benar-benar bekerja — ia hanya membuktikan bahwa yang berhasil memang berhasil. Karena itu
ringkasan di sini menonjolkan `DENIED` dan `FAILED`, dan layarnya membukanya lebih dulu.

CATATAN CAKUPAN. `audit_logs` tidak memiliki kolom lokasi maupun fungsi, sehingga jejak ini
**tidak dapat** dibatasi per wilayah. Itulah sebabnya `audit:read` dicabut sementara dari
peran Polsek dan Fungsi (lihat `config/rbac/permissions.yaml`): memberikannya berarti
memberi akses penuh, dan itu pelebaran kewenangan yang menunggu keputusan pemilik proyek —
bukan sesuatu yang boleh diputuskan di lapisan ini.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from ...models import AuditLog, User
from ..deps import CurrentUser, get_db, require_permission
from ..errors import ApiError
from ..pagination import PageParams, page_params, paginate

router = APIRouter(tags=["audit"])

#: Zona penyajian. Penyimpanan tetap UTC; yang berpindah hanya tampilannya.
WIB = timezone(timedelta(hours=7))

#: Batas rentang yang boleh diminta sekaligus. Bukan ambang kebijakan, melainkan
#: pembatas biaya satu permintaan — disebut terbuka pada `filter_basis`.
MAX_RANGE_DAYS = 366

SCOPE_BASIS = (
    "Jejak audit tidak dapat dibatasi per wilayah maupun per fungsi: tabel audit_logs "
    "tidak menyimpan lokasi. Peran yang berwenang membacanya karena itu membacanya "
    "seluruhnya, dan hanya peran bercakupan penuh yang diberi kewenangan ini."
)

APPEND_ONLY_BASIS = (
    "Jejak audit bersifat hanya-tambah: tidak ada endpoint yang dapat mengubah maupun "
    "menghapusnya, termasuk bagi Administrator. Catatan yang dapat disunting bukan bukti."
)

DENIED_BASIS = (
    "DENIED berarti permintaan ditolak karena kewenangan; FAILED berarti permintaan "
    "berwenang tetapi melanggar aturan bisnis, misalnya transisi status yang tidak sah. "
    "Keduanya sengaja ikut dicatat — audit yang hanya memuat keberhasilan tidak dapat "
    "dipakai menilai apakah pembatasan kewenangan bekerja."
)


def _wib(moment: datetime) -> datetime:
    return moment.astimezone(WIB)


def _range(date_from: date | None, date_to: date | None) -> tuple[datetime | None, datetime | None]:
    """Rentang tanggal WIB diubah menjadi batas waktu yang dapat dibandingkan."""
    if date_from and date_to and date_from > date_to:
        raise ApiError(
            status.HTTP_400_BAD_REQUEST,
            f"Tanggal awal ({date_from}) melewati tanggal akhir ({date_to}).",
        )
    if date_from and date_to and (date_to - date_from).days > MAX_RANGE_DAYS:
        raise ApiError(
            status.HTTP_400_BAD_REQUEST,
            f"Rentang melebihi {MAX_RANGE_DAYS} hari. Persempit rentangnya.",
        )

    start = datetime.combine(date_from, time.min, tzinfo=WIB) if date_from else None
    # Batas akhir mencakup seluruh hari itu; tanpa ini, memilih satu tanggal yang sama
    # untuk awal dan akhir tidak akan mengembalikan apa pun.
    end = datetime.combine(date_to + timedelta(days=1), time.min, tzinfo=WIB) if date_to else None
    return start, end


def _filtered(
    query: Select[Any],
    *,
    action: str | None,
    result: str | None,
    resource_type: str | None,
    start: datetime | None,
    end: datetime | None,
) -> Select[Any]:
    if action:
        query = query.where(AuditLog.action == action.upper())
    if result:
        query = query.where(AuditLog.result == result.upper())
    if resource_type:
        query = query.where(AuditLog.resource_type == resource_type.lower())
    if start is not None:
        query = query.where(AuditLog.timestamp >= start)
    if end is not None:
        query = query.where(AuditLog.timestamp < end)
    return query


@router.get("/audit-logs", summary="Penelusuran jejak audit")
def list_audit_logs(
    session: Session = Depends(get_db),
    params: PageParams = Depends(page_params),
    current: CurrentUser = require_permission("audit:read"),
    action: str | None = Query(None),
    result: str | None = Query(None, description="SUCCESS, DENIED, atau FAILED"),
    resource_type: str | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
) -> dict[str, Any]:
    start, end = _range(date_from, date_to)

    query = _filtered(
        select(AuditLog, User.username, User.code)
        .outerjoin(User, User.user_id == AuditLog.user_id)
        .order_by(AuditLog.timestamp.desc()),
        action=action,
        result=result,
        resource_type=resource_type,
        start=start,
        end=end,
    )

    total = session.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = session.execute(query.offset(params.offset).limit(params.page_size)).all()

    page = paginate(
        [
            {
                "code": entry.code,
                "timestamp": entry.timestamp,
                "timestamp_wib": _wib(entry.timestamp),
                "action": entry.action,
                "resource_type": entry.resource_type,
                "resource_id": entry.resource_id,
                "result": entry.result,
                "detail": entry.detail,
                # Peristiwa sistem tidak dipicu pengguna; ditandai apa adanya, bukan
                # diisi nama pengganti yang seolah-olah ada pelakunya.
                "username": username,
                "user_code": user_code,
            }
            for entry, username, user_code in rows
        ],
        total,
        params,
    )
    page["filter_basis"] = (
        f"Rentang tanggal dibaca sebagai waktu setempat (WIB) dan mencakup seluruh hari "
        f"yang dipilih. Satu permintaan dibatasi {MAX_RANGE_DAYS} hari."
    )
    page["scope_basis"] = SCOPE_BASIS
    page["append_only_basis"] = APPEND_ONLY_BASIS
    return page


@router.get("/audit-logs/summary", summary="Ringkasan jejak audit")
def audit_summary(
    session: Session = Depends(get_db),
    current: CurrentUser = require_permission("audit:read"),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
) -> dict[str, Any]:
    """Ringkasan yang menonjolkan penolakan, bukan keberhasilan.

    Urutan penyajiannya disengaja: yang pertama dicari saat memeriksa audit adalah
    percobaan yang ditolak, bukan pekerjaan yang berhasil.
    """
    start, end = _range(date_from, date_to)

    def grouped(column: Any, limit: int | None = None) -> list[dict[str, Any]]:
        query = (
            _filtered(
                select(column, func.count()).select_from(AuditLog),
                action=None,
                result=None,
                resource_type=None,
                start=start,
                end=end,
            )
            .group_by(column)
            .order_by(func.count().desc(), column)
        )
        if limit is not None:
            query = query.limit(limit)
        return [{"key": key, "count": int(count)} for key, count in session.execute(query).all()]

    per_result = {row["key"]: row["count"] for row in grouped(AuditLog.result)}

    denied = session.execute(
        _filtered(
            select(AuditLog, User.username)
            .outerjoin(User, User.user_id == AuditLog.user_id)
            .where(AuditLog.result.in_(("DENIED", "FAILED")))
            .order_by(AuditLog.timestamp.desc()),
            action=None,
            result=None,
            resource_type=None,
            start=start,
            end=end,
        ).limit(10)
    ).all()

    earliest, latest = session.execute(
        _filtered(
            select(func.min(AuditLog.timestamp), func.max(AuditLog.timestamp)).select_from(
                AuditLog
            ),
            action=None,
            result=None,
            resource_type=None,
            start=start,
            end=end,
        )
    ).one()

    return {
        "total": sum(per_result.values()),
        "per_result": per_result,
        "per_action": grouped(AuditLog.action, limit=10),
        "per_resource_type": grouped(AuditLog.resource_type),
        "recent_refusals": [
            {
                "code": entry.code,
                "timestamp_wib": _wib(entry.timestamp),
                "action": entry.action,
                "result": entry.result,
                "resource_type": entry.resource_type,
                "resource_id": entry.resource_id,
                "username": username,
                "detail": entry.detail,
            }
            for entry, username in denied
        ],
        "earliest": earliest,
        "latest": latest,
        "denied_basis": DENIED_BASIS,
        "scope_basis": SCOPE_BASIS,
        "append_only_basis": APPEND_ONLY_BASIS,
    }
