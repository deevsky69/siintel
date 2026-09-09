"""Kanal imbauan kepada masyarakat — `public_alerts` (TASK 111, docs/05 §2.7).

Sampai 9 September 2026 tabel ini punya 25 baris, seeder, dan model — tetapi TIDAK ADA
satu endpoint pun. Peringatan dini berhenti di dalam organisasi, dan `public_alert:publish`
bahkan tidak dipegang satu peran pun. Modul ini menutup lengan terakhir rantai pada
CLAUDE.md §9: prediksi → peringatan → **imbauan kepada yang berkepentingan**.

Lima hal yang dijaga di sini:

1. **Menerbitkan adalah keputusan komando, bukan tindakan teknis.** Hanya pemegang
   `public_alert:publish` — Pimpinan, ditetapkan pemilik proyek 9 September 2026 — yang
   dapat menerbitkan maupun mencabut. Administrator yang menjalankan prediksi tidak dapat
   mengumumkan hasilnya sendiri.

2. **Isi imbauan ditulis manusia.** `suggested_message` pada daftar calon hanyalah RANCANGAN
   yang diturunkan aturan dari kolom peringatannya, dan ia tidak pernah tersimpan sendiri:
   yang tersimpan adalah teks yang benar-benar dikirim penerbitnya. Menerbitkan kalimat
   yang tidak pernah dibaca siapa pun kepada masyarakat adalah persis yang dilarang
   CLAUDE.md §13.

3. **Tidak ada detail internal yang ikut keluar.** `public_alerts` sengaja tidak menyimpan
   `location_id` (docs/02 §7): wilayah dinyatakan sebagai `area_text` setingkat kecamatan,
   dan skor risiko maupun `grid_id` tidak pernah masuk ke respons publik.

4. **Satu peringatan tidak diumumkan dua kali.** Peringatan yang masih punya imbauan
   berstatus ACTIVE dijawab 409, bukan diterbitkan ulang — dua imbauan berbeda atas satu
   kejadian membuat pembacanya tidak tahu mana yang berlaku.

5. **Audit wajib.** `PUBLISH_PUBLIC_ALERT` dan `RESOLVE_PUBLIC_ALERT` dicatat, termasuk
   percobaan yang ditolak (CLAUDE.md §29 menyebut "warning publication" secara eksplisit).

> **BELUM DITETAPKAN — sisa U-10.** Severity minimum yang boleh diumumkan. Yang diputus
> 9 September 2026 adalah SIAPA yang berwenang, bukan MULAI TINGKAT MANA. Karena itu
> TIDAK ADA gerbang severity di sini: seluruh peringatan yang masih hidup dapat
> diterbitkan, dan setiap respons menyatakannya lewat `severity_gate_basis`. Menambahkan
> ambang diam-diam berarti memutuskan kebijakan yang belum diputus (CLAUDE.md §2D).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Path, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from ...models import EarlyWarning, Location, PublicAlert
from ...services import audit, clock
from ..deps import CurrentUser, get_db, jurisdiction_filter, not_found, require_permission
from ..errors import ApiError
from ..pagination import PageParams, page_params, paginate

router = APIRouter(prefix="/public-alerts", tags=["imbauan publik"])

STATUS_ACTIVE = "ACTIVE"
STATUS_RESOLVED = "RESOLVED"
STATUS_EXPIRED = "EXPIRED"

#: Status peringatan yang isinya masih layak diumumkan. Peringatan yang sudah `RESOLVED`
#: menggambarkan keadaan yang sudah lewat; mengumumkannya membuat masyarakat bersiap
#: menghadapi sesuatu yang sudah berakhir.
PUBLISHABLE_WARNING_STATUS = ("ACTIVE", "ACKNOWLEDGED")

#: Imbauan yang masih boleh dicabut. Yang sudah dicabut atau kedaluwarsa tidak diubah lagi.
RESOLVABLE_FROM = (STATUS_ACTIVE,)

SEVERITY_GATE_BASIS = (
    "TIDAK ada ambang severity minimum di kanal ini. Kewenangan menerbitkan ditetapkan "
    "pemilik proyek 9 September 2026 pada peran Pimpinan, tetapi ambang severity-nya "
    "belum ditetapkan (sisa U-10) — sehingga seluruh peringatan yang masih hidup dapat "
    "diterbitkan, apa pun tingkatnya. Ambang tidak ditambahkan diam-diam karena itu "
    "keputusan kebijakan, bukan keputusan teknis."
)

LIST_BASIS = (
    "Imbauan tidak menyimpan lokasi internal: wilayah dinyatakan sebagai teks setingkat "
    "kecamatan, dan skor risiko maupun grid tidak pernah ikut. Setiap baris menunjuk "
    "peringatan yang menjadi dasarnya, sehingga imbauan yang beredar selalu dapat "
    "dikembalikan ke prediksi yang melahirkannya."
)


class PublishRequest(BaseModel):
    """Permintaan menerbitkan satu imbauan."""

    warning_code: str = Field(description="Kode peringatan yang menjadi dasar, mis. WRN-00012")
    public_message: str = Field(
        min_length=40,
        max_length=1200,
        description=(
            "Kalimat yang benar-benar dibaca masyarakat. Wajib diisi penerbitnya — "
            "rancangan pada `suggested_message` hanya titik awal, bukan isi yang tersimpan."
        ),
    )


def _scoped(query: Select[Any], polsek: str | None) -> Select[Any]:
    """Menyaring menurut wilayah lewat peringatan yang menjadi dasar imbauan.

    Imbauan **tanpa** peringatan tidak dapat dipastikan berada di wilayah siapa pun, jadi
    ia tidak ikut terlihat oleh pengguna yang dibatasi cakupan — perlakuan yang sama dengan
    laporan masyarakat tanpa lokasi. Bagi pengguna tanpa batas wilayah ia tetap tampil.
    """
    if polsek is None:
        return query
    return (
        query.join(EarlyWarning, EarlyWarning.warning_id == PublicAlert.warning_id)
        .join(Location, Location.location_id == EarlyWarning.location_id)
        .where(Location.polsek == polsek)
    )


def _serialize(alert: PublicAlert) -> dict[str, Any]:
    return {
        "code": alert.code,
        "severity": alert.severity,
        "threat_type": alert.threat_type,
        "area_text": alert.area_text,
        "time_window": alert.time_window,
        "window_start": alert.window_start,
        "window_end": alert.window_end,
        "status": alert.status,
        "public_message": alert.public_message,
        "warning_code": None if alert.warning is None else alert.warning.code,
        "published_at": alert.created_at,
    }


def suggested_message(warning: EarlyWarning, area_text: str) -> str:
    """Rancangan kalimat imbauan, diturunkan ATURAN dari kolom peringatannya.

    Bukan keluaran model, dan tidak pernah tersimpan tanpa dibaca manusia: yang tersimpan
    adalah teks yang dikirim penerbitnya. Fungsi ini hanya menghemat pengetikan, dan
    layar menyatakannya sebagai rancangan.

    Sengaja tidak menyebut skor risiko maupun tingkat kepercayaan. Keduanya angka internal
    yang tidak berarti bagi pembaca di luar organisasi, dan menyebutnya justru mengundang
    pertanyaan yang tidak dapat dijawab pada kanal satu arah.
    """
    jam = f" pada pukul {warning.time_window} WIB" if warning.time_window else ""
    return (
        f"Imbauan kewaspadaan terhadap {warning.threat_type} di wilayah {area_text}{jam}. "
        "Tingkatkan kewaspadaan, pastikan rumah dan kendaraan dalam keadaan terkunci, "
        "serta laporkan hal mencurigakan kepada Polsek setempat atau melalui kanal "
        "LAPOR PRESISI."
    )


@router.get("", summary="Daftar imbauan yang pernah diterbitkan")
def list_alerts(
    session: Session = Depends(get_db),
    params: PageParams = Depends(page_params),
    current: CurrentUser = require_permission("public_alert:read"),
    status_filter: str | None = Query(None, alias="status", description="ACTIVE/RESOLVED/EXPIRED"),
) -> dict[str, Any]:
    polsek = jurisdiction_filter(current, "public_alert:read")

    query = _scoped(select(PublicAlert), polsek).order_by(PublicAlert.created_at.desc())
    if status_filter:
        query = query.where(PublicAlert.status == status_filter.upper())

    total = session.scalar(select(func.count()).select_from(query.order_by(None).subquery())) or 0
    rows = session.scalars(query.offset(params.offset).limit(params.page_size)).all()

    page = paginate([_serialize(alert) for alert in rows], total, params)
    page["basis"] = LIST_BASIS
    page["severity_gate_basis"] = SEVERITY_GATE_BASIS
    return page


@router.get("/candidates", summary="Peringatan yang masih dapat diumumkan")
def list_candidates(
    session: Session = Depends(get_db),
    current: CurrentUser = require_permission("public_alert:publish"),
) -> dict[str, Any]:
    """Peringatan hidup yang belum punya imbauan aktif, beserta rancangan kalimatnya.

    Dibatasi `public_alert:publish`, bukan `public_alert:read`: daftar ini adalah antrean
    kerja penerbit, dan menampilkannya kepada peran yang tidak dapat berbuat apa-apa
    hanya menjanjikan tombol yang tidak ada.
    """
    polsek = jurisdiction_filter(current, "public_alert:publish")

    published = select(PublicAlert.warning_id).where(PublicAlert.status == STATUS_ACTIVE)
    query = (
        select(EarlyWarning, Location)
        .join(Location, Location.location_id == EarlyWarning.location_id)
        .where(
            EarlyWarning.status.in_(PUBLISHABLE_WARNING_STATUS),
            EarlyWarning.warning_id.not_in(published),
        )
        .order_by(EarlyWarning.risk_score.desc(), EarlyWarning.created_at.desc())
    )
    if polsek is not None:
        query = query.where(Location.polsek == polsek)

    rows = session.execute(query).all()

    return {
        "data": [
            {
                "warning_code": warning.code,
                "severity": warning.severity,
                "threat_type": warning.threat_type,
                "time_window": warning.time_window,
                "window_start": warning.window_start,
                "window_end": warning.window_end,
                "kecamatan": location.kecamatan,
                # Rancangan, bukan isi tersimpan. Wilayahnya setingkat kecamatan.
                "suggested_message": suggested_message(warning, location.kecamatan),
            }
            for warning, location in rows
        ],
        "severity_gate_basis": SEVERITY_GATE_BASIS,
        "draft_basis": (
            "`suggested_message` diturunkan ATURAN dari kolom peringatannya dan berstatus "
            "RANCANGAN. Yang tersimpan adalah teks yang benar-benar dikirim penerbitnya; "
            "tidak ada kalimat yang terbit tanpa dibaca manusia lebih dahulu."
        ),
        "reference_time": clock.reference_now(),
        "demo_clock": clock.is_demo_clock(),
    }


def _next_code(session: Session) -> str:
    latest = session.scalar(select(PublicAlert.code).order_by(PublicAlert.code.desc()).limit(1))
    number = 0 if latest is None else int(str(latest).split("-")[-1])
    return f"PAL-{number + 1:04d}"


@router.post("", status_code=status.HTTP_201_CREATED, summary="Menerbitkan imbauan")
def publish_alert(
    payload: PublishRequest,
    session: Session = Depends(get_db),
    current: CurrentUser = require_permission("public_alert:publish"),
) -> dict[str, Any]:
    """Menerbitkan satu imbauan atas sebuah peringatan dini."""
    polsek = jurisdiction_filter(current, "public_alert:publish")

    query = (
        select(EarlyWarning, Location)
        .join(Location, Location.location_id == EarlyWarning.location_id)
        .where(EarlyWarning.code == payload.warning_code)
    )
    if polsek is not None:
        query = query.where(Location.polsek == polsek)

    found = session.execute(query).first()
    if found is None:
        raise not_found()
    warning, location = found

    def refuse(reason: str, message: str, http: int) -> ApiError:
        audit.record(
            session,
            action="PUBLISH_PUBLIC_ALERT",
            resource_type="public_alert",
            resource_id=warning.code,
            result=audit.RESULT_FAILED,
            user_id=current.user.user_id,
            detail={"warning_status": warning.status, "reason": reason},
        )
        session.commit()
        return ApiError(http, message)

    if warning.status not in PUBLISHABLE_WARNING_STATUS:
        raise refuse(
            "peringatan tidak lagi hidup",
            f"Peringatan berstatus {warning.status} tidak lagi menggambarkan keadaan yang "
            "perlu diumumkan.",
            status.HTTP_409_CONFLICT,
        )

    already = session.scalar(
        select(PublicAlert).where(
            PublicAlert.warning_id == warning.warning_id,
            PublicAlert.status == STATUS_ACTIVE,
        )
    )
    if already is not None:
        raise refuse(
            "sudah ada imbauan aktif",
            f"Peringatan ini sudah diumumkan lewat {already.code} dan imbauan itu masih "
            "berlaku. Cabut imbauan tersebut lebih dahulu bila isinya perlu diganti.",
            status.HTTP_409_CONFLICT,
        )

    alert = PublicAlert(
        code=_next_code(session),
        warning_id=warning.warning_id,
        severity=warning.severity,
        threat_type=warning.threat_type,
        # Setingkat kecamatan, bukan kelurahan maupun grid: imbauan menyebut wilayah
        # secukupnya agar warga tahu ini tentang daerahnya, tanpa menunjuk titik yang
        # justru memberi tahu pelaku di mana perhatian sedang terpusat.
        area_text=f"Kecamatan {location.kecamatan}",
        time_window=warning.time_window,
        window_start=warning.window_start,
        window_end=warning.window_end,
        status=STATUS_ACTIVE,
        public_message=payload.public_message.strip(),
    )
    session.add(alert)
    session.flush()

    audit.record(
        session,
        action="PUBLISH_PUBLIC_ALERT",
        resource_type="public_alert",
        resource_id=alert.code,
        result=audit.RESULT_SUCCESS,
        user_id=current.user.user_id,
        # Isi pesannya TIDAK ikut ke audit detail. Ia sudah tersimpan utuh pada barisnya,
        # dan menyalinnya membuat dua salinan yang dapat berbeda setelah revisi.
        detail={"warning_code": warning.code, "severity": alert.severity},
    )
    session.commit()

    return {"data": _serialize(alert), "severity_gate_basis": SEVERITY_GATE_BASIS}


@router.post("/{code}/resolve", summary="Mencabut imbauan")
def resolve_alert(
    code: str = Path(description="Kode imbauan, mis. PAL-0026"),
    session: Session = Depends(get_db),
    current: CurrentUser = require_permission("public_alert:publish"),
) -> dict[str, Any]:
    """Menutup imbauan yang sudah tidak berlaku.

    Memakai `public_alert:publish`, bukan permission tersendiri: mencabut imbauan sama
    kadarnya dengan menerbitkannya — keduanya mengubah apa yang dibaca masyarakat.
    """
    polsek = jurisdiction_filter(current, "public_alert:publish")

    alert = session.scalar(_scoped(select(PublicAlert), polsek).where(PublicAlert.code == code))
    if alert is None:
        raise not_found()

    if alert.status not in RESOLVABLE_FROM:
        audit.record(
            session,
            action="RESOLVE_PUBLIC_ALERT",
            resource_type="public_alert",
            resource_id=alert.code,
            result=audit.RESULT_FAILED,
            user_id=current.user.user_id,
            detail={"status_before": alert.status, "reason": "transisi tidak sah"},
        )
        session.commit()
        raise ApiError(
            status.HTTP_409_CONFLICT,
            f"Imbauan berstatus {alert.status} tidak dapat dicabut lagi.",
        )

    previous = alert.status
    alert.status = STATUS_RESOLVED
    audit.record(
        session,
        action="RESOLVE_PUBLIC_ALERT",
        resource_type="public_alert",
        resource_id=alert.code,
        result=audit.RESULT_SUCCESS,
        user_id=current.user.user_id,
        detail={"status_before": previous, "status_after": STATUS_RESOLVED},
    )
    session.commit()

    return {"data": _serialize(alert)}
