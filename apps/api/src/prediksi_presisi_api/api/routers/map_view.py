"""API peta — layer risiko berjalan, layer prediktif, dan panel detail (TASK 082–084).

Tiga layer pada CLAUDE.md §24 bersandar pada tabel yang berbeda dan **tidak** digabung
menjadi satu endpoint (docs/05 §2.4):

```text
/map/historical          ← crime_incidents (kejadian yang sudah terjadi)
/map/current-risk        ← risk_scores     (kondisi berjalan)
/map/predictive-heatmap  ← predictions     (jendela waktu ke depan)
/map/area/{kecamatan}    ← ketiganya + peringatan aktif
```

Dua catatan yang menentukan bentuk modul ini:

1. **Tidak ada ambang risiko di kode.** `risk_class` selalu diambil dari kolom
   `risk_scores.risk_class` yang sudah tersimpan; tidak ada perhitungan kelas dari skor
   di sini. Ambang berasal dari `config/risk/warning-thresholds.yaml` yang masih
   berstatus DEMO / PROPOSED (U-01), sehingga menghitung ulang kelas di lapisan API
   berarti mengunci angka yang belum disetujui siapa pun (CLAUDE.md §11, §12).
   Prediksi tidak menyimpan kelas risiko, maka responsnya pun tidak mengarang kelas.

2. **Setiap angka turunan membawa `*_basis`.** Nilai puncak, rata-rata, dan titik pusat
   kecamatan bukan angka yang tersimpan di database melainkan hasil agregasi di sini;
   menampilkannya tanpa menyebut asalnya akan menyesatkan pembaca peta.

Penyaringan cakupan dilakukan **di query** (`Location.polsek`), bukan setelah data
terambil. Kecamatan di luar cakupan pengguna dijawab **404**, bukan 403, agar keberadaan
data di wilayah lain tidak bocor (docs/05 §1).
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from ...models import CrimeIncident, EarlyWarning, Location, Prediction, RiskScore
from ...models.prediction import FORECAST_HORIZONS
from ...services import clock
from ..deps import CurrentUser, get_db, jurisdiction_filter, not_found, require_permission
from ..errors import ApiError

router = APIRouter(prefix="/map", tags=["peta"])

#: Banyaknya prediksi teratas yang dibawa panel detail kecamatan. Panel klik dimaksudkan
#: untuk dibaca sekilas, bukan menggantikan `GET /predictions` yang sudah berpaginasi.
AREA_PREDICTION_LIMIT = 5

#: Status prediksi yang belum layak tampil di peta. `DRAFT` adalah hasil yang belum
#: dipublikasikan; menampilkannya menyamakan rancangan dengan prediksi resmi
#: (docs/05 §2.6, `prediction:publish`).
UNPUBLISHED_PREDICTION_STATUS = "DRAFT"

#: Peringatan yang dihitung sebagai "aktif" pada panel detail. Sengaja hanya `ACTIVE`:
#: peringatan yang sudah di-*acknowledge* bukan lagi peringatan yang menunggu tindakan.
ACTIVE_WARNING_STATUS = "ACTIVE"

AGGREGATION_BASIS = (
    "Nilai per kecamatan adalah hasil agregasi sel grid di lapisan API, bukan angka "
    "tersimpan: risk_score = skor tertinggi antar sel, average_risk_score = rata-rata "
    "seluruh sel, dan latitude/longitude = rata-rata titik pusat grid dalam kecamatan. "
    "risk_class diambil apa adanya dari sel dengan skor tertinggi — tidak dihitung ulang "
    "dari ambang mana pun, karena ambang pada config/risk/ masih DEMO / PROPOSED (U-01)."
)

PREDICTIVE_BASIS = (
    "Nilai per kecamatan adalah hasil agregasi prediksi di lapisan API: risk_score = skor "
    "tertinggi antar sel pada horizon tersebut, confidence dan jendela waktu diambil dari "
    "prediksi berskor tertinggi itu. Prediksi tidak menyimpan kelas risiko dan tidak "
    "diberi kelas di sini — ambang kelas belum ditetapkan (U-01). Prediksi berstatus "
    f"{UNPUBLISHED_PREDICTION_STATUS} tidak ikut."
)


def _jurisdiction(current: CurrentUser, *permissions: str) -> str | None:
    """Polsek yang boleh dilihat menurut cakupan **tersempit** dari beberapa permission.

    Endpoint peta membutuhkan lebih dari satu permission; bila salah satunya dibatasi
    wilayah, seluruh respons ikut dibatasi. Cakupan terluas tidak boleh menang di sini.
    """
    for permission in permissions:
        polsek = jurisdiction_filter(current, permission)
        if polsek is not None:
            return polsek
    return None


def _scoped(query: Select[Any], polsek: str | None) -> Select[Any]:
    return query if polsek is None else query.where(Location.polsek == polsek)


def _latest_assessment_date(session: Session, polsek: str | None) -> Any:
    """Tanggal penilaian risiko terakhir yang terlihat oleh pengguna.

    Ikut disaring cakupan: pengguna ber-scope tidak boleh menyimpulkan adanya penilaian
    yang lebih baru di wilayah lain hanya dari tanggal yang dikembalikan.
    """
    return session.scalar(
        _scoped(
            select(func.max(RiskScore.assessment_date))
            .select_from(RiskScore)
            .join(Location, Location.location_id == RiskScore.location_id),
            polsek,
        )
    )


def _current_risk_rows(
    session: Session, polsek: str | None, assessment_date: date, kecamatan: str | None = None
) -> list[Any]:
    """Sel risiko satu tanggal penilaian, sudah tersaring cakupan.

    Agregasi dilakukan di Python karena satu tanggal penilaian hanya mencakup
    (jumlah grid × jenis ancaman × jendela waktu) baris, sementara `risk_class` yang
    ingin dibawa adalah kelas milik sel puncak — bukan nilai yang dapat diagregasi.
    """
    query = _scoped(
        select(RiskScore, Location)
        .join(Location, Location.location_id == RiskScore.location_id)
        .where(RiskScore.assessment_date == assessment_date),
        polsek,
    )
    if kecamatan is not None:
        query = query.where(Location.kecamatan == kecamatan)

    return list(session.execute(query).all())


def _single_version(versions: set[str | None]) -> str | None:
    """Satu versi bobot bila seragam; bila bercampur, dinyatakan apa adanya.

    Menyembunyikan percampuran akan membuat satu angka tampak berasal dari satu
    konfigurasi padahal tidak.
    """
    known = sorted(version for version in versions if version)
    if not known:
        return None
    return known[0] if len(known) == 1 else " + ".join(known)


def _aggregate_current_risk(rows: list[Any]) -> list[dict[str, Any]]:
    """Meringkas sel risiko menjadi satu baris per kecamatan."""
    areas: dict[str, dict[str, Any]] = {}

    for score, location in rows:
        area = areas.setdefault(
            location.kecamatan,
            {
                "kecamatan": location.kecamatan,
                "polsek": location.polsek,
                "risk_score": 0,
                "risk_class": None,
                "cell_count": 0,
                "grids": {},
                "score_total": 0,
                "threats": {},
                # Versi bobot yang menghasilkan angka ini. Dikumpulkan sebagai himpunan
                # karena satu kecamatan bisa saja memuat sel dari lebih dari satu versi —
                # dan bila itu terjadi, layar harus menyatakannya, bukan memilih salah satu.
                "weights_versions": set(),
            },
        )

        area["weights_versions"].add(score.weights_version)
        area["cell_count"] += 1
        area["score_total"] += score.risk_score
        area["grids"][location.grid_id] = (float(location.latitude), float(location.longitude))

        if area["risk_class"] is None or score.risk_score > area["risk_score"]:
            area["risk_score"] = score.risk_score
            area["risk_class"] = score.risk_class

        threat = area["threats"].setdefault(
            score.threat_type,
            {
                "threat_type": score.threat_type,
                "risk_score": score.risk_score,
                "risk_class": score.risk_class,
                "time_window": score.time_window,
                "cell_count": 0,
            },
        )
        threat["cell_count"] += 1
        if score.risk_score > threat["risk_score"]:
            threat["risk_score"] = score.risk_score
            threat["risk_class"] = score.risk_class
            threat["time_window"] = score.time_window

    result: list[dict[str, Any]] = []
    for area in areas.values():
        grids: dict[str, tuple[float, float]] = area["grids"]
        cell_count = int(area["cell_count"])
        result.append(
            {
                "kecamatan": area["kecamatan"],
                "polsek": area["polsek"],
                "risk_score": int(area["risk_score"]),
                "risk_class": area["risk_class"],
                "average_risk_score": round(int(area["score_total"]) / cell_count),
                "cell_count": cell_count,
                "grid_count": len(grids),
                # Ketertelusuran bobot (CLAUDE.md §25): tanpa ini skor di layar tidak
                # dapat dikembalikan ke konfigurasi yang menghasilkannya.
                "weights_version": _single_version(area["weights_versions"]),
                "latitude": round(sum(point[0] for point in grids.values()) / len(grids), 6),
                "longitude": round(sum(point[1] for point in grids.values()) / len(grids), 6),
                "threats": sorted(
                    area["threats"].values(),
                    key=lambda item: int(item["risk_score"]),
                    reverse=True,
                ),
            }
        )

    return sorted(result, key=lambda item: int(item["risk_score"]), reverse=True)


@router.get("/current-risk", summary="Layer risiko berjalan teragregasi per kecamatan")
def current_risk(
    session: Session = Depends(get_db),
    current: CurrentUser = require_permission("map:read"),
    _risk_reader: CurrentUser = require_permission("risk_score:read"),
) -> dict[str, Any]:
    """Risiko berjalan pada tanggal penilaian terakhir, satu baris per kecamatan.

    Membutuhkan `map:read` **dan** `risk_score:read` (docs/05 §2.4). Keduanya diperiksa
    sebagai dependency terpisah sehingga penolakan salah satunya tetap tercatat di audit.
    """
    polsek = _jurisdiction(current, "map:read", "risk_score:read")
    assessment_date = _latest_assessment_date(session, polsek)

    areas: list[dict[str, Any]] = []
    if assessment_date is not None:
        areas = _aggregate_current_risk(_current_risk_rows(session, polsek, assessment_date))

    return {
        "reference_time": clock.reference_now(),
        "demo_clock": clock.is_demo_clock(),
        "assessment_date": assessment_date,
        "areas": areas,
        "aggregation_basis": AGGREGATION_BASIS,
    }


@router.get("/predictive-heatmap", summary="Layer prediktif teragregasi per kecamatan")
def predictive_heatmap(
    session: Session = Depends(get_db),
    current: CurrentUser = require_permission("map:read"),
    _prediction_reader: CurrentUser = require_permission("prediction:read"),
    horizon: str = Query("6H", description="6H, 12H, 24H, 3D, atau 7D"),
) -> dict[str, Any]:
    """Prediksi pada satu horizon, satu baris per kecamatan."""
    requested = horizon.upper()
    if requested not in FORECAST_HORIZONS:
        raise ApiError(
            status.HTTP_400_BAD_REQUEST,
            "Horizon prediksi tidak dikenal.",
            details=[{"field": "horizon", "issue": f"harus salah satu dari {FORECAST_HORIZONS}"}],
        )

    polsek = _jurisdiction(current, "map:read", "prediction:read")

    query = _scoped(
        select(Prediction, Location)
        .join(Location, Location.location_id == Prediction.location_id)
        .where(
            Prediction.forecast_horizon == requested,
            Prediction.status != UNPUBLISHED_PREDICTION_STATUS,
        )
        .order_by(Prediction.risk_score.desc()),
        polsek,
    )

    areas: dict[str, dict[str, Any]] = {}
    for prediction, location in session.execute(query).all():
        area = areas.setdefault(
            location.kecamatan,
            {
                "kecamatan": location.kecamatan,
                "polsek": location.polsek,
                # Baris pertama tiap kecamatan sudah merupakan yang berskor tertinggi
                # karena query diurutkan menurun.
                "risk_score": prediction.risk_score,
                "confidence": prediction.confidence,
                "threat_type": prediction.threat_type,
                "time_window": prediction.time_window,
                "window_start": prediction.window_start,
                "window_end": prediction.window_end,
                "prediction_code": prediction.code,
                "model_version": prediction.model_version,
                "cell_count": 0,
                "threats": {},
            },
        )
        area["cell_count"] += 1

        threat = area["threats"].setdefault(
            prediction.threat_type,
            {
                "threat_type": prediction.threat_type,
                "risk_score": prediction.risk_score,
                "confidence": prediction.confidence,
                "time_window": prediction.time_window,
                "cell_count": 0,
            },
        )
        threat["cell_count"] += 1

    ordered = sorted(areas.values(), key=lambda item: int(item["risk_score"]), reverse=True)
    for area in ordered:
        area["threats"] = sorted(
            area["threats"].values(), key=lambda item: int(item["risk_score"]), reverse=True
        )

    return {
        "reference_time": clock.reference_now(),
        "demo_clock": clock.is_demo_clock(),
        "horizon": requested,
        "areas": ordered,
        "aggregation_basis": PREDICTIVE_BASIS,
    }


#: Panjang jendela historis yang boleh diminta, dalam bulan. Daftar tertutup dengan
#: sengaja: rentang bebas mengundang pertanyaan "kenapa 7 bulan" yang tidak ada jawabannya,
#: sementara empat pilihan ini menjawab pertanyaan nyata — sebulan terakhir, satu triwulan,
#: setahun, dan seluruh rentang data 2023–2025.
HISTORICAL_MONTHS = (1, 3, 12, 36)

HISTORICAL_BASIS = (
    "Angka per kecamatan adalah **cacah kejadian mentah** pada jendela waktu terpilih, "
    "bukan skor risiko: tidak ada pembobotan, tidak ada normalisasi terhadap luas maupun "
    "jumlah penduduk, dan karenanya tidak ada kelas risiko. Wilayah dengan kejadian "
    "terbanyak belum tentu wilayah paling rawan. "
    "Titik pada peta berada di koordinat **lokasi**, bukan di tempat kejadian sebenarnya: "
    "crime_incidents menyimpan location_id dan tidak menyimpan koordinatnya sendiri, "
    "sehingga seluruh kejadian pada satu lokasi menumpuk di satu titik yang sama."
)


def _month_window(months: int) -> tuple[date, date]:
    """Jendela `months` bulan ke belakang dari tanggal acuan, kedua ujung inklusif.

    Dihitung mundur per bulan kalender, bukan dengan mengalikan 30 hari: "12 bulan
    terakhir" yang meleset dua hari akan membuat cacah tahunan tidak pernah cocok dengan
    cacah yang sama pada layar analitik.
    """
    end = clock.reference_now().astimezone(clock.JAKARTA).date()
    month_index = end.year * 12 + (end.month - 1) - months
    year, month = divmod(month_index, 12)
    # Hari yang sama pada bulan awal; bila tanggalnya tidak ada di bulan itu (31 Februari)
    # dipakai hari pertama bulan berikutnya, lalu mundur sehari.
    try:
        start = date(year, month + 1, end.day)
    except ValueError:
        start = date(year + (month + 1) // 12, (month + 1) % 12 + 1, 1) - timedelta(days=1)
    return start + timedelta(days=1), end


@router.get("/historical", summary="Layer kerawanan historis per kecamatan beserta titiknya")
def historical(
    session: Session = Depends(get_db),
    current: CurrentUser = require_permission("map:read"),
    _crime_reader: CurrentUser = require_permission("crime:read"),
    months: int = Query(12, description=f"Panjang jendela, salah satu dari {HISTORICAL_MONTHS}"),
) -> dict[str, Any]:
    """Kejadian yang **sudah terjadi**, sebagai bidang warna per kecamatan dan titik lokasi.

    Layer ketiga CLAUDE.md §24, dan satu-satunya yang memandang ke belakang. Ia menjawab
    "di mana selama ini kejadian menumpuk", bukan "di mana risikonya tinggi" — dua hal
    yang mudah tertukar justru karena keduanya digambar di bidang yang sama. Karena itu
    responsnya tidak pernah membawa `risk_class`, dan `aggregation_basis` menyatakan
    terbuka bahwa yang dicacah adalah kejadian, bukan risiko.

    Membutuhkan `map:read` **dan** `crime:read`, diperiksa sebagai dependency terpisah
    supaya penolakan salah satunya tetap tercatat di audit.
    """
    if months not in HISTORICAL_MONTHS:
        raise ApiError(
            status.HTTP_400_BAD_REQUEST,
            "Panjang jendela historis tidak dikenal.",
            details=[{"field": "months", "issue": f"harus salah satu dari {HISTORICAL_MONTHS}"}],
        )

    polsek = _jurisdiction(current, "map:read", "crime:read")
    window_from, window_to = _month_window(months)

    def scoped(query: Select[Any]) -> Select[Any]:
        return _scoped(
            query.join(Location, Location.location_id == CrimeIncident.location_id).where(
                CrimeIncident.incident_date >= window_from,
                CrimeIncident.incident_date <= window_to,
            ),
            polsek,
        )

    areas: dict[str, dict[str, Any]] = {}
    by_type = session.execute(
        scoped(
            select(Location.kecamatan, Location.polsek, CrimeIncident.incident_type, func.count())
        )
        .group_by(Location.kecamatan, Location.polsek, CrimeIncident.incident_type)
        .order_by(func.count().desc())
    ).all()
    for kecamatan, area_polsek, incident_type, count in by_type:
        area = areas.setdefault(
            kecamatan,
            {
                "kecamatan": kecamatan,
                "polsek": area_polsek,
                "incidents": 0,
                "by_threat_type": [],
            },
        )
        area["incidents"] += int(count)
        area["by_threat_type"].append(
            {"threat_type": incident_type, "incidents": int(count)},
        )

    points = [
        {
            "location_code": code,
            "kecamatan": kecamatan,
            "kelurahan": kelurahan,
            # Koordinat disalin apa adanya dari `locations`; lihat HISTORICAL_BASIS soal
            # mengapa ini koordinat lokasi dan bukan koordinat kejadian.
            "latitude": float(latitude),
            "longitude": float(longitude),
            "incidents": int(count),
            "dominant_threat_type": dominant,
        }
        for code, kecamatan, kelurahan, latitude, longitude, count, dominant in session.execute(
            scoped(
                select(
                    Location.code,
                    Location.kecamatan,
                    Location.kelurahan,
                    Location.latitude,
                    Location.longitude,
                    func.count(),
                    # Jenis gangguan terbanyak di lokasi itu, dihitung di database supaya
                    # tidak perlu menarik 1.200 baris kejadian ke lapisan API.
                    func.mode().within_group(CrimeIncident.incident_type),
                )
            )
            .where(Location.latitude.is_not(None), Location.longitude.is_not(None))
            .group_by(
                Location.code,
                Location.kecamatan,
                Location.kelurahan,
                Location.latitude,
                Location.longitude,
            )
            .order_by(func.count().desc())
        ).all()
    ]

    observed_from, observed_to = session.execute(
        scoped(select(func.min(CrimeIncident.incident_date), func.max(CrimeIncident.incident_date)))
    ).one()

    return {
        "reference_time": clock.reference_now(),
        "demo_clock": clock.is_demo_clock(),
        "months": months,
        "window_from": window_from,
        "window_to": window_to,
        # Rentang data yang benar-benar ditemukan di dalam jendela. Dikembalikan terpisah
        # supaya hasil kosong dapat dibedakan: jendela yang salah, atau memang tidak ada
        # kejadian. Tanpa ini keduanya terbaca sama di layar.
        "observed_from": observed_from,
        "observed_to": observed_to,
        "total_incidents": sum(int(area["incidents"]) for area in areas.values()),
        "areas": sorted(areas.values(), key=lambda item: int(item["incidents"]), reverse=True),
        "points": points,
        "aggregation_basis": HISTORICAL_BASIS,
    }


def _area_predictions(session: Session, polsek: str | None, kecamatan: str) -> list[dict[str, Any]]:
    """Prediksi teratas satu kecamatan, lengkap dengan WHAT/WHERE/WHEN/RISK/CONFIDENCE/WHY.

    `dominant_factors` selalu ikut: menyembunyikan asal penjelasan membuat hasil aturan
    terbaca sebagai temuan model (CLAUDE.md §10, §27).
    """
    query = _scoped(
        select(Prediction, Location)
        .join(Location, Location.location_id == Prediction.location_id)
        .where(
            Location.kecamatan == kecamatan,
            Prediction.status != UNPUBLISHED_PREDICTION_STATUS,
        )
        .order_by(Prediction.risk_score.desc(), Prediction.prediction_date.desc())
        .limit(AREA_PREDICTION_LIMIT),
        polsek,
    )

    return [
        {
            "code": prediction.code,
            "threat_type": prediction.threat_type,  # WHAT
            "kecamatan": location.kecamatan,  # WHERE
            "kelurahan": location.kelurahan,
            "grid_id": location.grid_id,
            "latitude": float(location.latitude),
            "longitude": float(location.longitude),
            "time_window": prediction.time_window,  # WHEN
            "window_start": prediction.window_start,
            "window_end": prediction.window_end,
            "prediction_date": prediction.prediction_date,
            "forecast_horizon": prediction.forecast_horizon,
            "risk_score": prediction.risk_score,  # RISK
            "confidence": prediction.confidence,  # CONFIDENCE
            "dominant_factors": prediction.dominant_factors,  # WHY
            "model_version": prediction.model_version,
            "status": prediction.status,
        }
        for prediction, location in session.execute(query).all()
    ]


def _area_history(session: Session, polsek: str | None, kecamatan: str) -> dict[str, Any]:
    """Jumlah kejadian historis kecamatan beserta rentang data yang menghasilkannya.

    Rentang ikut dikembalikan agar angka dapat ditelusuri kembali ke data sumber —
    pola `source` pada respons analitik (docs/05 §2.5).
    """
    totals_query = _scoped(
        select(
            func.count(),
            func.min(CrimeIncident.incident_date),
            func.max(CrimeIncident.incident_date),
        )
        .select_from(CrimeIncident)
        .join(Location, Location.location_id == CrimeIncident.location_id)
        .where(Location.kecamatan == kecamatan),
        polsek,
    )
    total, date_from, date_to = session.execute(totals_query).one()

    by_type_query = _scoped(
        select(CrimeIncident.incident_type, func.count())
        .select_from(CrimeIncident)
        .join(Location, Location.location_id == CrimeIncident.location_id)
        .where(Location.kecamatan == kecamatan)
        .group_by(CrimeIncident.incident_type)
        .order_by(func.count().desc()),
        polsek,
    )

    return {
        "total_incidents": int(total or 0),
        "date_from": date_from,
        "date_to": date_to,
        "by_threat_type": [
            {"threat_type": incident_type, "incidents": int(count)}
            for incident_type, count in session.execute(by_type_query).all()
        ],
    }


def _area_warnings(session: Session, polsek: str | None, kecamatan: str) -> list[dict[str, Any]]:
    """Peringatan yang masih berstatus ACTIVE di kecamatan tersebut."""
    query = _scoped(
        select(EarlyWarning, Location, Prediction.code)
        .join(Location, Location.location_id == EarlyWarning.location_id)
        .join(Prediction, Prediction.prediction_id == EarlyWarning.prediction_id)
        .where(
            Location.kecamatan == kecamatan,
            EarlyWarning.status == ACTIVE_WARNING_STATUS,
        )
        .order_by(EarlyWarning.risk_score.desc(), EarlyWarning.created_at.desc()),
        polsek,
    )

    return [
        {
            "code": warning.code,
            "severity": warning.severity,
            "threat_type": warning.threat_type,
            "time_window": warning.time_window,
            "window_start": warning.window_start,
            "window_end": warning.window_end,
            "risk_score": warning.risk_score,
            "confidence": warning.confidence,
            "status": warning.status,
            "grid_id": location.grid_id,
            "prediction_code": prediction_code,
            "threshold_version": warning.threshold_version,
        }
        for warning, location, prediction_code in session.execute(query).all()
    ]


@router.get("/area/{kecamatan}", summary="Detail satu kecamatan untuk panel klik peta")
def area_detail(
    kecamatan: str = Path(description="Nama kecamatan persis seperti pada master lokasi"),
    session: Session = Depends(get_db),
    current: CurrentUser = require_permission("map:read"),
) -> dict[str, Any]:
    """Panel detail: potensi ancaman, jendela paling rawan, prediksi + WHY, riwayat, peringatan.

    Kecamatan yang tidak ada **dan** kecamatan di luar cakupan pengguna sama-sama dijawab
    404 (docs/05 §1). Membedakan keduanya akan memberi tahu pengguna bahwa wilayah itu ada.
    """
    polsek = _jurisdiction(current, "map:read")

    area = session.execute(
        _scoped(
            select(Location.kecamatan, Location.polsek, func.count())
            .where(Location.kecamatan == kecamatan)
            .group_by(Location.kecamatan, Location.polsek),
            polsek,
        )
    ).first()
    if area is None:
        raise not_found()

    assessment_date = _latest_assessment_date(session, polsek)

    threats: list[dict[str, Any]] = []
    windows: list[dict[str, Any]] = []
    weights_version: str | None = None
    if assessment_date is not None:
        rows = _current_risk_rows(session, polsek, assessment_date, kecamatan=kecamatan)
        aggregated = _aggregate_current_risk(rows)
        if aggregated:
            threats = aggregated[0]["threats"]
            weights_version = aggregated[0]["weights_version"]

        # Jendela waktu paling rawan menurut sel risiko tanggal penilaian terakhir.
        by_window: dict[str | None, dict[str, Any]] = {}
        for score, _location in rows:
            window = by_window.setdefault(
                score.time_window,
                {"time_window": score.time_window, "risk_score": 0, "risk_class": None},
            )
            if score.risk_score > int(window["risk_score"]):
                window["risk_score"] = score.risk_score
                window["risk_class"] = score.risk_class
        windows = sorted(by_window.values(), key=lambda item: int(item["risk_score"]), reverse=True)

    return {
        "reference_time": clock.reference_now(),
        "demo_clock": clock.is_demo_clock(),
        "kecamatan": area[0],
        "polsek": area[1],
        "grid_count": int(area[2]),
        "assessment_date": assessment_date,
        "weights_version": weights_version,
        "threats": threats,
        "critical_time_window": windows[0]["time_window"] if windows else None,
        "time_windows": windows,
        "top_predictions": _area_predictions(session, polsek, kecamatan),
        "history": _area_history(session, polsek, kecamatan),
        "active_warnings": _area_warnings(session, polsek, kecamatan),
        "aggregation_basis": AGGREGATION_BASIS,
        "time_window_basis": (
            "Jendela paling rawan adalah jendela dengan sel risiko tertinggi pada tanggal "
            "penilaian terakhir; peringkatnya dihitung di lapisan API, bukan tersimpan."
        ),
        "active_warnings_basis": (
            f"Hanya peringatan berstatus {ACTIVE_WARNING_STATUS}. Peringatan yang sudah "
            "di-acknowledge atau resolve tidak dihitung sebagai menunggu tindakan."
        ),
    }
