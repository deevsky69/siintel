"""Mesin penilaian risiko — menghitung `risk_scores` dari data yang benar-benar ada.

Yang dihasilkan modul ini adalah **penilaian risiko atas keadaan berjalan**, bukan
prediksi: ia menimbang jejak yang sudah tercatat pada satu sel grid, satu jenis ancaman,
dan satu jendela waktu. Tidak ada pernyataan tentang apa yang akan terjadi, tidak ada
`confidence`, dan tidak ada model terlatih — seluruh faktor dominan berlabel `RULE`
(CLAUDE.md §27).

Rancangannya: `docs/16-rancangan-risk-scoring.md`. Bobot: `config/risk/risk-weights.yaml`.
Ambang kelas: `config/risk/warning-thresholds.yaml`.

EMPAT BATAS YANG MENENTUKAN BENTUK MODUL INI

1. **Tidak ada satu pun bobot atau ambang di kode ini.** Keduanya dibaca dari
   `config/risk/`, dan versinya ikut dibawa keluar. Menyalin angkanya ke sini akan
   membuat baris skor tidak lagi dapat dikembalikan ke konfigurasi yang menghasilkannya
   (CLAUDE.md §11, §12; temuan audit S-04).

2. **Faktor yang tidak dapat dihitung bernilai `null`, bukan 0.** Nol berarti "diukur dan
   hasilnya nol" — sel yang benar-benar tidak memiliki kejadian jenis itu. `null` berarti
   "tidak ada dasar untuk mengukurnya", dan setiap `null` membawa alasannya. Menggantinya
   dengan 0 akan menurunkan skor secara diam-diam dan membuat sel tanpa data terbaca
   sebagai sel yang aman.

3. **Kombinasi dengan faktor berbobot yang `null` tidak diberi skor sama sekali.**
   Membagi ulang bobot ke faktor yang tersisa berarti mengarang bobot baru; melewatkan
   faktornya berarti menurunkan skor tertinggi yang mungkin dicapai tanpa ada yang
   menyadarinya — persis kegagalan yang diperingatkan `config/risk/risk-weights.yaml`.
   Karena itu barisnya dilaporkan sebagai **tidak dinilai** beserta alasannya.

4. **Normalisasi dilakukan terhadap data, bukan terhadap tabel angka yang dikarang.**
   Setiap faktor 0–100 diperoleh dengan membandingkan sel terhadap sel/lokasi terpadat
   pada jenis yang sama. Tidak ada satu pun daftar seperti "Pasar = 80, Permukiman = 40":
   daftar semacam itu belum ditetapkan siapa pun (U-16).
"""

from __future__ import annotations

import math
import uuid
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Any

import yaml
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from ..models import CitizenReport, CrimeIncident, IntelligenceReport, Location
from ..seeding.paths import REPO_ROOT
from . import clock

RISK_WEIGHTS_FILE = REPO_ROOT / "config" / "risk" / "risk-weights.yaml"
THRESHOLDS_FILE = REPO_ROOT / "config" / "risk" / "warning-thresholds.yaml"

#: Nama profil pada `risk-weights.yaml`.
PROFILE_HISTORICAL = "historical"
PROFILE_PLANNED = "planned"

#: Empat bin 6 jam yang dipakai seluruh dataset (docs/02 §21). Batas akhir 24 berarti
#: pukul 00.00 hari berikutnya — sesuai baris `risk_scores` yang sudah ada.
TIME_WINDOWS: dict[str, tuple[int, int]] = {
    "00:00-06:00": (0, 6),
    "06:00-12:00": (6, 12),
    "12:00-18:00": (12, 18),
    "18:00-23:59": (18, 24),
}

#: Satu hari penuh, dipakai membaca batas akhir jendela 24 sebagai pukul 00.00 esok hari.
HOURS_PER_DAY = 24

#: Panjang jendela "terkini" untuk `recent_trend_factor`, dihitung mundur dari waktu
#: acuan aplikasi (`clock.reference_now()`).
RECENT_DAYS = 30

#: Jarak hari yang masih dihitung sebagai pengulangan pada sel yang sama.
#:
#: Ini **parameter perhitungan**, bukan ambang risiko: ia menentukan apa yang disebut
#: "berulang", bukan kapan sebuah wilayah disebut rawan. Nilainya disebut terbuka pada
#: `spatial_factor` agar dapat diperdebatkan, dan tidak diambil dari config karena
#: config/risk/ memuat bobot dan ambang — bukan definisi pengukuran.
NEAR_REPEAT_WINDOW_DAYS = 14

#: Titik tengah skala `recent_trend_factor`: kejadian 30 hari terakhir yang sama banyak
#: dengan rata-rata periode 30 harian bernilai 50, dua kali lipat bernilai 100.
TREND_PARITY = 50

#: Status laporan intelijen yang boleh memengaruhi penilaian (docs/16 §3).
INTELLIGENCE_STATUSES = ("VERIFIED", "FOLLOWED_UP")

#: Status laporan masyarakat "VERIFIED ke atas" menurut urutan tahapan pada
#: `config/taxonomy/mappings.yaml` (Diterima → Diverifikasi → Diteruskan → Ditangani →
#: Selesai). `RECEIVED` sengaja tidak ikut: laporan yang belum diverifikasi tidak boleh
#: dianggap fakta (spesifikasi §4).
COMMUNITY_STATUSES = ("VERIFIED", "FORWARDED", "IN_PROGRESS", "CLOSED")

