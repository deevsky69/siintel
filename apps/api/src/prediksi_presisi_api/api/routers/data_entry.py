"""Pintu masuk data (TASK 132) — kejadian, laporan intelijen, dan triase laporan masyarakat.

Sebelum berkas ini, satu-satunya cara data masuk ke sistem adalah proses seed. Katalog
RBAC sudah lama mendeklarasikan `crime:write`, `intelligence:write`, dan
`citizen_report:write`, tetapi tidak satu pun endpoint menegakkannya — kewenangan yang
dideklarasikan tanpa pernah dipakai tidak membuktikan apa pun.

Tiga hal dijaga sama di ketiga endpoint:

1. **Cakupan wilayah.** Lokasi di luar wilayah pengguna dijawab `404`, bukan `403`.
   Menjawab `403` akan membocorkan bahwa lokasi itu ada di wilayah lain (docs/05 §1,
   pola `not_found()` pada `api/deps.py`).
2. **Waktu acuan aplikasi.** Kejadian "di masa depan" diukur terhadap
   `clock.reference_now()`, bukan jam dinding. Dataset demo berhenti 31 Desember 2025
   dan jam acuan dibekukan di sana (SDL-16); memakai jam dinding akan menolak seluruh
   isian yang wajar saat paparan.
3. **Audit.** Setiap penulisan — berhasil maupun ditolak karena di luar cakupan —
   meninggalkan jejak (CLAUDE.md §29).

**Identitas orang tidak diterima.** Spesifikasi §6.1 menyatakan identitas
korban/pelaku/saksi tidak diperlukan untuk PoC, dan `crime_incidents` memang tidak
memiliki kolomnya (CLAUDE.md §16). Karena itu skema permintaan di sini mengabaikan
bidang tambahan apa pun secara diam-diam: bidang seperti `nama_korban` yang terlanjur
dikirim klien tidak disimpan, tidak dikembalikan, dan **tidak ikut masuk ke detail
audit**. Audit yang memuat nama korban akan menjadi tempat penyimpanan data pribadi
yang tidak pernah disetujui siapa pun.

CATATAN KONTRAK. Endpoint ini sempat dibangun pada `/intelligence` — nama yang saya
sebut keliru pada instruksi, bukan yang tertulis di `docs/05` §2.3 (`/intelligence-reports`).
Kode disesuaikan ke kontrak, bukan sebaliknya.
"""

from __future__ import annotations

from datetime import date, datetime, time
from functools import lru_cache
from typing import Any

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from ...models import CitizenReport, CrimeIncident, IntelligenceReport, Location
from ...seeding.taxonomy import Taxonomy, load_taxonomy
from ...services import audit, clock
from ..deps import (
    CurrentUser,
    get_db,
    jurisdiction_filter,
    not_found,
    require_permission,
)
from ..errors import ApiError

router = APIRouter(tags=["input data"])

#: Domain taksonomi pada `config/taxonomy/mappings.yaml`.
DOMAIN_INCIDENT_TYPE = "incident_type"
DOMAIN_CRIME_STATUS = "status_crime"
DOMAIN_INTELLIGENCE_STATUS = "status_intelligence"
DOMAIN_CITIZEN_STATUS = "status_citizen_report"
DOMAIN_IMPACT = "impact"

#: Status awal bila pengisi tidak menyebutkannya. TECHNICAL DECISION: keduanya adalah
#: nilai pertama pada alur masing-masing taksonomi, bukan angka yang dikarang.
DEFAULT_CRIME_STATUS = "REPORTED"
DEFAULT_INTELLIGENCE_STATUS = "NEW"

#: Awalan dan lebar nomor kode, mengikuti dataset yang sudah ada
#: (`INC-01200`, `INT-0120`).
CRIME_CODE_PREFIX = "INC"
CRIME_CODE_WIDTH = 5
INTELLIGENCE_CODE_PREFIX = "INT"
INTELLIGENCE_CODE_WIDTH = 4

#: Mengapa verifikasi laporan masyarakat bukan sekadar label — dikembalikan API supaya
#: layar tidak perlu menuliskan ulang klaim yang bisa melenceng dari konfigurasi.
VERIFICATION_BASIS = (
    "Status VERIFIED adalah tindakan yang bermakna, bukan penanda administratif: "
    "`config/risk/risk-weights.yaml` menyediakan `community_factor` yang menghitung "
    "laporan masyarakat terverifikasi pada sebuah sel grid. Bobotnya kini 0,00 — "
    "sengaja ditulis nol dan bukan dihapus — sehingga verifikasi BELUM menggerakkan "
    "risk score sama sekali. Begitu bobot itu dinaikkan, keputusan verifikasi yang "
    "diambil hari ini ikut menentukan angka risiko."
)

