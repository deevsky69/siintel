"""Kalender SOP — catatan pelaksanaan butir berkala SOP deteksi dini (naskah Lampiran I).

```text
GET  /sop/calendar?period=YYYY-MM          (dashboard:read)  butir, status, fakta, rekap triwulan
POST /sop/calendar/{period}/{item} {note?} (izin per butir)  mencatat butir sudah dikerjakan
```

Dua jenis butir:

* **dicatat pejabat** — hal yang terjadi di luar aplikasi (data diterima, catatan akses
  diperiksa, pencadangan diperiksa, laporan triwulan). Aplikasi tidak menilai tepat-waktunya:
  jam acuan purwarupa dikunci (mode demo), sehingga "terlambat" tidak dapat dihitung dengan jujur.
  Yang disimpan adalah siapa mencatat, kapan, dan catatannya.
* **dari sistem** — hal yang memang diketahui aplikasi (peringkat bulan itu sudah dibekukan,
  produk bulan itu sudah ditelaah). Tidak dapat dicentang tangan.

Di samping tiap butir tampil fakta sistem yang relevan, supaya pencatat membaca angka yang sama
dengan yang tersimpan — bukan mengingat-ingat.
"""

from __future__ import annotations

from datetime import date, datetime
from statistics import median
from typing import Any

from fastapi import APIRouter, Depends, Path, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ...models import AuditLog, CrimeIncident, MonthlyProduct, MonthlyRanking, SopCheck, User
from ...services import audit, clock
from ...services import monthly_product as products
from ..deps import CurrentUser, get_db, require_permission
from ..errors import ApiError

router = APIRouter(tags=["sop"])

PERIOD = r"^\d{4}-(0[1-9]|1[0-2])$"

#: Butir berkala SOP: (kunci, bagian SOP, ketentuan menurut naskah, pencatat, izin).
#: Izin `None` = diturunkan dari sistem, tidak dicatat tangan.
ITEMS: tuple[tuple[str, str, str, str, str | None], ...] = (
    (
        "data_received",
        "Penerimaan data",
        "Data kejadian bulan sebelumnya diterima dari fungsi dan Polsek paling lambat tanggal 5 "
        "sesuai format isian minimal",
        "KBO",
        "monthly_product:review",
    ),
    (
        "data_checked",
        "Pembakuan data",
        "Data kosong, ganda, dan bertentangan diperiksa melalui modul pembakuan; koreksi dicatat",
        "KBO",
        "monthly_product:review",
    ),
    (
        "ranking_frozen",
        "Penilaian kerawanan dan prediksi",
        "Peta, Indeks Kerawanan Wilayah, dan peringkat 65 kelurahan diterbitkan pada minggu "
        "pertama",
        "sistem",
        None,
    ),
    (
        "product_validated",
        "Validasi dan penyampaian",
        "Draf rekomendasi diperiksa analis, KBO, Wakasatintelkam, dan Kasatintelkam sebelum "
        "diajukan kepada Kapolres",
        "sistem",
        None,
    ),
    (
        "evaluation_done",
        "Evaluasi",
        "Pilihan bulan sebelumnya dibandingkan dengan kejadian aktual pada awal bulan; mutu "
        "draf, waktu kerja, dan tindak lanjut dicatat",
        "KBO",
        "monthly_product:review",
    ),
    (
        "access_log_reviewed",
        "Keamanan informasi",
        "Catatan akses diperiksa setiap bulan",
        "pemegang Audit Log",
        "audit:read",
    ),
    (
        "backup_checked",
        "Keamanan informasi",
        "Data dicadangkan secara terjadwal; hasil pencadangan diperiksa",
        "pemegang Audit Log",
        "audit:read",
    ),
    (
        "quarterly_report",
        "Evaluasi",
        "Hasil evaluasi dilaporkan kepada Kapolres setiap triwulan",
        "Kasat Intelkam",
        "monthly_product:validate",
    ),
)
ITEM_PERMISSION = {key: permission for key, _, _, _, permission in ITEMS}


def _period(value: str | None) -> str:
    if value:
        return value
    today = clock.reference_now().astimezone(clock.JAKARTA).date()
    return f"{today.year:04d}-{today.month:02d}"


def _month(period: str) -> date:
    return date(int(period[:4]), int(period[5:7]), 1)