#: Kolom faktor yang benar-benar dapat disimpan pada tabel `risk_scores`
#: (migration 0005). Faktor di luar daftar ini dapat dihitung dan ditampilkan, tetapi
#: tidak dapat dipersistenkan tanpa migration baru.
PERSISTED_FACTORS = (
    "historical_factor",
    "recent_trend_factor",
    "temporal_factor",
    "spatial_factor",
    "context_factor",
)

FACTOR_BASIS: dict[str, str] = {
    "historical_factor": (
        "Jumlah kejadian jenis ini pada sel tersebut sepanjang rentang data, dinormalkan "
        "terhadap sel dengan kejadian terbanyak untuk jenis yang sama (sel terpadat = 100). "
        "Bernilai 0 bila sel benar-benar tidak memiliki kejadian jenis ini; null bila "
        "jenis ini tidak memiliki kejadian sama sekali sehingga tidak ada pembanding."
    ),
    "recent_trend_factor": (
        f"Kejadian {RECENT_DAYS} hari terakhir terhadap waktu acuan aplikasi, dibandingkan "
        f"rata-rata kejadian per {RECENT_DAYS} hari pada sel dan jenis yang sama sepanjang "
        f"rentang data. Sama dengan rata-rata bernilai {TREND_PARITY}, dua kali lipat atau "
        "lebih bernilai 100. Null bila sel tidak memiliki kejadian jenis ini sepanjang "
        "rentang data — tidak ada rata-rata yang dapat dijadikan pembanding."
    ),
    "temporal_factor": (
        "Proporsi kejadian jenis ini yang jatuh pada jendela waktu tersebut, dinormalkan "
        "terhadap jendela tersibuk jenis yang sama (jendela tersibuk = 100). Dihitung per "
        "jenis ancaman atas seluruh cakupan, bukan per sel: jumlah kejadian satu sel "
        "terlalu sedikit untuk membentuk pola jam. Jam diambil dari kolom incident_time "
        "(waktu setempat), bukan occurred_at (UTC) yang akan menggeser jam rawan tujuh jam."
    ),
    "spatial_factor": (
        "Rata-rata dua ukuran: (1) konsentrasi — porsi kejadian jenis ini di kecamatan yang "
        "jatuh pada sel tersebut, dinormalkan terhadap sel terpadat di kecamatan yang sama; "
        f"(2) pengulangan — banyaknya kejadian yang didahului kejadian lain pada sel dan "
        f"jenis yang sama dalam {NEAR_REPEAT_WINDOW_DAYS} hari, dinormalkan terhadap sel "
        "dengan pengulangan terbanyak. Ini pengulangan sederhana per sel, BUKAN analisis "
        "near-repeat spasial-temporal penuh pada docs/01 §5.4."
    ),
    "context_factor": (
        "Rata-rata kejadian jenis ini per sel untuk kategori TKP sel tersebut "
        "(locations.location_type), dinormalkan terhadap kategori TKP dengan rata-rata "
        "tertinggi pada jenis yang sama. Diturunkan dari data, BUKAN dari daftar bobot per "
        "jenis lokasi — daftar semacam itu belum ditetapkan siapa pun (U-16). Null bila "
        "kategori TKP sel tersebut kosong."
    ),
    "intelligence_factor": (
        f"Jumlah laporan intelijen berstatus {'/'.join(INTELLIGENCE_STATUSES)} yang menyebut "
        "sel tersebut, dinormalkan terhadap sel dengan laporan terbanyak. Tidak disaring "
        "per jenis ancaman: kategori laporan intelijen belum dipetakan ke taksonomi ancaman."
    ),
    "community_factor": (
        f"Jumlah laporan masyarakat berstatus {'/'.join(COMMUNITY_STATUSES)} pada sel "
        "tersebut, dinormalkan terhadap sel dengan laporan terbanyak. Laporan berstatus "
        "RECEIVED tidak ikut karena belum diverifikasi. Nilainya dihitung dan ditampilkan "
        "agar jalurnya terlihat, tetapi selama bobotnya nol ia TIDAK menyumbang apa pun "
        "pada skor."
    ),
}

SCORE_BASIS = (
    "risk_score = round(Sum(bobot x faktor)) dengan bobot dari config/risk/risk-weights.yaml "
    "versi aktif dan faktor 0-100 yang dihitung dari crime_incidents, intelligence_reports, "
    "citizen_reports, dan locations. Kelas risiko dibaca dari config/risk/warning-thresholds.yaml, "
    "tidak dihitung ulang di kode. Ini penilaian atas keadaan berjalan, BUKAN prediksi: tidak "
    "ada pernyataan tentang apa yang akan terjadi dan tidak ada model terlatih — seluruh faktor "
    "dominan berlabel RULE (CLAUDE.md §27)."
)

UNSCORED_BASIS = (
    "Kombinasi yang salah satu faktor berbobotnya tidak dapat dihitung TIDAK diberi skor. "
    "Membagi ulang bobot ke faktor yang tersisa berarti mengarang bobot baru, dan "
    "melewatkan faktornya menurunkan skor tertinggi yang mungkin dicapai tanpa terlihat."
)


class RiskEngineError(Exception):
    """Konfigurasi risiko tidak dapat dipakai menghitung apa pun."""


