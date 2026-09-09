"""Kanal publik LAPOR PRESISI — pengiriman laporan masyarakat tanpa akun (TASK 160).

Keputusan pemilik proyek, 2 September 2026, atas pilihan yang diuraikan `docs/14` §3.

Ini **satu-satunya** modul yang melayani permintaan tanpa autentikasi. Karena itu setiap
keputusan di dalamnya berangkat dari satu pertanyaan: apa yang dapat dilakukan seseorang
yang tidak dikenal, tidak dapat dimintai tanggung jawab, dan mungkin bermaksud buruk?

EMPAT BATAS YANG MENENTUKAN BENTUK MODUL INI

1. **Tanpa akun, dan karena itu tanpa identitas.** `citizen_reports` sengaja tidak memiliki
   kolom identitas pelapor (`docs/02` §K, U-13). Model permintaan di bawah menolak field
   yang tidak dikenal alih-alih mengabaikannya diam-diam: pengirim yang menyertakan nama
   atau nomor telepon menerima penolakan yang menjelaskan, bukan keberhasilan yang
   membuatnya mengira datanya tersimpan.

2. **Pelapor tidak menetapkan apa pun selain isi laporannya.** `status` selalu `RECEIVED`,
   dan `urgency_score` maupun `verification_score` tidak diterima sama sekali. Keduanya
   adalah penilaian petugas; membiarkan pelapor mengisinya berarti membiarkan siapa pun
   menaikkan prioritas laporannya sendiri.

3. **Kategori dari daftar tertutup.** Isian bebas akan memecah analisis pola dengan dua
   ejaan untuk satu hal, dan pada kanal publik ejaannya pasti bermacam-macam. Daftarnya
   dibaca dari `config/taxonomy/mappings.yaml`, bukan ditulis di sini.

4. **Koordinat boleh datang dari pelapor, dan asalnya selalu dicatat.** Sampai 8 September
   2026 koordinat selalu diambil dari titik pusat kecamatan. Pemilik proyek kemudian
   memutuskan tombol "bagikan lokasi" boleh mengirim titik peranti, disimpan apa adanya
   sebagai titik kejadian.

   Yang tidak berubah: **sepasang angka tidak menyatakan asal-usulnya.** Titik pusat
   kecamatan dan titik peranti terlihat persis sama padahal yang pertama berjarak kilometer
   dari kejadian. Karena itu `coordinate_source` selalu diisi, dan respons menyebutnya.

5. **Lampiran dilucuti metadatanya sebelum tersimpan.** Foto ponsel hampir selalu membawa
   koordinat GPS di EXIF; pelapor yang tidak mengetik namanya tetap dikenali dari sana.
   Lihat `services/attachments.py`. Berkas dihapus 90 hari setelah laporannya selesai, dan
   hanya peran yang berwenang memverifikasi yang dapat membukanya.

Kode status mengikuti kontrak `docs/05` §1: input yang tidak sah dijawab **400
VALIDATION_ERROR**, dan pembanjiran dijawab **429**.

Setiap pengiriman meninggalkan jejak audit **tanpa `user_id`** — memang tidak ada pengguna
di balik peristiwa ini, dan mengarangnya akan merusak arti kolom itu.
"""

from __future__ import annotations

import threading
import time
from datetime import datetime, timedelta
from typing import Any

import yaml
from fastapi import APIRouter, Depends, File, Request, UploadFile, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ...models import (
    COORDINATE_SOURCE_CENTROID,
    COORDINATE_SOURCE_GPS,
    CitizenReport,
    CitizenReportAttachment,
    Location,
    PublicAlert,
)
from ...seeding.paths import TAXONOMY_FILE
from ...services import attachments as attachment_store
from ...services import audit, clock
from ..deps import get_db
from ..errors import ApiError

router = APIRouter(prefix="/public", tags=["kanal publik"])

#: Status awal setiap laporan yang masuk lewat kanal ini. Tidak dapat dipilih pelapor.
INITIAL_STATUS = "RECEIVED"

#: Batas panjang isian bebas. Bukan aturan bisnis melainkan penjagaan: kolom teks yang
#: dapat diisi siapa saja tanpa akun adalah tempat paling mudah membanjiri basis data.
MAX_DESCRIPTION = 1000
MAX_LOCATION_TEXT = 255

#: Status imbauan yang sedang berlaku, dan batas berapa banyak yang ditampilkan sekaligus.
#: Halaman muka publik bukan arsip: yang berguna dibaca adalah yang berlaku sekarang, dan
#: daftar panjang justru membuat tidak satu pun terbaca.
ACTIVE_ALERT_STATUS = "ACTIVE"
MAX_PUBLIC_ALERTS = 10