def _system_facts(session: Session, period: str) -> dict[str, dict[str, Any]]:
    """Fakta yang diketahui aplikasi untuk periode itu — angka, bukan penilaian."""
    month = _month(period)
    following = date(month.year + (month.month == 12), month.month % 12 + 1, 1)
    start = datetime.combine(month, datetime.min.time(), tzinfo=clock.JAKARTA)
    end = datetime.combine(following, datetime.min.time(), tzinfo=clock.JAKARTA)
    loaded = session.scalar(select(func.max(CrimeIncident.created_at)))
    frozen = session.scalar(
        select(func.count()).select_from(MonthlyRanking).where(MonthlyRanking.target_month == month)
    )
    product = session.scalar(select(MonthlyProduct).where(MonthlyProduct.target_month == month))
    entries = session.scalar(
        select(func.count())
        .select_from(AuditLog)
        .where(AuditLog.timestamp >= start, AuditLog.timestamp < end)
    )
    refused = session.scalar(
        select(func.count())
        .select_from(AuditLog)
        .where(
            AuditLog.timestamp >= start,
            AuditLog.timestamp < end,
            AuditLog.result != audit.RESULT_SUCCESS,
        )
    )
    work = products.work_summary(product) if product is not None else None
    reviewed = product is not None and product.status in ("VALIDATED", "DECIDED")
    return {
        "data_received": {
            "fact": f"Data kejadian terakhir dimuat {loaded.astimezone(clock.JAKARTA):%d-%m-%Y}."
            if loaded
            else "Belum ada data kejadian."
        },
        "data_checked": {"fact": "Rincian isian yang ditandai ada di Data → Mutu Data."},
        "ranking_frozen": {
            "done": bool(frozen),
            "fact": "Peringkat bulan ini sudah dibekukan."
            if frozen
            else "Peringkat bulan ini belum dibekukan (dibekukan saat draf produk disusun).",
        },
        "product_validated": {
            "done": reviewed,
            "fact": f"Produk bulan ini berstatus {product.status}."
            if product is not None
            else "Produk bulan ini belum disusun.",
        },
        "evaluation_done": {
            "fact": (
                f"Mutu draf tercatat {work['quality_sigap_total']} dari {work['quality_max']}."
                if work and work["quality_sigap_total"] is not None
                else "Mutu draf dan waktu kerja bulan ini belum dicatat (Bulan Ini → Evaluasi)."
            )
        },
        "access_log_reviewed": {
            "fact": f"{int(entries or 0)} catatan audit pada bulan ini; {int(refused or 0)} "
            "ditolak atau gagal."
        },
        "backup_checked": {
            "fact": "Cadangan basis data harian dijalankan di server oleh "
            "infra/cadangan-harian.sh; hasilnya dilihat pada log server, bukan dari aplikasi."
        },
        "quarterly_report": {"fact": "Rekap triwulan di bawah dihitung dari catatan Evaluasi."},
    }


def _quarter(session: Session, period: str) -> dict[str, Any]:
    """Rekap triwulan (naskah Lampiran L huruf D): median skor mutu draf dan median menit dari
    data siap olah sampai validasi, atas produk bulanan pada triwulan itu yang sudah dicatat."""
    month = _month(period)
    first = (month.month - 1) // 3 * 3 + 1
    months = [date(month.year, first + offset, 1) for offset in range(3)]
    rows = session.scalars(
        select(MonthlyProduct).where(MonthlyProduct.target_month.in_(months))
    ).all()
    summaries = [products.work_summary(row) for row in rows]
    sigap = [s["quality_sigap_total"] for s in summaries if s["quality_sigap_total"] is not None]
    manual = [s["quality_manual_total"] for s in summaries if s["quality_manual_total"] is not None]
    minutes = [
        s["minutes_ready_to_validated"]
        for s in summaries
        if s["minutes_ready_to_validated"] is not None
    ]
    return {
        "label": f"Triwulan {(first - 1) // 3 + 1} {month.year}",
        "months": [m.isoformat()[:7] for m in months],
        "products": len(rows),
        "recorded": len(sigap),
        "median_quality_sigap": median(sigap) if sigap else None,
        "median_quality_manual": median(manual) if manual else None,
        "median_minutes_ready_to_validated": median(minutes) if minutes else None,
        "quality_max": 2 * len(products.QUALITY_ITEMS),
    }