# ---------------------------------------------------------------------------
# Konfigurasi
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Profile:
    """Satu profil penilaian beserta bobot dan jenis ancaman yang dicakupnya."""

    name: str
    applies_to: tuple[str, ...]
    weights: dict[str, float]

    @property
    def positive_total(self) -> float:
        """Jumlah bobot **positif**. Inilah yang wajib bernilai 1 (docs/16 §4)."""
        return sum(value for value in self.weights.values() if value > 0)


@dataclass(frozen=True)
class WeightsVersion:
    version: str
    status: str
    profiles: dict[str, Profile]


@dataclass(frozen=True)
class WeightsCatalogue:
    active_version: str
    versions: dict[str, WeightsVersion]

    @property
    def active(self) -> WeightsVersion:
        return self.versions[self.active_version]


@dataclass(frozen=True)
class RiskBand:
    risk_class: str
    minimum: int
    maximum: int


@dataclass(frozen=True)
class Thresholds:
    version: str
    status: str
    bands: tuple[RiskBand, ...]

    def class_for(self, score: int) -> str:
        for band in self.bands:
            if band.minimum <= score <= band.maximum:
                return band.risk_class

        message = (
            f"skor {score} tidak masuk kelas mana pun pada "
            f"config/risk/warning-thresholds.yaml versi {self.version}"
        )
        raise RiskEngineError(message)


def load_weights() -> WeightsCatalogue:
    """Membaca seluruh versi bobot apa adanya dari `config/risk/risk-weights.yaml`.

    Seluruh versi dibaca, bukan hanya yang aktif: baris skor lama tetap merujuk versi
    lama, dan layar harus dapat menampilkan dasar keduanya.
    """
    if not RISK_WEIGHTS_FILE.exists():
        message = "config/risk/risk-weights.yaml tidak ditemukan"
        raise RiskEngineError(message)

    raw: dict[str, Any] = yaml.safe_load(RISK_WEIGHTS_FILE.read_text(encoding="utf-8"))
    active = str(raw["active_version"])
    versions: dict[str, WeightsVersion] = {}

    for name, body in raw["versions"].items():
        profiles = {
            profile_name: Profile(
                name=profile_name,
                applies_to=tuple(str(threat) for threat in profile["applies_to"]),
                weights={key: float(value) for key, value in profile["weights"].items()},
            )
            for profile_name, profile in body["profiles"].items()
        }
        versions[str(name)] = WeightsVersion(
            version=str(name), status=str(body.get("status", "UNKNOWN")), profiles=profiles
        )

    if active not in versions:
        message = f"active_version '{active}' tidak ada pada daftar versi"
        raise RiskEngineError(message)

    for version in versions.values():
        for profile in version.profiles.values():
            # Bobot positif yang tidak berjumlah 1 tidak menimbulkan kesalahan apa pun —
            # ia hanya menurunkan skor tertinggi yang mungkin dicapai, diam-diam.
            if abs(profile.positive_total - 1.0) > 1e-9:
                message = (
                    f"bobot positif profil '{version.version}/{profile.name}' berjumlah "
                    f"{profile.positive_total}, bukan 1"
                )
                raise RiskEngineError(message)

    return WeightsCatalogue(active_version=active, versions=versions)


def load_thresholds() -> Thresholds:
    """Membaca kelas risiko dari config. Ambang **tidak** dihitung ulang di kode."""
    if not THRESHOLDS_FILE.exists():
        message = "config/risk/warning-thresholds.yaml tidak ditemukan"
        raise RiskEngineError(message)

    catalogue: dict[str, Any] = yaml.safe_load(THRESHOLDS_FILE.read_text(encoding="utf-8"))
    # Ambang berversi sejak 1 September 2026: kelas risiko diambil dari versi yang
    # sedang berlaku, bukan dari tingkat atas berkas.
    raw: dict[str, Any] = catalogue["versions"][str(catalogue["active_version"])]
    bands = tuple(
        RiskBand(risk_class=str(band["class"]), minimum=int(band["min"]), maximum=int(band["max"]))
        for band in raw["risk_classes"]
    )
    if not bands:
        message = "config/risk/warning-thresholds.yaml tidak memuat satu pun kelas risiko"
        raise RiskEngineError(message)

    return Thresholds(
        version=str(catalogue["active_version"]), status=str(raw["status"]), bands=bands
    )


# ---------------------------------------------------------------------------
# Hasil penilaian
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Factor:
    """Satu faktor penyusun risiko.

    `value` bernilai `None` **hanya** bila faktornya tidak dapat diukur; alasannya wajib
    ikut. Faktor yang terukur bernilai nol tetap 0, bukan `None`.
    """

    name: str
    value: int | None
    weight: float | None
    reason: str | None = None

    @property
    def contribution(self) -> float:
        if self.value is None or self.weight is None:
            return 0.0
        return round(self.weight * self.value, 2)

    def as_dict(self) -> dict[str, Any]:
        return {
            "factor": self.name,
            "value": self.value,
            "weight": self.weight,
            "contribution": self.contribution,
            # Penjelasan berasal dari aturan yang benar-benar dijalankan, bukan dari
            # model — dan itu dinyatakan, bukan disamarkan (CLAUDE.md §27).
            "source": "RULE",
            "reason": self.reason,
            "basis": FACTOR_BASIS.get(self.name),
        }