#: Mengapa perpindahan status tidak dibatasi. Dipakai docstring endpoint dan layar.
TRANSITION_BASIS = (
    "Belum ada SOP triase yang menetapkan urutan wajib maupun status akhir. Karena itu "
    "setiap perpindahan antar-status diterima dan dicatat; yang ditolak hanya "
    "perpindahan ke status yang sedang berlaku."
)


@lru_cache(maxsize=1)
def _taxonomy() -> Taxonomy:
    """Taksonomi dibaca sekali; berkasnya konfigurasi, bukan data yang berubah tiap request."""
    return load_taxonomy()


def _choices(domain: str) -> dict[str, str]:
    """Nilai tersimpan → label Bahasa Indonesia, dalam urutan konfigurasi.

    Label diambil dari blok `labels` bila ada. Bila tidak, dipakai kunci sumber Bahasa
    Indonesia yang memetakan ke nilai itu (`Begal` → `BEGAL`). Bila kunci sumbernya sama
    dengan nilainya (`CURANMOR`), label dibentuk dari nilainya sendiri. Tidak ada label
    yang dikarang di luar isi konfigurasi.
    """
    taxonomy = _taxonomy()
    table = taxonomy.mappings.get(domain)
    if table is None:
        raise ApiError(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Konfigurasi taksonomi tidak lengkap.",
        )

    explicit = taxonomy.labels.get(domain, {})
    ordered: dict[str, str] = {}
    for source, value in table.items():
        if value in ordered:
            continue
        fallback = source if source != value else value.replace("_", " ").title()
        ordered[value] = explicit.get(value, fallback)

    return ordered


def _options(domain: str) -> list[dict[str, str]]:
    return [{"value": value, "label": label} for value, label in _choices(domain).items()]


def _validated(domain: str, raw: str, field_label: str) -> str:
    """Nilai taksonomi yang sah, atau `400` beserta daftar yang sah.

    Hanya nilai tersimpan (UPPER_SNAKE) yang diterima — bukan label Bahasa Indonesia.
    Menerima keduanya akan membuat dua ejaan untuk satu nilai masuk ke basis data lewat
    pintu yang sama, dan taksonomi bayangan seperti itulah yang justru dicegah oleh
    `config/taxonomy/mappings.yaml`.
    """
    allowed = _choices(domain)
    value = raw.strip()
    if value in allowed:
        return value

    raise ApiError(
        status.HTTP_400_BAD_REQUEST,
        f"{field_label} '{raw}' tidak dikenal. Nilai yang sah: {', '.join(allowed)}.",
    )


def _reject_future(moment: datetime, field_label: str) -> None:
    """Menolak waktu setelah waktu acuan aplikasi.

    Diukur terhadap `clock.reference_now()`, bukan `datetime.now()`: jam acuan demo beku
    pada 31 Desember 2025 (SDL-16), dan memakai jam dinding akan membuat pencatatan
    kejadian nyata pada dataset ini selalu tampak "di masa depan" — atau sebaliknya,
    membiarkan kejadian yang belum terjadi tercatat sebagai fakta.
    """
    now = clock.reference_now()
    if moment > now:
        raise ApiError(
            status.HTTP_400_BAD_REQUEST,
            f"{field_label} tidak boleh melewati waktu acuan sistem "
            f"({clock.to_jakarta(now):%d %b %Y %H:%M} WIB). "
            f"Kejadian yang belum terjadi tidak dicatat sebagai fakta.",
        )


def _next_code(session: Session, column: Any, prefix: str, width: int) -> str:
    """Kode berurut berikutnya, mis. `INC-01201`.

    Hanya kode yang benar-benar berbentuk `PREFIX-<angka>` yang diperhitungkan, sehingga
    kode buatan test (`INC-UJI-…`) tidak membuat pembacaan nomornya gagal.

    Nomor diambil dan dipakai dalam satu transaksi tanpa penguncian. Dua penulisan yang
    benar-benar bersamaan akan bertabrakan pada unique constraint `code`. Pada PoC satu
    pengguna hal ini tidak terjadi, dan penyelesaian yang benar kelak adalah sequence
    database — bukan penguncian di lapisan aplikasi.
    """
    latest: str | None = session.scalar(
        select(column).where(column.regexp_match(f"^{prefix}-[0-9]+$")).order_by(column.desc())
    )
    number = 1 if latest is None else int(latest.rsplit("-", 1)[-1]) + 1
    return f"{prefix}-{number:0{width}d}"