PUBLIC_ALERT_BASIS = (
    "Imbauan di sini adalah satu-satunya isi kamtibmas yang keluar tanpa akun, dan ia "
    "keluar justru karena setiap barisnya sudah melewati keputusan publikasi oleh pejabat "
    "berwenang. Peringatan dini yang belum diumumkan tidak pernah sampai ke halaman ini. "
    "Wilayah disebut setingkat kecamatan; skor risiko dan lokasi rinci tidak ikut."
)

#: Berapa lama ke belakang waktu kejadian masih diterima. Laporan yang lebih tua dari ini
#: bukan laporan kamtibmas yang dapat ditindak, dan lebih pantas lewat jalur resmi.
MAX_INCIDENT_AGE_DAYS = 30

#: Jatah pengiriman per alamat IP dalam satu jam.
#:
#: Angkanya longgar dengan sengaja: satu keluarga atau satu kantor dapat berbagi satu
#: alamat IP, dan menolak laporan kedua dari alamat yang sama akan membungkam pelapor yang
#: sah. Yang ingin dicegah bukan pengiriman berulang yang wajar, melainkan pembanjiran.
RATE_LIMIT_PER_HOUR = 10
RATE_WINDOW_SECONDS = 3600

COORDINATE_BASIS = (
    "Bila pelapor membagikan lokasinya, koordinat itu disimpan apa adanya sebagai titik "
    "kejadian (coordinate_source = REPORTER_GPS). Bila tidak, koordinat diambil dari titik "
    "pusat kecamatan pada master lokasi (coordinate_source = KECAMATAN_CENTROID) dan "
    "ketepatannya sebatas kecamatan — BUKAN tempat kejadian sebenarnya."
)

ATTACHMENT_BASIS = (
    "Metadata berkas — termasuk koordinat GPS yang ditanam kamera ponsel — dilucuti sebelum "
    "berkas disimpan. Lampiran hanya dapat dibuka petugas yang berwenang memverifikasi "
    "laporan, dan dihapus 90 hari setelah laporannya selesai."
)

INTAKE_BASIS = (
    "Laporan masuk berstatus RECEIVED dan belum diverifikasi siapa pun. Selama belum "
    "diverifikasi, ia tidak menjadi dasar tindakan dan tidak memengaruhi penilaian risiko."
)


# ---------------------------------------------------------------------------
# Pembatas laju
# ---------------------------------------------------------------------------


class _RateLimiter:
    """Pembatas laju per alamat IP, jendela bergulir, di dalam proses.

    **Batasnya dinyatakan terbuka**: keadaan ini hidup di memori satu proses. Ia hilang
    saat aplikasi dijalankan ulang, dan tidak dibagi antar replika. Untuk PoC satu proses
    itu memadai; sebelum ada replika kedua, pembatas ini harus pindah ke penyimpanan
    bersama (Redis) — kalau tidak, batasnya terkalikan diam-diam sebanyak jumlah replika.

    Dipakai dengan kunci karena Uvicorn melayani permintaan pada beberapa thread.
    """

    def __init__(self, limit: int, window_seconds: int) -> None:
        self._limit = limit
        self._window = window_seconds
        self._hits: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def allow(self, key: str, now: float | None = None) -> bool:
        moment = time.monotonic() if now is None else now
        with self._lock:
            recent = [hit for hit in self._hits.get(key, []) if moment - hit < self._window]
            if len(recent) >= self._limit:
                self._hits[key] = recent
                return False
            recent.append(moment)
            self._hits[key] = recent
            # Kunci yang sudah tidak menyisakan jejak dibuang supaya kamus ini tidak tumbuh
            # tanpa batas sepanjang umur proses.
            for stale in [k for k, v in self._hits.items() if not v]:
                del self._hits[stale]
            return True

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


limiter = _RateLimiter(RATE_LIMIT_PER_HOUR, RATE_WINDOW_SECONDS)


def _client_key(request: Request) -> str:
    """Alamat pengirim, menghormati header proxy bila ada.

    Aplikasi berjalan di belakang Traefik, sehingga `request.client.host` selalu berisi
    alamat proxy dan pembatas laju akan memperlakukan seluruh dunia sebagai satu pengirim.
    """
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "tak-dikenal"


# ---------------------------------------------------------------------------
# Kategori
# ---------------------------------------------------------------------------