@dataclass(frozen=True)
class CellAssessment:
    """Penilaian satu sel grid × jenis ancaman × jendela waktu."""

    location_id: uuid.UUID
    grid_id: str
    kecamatan: str
    kelurahan: str | None
    polsek: str
    location_type: str | None
    threat_type: str
    time_window: str
    window_start: datetime
    window_end: datetime
    factors: tuple[Factor, ...]
    risk_score: int | None
    risk_class: str | None
    unscored_reason: str | None

    @property
    def scored(self) -> bool:
        return self.risk_score is not None

    def dominant_factors(self) -> list[dict[str, Any]]:
        """Faktor terurut menurut sumbangannya — jawaban WHY."""
        return [
            factor.as_dict()
            for factor in sorted(self.factors, key=lambda item: item.contribution, reverse=True)
        ]

    def as_dict(self) -> dict[str, Any]:
        return {
            "grid_id": self.grid_id,
            "kecamatan": self.kecamatan,
            "kelurahan": self.kelurahan,
            "polsek": self.polsek,
            "location_type": self.location_type,
            "threat_type": self.threat_type,
            "time_window": self.time_window,
            "window_start": self.window_start,
            "window_end": self.window_end,
            "risk_score": self.risk_score,
            "risk_class": self.risk_class,
            "unscored_reason": self.unscored_reason,
            "factors": self.dominant_factors(),
        }


@dataclass(frozen=True)
class ProfileAssessment:
    """Hasil satu profil penilaian."""

    profile: str
    version: str
    weights: dict[str, float]
    threat_types: tuple[str, ...]
    cells: tuple[CellAssessment, ...]
    #: Alasan profil ini tidak menghasilkan apa pun. Kosong bila ia menghasilkan.
    not_computed_reason: str | None = None

    @property
    def scored(self) -> list[CellAssessment]:
        return [cell for cell in self.cells if cell.scored]

    @property
    def unscored(self) -> list[CellAssessment]:
        return [cell for cell in self.cells if not cell.scored]


@dataclass(frozen=True)
class Assessment:
    """Seluruh hasil satu kali penilaian."""

    assessment_date: date
    reference_time: datetime
    weights_version: str
    weights_status: str
    threshold_version: str
    threshold_status: str
    profiles: tuple[ProfileAssessment, ...]
    evidence_from: date | None
    evidence_to: date | None
    incidents_considered: int

    def profile(self, name: str) -> ProfileAssessment | None:
        return next((item for item in self.profiles if item.profile == name), None)


# ---------------------------------------------------------------------------
# Bahan penilaian — agregat dari database
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Cell:
    """Satu sel grid beserta wilayah dan kategori TKP-nya."""

    location_id: uuid.UUID
    grid_id: str
    kecamatan: str
    kelurahan: str | None
    polsek: str
    location_type: str | None


@dataclass
class Evidence:
    """Agregat yang dipakai seluruh faktor, diambil sekali dari database.

    Seluruh perhitungan berat dilakukan sebagai agregasi SQL; sisanya perbandingan
    biasa di Python. Tidak ada pustaka numerik yang dilibatkan.
    """

    cells: tuple[Cell, ...]
    incidents: dict[tuple[uuid.UUID, str], int]
    recent: dict[tuple[uuid.UUID, str], int]
    hours: dict[tuple[str, int], int]
    incident_days: dict[tuple[uuid.UUID, str], list[tuple[date, int]]]
    intelligence: dict[uuid.UUID, int]
    community: dict[uuid.UUID, int]
    date_from: date | None
    date_to: date | None
    total_incidents: int

    @property
    def span_days(self) -> int:
        if self.date_from is None or self.date_to is None:
            return 0
        return (self.date_to - self.date_from).days + 1


def _scoped(query: Select[Any], polsek: str | None) -> Select[Any]:
    return query if polsek is None else query.where(Location.polsek == polsek)


