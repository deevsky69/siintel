"""Mesin prediksi — memproyeksikan `risk_scores` yang sudah ada ke jendela waktu ke depan.

Modul ini **bukan** machine learning. Tidak ada model yang dilatih, tidak ada fitur yang
dipelajari, dan tidak ada bobot yang diperoleh dari data latih. Yang dikerjakan di sini
adalah **proyeksi persistensi**: risiko sebuah sel pada sebuah jendela waktu ke depan
diperkirakan sama dengan penilaian risiko terakhir untuk sel, jenis ancaman, dan label
jendela yang sama. `model_version` karena itu menyebut versi **aturan**
(`rule-persistence-v1`), bukan nama model, dan seluruh `dominant_factors` berlabel `RULE`
(CLAUDE.md §25, §27).

Bentuknya sengaja mengikuti `services/risk_engine.py`: konfigurasi dibaca dari
`config/risk/`, setiap angka turunan membawa `*_basis`, dan kombinasi yang tidak dapat
diproyeksikan dilaporkan beserta alasannya — bukan diisi tebakan.

EMPAT BATAS YANG MENENTUKAN BENTUK MODUL INI

1. **Tidak ada satu pun koefisien baru.** Skor prediksi sama persis dengan skor penilaian
   yang menjadi dasarnya, dan `baseline_risk_score_id` menunjuk baris itu. Penyesuaian
   terhadap pola temporal dilakukan dengan **memilih baris penilaian pada label jendela
   yang sama**, bukan dengan mengalikan angka dengan faktor yang dikarang. Mengalikan
   akan memerlukan koefisien yang belum ditetapkan siapa pun (CLAUDE.md §11).

2. **Kombinasi tanpa dasar tidak diprediksi.** Sel × jenis × jendela yang tidak memiliki
   satu pun baris `risk_scores` pada label jendela yang sama dilaporkan sebagai tidak
   diprediksi beserta alasannya. Menyalin skor dari jendela lain berarti mengarang
   penyesuaian temporal yang tidak pernah dihitung.

3. **`confidence` mengukur ketebalan bukti, bukan peluang kejadian.** Nilainya berasal
   dari banyaknya kejadian historis yang menopang sel dan jendela itu, dinormalkan
   terhadap kombinasi terpadat. Dasar tipis menghasilkan angka rendah, dan alasannya
   ikut pada setiap baris.

4. **Prediksi tidak diberi kelas risiko sama sekali.** Keputusan pemilik proyek
   9 September 2026: prediksi tetap skor mentah. Sampai hari itu mesin ini memberi tiap
   prediksi kelas hasil `thresholds.class_for(...)`, sehingga layar Prediction Center
   menampilkan "95 CRITICAL" di sebelah skor — tangga yang ditetapkan bagi PENILAIAN
   keadaan berjalan dipinjamkan kepada PERKIRAAN, dan perkiraan terbaca sebagai keadaan.
   Kelas penilaian dasarnya tetap terbawa sebagai `baseline_risk_class`, dengan nama yang
   menyebut milik siapa kelas itu.

   Versi ambang tetap dicatat pada tiap putaran (`threshold_version`), karena ambang itulah
   yang menentukan apakah sebuah prediksi kelak melahirkan peringatan.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from ..models import CrimeIncident, Location, RiskScore
from ..models.prediction import FORECAST_HORIZONS
from . import clock
from . import risk_engine as risk

#: Versi **aturan** proyeksi, bukan nama model. Disimpan pada `predictions.model_version`
#: supaya setiap baris dapat dikembalikan ke aturan yang menghasilkannya.
RULE_VERSION = "rule-persistence-v1"

#: Status prediksi. Hanya `PUBLISHED` yang boleh melahirkan peringatan — itulah sebabnya
#: publikasi adalah tindakan tersendiri, bukan efek samping menjalankan prediksi.
STATUS_DRAFT = "DRAFT"
STATUS_PUBLISHED = "PUBLISHED"
STATUS_VALIDATED = "VALIDATED"

#: JARAK dari `prediction_date` ke jendela yang diprediksi — bukan panjang rentang yang
#: dicakup (`predictions.forecast_horizon`, docs/02 §10).
#:
#: Pembacaan ini diambil dari data yang sudah ada, bukan dari dokumen saja: pada 180
#: prediksi seed, panjang jendela SELALU 6 jam berapa pun horizonnya, sedangkan jarak dari
#: `prediction_date` ke `window_start` bertambah mengikuti horizon. Lihat
#: `test_horizon_matches_the_predictions_already_in_the_database`, yang mengunci
#: pembacaan ini terhadap baris-baris itu.
HORIZON_OFFSETS: dict[str, timedelta] = {
    "6H": timedelta(hours=6),
    "12H": timedelta(hours=12),
    "24H": timedelta(hours=24),
    "3D": timedelta(days=3),
    "7D": timedelta(days=7),
}

HORIZON_BASIS = (
    "Horizon adalah JARAK dari prediction_date ke hari yang diprediksi, bukan panjang "
    "rentang yang dicakup. Hari sasaran = prediction_date + horizon dibulatkan ke bawah ke "
    "hari penuh: 6H dan 12H jatuh pada hari prediksi itu sendiri (jarak 0 hari), 24H pada "
    "H+1, 3D pada H+3, dan 7D pada H+7. Untuk hari sasaran itu diprediksi keempat bin 6 "
    "jam, sehingga satu prediksi selalu mencakup TEPAT SATU jendela 6 jam dan satu kali "
    "penjalanan menghasilkan jumlah baris yang sama untuk setiap horizon. "
    "Pembacaan ini cocok dengan 180 prediksi yang sudah ada di basis data. "
    "KETERBATASAN YANG DINYATAKAN TERBUKA: karena prediction_date bertipe DATE, 6H dan 12H "
    "sama-sama berjarak 0 hari dan karena itu menghasilkan jendela yang sama persis — "
    "keduanya juga tidak terbedakan pada data seed. Membedakannya menuntut jam pembuatan "
    "prediksi, bukan hanya tanggalnya, dan itu perubahan model data."
)

PROJECTION_BASIS = (
    "risk_score prediksi = risk_score baris risk_scores TERAKHIR (assessment_date <= "
    "prediction_date) untuk sel, jenis ancaman, dan LABEL jendela waktu yang sama. Tidak "
    "ada koefisien baru: penyesuaian terhadap pola temporal dilakukan dengan memilih baris "
    "penilaian pada jendela yang sama, bukan dengan mengalikan angka. Ini proyeksi "
    "persistensi berbasis aturan — BUKAN model terlatih; tidak ada pelatihan, tidak ada "
    "fitur yang dipelajari, dan tidak ada evaluasi model di baliknya. "
    "baseline_risk_score_id menunjuk baris yang dipakai, sehingga skor prediksi dapat "
    "ditelusuri sampai ke versi bobot yang menghasilkannya."
)

CONFIDENCE_BASIS = (
    "confidence = round(100 x kejadian jenis ini pada sel DAN jendela ini / kejadian "
    "terbanyak pada kombinasi jenis+jendela yang sama di seluruh cakupan). Yang diukur "
    "adalah KETEBALAN BUKTI yang menopang perkiraan, bukan peluang kejadian. Dasar yang "
    "tipis menghasilkan angka rendah, dan alasannya dibawa pada setiap baris. "
    "Confidence TIDAK diturunkan oleh panjang horizon: koefisien peluruhan semacam itu "
    "belum ditetapkan siapa pun dan mengarangnya dilarang (CLAUDE.md §11) — ini "
    "keterbatasan yang dinyatakan terbuka, bukan disembunyikan."
)

NOT_PREDICTED_BASIS = (
    "Kombinasi yang tidak memiliki baris risk_scores pada label jendela yang sama TIDAK "
    "diprediksi. Menyalin skor dari jendela lain berarti mengarang penyesuaian temporal "
    "yang tidak pernah dihitung, dan barisnya akan tampak lengkap tanpa dapat menjelaskan "
    "dirinya sendiri."
)

MODEL_DISCLAIMER = (
    "Tidak ada model terlatih di balik angka ini. model_version berisi versi ATURAN "
    f"('{RULE_VERSION}'), bukan nama model, dan seluruh dominant_factors berlabel RULE "
    "(CLAUDE.md §25, §27)."
)

PUBLICATION_BASIS = (
    "Prediksi baru berstatus DRAFT. Hanya prediksi PUBLISHED yang boleh melahirkan "
    "peringatan dini — karena itu publikasi adalah tindakan tersendiri dengan kewenangan "
    "sendiri (prediction:publish), bukan efek samping menjalankan prediksi."
)

#: Nama faktor yang membawa dasar `confidence` pada `dominant_factors`.
#:
#: Tabel `predictions` tidak memiliki kolom untuk dasar confidence, sedangkan angka
#: turunan tanpa dasar tidak dapat diperiksa siapa pun. Entri ini menyimpannya di dalam
#: JSONB yang sudah ada, dengan `contribution` nol karena ia **tidak** menyumbang pada
#: risk_score. Menambah kolom tersendiri memerlukan migration dan persetujuan pemilik
#: proyek.
CONFIDENCE_FACTOR = "confidence_support"


class PredictionEngineError(Exception):
    """Prediksi tidak dapat dihitung sama sekali."""


# ---------------------------------------------------------------------------
# Hasil proyeksi
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Baseline:
    """Baris `risk_scores` yang menjadi dasar satu prediksi."""

    risk_score_id: uuid.UUID
    code: str
    assessment_date: date
    risk_score: int
    risk_class: str
    weights_version: str | None
    factors: dict[str, int | None]


@dataclass(frozen=True)
class Forecast:
    """Satu prediksi: sel grid × jenis ancaman × jendela waktu, pada satu horizon."""

    location_id: uuid.UUID
    grid_id: str
    kecamatan: str
    kelurahan: str | None
    polsek: str
    threat_type: str
    time_window: str
    window_start: datetime
    window_end: datetime
    baseline: Baseline | None
    risk_score: int | None
    # TIDAK ADA `risk_class` di sini, dan itu keputusan pemilik proyek 9 September 2026:
    # prediksi tetap skor mentah. Tangga kelas ditetapkan hari yang sama (U-01) bagi
    # PENILAIAN keadaan berjalan; skor prediksi 80 tidak menyatakan hal yang sama dengan
    # skor penilaian 80, dan satu tangga untuk keduanya membuat perkiraan terbaca sebagai
    # keadaan. Kelas penilaian dasarnya tetap dapat dicapai lewat `baseline.risk_class` —
    # ia fakta tentang baris `risk_scores`, bukan label atas prediksi ini.
    confidence: int | None
    confidence_reason: str
    supporting_incidents: int
    dominant_factors: tuple[dict[str, Any], ...]
    not_predicted_reason: str | None

    @property
    def predicted(self) -> bool:
        return self.risk_score is not None

    @property
    def baseline_age_days(self) -> int | None:
        """Umur penilaian dasar terhadap hari yang diprediksi, dalam hari."""
        if self.baseline is None:
            return None
        return (self.window_start.date() - self.baseline.assessment_date).days

    def as_dict(self) -> dict[str, Any]:
        return {
            "grid_id": self.grid_id,
            "kecamatan": self.kecamatan,
            "kelurahan": self.kelurahan,
            "polsek": self.polsek,
            "threat_type": self.threat_type,
            "time_window": self.time_window,
            "window_start": self.window_start,
            "window_end": self.window_end,
            "risk_score": self.risk_score,
            # Namanya menyebut MILIK SIAPA kelas itu. `risk_class` di sebelah `risk_score`
            # pada baris prediksi terbaca sebagai kelas prediksi itu sendiri, dan itulah
            # yang tidak boleh.
            "baseline_risk_class": None if self.baseline is None else self.baseline.risk_class,
            "confidence": self.confidence,
            "confidence_reason": self.confidence_reason,
            "supporting_incidents": self.supporting_incidents,
            "baseline_code": None if self.baseline is None else self.baseline.code,
            "baseline_assessment_date": (
                None if self.baseline is None else self.baseline.assessment_date
            ),
            "baseline_age_days": self.baseline_age_days,
            "weights_version": None if self.baseline is None else self.baseline.weights_version,
            "dominant_factors": list(self.dominant_factors),
            "not_predicted_reason": self.not_predicted_reason,
        }


@dataclass(frozen=True)
class Projection:
    """Seluruh hasil satu kali penjalanan prediksi."""

    prediction_date: date
    horizon: str
    #: Hari yang diprediksi = prediction_date + jarak horizon (HORIZON_BASIS).
    target_date: date
    #: Batas terluar keempat jendela pada hari sasaran.
    window_from: datetime
    window_to: datetime
    time_windows: tuple[str, ...]
    reference_time: datetime
    rule_version: str
    weights_versions: tuple[str, ...]
    threshold_version: str
    threshold_status: str
    threat_types: tuple[str, ...]
    forecasts: tuple[Forecast, ...]
    evidence_from: date | None
    evidence_to: date | None
    incidents_considered: int
    not_computed_reason: str | None = None

    @property
    def predicted(self) -> list[Forecast]:
        return [item for item in self.forecasts if item.predicted]

    @property
    def not_predicted(self) -> list[Forecast]:
        return [item for item in self.forecasts if not item.predicted]


# ---------------------------------------------------------------------------
# Jendela yang diprediksi
# ---------------------------------------------------------------------------


def horizon_day_offset(horizon: str) -> int:
    """Jarak `prediction_date` → hari sasaran, dalam hari penuh. Lihat `HORIZON_BASIS`.

    Dipisahkan agar dapat diuji sendiri: inilah satu-satunya tempat horizon diterjemahkan
    menjadi jarak, dan salah membacanya sebagai panjang rentang akan menggandakan seluruh
    keluaran tanpa ada yang menyadarinya.
    """
    offset = HORIZON_OFFSETS.get(horizon)
    if offset is None:
        message = (
            f"horizon '{horizon}' tidak dikenal; yang tersedia "
            f"{', '.join(FORECAST_HORIZONS)} (predictions.forecast_horizon)"
        )
        raise PredictionEngineError(message)

    return offset // timedelta(days=1)


def horizon_windows(
    prediction_date: date, horizon: str
) -> tuple[tuple[str, datetime, datetime], ...]:
    """Keempat bin 6 jam pada hari sasaran. Lihat `HORIZON_BASIS`.

    Batas jendela memakai `risk_engine._window_bounds` supaya `window_start` prediksi jatuh
    tepat pada batas yang sama dengan baris `risk_scores`; menghitungnya ulang di sini
    berisiko menggeser satu jam dan membuat kedua tabel tidak lagi dapat disandingkan.
    """
    target = prediction_date + timedelta(days=horizon_day_offset(horizon))

    return tuple((label, *risk._window_bounds(target, label)) for label in risk.TIME_WINDOWS)


# ---------------------------------------------------------------------------
# Bahan proyeksi
# ---------------------------------------------------------------------------


def _scoped(query: Select[Any], polsek: str | None) -> Select[Any]:
    return query if polsek is None else query.where(Location.polsek == polsek)


def collect_baselines(
    session: Session, prediction_date: date, polsek: str | None = None
) -> dict[tuple[uuid.UUID, str, str], Baseline]:
    """Penilaian **terakhir** per (sel, jenis ancaman, label jendela).

    Bukan satu tanggal penilaian untuk semua: tanggal penilaian pada dataset tidak selalu
    mencakup seluruh kombinasi, dan memaksakan satu tanggal akan membuat sebagian besar
    kombinasi kehilangan dasar hanya karena penilaian hari itu kebetulan tidak lengkap.
    Setiap prediksi karena itu membawa `baseline_assessment_date`-nya sendiri.
    """
    query = (
        select(RiskScore)
        .join(Location, Location.location_id == RiskScore.location_id)
        .where(RiskScore.assessment_date <= prediction_date)
        .distinct(RiskScore.location_id, RiskScore.threat_type, RiskScore.time_window)
        .order_by(
            RiskScore.location_id,
            RiskScore.threat_type,
            RiskScore.time_window,
            RiskScore.assessment_date.desc(),
        )
    )

    baselines: dict[tuple[uuid.UUID, str, str], Baseline] = {}
    for row in session.scalars(_scoped(query, polsek)).all():
        if row.time_window is None:
            # Baris tanpa label jendela tidak dapat dipasangkan dengan jendela yang
            # diprediksi; ia diabaikan di sini, bukan dipaksakan ke jendela mana pun.
            continue
        baselines[(row.location_id, row.threat_type, row.time_window)] = Baseline(
            risk_score_id=row.risk_score_id,
            code=row.code,
            assessment_date=row.assessment_date,
            risk_score=row.risk_score,
            risk_class=row.risk_class,
            weights_version=row.weights_version,
            factors={name: getattr(row, name) for name in risk.PERSISTED_FACTORS},
        )

    return baselines


def collect_support(
    session: Session, polsek: str | None = None
) -> dict[tuple[uuid.UUID, str, str], int]:
    """Kejadian historis per (sel, jenis ancaman, label jendela) — dasar `confidence`.

    Jam diambil dari `incident_time` (waktu setempat), bukan `occurred_at` (UTC), dengan
    alasan yang sama seperti `temporal_factor` pada `risk_engine`: UTC akan menggeser jam
    rawan tujuh jam dan memindahkan kejadian ke bin yang salah.
    """
    rows = session.execute(
        _scoped(
            select(
                CrimeIncident.location_id,
                CrimeIncident.incident_type,
                func.extract("hour", CrimeIncident.incident_time),
                func.count(),
            )
            .join(Location, Location.location_id == CrimeIncident.location_id)
            .group_by(
                CrimeIncident.location_id,
                CrimeIncident.incident_type,
                func.extract("hour", CrimeIncident.incident_time),
            ),
            polsek,
        )
    ).all()

    support: dict[tuple[uuid.UUID, str, str], int] = defaultdict(int)
    for location_id, threat, hour, count in rows:
        for label, (begin, finish) in risk.TIME_WINDOWS.items():
            if begin <= int(hour) < finish:
                support[(location_id, str(threat), label)] += int(count)
                break

    return dict(support)


def _cells(session: Session, polsek: str | None) -> tuple[risk.Cell, ...]:
    """Seluruh sel grid dalam cakupan, dalam bentuk yang sama dengan `risk_engine.Cell`."""
    return tuple(
        risk.Cell(
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


# ---------------------------------------------------------------------------
# Confidence
# ---------------------------------------------------------------------------


def confidence_of(support: int, busiest: int, threat: str, window: str) -> tuple[int, str]:
    """`confidence` beserta alasannya. Lihat `CONFIDENCE_BASIS`.

    Dipisahkan dari pengambilan data supaya aritmetikanya dapat diuji tanpa database.
    Bentuk normalisasinya sama dengan `risk_engine._normalise`: 0–100 terhadap nilai
    tertinggi, tanpa satu pun angka yang dikarang.
    """
    if busiest <= 0:
        return 0, (
            f"tidak ada satu pun kejadian {threat} yang tercatat pada jendela {window} di "
            "seluruh cakupan, sehingga tidak ada pembanding untuk menormalkan dasar "
            "perkiraan — confidence 0"
        )

    value = max(0, min(100, round(100 * support / busiest)))
    if support == 0:
        return 0, (
            f"tidak ada kejadian {threat} pada sel ini di jendela {window}; kombinasi "
            f"terpadat pada jenis dan jendela yang sama memiliki {busiest} kejadian — "
            "confidence 0, dasar perkiraan sangat tipis"
        )

    return value, (
        f"{support} kejadian {threat} pada sel ini di jendela {window}; kombinasi terpadat "
        f"pada jenis dan jendela yang sama memiliki {busiest} kejadian — "
        f"confidence = round(100 x {support}/{busiest}) = {value}"
    )


# ---------------------------------------------------------------------------
# Proyeksi
# ---------------------------------------------------------------------------


def _weights_for(
    catalogue: risk.WeightsCatalogue, version: str | None
) -> tuple[dict[str, float], str | None]:
    """Bobot yang dipakai baris penilaian dasar, beserta alasan bila tidak ditemukan.

    Bobot diambil dari versi yang **tercatat pada baris penilaian**, bukan dari versi
    aktif: sumbangan tiap faktor harus menjumlah kembali ke skor yang benar-benar
    tersimpan, dan skor itu dihitung dengan bobot versi tersebut.
    """
    if version is not None and version in catalogue.versions:
        profile = catalogue.versions[version].profiles.get(risk.PROFILE_HISTORICAL)
        if profile is not None:
            return dict(profile.weights), None
        return {}, (
            f"versi bobot '{version}' tidak memiliki profil "
            f"'{risk.PROFILE_HISTORICAL}', sehingga sumbangan tiap faktor tidak dapat dihitung"
        )

    return {}, (
        f"versi bobot '{version}' tidak ada pada config/risk/risk-weights.yaml, sehingga "
        "sumbangan tiap faktor tidak dapat dihitung"
    )


def _dominant_factors(
    baseline: Baseline,
    weights: dict[str, float],
    weights_reason: str | None,
    confidence_reason: str,
    support: int,
) -> tuple[dict[str, Any], ...]:
    """Jawaban WHY: faktor penilaian dasar, terurut menurut sumbangannya.

    Sumbernya adalah mekanisme yang benar-benar dipakai — bobot dari `config/risk/` dikali
    faktor yang tersimpan pada baris `risk_scores` — sehingga labelnya `RULE` dan bukan
    kalimat yang disusun belakangan (CLAUDE.md §27).
    """
    entries: list[dict[str, Any]] = []
    for name, value in baseline.factors.items():
        weight = weights.get(name)
        contribution = 0.0 if (weight is None or value is None) else round(weight * value, 2)
        entries.append(
            {
                "factor": name,
                "value": value,
                "weight": weight,
                "contribution": contribution,
                "source": "RULE",
                "reason": weights_reason if weight is None else None,
                "basis": risk.FACTOR_BASIS.get(name),
            }
        )

    entries.sort(key=lambda item: float(item["contribution"]), reverse=True)
    entries.append(
        {
            "factor": CONFIDENCE_FACTOR,
            "value": support,
            "weight": None,
            # Nol karena dasar confidence tidak menyumbang apa pun pada risk_score; ia
            # disimpan di sini agar angka confidence tidak kehilangan dasarnya.
            "contribution": 0.0,
            "source": "RULE",
            "reason": confidence_reason,
            "basis": CONFIDENCE_BASIS,
        }
    )

    return tuple(entries)


def project(
    session: Session,
    prediction_date: date,
    horizon: str,
    polsek: str | None = None,
) -> Projection:
    """Memproyeksikan penilaian risiko terakhir ke jendela waktu pada rentang horizon."""
    windows = horizon_windows(prediction_date, horizon)

    try:
        catalogue = risk.load_weights()
        thresholds = risk.load_thresholds()
    except risk.RiskEngineError as error:
        raise PredictionEngineError(str(error)) from error

    profile = catalogue.active.profiles.get(risk.PROFILE_HISTORICAL)
    threats = () if profile is None else profile.applies_to

    cells = _cells(session, polsek)
    baselines = collect_baselines(session, prediction_date, polsek)
    support = collect_support(session, polsek)

    busiest: dict[tuple[str, str], int] = defaultdict(int)
    for (_location_id, threat, window), count in support.items():
        busiest[(threat, window)] = max(busiest[(threat, window)], count)

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

    not_computed: str | None = None
    if profile is None:
        not_computed = (
            f"versi bobot aktif '{catalogue.active_version}' tidak memiliki profil "
            f"'{risk.PROFILE_HISTORICAL}', sehingga tidak ada jenis ancaman yang dapat "
            "diproyeksikan."
        )
    elif not baselines:
        not_computed = (
            f"tidak ada satu pun baris risk_scores dengan assessment_date <= "
            f"{prediction_date.isoformat()} pada cakupan ini. Prediksi memproyeksikan "
            "penilaian risiko yang sudah ada; tanpa penilaian, tidak ada yang dapat "
            "diproyeksikan — jalankan penilaian risiko lebih dahulu."
        )

    forecasts: list[Forecast] = []
    versions: set[str] = set()

    for cell in cells:
        for threat in threats:
            for label, window_start, window_end in windows:
                baseline = baselines.get((cell.location_id, threat, label))
                count = support.get((cell.location_id, threat, label), 0)
                confidence, confidence_reason = confidence_of(
                    count, busiest.get((threat, label), 0), threat, label
                )

                if baseline is None:
                    forecasts.append(
                        Forecast(
                            location_id=cell.location_id,
                            grid_id=cell.grid_id,
                            kecamatan=cell.kecamatan,
                            kelurahan=cell.kelurahan,
                            polsek=cell.polsek,
                            threat_type=threat,
                            time_window=label,
                            window_start=window_start,
                            window_end=window_end,
                            baseline=None,
                            risk_score=None,
                            confidence=None,
                            confidence_reason=confidence_reason,
                            supporting_incidents=count,
                            dominant_factors=(),
                            not_predicted_reason=(
                                f"tidak ada baris risk_scores untuk sel {cell.grid_id}, jenis "
                                f"{threat}, dan jendela {label} pada tanggal penilaian mana pun "
                                f"sampai {prediction_date.isoformat()}"
                            ),
                        )
                    )
                    continue

                if baseline.weights_version is not None:
                    versions.add(baseline.weights_version)

                weights, weights_reason = _weights_for(catalogue, baseline.weights_version)

                forecasts.append(
                    Forecast(
                        location_id=cell.location_id,
                        grid_id=cell.grid_id,
                        kecamatan=cell.kecamatan,
                        kelurahan=cell.kelurahan,
                        polsek=cell.polsek,
                        threat_type=threat,
                        time_window=label,
                        window_start=window_start,
                        window_end=window_end,
                        baseline=baseline,
                        risk_score=baseline.risk_score,
                        confidence=confidence,
                        confidence_reason=confidence_reason,
                        supporting_incidents=count,
                        dominant_factors=_dominant_factors(
                            baseline, weights, weights_reason, confidence_reason, count
                        ),
                        not_predicted_reason=None,
                    )
                )

    return Projection(
        prediction_date=prediction_date,
        horizon=horizon,
        target_date=windows[0][1].date(),
        window_from=windows[0][1],
        window_to=windows[-1][2],
        time_windows=tuple(dict.fromkeys(label for label, _start, _end in windows)),
        reference_time=clock.reference_now(),
        rule_version=RULE_VERSION,
        weights_versions=tuple(sorted(versions)),
        threshold_version=thresholds.version,
        threshold_status=thresholds.status,
        threat_types=tuple(threats),
        forecasts=tuple(forecasts),
        evidence_from=span[0],
        evidence_to=span[1],
        incidents_considered=int(span[2] or 0),
        not_computed_reason=not_computed,
    )
