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

4. **Koordinat berasal dari master lokasi, bukan dari pelapor.** `latitude`/`longitude`
   wajib pada tabelnya, tetapi meminta koordinat kepada pelapor berarti menerima titik yang
   tidak dapat diperiksa siapa pun. Pelapor memilih kecamatan; koordinatnya diambil dari
   `locations`. Ketepatannya sebatas kecamatan, dan respons menyatakannya.

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
from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ...models import CitizenReport, Location
from ...seeding.paths import TAXONOMY_FILE
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
    "Koordinat laporan diambil dari titik pusat kecamatan pada master lokasi, BUKAN dari "
    "tempat kejadian sebenarnya: pelapor hanya memilih kecamatan. Keterangan tempat yang "
    "lebih rinci tersimpan sebagai teks pada location_text dan tidak diubah menjadi titik."
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


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


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

    report = CitizenReport(
        code=_next_code(session),
        reported_at=now,
        incident_time=incident_time,
        category=payload.category,
        description=payload.description.strip(),
        # Koordinat dari master lokasi — lihat COORDINATE_BASIS.
        latitude=location.latitude,
        longitude=location.longitude,
        geom=func.ST_SetSRID(
            func.ST_MakePoint(float(location.longitude), float(location.latitude)), 4326
        ),
        location_id=location.location_id,
        location_text=(payload.location_text or "").strip() or None,
        # Penilaian petugas, bukan pelapor: keduanya sengaja dibiarkan kosong.
        urgency_score=None,
        verification_score=None,
        status=INITIAL_STATUS,
    )
    session.add(report)

    # `user_id` kosong karena memang tidak ada pengguna di balik peristiwa ini. Mengisinya
    # dengan akun sistem akan membuat jejak audit menyatakan sesuatu yang tidak terjadi.
    audit.record(
        session,
        action="SUBMIT_CITIZEN_REPORT",
        resource_type="citizen_report",
        result=audit.RESULT_SUCCESS,
        user_id=None,
        resource_id=report.code,
        detail={"category": report.category, "kecamatan": payload.kecamatan, "channel": "PUBLIC"},
    )
    session.commit()
    session.refresh(report)

    return {
        "ticket": report.code,
        "status": report.status,
        "reported_at": report.reported_at,
        "kecamatan": payload.kecamatan,
        "message": (
            "Laporan Anda tercatat. Simpan nomor tiket ini untuk menanyakan "
            "perkembangannya kepada petugas."
        ),
        "basis": INTAKE_BASIS,
    }