def collect_evidence(session: Session, polsek: str | None = None) -> Evidence:
    """Mengambil seluruh agregat yang dibutuhkan penilaian dalam beberapa query."""
    cells = tuple(
        Cell(
            location_id=row[0],
            grid_id=row[1],
            kecamatan=row[2],
            kelurahan=row[3],
            polsek=row[4],
            location_type=row[5],
        )
        for row in session.execute(
            _scoped(
                select(
                    Location.location_id,
                    Location.grid_id,
                    Location.kecamatan,
                    Location.kelurahan,
                    Location.polsek,
                    Location.location_type,
                ).order_by(Location.grid_id),
                polsek,
            )
        ).all()
    )

    incidents = {
        (row[0], row[1]): int(row[2])
        for row in session.execute(
            _scoped(
                select(CrimeIncident.location_id, CrimeIncident.incident_type, func.count())
                .join(Location, Location.location_id == CrimeIncident.location_id)
                .group_by(CrimeIncident.location_id, CrimeIncident.incident_type),
                polsek,
            )
        ).all()
    }

    since, now = clock.window(RECENT_DAYS * 24)
    recent = {
        (row[0], row[1]): int(row[2])
        for row in session.execute(
            _scoped(
                select(CrimeIncident.location_id, CrimeIncident.incident_type, func.count())
                .join(Location, Location.location_id == CrimeIncident.location_id)
                .where(CrimeIncident.occurred_at > since, CrimeIncident.occurred_at <= now)
                .group_by(CrimeIncident.location_id, CrimeIncident.incident_type),
                polsek,
            )
        ).all()
    }

    hours = {
        (str(row[0]), int(row[1])): int(row[2])
        for row in session.execute(
            _scoped(
                select(
                    CrimeIncident.incident_type,
                    func.extract("hour", CrimeIncident.incident_time),
                    func.count(),
                )
                .join(Location, Location.location_id == CrimeIncident.location_id)
                .group_by(
                    CrimeIncident.incident_type,
                    func.extract("hour", CrimeIncident.incident_time),
                ),
                polsek,
            )
        ).all()
    }

    incident_days: dict[tuple[uuid.UUID, str], list[tuple[date, int]]] = defaultdict(list)
    for row in session.execute(
        _scoped(
            select(
                CrimeIncident.location_id,
                CrimeIncident.incident_type,
                CrimeIncident.incident_date,
                func.count(),
            )
            .join(Location, Location.location_id == CrimeIncident.location_id)
            .group_by(
                CrimeIncident.location_id,
                CrimeIncident.incident_type,
                CrimeIncident.incident_date,
            )
            .order_by(CrimeIncident.location_id, CrimeIncident.incident_date),
            polsek,
        )
    ).all():
        incident_days[(row[0], row[1])].append((row[2], int(row[3])))

    intelligence = {
        row[0]: int(row[1])
        for row in session.execute(
            _scoped(
                select(IntelligenceReport.location_id, func.count())
                .join(Location, Location.location_id == IntelligenceReport.location_id)
                .where(IntelligenceReport.status.in_(INTELLIGENCE_STATUSES))
                .group_by(IntelligenceReport.location_id),
                polsek,
            )
        ).all()
    }

    community = {
        row[0]: int(row[1])
        for row in session.execute(
            _scoped(
                select(CitizenReport.location_id, func.count())
                .join(Location, Location.location_id == CitizenReport.location_id)
                .where(CitizenReport.status.in_(COMMUNITY_STATUSES))
                .group_by(CitizenReport.location_id),
                polsek,
            )
        ).all()
    }

    span = session.execute(
        _scoped(
            select(
                func.min(CrimeIncident.incident_date),
                func.max(CrimeIncident.incident_date),
                func.count(),
            ).join(Location, Location.location_id == CrimeIncident.location_id),
            polsek,
        )
    ).one()

    return Evidence(
        cells=cells,
        incidents=incidents,
        recent=recent,
        hours=hours,
        incident_days=dict(incident_days),
        intelligence=intelligence,
        community=community,
        date_from=span[0],
        date_to=span[1],
        total_incidents=int(span[2] or 0),
    )


# ---------------------------------------------------------------------------
# Perhitungan faktor
# ---------------------------------------------------------------------------


def _normalise(value: float, highest: float) -> int:
    """Nilai 0–100 terhadap nilai tertinggi. Pemanggil memastikan `highest > 0`."""
    return max(0, min(100, round(100 * value / highest)))


def repeat_events(days: list[tuple[date, int]]) -> int:
    """Banyaknya kejadian yang didahului kejadian lain pada sel & jenis yang sama.

    Kejadian pada hari yang sama dihitung sebagai pengulangan (jarak nol hari); kejadian
    pertama pada suatu hari dihitung bila ada hari sebelumnya dalam jendela pengulangan.
    """
    total = 0
    previous: date | None = None

    for day, count in sorted(days):
        # Kejadian kedua dan seterusnya pada hari yang sama selalu berulang.
        total += count - 1
        if previous is not None and (day - previous).days <= NEAR_REPEAT_WINDOW_DAYS:
            total += 1
        previous = day

    return total


@dataclass(frozen=True)
class _Derived:
    """Nilai pembanding yang dihitung sekali untuk seluruh sel."""

    busiest_cell: dict[str, int]
    kecamatan_total: dict[tuple[str, str], int]
    kecamatan_busiest_cell: dict[tuple[str, str], int]
    repeats: dict[tuple[uuid.UUID, str], int]
    busiest_repeat: dict[str, int]
    window_share: dict[tuple[str, str], float]
    busiest_window_share: dict[str, float]
    context_mean: dict[tuple[str, str], float]
    busiest_context: dict[str, float]
    busiest_intelligence: int
    busiest_community: int