def load_report_categories() -> list[str]:
    """Kategori yang boleh dipilih pelapor, dari config taksonomi."""
    raw: dict[str, Any] = yaml.safe_load(TAXONOMY_FILE.read_text(encoding="utf-8"))
    categories = raw.get("citizen_report_categories") or []
    if not categories:
        message = "config/taxonomy/mappings.yaml tidak memuat citizen_report_categories"
        raise ApiError(status.HTTP_500_INTERNAL_SERVER_ERROR, message)
    return [str(name) for name in categories]


# ---------------------------------------------------------------------------
# Model permintaan
# ---------------------------------------------------------------------------


class ReportRequest(BaseModel):
    # `extra="forbid"` disengaja. Bila pengirim menyertakan nama, nomor telepon, atau
    # `urgency_score`, ia menerima penolakan yang menyebutkan field-nya — bukan
    # keberhasilan yang membuatnya mengira data itu tersimpan. Diam-diam membuang field
    # identitas terasa lebih ramah, tetapi menyesatkan orang yang menyerahkan datanya.
    model_config = ConfigDict(extra="forbid")

    category: str = Field(description="Salah satu kategori dari GET /public/report-options")
    kecamatan: str = Field(description="Kecamatan tempat kejadian")
    description: str = Field(min_length=10, max_length=MAX_DESCRIPTION)
    location_text: str | None = Field(default=None, max_length=MAX_LOCATION_TEXT)
    incident_time: datetime | None = Field(
        default=None, description="Waktu kejadian. Kosong berarti sekarang."
    )

    # Lintang dan bujur harus datang berpasangan. Salah satu saja bukan lokasi, dan
    # menerimanya berarti menyimpan titik yang separuhnya karangan.
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    accuracy_m: float | None = Field(
        default=None, ge=0, le=100_000, description="Ketelitian yang dilaporkan peranti, meter."
    )

    attachments: list[str] = Field(
        default_factory=list,
        max_length=attachment_store.MAX_ATTACHMENTS_PER_REPORT,
        description="Handle dari POST /public/attachments.",
    )


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.get("/alerts", summary="Imbauan kewaspadaan yang sedang berlaku")
def public_alerts(session: Session = Depends(get_db)) -> dict[str, Any]:
    """Imbauan yang sedang berlaku, untuk dibaca siapa saja. **Tanpa autentikasi.**

    Inilah satu-satunya angka— bukan, satu-satunya ISI kamtibmas yang boleh keluar tanpa
    akun, dan ia boleh keluar justru karena setiap barisnya adalah hasil KEPUTUSAN
    PUBLIKASI oleh pemegang `public_alert:publish` (CLAUDE.md §24). Peringatan dini yang
    belum diumumkan tidak pernah sampai ke sini.

    Yang dikirim sengaja sedikit: tingkat, jenis, wilayah setingkat kecamatan, jendela
    waktu, dan kalimat imbauannya. TIDAK ada skor risiko, tidak ada `grid_id`, tidak ada
    kode peringatan internal — ketiganya tidak berarti bagi pembaca di luar organisasi dan
    justru memberi tahu di mana perhatian sedang terpusat.
    """
    rows = session.scalars(
        select(PublicAlert)
        .where(PublicAlert.status == ACTIVE_ALERT_STATUS)
        .order_by(PublicAlert.window_start.desc().nullslast(), PublicAlert.created_at.desc())
        .limit(MAX_PUBLIC_ALERTS)
    ).all()

    return {
        "data": [
            {
                "code": alert.code,
                "severity": alert.severity,
                "threat_type": alert.threat_type,
                "area_text": alert.area_text,
                "time_window": alert.time_window,
                "window_start": alert.window_start,
                "window_end": alert.window_end,
                "message": alert.public_message,
            }
            for alert in rows
        ],
        "basis": PUBLIC_ALERT_BASIS,
    }


@router.get("/report-options", summary="Pilihan isian formulir laporan masyarakat")
def report_options(session: Session = Depends(get_db)) -> dict[str, Any]:
    """Kategori dan kecamatan yang boleh dipilih. **Tanpa autentikasi.**

    Hanya mengembalikan daftar pilihan — tidak satu pun laporan, kejadian, skor risiko,
    maupun angka lain. Kanal publik tidak boleh menjadi jendela ke dalam sistem.
    """
    kecamatan = list(
        session.scalars(
            select(Location.kecamatan).where(Location.kecamatan.is_not(None)).distinct()
        ).all()
    )
    return {
        "categories": load_report_categories(),
        "kecamatan": sorted(str(name) for name in kecamatan),
        "max_description": MAX_DESCRIPTION,
        "coordinate_basis": COORDINATE_BASIS,
        "intake_basis": INTAKE_BASIS,
        "attachment_basis": ATTACHMENT_BASIS,
        "max_attachments": attachment_store.MAX_ATTACHMENTS_PER_REPORT,
        "max_attachment_bytes": attachment_store.MAX_ATTACHMENT_BYTES,
    }