def _resolve_location(
    session: Session,
    current: CurrentUser,
    permission: str,
    location_code: str,
    *,
    audit_action: str,
    resource_type: str,
) -> Location:
    """Lokasi tujuan penulisan, sudah tersaring menurut cakupan wilayah pengguna.

    Lokasi yang tidak dikenal dan lokasi di luar wilayah pengguna menghasilkan jawaban
    yang **sama persis** (`404`). Membedakan keduanya akan memberi tahu pengguna Polsek
    Tebet bahwa `LOC-042` itu ada — hanya saja bukan miliknya (docs/05 §1).

    Percobaannya tetap dicatat: penolakan yang tidak meninggalkan jejak membuat audit
    tidak dapat dipakai menilai kepatuhan RBAC.
    """
    polsek = jurisdiction_filter(current, permission)

    query = select(Location).where(Location.code == location_code)
    if polsek is not None:
        query = query.where(Location.polsek == polsek)

    location = session.scalar(query)
    if location is None:
        audit.record(
            session,
            action=audit_action,
            resource_type=resource_type,
            result=audit.RESULT_FAILED,
            user_id=current.user.user_id,
            detail={
                "reason": "lokasi tidak dikenal atau di luar cakupan wilayah",
                "location_code": location_code,
            },
        )
        session.commit()
        raise not_found()

    return location


class CrimeRequest(BaseModel):
    """Kejadian yang dicatat petugas.

    `extra="ignore"` disengaja dan merupakan pengaman privasi, bukan kelonggaran:
    identitas korban/pelaku/saksi yang terlanjur dikirim klien tidak pernah menjadi
    bagian dari objek ini, sehingga tidak dapat tersimpan maupun ikut tercatat di audit
    (CLAUDE.md §16, spesifikasi §6.1).
    """

    model_config = ConfigDict(extra="ignore")

    incident_type: str = Field(description="Jenis kejadian menurut taksonomi")
    incident_date: date = Field(description="Tanggal kejadian")
    incident_time: time = Field(description="Jam kejadian (WIB)")
    location_code: str = Field(description="Kode lokasi dari GET /locations, mis. LOC-001")
    location_type: str | None = Field(default=None, max_length=100, description="Kategori TKP")
    modus: str | None = Field(default=None, max_length=100)
    target_type: str | None = Field(default=None, max_length=100)
    status: str | None = Field(default=None, description="Status penanganan; kosong = REPORTED")


class IntelligenceRequest(BaseModel):
    """Laporan intelijen. Bidangnya mengikuti `intelligence_reports` apa adanya.

    Tabel ini memang tidak memiliki kolom uraian bebas: yang disimpan adalah kategori,
    penilaian sumber, dan dampaknya. Menambahkan kolom uraian merupakan perubahan schema
    dan bukan bagian dari task ini.
    """

    model_config = ConfigDict(extra="ignore")

    report_date: date = Field(description="Tanggal laporan")
    category: str = Field(min_length=1, max_length=100, description="Kategori kerawanan")
    location_code: str = Field(description="Kode lokasi dari GET /locations")
    reliability: str | None = Field(default=None, max_length=10, description="Keandalan sumber")
    confidence: int | None = Field(default=None, ge=0, le=100)
    urgency: int | None = Field(default=None, ge=0, le=100)
    impact: str | None = Field(default=None, description="LOW, MEDIUM, HIGH, CRITICAL")
    status: str | None = Field(default=None, description="Status tindak lanjut; kosong = NEW")


class ReportStatusRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    status: str = Field(description="Status baru menurut taksonomi status_citizen_report")
    note: str | None = Field(default=None, max_length=1000, description="Alasan/keterangan triase")


def _distinct(session: Session, query: Select[Any]) -> list[str]:
    return [str(value) for value in session.scalars(query).all() if value]