def _derive(evidence: Evidence, threat_types: tuple[str, ...]) -> _Derived:
    cell_of = {cell.location_id: cell for cell in evidence.cells}

    busiest_cell: dict[str, int] = defaultdict(int)
    kecamatan_total: dict[tuple[str, str], int] = defaultdict(int)
    kecamatan_busiest_cell: dict[tuple[str, str], int] = defaultdict(int)
    type_of_location: dict[tuple[str, str], int] = defaultdict(int)

    for (location_id, threat), count in evidence.incidents.items():
        cell = cell_of.get(location_id)
        if cell is None:
            continue
        busiest_cell[threat] = max(busiest_cell[threat], count)
        kecamatan_total[(cell.kecamatan, threat)] += count
        kecamatan_busiest_cell[(cell.kecamatan, threat)] = max(
            kecamatan_busiest_cell[(cell.kecamatan, threat)], count
        )
        if cell.location_type is not None:
            type_of_location[(cell.location_type, threat)] += count

    repeats = {
        key: repeat_events(days)
        for key, days in evidence.incident_days.items()
        if key[0] in cell_of
    }
    busiest_repeat: dict[str, int] = defaultdict(int)
    for (_location_id, threat), count in repeats.items():
        busiest_repeat[threat] = max(busiest_repeat[threat], count)

    # Porsi jendela waktu per jenis ancaman.
    window_share: dict[tuple[str, str], float] = {}
    busiest_window_share: dict[str, float] = defaultdict(float)
    for threat in threat_types:
        total = sum(count for (kind, _hour), count in evidence.hours.items() if kind == threat)
        if total == 0:
            continue
        for label, (start, end) in TIME_WINDOWS.items():
            inside = sum(
                count
                for (kind, hour), count in evidence.hours.items()
                if kind == threat and start <= hour < end
            )
            share = inside / total
            window_share[(threat, label)] = share
            busiest_window_share[threat] = max(busiest_window_share[threat], share)

    # Rata-rata kejadian per sel untuk setiap kategori TKP.
    cells_per_type: dict[str, int] = defaultdict(int)
    for cell in evidence.cells:
        if cell.location_type is not None:
            cells_per_type[cell.location_type] += 1

    context_mean: dict[tuple[str, str], float] = {}
    busiest_context: dict[str, float] = defaultdict(float)
    for location_type, cell_count in cells_per_type.items():
        for threat in threat_types:
            mean = type_of_location[(location_type, threat)] / cell_count
            context_mean[(location_type, threat)] = mean
            busiest_context[threat] = max(busiest_context[threat], mean)

    return _Derived(
        busiest_cell=dict(busiest_cell),
        kecamatan_total=dict(kecamatan_total),
        kecamatan_busiest_cell=dict(kecamatan_busiest_cell),
        repeats=repeats,
        busiest_repeat=dict(busiest_repeat),
        window_share=window_share,
        busiest_window_share=dict(busiest_window_share),
        context_mean=context_mean,
        busiest_context=dict(busiest_context),
        busiest_intelligence=max(evidence.intelligence.values(), default=0),
        busiest_community=max(evidence.community.values(), default=0),
    )


def _historical(cell: Cell, threat: str, evidence: Evidence, derived: _Derived) -> int | None:
    highest = derived.busiest_cell.get(threat, 0)
    if highest <= 0:
        return None
    return _normalise(evidence.incidents.get((cell.location_id, threat), 0), highest)


def _recent_trend(cell: Cell, threat: str, evidence: Evidence, _derived: _Derived) -> int | None:
    total = evidence.incidents.get((cell.location_id, threat), 0)
    if total == 0 or evidence.span_days <= 0:
        return None

    expected = total * RECENT_DAYS / evidence.span_days
    if expected <= 0:
        return None

    ratio = evidence.recent.get((cell.location_id, threat), 0) / expected
    return max(0, min(100, round(TREND_PARITY * ratio)))


def _temporal(threat: str, window: str, derived: _Derived) -> int | None:
    highest = derived.busiest_window_share.get(threat, 0.0)
    share = derived.window_share.get((threat, window))
    if share is None or highest <= 0:
        return None
    return _normalise(share, highest)


def _spatial(cell: Cell, threat: str, evidence: Evidence, derived: _Derived) -> int | None:
    parts: list[int] = []

    kecamatan_top = derived.kecamatan_busiest_cell.get((cell.kecamatan, threat), 0)
    if kecamatan_top > 0:
        parts.append(
            _normalise(evidence.incidents.get((cell.location_id, threat), 0), kecamatan_top)
        )

    repeat_top = derived.busiest_repeat.get(threat, 0)
    if repeat_top > 0:
        parts.append(_normalise(derived.repeats.get((cell.location_id, threat), 0), repeat_top))

    if not parts:
        return None
    return round(sum(parts) / len(parts))


def _context(cell: Cell, threat: str, derived: _Derived) -> int | None:
    if cell.location_type is None:
        return None

    highest = derived.busiest_context.get(threat, 0.0)
    mean = derived.context_mean.get((cell.location_type, threat))
    if mean is None or highest <= 0:
        return None
    return _normalise(mean, highest)


def _intelligence(cell: Cell, evidence: Evidence, derived: _Derived) -> int | None:
    if derived.busiest_intelligence <= 0:
        return None
    return _normalise(evidence.intelligence.get(cell.location_id, 0), derived.busiest_intelligence)


def _community(cell: Cell, evidence: Evidence, derived: _Derived) -> int | None:
    if derived.busiest_community <= 0:
        return None
    return _normalise(evidence.community.get(cell.location_id, 0), derived.busiest_community)


#: Alasan baku ketika sebuah faktor tidak dapat dihitung. Dipakai apa adanya pada
#: respons API supaya pembaca tahu **mengapa** angkanya tidak ada.
_MISSING_REASON: dict[str, str] = {
    "historical_factor": (
        "tidak ada satu pun kejadian jenis ini pada cakupan data, sehingga tidak ada sel "
        "pembanding untuk normalisasi"
    ),
    "recent_trend_factor": (
        "sel ini tidak memiliki kejadian jenis ini sepanjang rentang data, sehingga tidak "
        "ada rata-rata periode yang dapat dijadikan pembanding"
    ),
    "temporal_factor": (
        "tidak ada kejadian jenis ini yang tercatat jamnya, sehingga sebaran jendela waktu "
        "tidak dapat dihitung"
    ),
    "spatial_factor": (
        "kecamatan ini tidak memiliki kejadian jenis ini dan tidak ada pengulangan yang "
        "dapat dibandingkan"
    ),
    "context_factor": (
        "locations.location_type sel ini kosong, sehingga tidak ada kategori TKP yang dapat "
        "dijadikan dasar"
    ),
    "intelligence_factor": (
        f"tidak ada laporan intelijen berstatus {'/'.join(INTELLIGENCE_STATUSES)} pada cakupan ini"
    ),
    "community_factor": (
        f"tidak ada laporan masyarakat berstatus {'/'.join(COMMUNITY_STATUSES)} pada cakupan ini"
    ),
}