@router.post(
    "/attachments",
    status_code=status.HTTP_201_CREATED,
    summary="Mengunggah satu lampiran sebelum mengirim laporan",
)
def upload_attachment(
    request: Request,
    berkas: UploadFile = File(description="Foto, rekaman suara, atau video."),
) -> dict[str, Any]:
    """Menerima satu berkas dan mengembalikan **handle** untuk disertakan saat mengirim.

    ## Mengapa terpisah dari pengiriman laporan

    Alternatifnya adalah satu permintaan multipart yang membawa isi laporan sekaligus
    berkasnya. Itu memaksa kanal ini punya dua bentuk permintaan untuk satu hal yang sama —
    JSON bagi pengirim tanpa lampiran, multipart bagi yang membawa lampiran — dan dua
    bentuk untuk satu hal adalah dua tempat yang harus diperbaiki setiap kali aturannya
    berubah. Dengan memisahkannya, kontrak `POST /citizen-reports` hanya bertambah satu
    field opsional, dan aplikasi Android maupun web memakai jalur yang sama.

    ## Handle-nya rahasia, bukan nomor

    Ia acak 256 bit. Nomor urut dapat ditebak, dan menebaknya berarti dapat menempelkan
    berkas orang lain ke laporan sendiri.

    Titipan yang tidak pernah dipakai terhapus sendiri setelah 30 menit.
    """
    if not limiter.allow(_client_key(request)):
        raise ApiError(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Terlalu banyak berkas dikirim dari jaringan ini dalam satu jam terakhir.",
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


def _next_code(session: Session) -> str:
    """Nomor laporan berikutnya, mengikuti format kode pada data awal."""
    latest = session.scalar(select(func.max(CitizenReport.code)))
    if latest is None:
        # Awalan mengikuti data contoh (`RPT-0001`). Memulai dengan awalan lain akan
        # membuat dua bentuk nomor tiket hidup berdampingan tanpa alasan.
        return "RPT-0001"
    prefix, _, number = str(latest).rpartition("-")
    return f"{prefix}-{int(number) + 1:04d}"


@router.post(
    "/citizen-reports",
    status_code=status.HTTP_201_CREATED,
    summary="Mengirim laporan masyarakat tanpa akun",
)
def submit_report(
    payload: ReportRequest,
    request: Request,
    session: Session = Depends(get_db),
) -> dict[str, Any]:
    """Menerima satu laporan dari masyarakat. **Tanpa autentikasi.**

    Jawabannya hanya nomor tiket dan keterangan; tidak ada data lain yang dikembalikan.
    Nomor tiket itulah satu-satunya penanda yang dipegang pelapor — bukan akun, bukan
    identitas (`docs/14` §3).
    """
    if not limiter.allow(_client_key(request)):
        raise ApiError(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Terlalu banyak laporan dikirim dari jaringan ini dalam satu jam terakhir. "
            "Untuk keadaan mendesak, hubungi 110.",
        )

    categories = load_report_categories()
    if payload.category not in categories:
        raise ApiError(
            status.HTTP_400_BAD_REQUEST,
            "Kategori laporan tidak dikenal.",
            details=[{"field": "category", "issue": f"harus salah satu dari {categories}"}],
        )

    location = session.scalar(
        select(Location)
        .where(
            Location.kecamatan == payload.kecamatan,
            Location.latitude.is_not(None),
            Location.longitude.is_not(None),
        )
        .order_by(Location.code)
    )
    if location is None:
        raise ApiError(
            status.HTTP_400_BAD_REQUEST,
            "Kecamatan tidak dikenal.",
            details=[{"field": "kecamatan", "issue": "pilih dari GET /public/report-options"}],
        )

    now = clock.reference_now()
    incident_time = payload.incident_time or now
    if incident_time > now:
        raise ApiError(
            status.HTTP_400_BAD_REQUEST,
            "Waktu kejadian berada di masa depan.",
            details=[{"field": "incident_time", "issue": "tidak boleh melewati waktu sekarang"}],
        )
    if incident_time < now - timedelta(days=MAX_INCIDENT_AGE_DAYS):
        raise ApiError(
            status.HTTP_400_BAD_REQUEST,
            f"Waktu kejadian lebih dari {MAX_INCIDENT_AGE_DAYS} hari yang lalu. "
            "Laporan selama itu lebih tepat disampaikan langsung ke Polsek setempat.",
            details=[{"field": "incident_time", "issue": "terlalu lama"}],
        )

    if (payload.latitude is None) != (payload.longitude is None):
        raise ApiError(
            status.HTTP_400_BAD_REQUEST,
            "Lokasi harus berisi lintang dan bujur sekaligus.",
            details=[{"field": "latitude", "issue": "harus berpasangan dengan longitude"}],
        )
    if payload.accuracy_m is not None and payload.latitude is None:
        raise ApiError(
            status.HTTP_400_BAD_REQUEST,
            "Ketelitian hanya berlaku bila lokasi dibagikan.",
            details=[{"field": "accuracy_m", "issue": "tanpa latitude/longitude tidak berarti"}],
        )

    # Master lokasi sudah disaring `is_not(None)` pada kueri di atas, tetapi tipenya tetap
    # nullable. Penegasan ini yang membuat pembaca — dan pemeriksa tipe — tahu mengapa.
    assert location.latitude is not None and location.longitude is not None  # noqa: S101

    if payload.latitude is not None and payload.longitude is not None:
        shared = True
        latitude, longitude = float(payload.latitude), float(payload.longitude)
    else:
        shared = False
        latitude, longitude = float(location.latitude), float(location.longitude)

    staged = []
    try:
        for handle in payload.attachments:
            staged.append(attachment_store.claim(handle))
    except attachment_store.AttachmentError as error:
        raise ApiError(status.HTTP_400_BAD_REQUEST, str(error)) from error

    report = CitizenReport(
        code=_next_code(session),
        reported_at=now,
        incident_time=incident_time,
        category=payload.category,
        description=payload.description.strip(),
        # Titik peranti pelapor bila ia membagikannya; kalau tidak, titik pusat kecamatan.
        # `coordinate_source` menyatakan yang mana — lihat COORDINATE_BASIS.
        latitude=latitude,
        longitude=longitude,
        geom=func.ST_SetSRID(func.ST_MakePoint(longitude, latitude), 4326),
        coordinate_source=COORDINATE_SOURCE_GPS if shared else COORDINATE_SOURCE_CENTROID,
        gps_accuracy_m=payload.accuracy_m if shared else None,
        # `location_id` tetap menunjuk master lokasi kecamatan meski koordinatnya dari
        # peranti: ia yang menghubungkan laporan ke wilayah pada seluruh agregasi, dan
        # memetakan titik bebas ke sel grid adalah pekerjaan geo-processing, bukan kanal ini.
        location_id=location.location_id,
        location_text=(payload.location_text or "").strip() or None,
        # Penilaian petugas, bukan pelapor: keduanya sengaja dibiarkan kosong.
        urgency_score=None,
        verification_score=None,
        status=INITIAL_STATUS,
    )
    session.add(report)
    session.flush()

    for stored in staged:
        session.add(
            CitizenReportAttachment(
                report_id=report.report_id,
                kind=stored.kind,
                media_type=stored.media_type,
                byte_size=stored.byte_size,
                sha256=stored.sha256,
                storage_key=stored.storage_key,
                metadata_stripped_with=stored.metadata_stripped_with,
                created_at=now,
            )
        )

    # `user_id` kosong karena memang tidak ada pengguna di balik peristiwa ini. Mengisinya
    # dengan akun sistem akan membuat jejak audit menyatakan sesuatu yang tidak terjadi.
    audit.record(
        session,
        action="SUBMIT_CITIZEN_REPORT",
        resource_type="citizen_report",
        result=audit.RESULT_SUCCESS,
        user_id=None,
        resource_id=report.code,
        detail={
            "category": report.category,
            "kecamatan": payload.kecamatan,
            "channel": "PUBLIC",
            # Asal koordinat dan jumlah lampiran ikut dicatat: keduanya menentukan berapa
            # banyak data pribadi yang masuk lewat peristiwa ini, dan itu justru yang perlu
            # dapat ditelusuri kemudian. Isi lampirannya sendiri tidak pernah masuk audit.
            "coordinate_source": report.coordinate_source,
            "attachments": len(staged),
        },
    )
    session.commit()
    session.refresh(report)

    return {
        "ticket": report.code,
        "status": report.status,
        "reported_at": report.reported_at,
        "kecamatan": payload.kecamatan,
        "coordinate_source": report.coordinate_source,
        "attachments": len(staged),
        "message": (
            "Laporan Anda tercatat. Simpan nomor tiket ini untuk menanyakan "
            "perkembangannya kepada petugas."
        ),
        "basis": INTAKE_BASIS,
    }