@router.get("/data-entry/options", summary="Pilihan isian formulir pemasukan data")
def entry_options(
    session: Session = Depends(get_db),
    current: CurrentUser = require_permission("location:read"),
) -> dict[str, Any]:
    """Nilai yang sah untuk ketiga formulir, dari taksonomi dan dari data yang ada.

    Dijaga `location:read` — permission yang dimiliki keempat peran — karena isinya
    kosakata isian, bukan data kamtibmas. Meski begitu, saran yang **berasal dari basis
    data** hanya diberikan kepada pengguna yang berwenang membaca tabel asalnya, dan
    disaring menurut cakupan wilayahnya. Tanpa itu, daftar modus operandi akan menjadi
    jalan memutar yang membocorkan isi wilayah lain lewat pintu belakang.

    Nilai taksonomi berstatus PROPOSED (U-16) — sama seperti berkas konfigurasinya.
    """
    suggestions: dict[str, list[str]] = {
        "location_type": _distinct(
            session,
            select(Location.location_type).where(Location.location_type.is_not(None)).distinct(),
        )
    }

    if current.permissions.allows("crime:read"):
        polsek = jurisdiction_filter(current, "crime:read")
        base = select(CrimeIncident).join(
            Location, Location.location_id == CrimeIncident.location_id
        )
        if polsek is not None:
            base = base.where(Location.polsek == polsek)
        suggestions["modus"] = _distinct(
            session, base.with_only_columns(CrimeIncident.modus).distinct()
        )
        suggestions["target_type"] = _distinct(
            session, base.with_only_columns(CrimeIncident.target_type).distinct()
        )

    if current.permissions.allows("intelligence:read"):
        polsek = jurisdiction_filter(current, "intelligence:read")
        intel = select(IntelligenceReport).join(
            Location, Location.location_id == IntelligenceReport.location_id
        )
        if polsek is not None:
            intel = intel.where(Location.polsek == polsek)
        suggestions["intelligence_category"] = _distinct(
            session, intel.with_only_columns(IntelligenceReport.category).distinct()
        )
        suggestions["reliability"] = _distinct(
            session, intel.with_only_columns(IntelligenceReport.reliability).distinct()
        )

    return {
        "incident_type": _options(DOMAIN_INCIDENT_TYPE),
        "crime_status": _options(DOMAIN_CRIME_STATUS),
        "intelligence_status": _options(DOMAIN_INTELLIGENCE_STATUS),
        "citizen_report_status": _options(DOMAIN_CITIZEN_STATUS),
        "impact": _options(DOMAIN_IMPACT),
        "suggestions": {key: sorted(values) for key, values in suggestions.items()},
        "taxonomy_version": _taxonomy().version,
        "reference_time": clock.reference_now(),
        "demo_clock": clock.is_demo_clock(),
        "verification_basis": VERIFICATION_BASIS,
        "transition_basis": TRANSITION_BASIS,
    }


@router.post(
    "/crimes",
    status_code=status.HTTP_201_CREATED,
    summary="Mencatat satu kejadian kriminal",
)
def create_crime(
    payload: CrimeRequest,
    session: Session = Depends(get_db),
    current: CurrentUser = require_permission("crime:write"),
) -> dict[str, Any]:
    """Kejadian baru, terikat pada satu sel grid dan pada waktu yang masuk akal.

    Bidangnya mengikuti spesifikasi §6.1 — jenis, tanggal, jam, lokasi, kategori TKP,
    modus, sasaran, dan status penanganan. Wilayah (`polsek`/`kecamatan`/`kelurahan`)
    tidak diminta dan tidak disalin: seluruhnya diperoleh dari `locations` lewat
    `location_id` (docs/02 K-8). Meminta pengisi mengetiknya lagi hanya menciptakan
    kemungkinan wilayah kejadian berbeda dari wilayah lokasinya.
    """
    incident_type = _validated(DOMAIN_INCIDENT_TYPE, payload.incident_type, "Jenis kejadian")
    incident_status = (
        DEFAULT_CRIME_STATUS
        if payload.status is None
        else _validated(DOMAIN_CRIME_STATUS, payload.status, "Status penanganan")
    )

    occurred_at = datetime.combine(payload.incident_date, payload.incident_time, clock.JAKARTA)
    _reject_future(occurred_at, "Waktu kejadian")

    location = _resolve_location(
        session,
        current,
        "crime:write",
        payload.location_code,
        audit_action="CREATE_CRIME_INCIDENT",
        resource_type="crime",
    )

    incident = CrimeIncident(
        code=_next_code(session, CrimeIncident.code, CRIME_CODE_PREFIX, CRIME_CODE_WIDTH),
        incident_type=incident_type,
        occurred_at=occurred_at,
        incident_date=payload.incident_date,
        incident_time=payload.incident_time,
        location_id=location.location_id,
        location_type=payload.location_type,
        modus=payload.modus,
        target_type=payload.target_type,
        status=incident_status,
    )
    session.add(incident)

    audit.record(
        session,
        action="CREATE_CRIME_INCIDENT",
        resource_type="crime",
        result=audit.RESULT_SUCCESS,
        user_id=current.user.user_id,
        resource_id=incident.code,
        # Hanya penanda yang dapat ditelusuri — tanpa identitas siapa pun.
        detail={
            "incident_type": incident_type,
            "location_code": location.code,
            "occurred_at": occurred_at.isoformat(),
        },
    )
    session.commit()
    session.refresh(incident)

    return {
        "code": incident.code,
        "incident_type": incident.incident_type,
        "occurred_at": incident.occurred_at,
        "status": incident.status,
        "location_code": location.code,
        "kecamatan": location.kecamatan,
        "kelurahan": location.kelurahan,
        "polsek": location.polsek,
        "grid_id": location.grid_id,
    }