def _window_bounds(assessment_date: date, window: str) -> tuple[datetime, datetime]:
    """Batas jendela dalam WIB, sepadan dengan baris `risk_scores` yang sudah ada."""
    start_hour, end_hour = TIME_WINDOWS[window]
    start = datetime.combine(assessment_date, time(hour=start_hour), tzinfo=clock.JAKARTA)
    if end_hour >= HOURS_PER_DAY:
        end = datetime.combine(
            assessment_date + timedelta(days=1), time(hour=0), tzinfo=clock.JAKARTA
        )
    else:
        end = datetime.combine(assessment_date, time(hour=end_hour), tzinfo=clock.JAKARTA)
    return start, end


def assess_historical(
    evidence: Evidence,
    profile: Profile,
    thresholds: Thresholds,
    assessment_date: date,
    version: str,
) -> ProfileAssessment:
    """Menilai seluruh sel × jenis ancaman × jendela waktu menurut Profil A."""
    derived = _derive(evidence, profile.applies_to)
    cells: list[CellAssessment] = []

    for cell in evidence.cells:
        for threat in profile.applies_to:
            values: dict[str, int | None] = {
                "historical_factor": _historical(cell, threat, evidence, derived),
                "recent_trend_factor": _recent_trend(cell, threat, evidence, derived),
                "spatial_factor": _spatial(cell, threat, evidence, derived),
                "context_factor": _context(cell, threat, derived),
                "intelligence_factor": _intelligence(cell, evidence, derived),
                "community_factor": _community(cell, evidence, derived),
            }

            for window in TIME_WINDOWS:
                window_values = dict(values)
                window_values["temporal_factor"] = _temporal(threat, window, derived)

                factors = tuple(
                    Factor(
                        name=name,
                        value=value,
                        weight=profile.weights.get(name),
                        reason=None if value is not None else _MISSING_REASON.get(name),
                    )
                    for name, value in window_values.items()
                )
                score, reason = score_of(factors, profile.weights)
                start, end = _window_bounds(assessment_date, window)

                cells.append(
                    CellAssessment(
                        location_id=cell.location_id,
                        grid_id=cell.grid_id,
                        kecamatan=cell.kecamatan,
                        kelurahan=cell.kelurahan,
                        polsek=cell.polsek,
                        location_type=cell.location_type,
                        threat_type=threat,
                        time_window=window,
                        window_start=start,
                        window_end=end,
                        factors=factors,
                        risk_score=score,
                        risk_class=None if score is None else thresholds.class_for(score),
                        unscored_reason=reason,
                    )
                )

    return ProfileAssessment(
        profile=profile.name,
        version=version,
        weights=dict(profile.weights),
        threat_types=profile.applies_to,
        cells=tuple(cells),
    )


def _rounded(terms: Iterable[tuple[float, int | None]]) -> int:
    """`round(Sum(bobot x faktor))` yang menghasilkan angka **yang sama bagi pemeriksanya**.

    Dua hal yang tampak sepele tetapi menentukan apakah skor tersimpan dapat dihitung
    ulang oleh orang lain:

    1. **Penjumlahan memakai `sum()`, bukan penambahan bertahap.** `sum()` mengompensasi
       galat pembulatan float. Penambahan bertahap menghasilkan 46,500000000000004 di
       tempat yang seharusnya 46,5 — dan angka tersimpan menjadi 47 padahal siapa pun
       yang memeriksanya memperoleh 46.

    2. **Nilai tepat 0,5 dibulatkan menjauhi nol, bukan ke bilangan genap.** `round()`
       bawaan Python membulatkan 18,5 menjadi 18. PostgreSQL, papan hitung, dan lembar
       kerja membulatkannya menjadi 19 — dan itulah alat yang dipakai orang untuk
       memeriksa. Perbedaannya nyata: 23 dari 656 baris pada percobaan pertama tampak
       meleset satu angka hanya karena hal ini, sementara 2019 baris dummy yang sudah ada
       lolos pemeriksaan SQL yang sama.

    Galat float dibuang lebih dahulu (9 desimal) supaya 18,499999999999996 tidak terbaca
    sebagai bukan-seri.
    """
    total = round(sum(weight * value for weight, value in terms if value is not None), 9)
    return math.floor(total + 0.5) if total >= 0 else -math.floor(-total + 0.5)


def score_of(
    factors: tuple[Factor, ...], weights: dict[str, float]
) -> tuple[int | None, str | None]:
    """`round(Sum(bobot x faktor))`, atau `None` beserta alasan bila tidak dapat dihitung.

    Faktor berbobot yang tidak terukur membuat seluruh kombinasi tidak dinilai. Lihat
    `UNSCORED_BASIS`: alternatifnya adalah mengarang bobot atau menurunkan skor tertinggi
    secara diam-diam.
    """
    measured = {factor.name: factor for factor in factors}

    unknown = sorted(name for name in weights if name not in measured)
    if unknown:
        return None, (
            f"mesin penilaian belum menghitung faktor {', '.join(unknown)} yang diberi bobot "
            f"pada versi aktif"
        )

    missing = sorted(
        name for name, weight in weights.items() if weight != 0 and measured[name].value is None
    )
    if missing:
        reasons = "; ".join(f"{name}: {measured[name].reason}" for name in missing)
        return None, f"faktor berbobot tidak dapat dihitung — {reasons}"

    return _rounded((weight, measured[name].value) for name, weight in weights.items()), None