def _calendar(session: Session, period: str, current: CurrentUser) -> dict[str, Any]:
    facts = _system_facts(session, period)
    checks = {
        row.item: (row, name)
        for row, name in session.execute(
            select(SopCheck, User.username)
            .outerjoin(User, User.user_id == SopCheck.done_by)
            .where(SopCheck.period == period)
        ).all()
    }
    items: list[dict[str, Any]] = []
    for key, section, rule, who, permission in ITEMS:
        recorded = checks.get(key)
        fact = facts[key]
        done = bool(fact.get("done")) if permission is None else recorded is not None
        items.append(
            {
                "key": key,
                "section": section,
                "rule": rule,
                "who": who,
                "source": "SYSTEM" if permission is None else "RECORDED",
                "done": done,
                "done_at": recorded[0].done_at if recorded else None,
                "done_by": recorded[1] if recorded else None,
                "note": recorded[0].note if recorded else None,
                "fact": fact["fact"],
                "can_record": permission is not None
                and recorded is None
                and current.permissions.allows(permission),
            }
        )
    return {
        "period": period,
        "items": items,
        "done": sum(1 for item in items if item["done"]),
        "total": len(items),
        "quarter": _quarter(session, period),
        "basis": (
            "Butir bersumber 'dicatat' adalah pernyataan pejabat yang berwenang bahwa ketentuan "
            "SOP itu sudah dikerjakan untuk periode ini; aplikasi menyimpan siapa dan kapan, dan "
            "tidak menilai ketepatan waktunya (jam acuan purwarupa dikunci). Butir bersumber "
            "'sistem' diturunkan dari data aplikasi dan tidak dapat dicentang tangan."
        ),
    }


@router.get("/sop/calendar", summary="Kalender SOP: butir berkala dan rekap triwulan")
def sop_calendar(
    period: str | None = Query(default=None, pattern=PERIOD, description="YYYY-MM"),
    session: Session = Depends(get_db),
    current: CurrentUser = require_permission("dashboard:read"),
) -> dict[str, Any]:
    return _calendar(session, _period(period), current)


class CheckRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    note: str | None = Field(default=None, max_length=1000)


@router.post(
    "/sop/calendar/{period}/{item}",
    status_code=status.HTTP_201_CREATED,
    summary="Mencatat satu butir SOP sudah dikerjakan",
)
def record_check(
    payload: CheckRequest,
    period: str = Path(pattern=PERIOD),
    item: str = Path(max_length=40),
    session: Session = Depends(get_db),
    current: CurrentUser = require_permission("dashboard:read"),
) -> dict[str, Any]:
    permission = ITEM_PERMISSION.get(item, "")
    if item not in ITEM_PERMISSION:
        raise ApiError(status.HTTP_404_NOT_FOUND, "Butir SOP tidak dikenal.")
    if permission is None:
        raise ApiError(
            status.HTTP_409_CONFLICT, "Butir ini diturunkan dari sistem dan tidak dicatat tangan."
        )
    if not current.permissions.allows(permission):
        audit.record(
            session,
            action="RECORD_SOP_CHECK",
            resource_type="sop_check",
            result=audit.RESULT_DENIED,
            user_id=current.user.user_id,
            resource_id=f"{period}:{item}",
            detail={"required": permission},
        )
        session.commit()
        raise ApiError(status.HTTP_403_FORBIDDEN, "Anda tidak berwenang mencatat butir ini.")
    exists = session.scalar(
        select(SopCheck).where(SopCheck.period == period, SopCheck.item == item)
    )
    if exists is not None:
        raise ApiError(status.HTTP_409_CONFLICT, "Butir ini sudah dicatat untuk periode itu.")
    session.add(
        SopCheck(
            period=period,
            item=item,
            done_by=current.user.user_id,
            done_at=datetime.now(tz=clock.JAKARTA),
            note=(payload.note or "").strip() or None,
        )
    )
    audit.record(
        session,
        action="RECORD_SOP_CHECK",
        resource_type="sop_check",
        result=audit.RESULT_SUCCESS,
        user_id=current.user.user_id,
        resource_id=f"{period}:{item}",
        detail={"note": bool(payload.note)},
    )
    session.commit()
    return _calendar(session, period, current)