@router.post(
    "/intelligence-reports",
    status_code=status.HTTP_201_CREATED,
    summary="Mencatat satu laporan intelijen",
)
def create_intelligence(
    payload: IntelligenceRequest,
    session: Session = Depends(get_db),
    current: CurrentUser = require_permission("intelligence:write"),
) -> dict[str, Any]:
    """Laporan intelijen baru pada satu sel grid.

    `category` tidak divalidasi terhadap taksonomi karena `config/taxonomy/mappings.yaml`
    memang tidak memiliki domain untuk kategori intelijen. Mengarang daftarnya di kode
    akan membuat taksonomi yang tidak pernah disetujui siapa pun; yang dilakukan sebagai
    gantinya adalah menawarkan kategori yang sudah ada lewat `/data-entry/options`.

    PERHATIAN KEWENANGAN. Per 1 September 2026 `intelligence:write` ada di katalog
    permission tetapi **tidak dipegang satu peran pun** — pemberiannya kepada peran
    Fungsi ditahan sampai ada keputusan pemilik proyek (`config/rbac/permissions.yaml`).
    Endpoint ini karena itu menjawab `403` untuk seluruh akun demo. Itu keadaan yang
    benar: yang kurang adalah keputusan kebijakan, bukan kodenya.
    """
    report_status = (
        DEFAULT_INTELLIGENCE_STATUS
        if payload.status is None
        else _validated(DOMAIN_INTELLIGENCE_STATUS, payload.status, "Status laporan")
    )
    impact = None if payload.impact is None else _validated(DOMAIN_IMPACT, payload.impact, "Dampak")

    today = clock.to_jakarta(clock.reference_now()).date()
    if payload.report_date > today:
        raise ApiError(
            status.HTTP_400_BAD_REQUEST,
            f"Tanggal laporan tidak boleh melewati waktu acuan sistem ({today:%d %b %Y} WIB).",
        )

    location = _resolve_location(
        session,
        current,
        "intelligence:write",
        payload.location_code,
        audit_action="CREATE_INTELLIGENCE_REPORT",
        resource_type="intelligence",
    )

    report = IntelligenceReport(
        code=_next_code(
            session,
            IntelligenceReport.code,
            INTELLIGENCE_CODE_PREFIX,
            INTELLIGENCE_CODE_WIDTH,
        ),
        report_date=payload.report_date,
        category=payload.category.strip(),
        location_id=location.location_id,
        reliability=payload.reliability,
        confidence=payload.confidence,
        urgency=payload.urgency,
        impact=impact,
        status=report_status,
    )
    session.add(report)

    audit.record(
        session,
        action="CREATE_INTELLIGENCE_REPORT",
        resource_type="intelligence",
        result=audit.RESULT_SUCCESS,
        user_id=current.user.user_id,
        resource_id=report.code,
        detail={"category": report.category, "location_code": location.code},
    )
    session.commit()
    session.refresh(report)

    return {
        "code": report.code,
        "report_date": report.report_date,
        "category": report.category,
        "status": report.status,
        "impact": report.impact,
        "location_code": location.code,
        "kecamatan": location.kecamatan,
        "polsek": location.polsek,
        "grid_id": location.grid_id,
    }