def planned_score(factors: dict[str, int | None], weights: dict[str, float]) -> int | None:
    """Aritmetika Profil B: bobot positif berjumlah 1, `readiness_factor` mengurangi.

    ```text
    dasar      = Sum( bobot_positif x faktor )
    risk_score = round( clamp( dasar + bobot_negatif x faktor, 0, 100 ) )
    ```

    Dipisahkan dari pengambilan data supaya rumusnya dapat diuji tanpa mengarang satu pun
    baris unjuk rasa (`tests/test_risk_engine.py`).

    Mengembalikan `None` bila ada faktor berbobot yang tidak terukur — alasan yang sama
    dengan Profil A: membagi ulang bobot berarti mengarang bobot baru.
    """
    for name, weight in weights.items():
        if weight != 0 and factors.get(name) is None:
            return None

    total = _rounded((weight, factors.get(name)) for name, weight in weights.items())
    return max(0, min(100, total))


def assess_planned(
    session: Session,
    catalogue: WeightsCatalogue,
    polsek: str | None = None,
) -> ProfileAssessment:
    """Profil B — gangguan terencana. Saat ini **tidak menghasilkan apa pun**, dengan alasan.

    Profil B menilai perkiraan dampak sebuah kegiatan yang **direncanakan dan diketahui
    sebelum terjadi**. Satuan penilaiannya bukan sel grid melainkan satu rencana kegiatan:
    kapan, di mana, oleh siapa, dan diperkirakan berapa massanya.

    Model data belum menyimpan rencana kegiatan sama sekali. `intelligence_reports` memuat
    kategori, keandalan, urgensi, dan status — tetapi tidak memuat waktu rencana, sasaran
    lokasi kegiatan, maupun perkiraan jumlah massa. Mengarang ketiganya berarti membuat
    data unjuk rasa yang tidak pernah ada (CLAUDE.md §17), jadi profil ini mengembalikan
    hasil kosong beserta keterangan — bukan angka.
    """
    profile = catalogue.active.profiles.get(PROFILE_PLANNED)
    if profile is None:
        elsewhere = sorted(
            version.version
            for version in catalogue.versions.values()
            if PROFILE_PLANNED in version.profiles
        )
        note = f" Profil ini ada pada versi {', '.join(elsewhere)}." if elsewhere else ""
        return ProfileAssessment(
            profile=PROFILE_PLANNED,
            version=catalogue.active_version,
            weights={},
            threat_types=(),
            cells=(),
            not_computed_reason=(
                f"versi bobot aktif '{catalogue.active_version}' tidak memiliki profil "
                f"'{PROFILE_PLANNED}', sehingga tidak ada rumus yang berlaku untuk gangguan "
                f"terencana.{note}"
            ),
        )

    recorded = (
        session.scalar(
            _scoped(
                select(func.count())
                .select_from(CrimeIncident)
                .join(Location, Location.location_id == CrimeIncident.location_id)
                .where(CrimeIncident.incident_type.in_(profile.applies_to)),
                polsek,
            )
        )
        or 0
    )

    return ProfileAssessment(
        profile=profile.name,
        version=catalogue.active_version,
        weights=dict(profile.weights),
        threat_types=profile.applies_to,
        cells=(),
        not_computed_reason=(
            "Profil ini menilai perkiraan dampak satu kegiatan yang direncanakan, dan "
            "satuan penilaiannya adalah rencana kegiatan — bukan sel grid. Model data belum "
            "menyimpannya: intelligence_reports tidak memiliki kolom waktu rencana, lokasi "
            "sasaran kegiatan, maupun perkiraan jumlah massa, sehingga mass_estimate_factor "
            "dan source_reliability_factor tidak memiliki masukan. Jenis "
            f"{', '.join(profile.applies_to)} tercatat {int(recorded)} kejadian pada "
            "crime_incidents. Rumusnya sudah diimplementasikan (planned_score) dan diuji, "
            "tetapi tidak dijalankan atas data yang tidak ada."
        ),
    )


def assess(
    session: Session,
    assessment_date: date,
    polsek: str | None = None,
) -> Assessment:
    """Menjalankan seluruh profil pada versi bobot aktif untuk satu tanggal penilaian."""
    catalogue = load_weights()
    thresholds = load_thresholds()
    evidence = collect_evidence(session, polsek)

    profiles: list[ProfileAssessment] = []

    historical = catalogue.active.profiles.get(PROFILE_HISTORICAL)
    if historical is not None:
        profiles.append(
            assess_historical(
                evidence, historical, thresholds, assessment_date, catalogue.active_version
            )
        )

    profiles.append(assess_planned(session, catalogue, polsek))

    return Assessment(
        assessment_date=assessment_date,
        reference_time=clock.reference_now(),
        weights_version=catalogue.active_version,
        weights_status=catalogue.active.status,
        threshold_version=thresholds.version,
        threshold_status=thresholds.status,
        profiles=tuple(profiles),
        evidence_from=evidence.date_from,
        evidence_to=evidence.date_to,
        incidents_considered=evidence.total_incidents,
    )