@router.post(
    "/citizen-reports/{code}/status",
    summary="Triase laporan masyarakat — mengubah statusnya",
)
def update_report_status(
    code: str,
    payload: ReportStatusRequest,
    session: Session = Depends(get_db),
    current: CurrentUser = require_permission("citizen_report:write"),
) -> dict[str, Any]:
    """Mengubah status satu laporan masyarakat, beserta jejaknya.

    ATURAN PERPINDAHAN STATUS — dan alasannya.

    Alur taksonomi `status_citizen_report` adalah
    `Diterima → Diverifikasi → Diteruskan → Ditangani → Selesai`. Yang **tidak** ada di
    mana pun — tidak di `docs/01` §5, tidak di `docs/02` §6, tidak di `docs/14` — adalah
    pernyataan bahwa urutan itu wajib, bahwa status tidak boleh mundur, atau bahwa
    `CLOSED` bersifat final. Urutan pada berkas taksonomi adalah urutan penulisan, bukan
    aturan yang disetujui.

    Karena itu di sini **tidak ada** larangan mundur maupun larangan melompat. Membuat
    keduanya berarti mengarang SOP: laporan yang keliru diverifikasi tidak akan pernah
    dapat dikembalikan, dan laporan yang jelas-jelas selesai tidak dapat langsung
    ditutup. Yang dipilih adalah pilihan paling longgar **tetapi tercatat** — setiap
    perpindahan menulis audit lengkap dengan status sebelum dan sesudah, sehingga
    perpindahan yang tidak wajar tetap terlihat oleh yang memeriksa.

    Satu-satunya yang ditolak adalah perpindahan ke status yang sedang berlaku (`409`).
    Itu bukan aturan alur kerja melainkan penjagaan audit: mencatat "perubahan" yang
    tidak mengubah apa pun membuat jejak audit memuat peristiwa yang tidak terjadi.

    **Ini menunggu keputusan pemilik proyek.** Begitu SOP triase ditetapkan, aturannya
    ditulis di satu tempat — di sini — dan bukan disebar ke layar.

    Cakupan wilayah mengikuti `community.py`: laporan yang belum tertaut ke sel grid
    tidak memiliki wilayah, dan karena itu tidak dapat ditriase oleh akun yang dibatasi
    wilayah. Menebak wilayahnya sama saja dengan mengarang lokasi.
    """
    new_status = _validated(DOMAIN_CITIZEN_STATUS, payload.status, "Status laporan")
    polsek = jurisdiction_filter(current, "citizen_report:write")

    query = (
        select(CitizenReport, Location)
        .outerjoin(Location, Location.location_id == CitizenReport.location_id)
        .where(CitizenReport.code == code)
    )
    if polsek is not None:
        query = query.where(Location.polsek == polsek)

    row = session.execute(query).first()
    if row is None:
        audit.record(
            session,
            action="UPDATE_CITIZEN_REPORT_STATUS",
            resource_type="citizen_report",
            result=audit.RESULT_FAILED,
            user_id=current.user.user_id,
            resource_id=code,
            detail={"reason": "laporan tidak dikenal atau di luar cakupan wilayah"},
        )
        session.commit()
        raise not_found()

    report: CitizenReport = row[0]
    location: Location | None = row[1]
    previous = report.status

    if previous == new_status:
        audit.record(
            session,
            action="UPDATE_CITIZEN_REPORT_STATUS",
            resource_type="citizen_report",
            result=audit.RESULT_FAILED,
            user_id=current.user.user_id,
            resource_id=report.code,
            detail={"reason": f"sudah berstatus {previous}"},
        )
        session.commit()
        raise ApiError(
            status.HTTP_409_CONFLICT,
            f"Laporan {report.code} sudah berstatus {_choices(DOMAIN_CITIZEN_STATUS)[previous]}.",
        )

    report.status = new_status

    detail: dict[str, Any] = {"status_before": previous, "status_after": new_status}
    if payload.note:
        detail["note"] = payload.note.strip()

    audit.record(
        session,
        action="UPDATE_CITIZEN_REPORT_STATUS",
        resource_type="citizen_report",
        result=audit.RESULT_SUCCESS,
        user_id=current.user.user_id,
        resource_id=report.code,
        detail=detail,
    )
    session.commit()
    session.refresh(report)

    return {
        "code": report.code,
        "status_before": previous,
        "status": report.status,
        "category": report.category,
        "kecamatan": location.kecamatan if location else None,
        "polsek": location.polsek if location else None,
        "verification_basis": VERIFICATION_BASIS,
        "transition_basis": TRANSITION_BASIS,
    }
