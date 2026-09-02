"""Pembangkitan ulang data dummy analitik (TASK 022).

Empat temuan audit tidak dapat diperbaiki lewat pemetaan saat impor karena datanya
memang tidak koheren. Modul ini membangkitkan ulang isinya secara **deterministik**
(seed acak tetap), sehingga hasilnya dapat direproduksi dan diperiksa:

| Temuan | Acceptance | Perbaikan |
|---|---|---|
| Jumlah faktor ≠ `risk_score` (1.822/1.848) | A-3 | Faktor dibangkitkan ulang agar
  `round(Σ(bobot × faktor)) = risk_score` |
| `forecast_horizon` hanya `24h` | A-4 | Horizon disebar merata ke `6H/12H/24H/3D/7D` |
| `dominant_factors` identik (180/180) | A-5 | WHY diturunkan dari faktor risiko
  pendamping, berbeda per baris |
| 171/180 prediksi tanpa `risk_scores` pendamping | A-6 | Baris pendamping dibuat bila belum ada |

**`risk_score` dan `risk_class` yang sudah ada tidak diubah.** Yang dibangkitkan ulang hanya
komponen penyusun dan metadatanya, sehingga sebaran risiko pada dataset tetap seperti semula.

Bobot dan threshold berasal dari `config/risk/` dan berstatus `DEMO / PROPOSED` (U-01, U-02).
"""

from __future__ import annotations

import csv
import json
import math
import random
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import yaml

from .csv_source import SOURCE_TIMEZONE
from .errors import SeedError
from .paths import REPO_ROOT, SAMPLE_DATA_DIR

RISK_WEIGHTS_FILE = REPO_ROOT / "config" / "risk" / "risk-weights.yaml"
THRESHOLDS_FILE = REPO_ROOT / "config" / "risk" / "warning-thresholds.yaml"

#: Seed tetap. Setiap baris memakai seed turunan dari kodenya sendiri, sehingga hasil
#: pembangkitan hanya bergantung pada isi baris — bukan pada urutan maupun jumlah baris
#: yang kebetulan sedang diproses. Tanpa itu, menjalankan ulang di atas hasil sebelumnya
#: akan menghasilkan angka yang berbeda.
RANDOM_SEED = 20260901


def row_rng(code: str) -> random.Random:
    """RNG khusus satu baris, sehingga pembangkitan bersifat murni terhadap isinya."""
    return random.Random(f"{RANDOM_SEED}:{code}")  # noqa: S311 — data sintetis


#: Jarak hari dari `prediction_date` ke jendela yang diprediksi.
#: Konvensi PROPOSED — definisi target prediksi belum ditetapkan (U-03).
HORIZON_OFFSET_DAYS: dict[str, int] = {"6H": 0, "12H": 0, "24H": 1, "3D": 3, "7D": 7}
HORIZONS = tuple(HORIZON_OFFSET_DAYS)

#: Empat bin 6 jam yang dipakai seluruh dataset (docs/02 §21).
WINDOW_BOUNDS: dict[str, tuple[int, int]] = {
    "00:00-06:00": (0, 6),
    "06:00-12:00": (6, 12),
    "12:00-18:00": (12, 18),
    "18:00-23:59": (18, 24),
}

FACTOR_COLUMNS = (
    "historical_factor",
    "recent_trend_factor",
    "temporal_factor",
    "spatial_factor",
    "context_factor",
)

#: Nama faktor yang dapat dibaca manusia untuk penjelasan WHY.
FACTOR_LABELS: dict[str, str] = {
    "historical_factor": "historical_incident_density",
    "recent_trend_factor": "recent_incident_trend",
    "temporal_factor": "time_window_pattern",
    "spatial_factor": "spatial_concentration",
    "context_factor": "contextual_activity",
}


@dataclass(frozen=True)
class RiskConfig:
    """Bobot dan threshold dari `config/risk/`."""

    weights_version: str
    weights: dict[str, float]
    threshold_version: str
    minimum_warning_score: int
    severities: list[dict[str, Any]]

    def severity_for(self, score: int) -> str | None:
        for band in self.severities:
            if band["min"] <= score <= band["max"]:
                return str(band["severity"])
        return None


def load_risk_config() -> RiskConfig:
    if not RISK_WEIGHTS_FILE.exists() or not THRESHOLDS_FILE.exists():
        message = "config/risk/risk-weights.yaml atau warning-thresholds.yaml tidak ditemukan"
        raise SeedError(message)

    weights_raw = yaml.safe_load(RISK_WEIGHTS_FILE.read_text(encoding="utf-8"))
    thresholds_raw = yaml.safe_load(THRESHOLDS_FILE.read_text(encoding="utf-8"))

    # Bobot kini berversi: baris `risk_scores` menyimpan `weights_version`, dan bobot
    # sebuah versi tidak boleh berubah selama masih dirujuk. Yang dipakai membangkitkan
    # adalah versi aktif, bukan versi terbaru — mengganti bobot berarti menambah versi
    # lalu membangkitkan ulang, bukan menyunting versi yang sedang berlaku.
    active = str(weights_raw["active_version"])
    profiles = weights_raw["versions"][active]["profiles"]
    weights = {key: float(value) for key, value in profiles["historical"]["weights"].items()}
    total = sum(weights.values())
    if abs(total - 1.0) > 1e-9:
        message = f"bobot risk score harus berjumlah 1, saat ini {total}"
        raise SeedError(message)

    return RiskConfig(
        weights_version=active,
        weights=weights,
        threshold_version=str(thresholds_raw["version"]),
        minimum_warning_score=int(thresholds_raw["early_warning"]["minimum_score"]),
        severities=list(thresholds_raw["early_warning"]["severities"]),
    )


def _weighted_score(factors: dict[str, int], weights: dict[str, float]) -> int:
    return round(sum(weights[name] * factors[name] for name in weights))


def build_factors(target: int, config: RiskConfig, rng: random.Random) -> dict[str, int]:
    """Membangkitkan lima faktor 0–100 yang benar-benar menghasilkan `target`.

    Koreksi dilakukan dua tahap — kasar lewat faktor berbobot terbesar, lalu halus lewat
    faktor berbobot terkecil — supaya nilainya tetap berada di sekitar `target` dan tidak
    terdorong menumpuk ke 0 atau 100.

    Kesesuaiannya diperiksa sebelum dikembalikan; bila tidak tercapai, prosesnya gagal
    alih-alih menghasilkan data yang tampak benar tetapi tidak konsisten.
    """
    factors = {name: min(100, max(0, target + rng.randint(-15, 15))) for name in FACTOR_COLUMNS}

    coarse = max(config.weights, key=lambda name: config.weights[name])
    fine = min(config.weights, key=lambda name: config.weights[name])

    residual = target - sum(config.weights[name] * factors[name] for name in FACTOR_COLUMNS)
    factors[coarse] = min(100, max(0, factors[coarse] + round(residual / config.weights[coarse])))

    for _ in range(400):
        current = _weighted_score(factors, config.weights)
        if current == target:
            return factors

        step = 1 if current < target else -1
        for name in (fine, coarse, *FACTOR_COLUMNS):
            candidate = factors[name] + step
            if 0 <= candidate <= 100:
                factors[name] = candidate
                break
        else:  # pragma: no cover — hanya mungkin bila target di luar 0..100
            break

    message = f"tidak dapat membangkitkan faktor yang konsisten untuk risk_score {target}"
    raise SeedError(message)


def explain(factors: dict[str, int], score: int, config: RiskConfig) -> list[dict[str, Any]]:
    """Menyusun WHY dari kontribusi faktor yang benar-benar dipakai.

    `source` bernilai `RULE`, bukan `MODEL`: data ini dihasilkan aturan aritmetika,
    bukan temuan model. Menyebutnya `MODEL` akan menjadi penjelasan fiktif (CLAUDE.md §27).
    """
    scored: list[tuple[float, str]] = [
        (round(config.weights[name] * factors[name] / max(score, 1), 3), FACTOR_LABELS[name])
        for name in FACTOR_COLUMNS
    ]
    scored.sort(reverse=True)

    return [
        {"factor": label, "contribution": contribution, "source": "RULE"}
        for contribution, label in scored[:3]
    ]


def _window_bounds(day: date, time_window: str) -> tuple[datetime, datetime]:
    start_hour, end_hour = WINDOW_BOUNDS[time_window]
    start = datetime(day.year, day.month, day.day, start_hour, tzinfo=SOURCE_TIMEZONE)
    end = start + timedelta(hours=end_hour - start_hour)
    return start, end


def _iso(moment: datetime) -> str:
    return moment.isoformat(timespec="minutes")


def regenerate(directory: Path | None = None) -> dict[str, int]:
    """Menulis ulang risk_scores.csv, predictions.csv, dan early_warnings.csv."""
    target_dir = directory or SAMPLE_DATA_DIR
    config = load_risk_config()

    risk_rows = list(csv.DictReader((target_dir / "risk_scores.csv").open(encoding="utf-8")))
    prediction_rows = list(csv.DictReader((target_dir / "predictions.csv").open(encoding="utf-8")))
    warning_rows = list(csv.DictReader((target_dir / "early_warnings.csv").open(encoding="utf-8")))

    # ---- A-3: faktor dibuat konsisten dengan risk_score ------------------------------
    risk_index: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for row in risk_rows:
        score = int(row["risk_score"])
        factors = build_factors(score, config, row_rng(row["risk_score_id"]))
        row.update({name: str(value) for name, value in factors.items()})

        assessment = date.fromisoformat(row["assessment_date"])
        start, end = _window_bounds(assessment, row["time_window"])
        row["window_start"] = _iso(start)
        row["window_end"] = _iso(end)
        row["weights_version"] = config.weights_version
        row.pop("is_synthetic", None)

        risk_index[
            (row["grid_id"], row["threat_type"], row["time_window"], row["assessment_date"])
        ] = row

    next_risk_number = len(risk_rows) + 1
    added_risk_rows = 0

    # ---- A-4, A-5, A-6: horizon, WHY, dan pendamping risk score -----------------------
    for index, row in enumerate(prediction_rows):
        horizon = HORIZONS[index % len(HORIZONS)]
        row["forecast_horizon"] = horizon

        prediction_date = date.fromisoformat(row["prediction_date"])
        window_day = prediction_date + timedelta(days=HORIZON_OFFSET_DAYS[horizon])
        start, end = _window_bounds(window_day, row["time_window"])
        row["window_start"] = _iso(start)
        row["window_end"] = _iso(end)

        key = (row["grid_id"], row["threat_type"], row["time_window"], row["prediction_date"])
        baseline = risk_index.get(key)
        if baseline is None:
            score = int(row["risk_score"])
            baseline_code = f"RS-{next_risk_number:05d}"
            factors = build_factors(score, config, row_rng(baseline_code))
            baseline_start, baseline_end = _window_bounds(prediction_date, row["time_window"])
            baseline = {
                "risk_score_id": baseline_code,
                "assessment_date": row["prediction_date"],
                "grid_id": row["grid_id"],
                "kecamatan": row["kecamatan"],
                "kelurahan": row["kelurahan"],
                "threat_type": row["threat_type"],
                "time_window": row["time_window"],
                "window_start": _iso(baseline_start),
                "window_end": _iso(baseline_end),
                "risk_score": row["risk_score"],
                "risk_class": _risk_class(score),
                **{name: str(value) for name, value in factors.items()},
                "weights_version": config.weights_version,
                "model_version": row["model_version"],
            }
            risk_index[key] = baseline
            risk_rows.append(baseline)
            next_risk_number += 1
            added_risk_rows += 1

        factors = {name: int(baseline[name]) for name in FACTOR_COLUMNS}
        row["dominant_factors"] = json.dumps(
            explain(factors, int(row["risk_score"]), config), ensure_ascii=False
        )
        row["baseline_risk_score_code"] = baseline["risk_score_id"]
        row.pop("is_synthetic", None)

    predictions_by_code = {row["prediction_id"]: row for row in prediction_rows}

    # ---- Peringatan disesuaikan dengan prediksi sumbernya ------------------------------
    for row in warning_rows:
        prediction = predictions_by_code.get(row["prediction_id"])
        if prediction is None:
            message = f"early_warnings.csv:{row['warning_id']}: prediksi tidak ditemukan"
            raise SeedError(message)

        score = int(prediction["risk_score"])
        severity = config.severity_for(score)
        if severity is None:
            message = (
                f"early_warnings.csv:{row['warning_id']}: skor {score} tidak masuk rentang "
                f"severity mana pun pada config/risk/warning-thresholds.yaml"
            )
            raise SeedError(message)

        row["severity"] = severity.title()
        row["risk_score"] = prediction["risk_score"]
        row["confidence"] = prediction["confidence"]
        row["threat_type"] = prediction["threat_type"]
        row["grid_id"] = prediction["grid_id"]
        row["kecamatan"] = prediction["kecamatan"]
        row["kelurahan"] = prediction["kelurahan"]
        row["time_window"] = prediction["time_window"]
        row["window_start"] = prediction["window_start"]
        row["window_end"] = prediction["window_end"]
        row["threshold_version"] = config.threshold_version

    _write(target_dir / "risk_scores.csv", risk_rows)
    _write(target_dir / "predictions.csv", prediction_rows)
    _write(target_dir / "early_warnings.csv", warning_rows)

    return {
        "risk_scores": len(risk_rows),
        "risk_scores_added": added_risk_rows,
        "predictions": len(prediction_rows),
        "early_warnings": len(warning_rows),
    }


def _risk_class(score: int) -> str:
    thresholds = yaml.safe_load(THRESHOLDS_FILE.read_text(encoding="utf-8"))["risk_classes"]
    for band in thresholds:
        if band["min"] <= score <= band["max"]:
            # Gaya penulisan mengikuti berkas sumber (Low/Moderate/...), bukan enum tersimpan;
            # penerjemahan ke enum terjadi saat seed lewat config/taxonomy.
            return str(band["class"]).title()
    message = f"risk_score {score} di luar seluruh rentang kelas risiko"
    raise SeedError(message)


def _write(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    fieldnames = list(rows[0])
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


# ======================================================================================
# TASK 023 — data operasional
# ======================================================================================

#: Pejabat yang memutuskan pada dataset dummy. Berkas sumber memuat 'USER-DEMO-PIMPINAN'
#: yang tidak ada di users.csv (temuan A-1), sehingga seluruh 63 keputusan gagal di-seed.
DECIDER_CODE = "USER-001"

#: Petugas yang membuat penugasan operasional (Command Center pada dataset dummy).
ACTION_CREATOR_CODE = "USER-002"

#: Jenis ancaman yang benar-benar diprediksi sistem. Kejadian di luar daftar ini tidak
#: dihitung sebagai false negative — memasukkannya berarti menghukum model atas ancaman
#: yang memang tidak pernah masuk cakupannya. Aturan cakupan ini PROPOSED (U-03).
EVALUATED_THREATS = ("CURANMOR", "CURAT", "CURAS")

#: Keputusan yang mengizinkan tindakan operasional lahir (CLAUDE.md §13).
DECISIONS_ALLOWING_ACTION = ("Approved", "Modified")

_ACTION_STATUS_CYCLE = ("Completed", "Completed", "Active", "Planned")

_ACTION_RESULTS = {
    "Completed": "Kegiatan preventif terlaksana; situasi terkendali.",
    "Active": "Penugasan sedang berjalan.",
    "Planned": "Penugasan dijadwalkan, menunggu pelaksanaan.",
}


def _bin_for(hour: int) -> str:
    for label, (start, end) in WINDOW_BOUNDS.items():
        if start <= hour < end:
            return label
    return "18:00-23:59"


def regenerate_operational(directory: Path | None = None) -> dict[str, int]:
    """Menulis ulang commander_decisions, operational_actions, dan prediction_actual.

    Menutup tiga temuan audit:

    - **A-1** `decision_by` menunjuk pengguna yang tidak ada (63/63 baris);
    - **A-8** hanya 3 tindakan untuk 52 keputusan yang menyetujui — dan 2 di antaranya
      justru lahir dari keputusan `Rejected`, yang berarti tindakan operasional pernah
      dibuat tanpa persetujuan;
    - **A-7** evaluasi menyentuh prediksi `Draft` dan tidak memuat satu pun
      `False Negative`, sehingga recall tidak dapat dihitung sama sekali.
    """
    target_dir = directory or SAMPLE_DATA_DIR

    def read(name: str) -> list[dict[str, str]]:
        with (target_dir / name).open(encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))

    decisions = read("commander_decisions.csv")
    recommendations = read("recommendations.csv")
    predictions = read("predictions.csv")
    incidents = read("crime_incidents.csv")
    evaluations = read("prediction_actual.csv")
    units = read("police_units.csv")

    prediction_by_code = {row["prediction_id"]: row for row in predictions}
    recommendation_by_code = {row["recommendation_id"]: row for row in recommendations}
    units_by_function: dict[str, list[str]] = {}
    for unit in units:
        units_by_function.setdefault(unit["function"].upper(), []).append(unit["unit_id"])

    # ---- A-1: keputusan menunjuk pengguna yang benar-benar ada -----------------------
    for row in decisions:
        row["decision_by"] = DECIDER_CODE
        if row["decision"] == "Modified":
            # CHECK database mensyaratkan isi baru bila keputusannya MODIFIED (U-07).
            row["modified_text"] = (
                "Disesuaikan komandan: fokuskan kegiatan pada jam puncak dan tambah satu unit."
            )
        else:
            row["modified_text"] = ""

    # ---- A-8: tindakan hanya lahir dari keputusan yang menyetujui ---------------------
    actions: list[dict[str, Any]] = []
    for index, decision in enumerate(
        sorted(
            (row for row in decisions if row["decision"] in DECISIONS_ALLOWING_ACTION),
            key=lambda row: row["decision_id"],
        )
    ):
        recommendation = recommendation_by_code.get(decision["recommendation_id"])
        if recommendation is None:
            message = f"commander_decisions.csv:{decision['decision_id']}: rekomendasi tidak ada"
            raise SeedError(message)

        prediction = prediction_by_code.get(recommendation["prediction_id"])
        if prediction is None:
            message = (
                f"recommendations.csv:{recommendation['recommendation_id']}: prediksi tidak ada"
            )
            raise SeedError(message)

        function = recommendation["recommended_function"].upper()
        candidates = units_by_function.get(function) or units_by_function["SAMAPTA"]
        status = _ACTION_STATUS_CYCLE[index % len(_ACTION_STATUS_CYCLE)]

        actions.append(
            {
                "action_id": f"ACT-{index + 1:04d}",
                "decision_id": decision["decision_id"],
                "unit_id": candidates[index % len(candidates)],
                "grid_id": prediction["grid_id"],
                "kecamatan": prediction["kecamatan"],
                "created_by": ACTION_CREATOR_CODE,
                "start_at": prediction["window_start"],
                "end_at": prediction["window_end"],
                "status": status,
                "result": _ACTION_RESULTS[status],
            }
        )

    # ---- A-7: evaluasi hanya atas prediksi terbit, dan memuat false negative ----------
    evaluable = {
        code
        for code, row in prediction_by_code.items()
        if row["status"] in {"Published", "Validated"}
    }
    kept = [row for row in evaluations if row["prediction_id"] in evaluable]
    dropped = len(evaluations) - len(kept)

    for row in kept:
        row["actual_incident_id"] = ""
        prediction = prediction_by_code[row["prediction_id"]]
        row["actual_window_start"] = prediction["window_start"]
        row["actual_window_end"] = prediction["window_end"]

    predicted_cells = {
        (row["grid_id"], row["threat_type"], row["time_window"], row["prediction_date"])
        for row in predictions
    }
    period = sorted(row["prediction_date"] for row in predictions)
    first_day, last_day = period[0], period[-1]

    # Nomor baru diambil dari nomor tertinggi yang sudah ada, bukan dari jumlah baris:
    # kode lama memiliki celah karena sebagian baris dibuang, sehingga menghitung dari
    # jumlah baris akan menabrak kode yang sudah terpakai.
    used_numbers = [int(row["evaluation_id"].split("-")[-1]) for row in kept]
    next_number = max(used_numbers, default=0) + 1
    false_negatives = 0
    for incident in incidents:
        if not first_day <= incident["incident_date"] <= last_day:
            continue
        if incident["incident_type"] not in EVALUATED_THREATS:
            continue

        window = _bin_for(int(incident["incident_time"].split(":")[0]))
        cell = (incident["grid_id"], incident["incident_type"], window, incident["incident_date"])
        if cell in predicted_cells:
            continue

        day = date.fromisoformat(incident["incident_date"])
        start, end = _window_bounds(day, window)

        kept.append(
            {
                "evaluation_id": f"EVA-{next_number:05d}",
                "prediction_id": "",
                "evaluation_date": incident["incident_date"],
                "actual_event": "True",
                "actual_threat_type": incident["incident_type"],
                "actual_grid_id": incident["grid_id"],
                "actual_time_window": window,
                "actual_window_start": _iso(start),
                "actual_window_end": _iso(end),
                "match_type": "False Negative",
                "actual_incident_id": incident["incident_id"],
                "notes": "Kejadian nyata pada sel tanpa prediksi terbit.",
            }
        )
        next_number += 1
        false_negatives += 1

    _write(target_dir / "commander_decisions.csv", decisions)
    _write(target_dir / "operational_actions.csv", actions)
    _write(target_dir / "prediction_actual.csv", kept)

    return {
        "commander_decisions": len(decisions),
        "operational_actions": len(actions),
        "prediction_actual": len(kept),
        "evaluations_dropped_draft": dropped,
        "false_negatives_added": false_negatives,
    }


# ======================================================================================
# TASK 024 — kanal masyarakat
# ======================================================================================
#
# Tiga berkas dibangkitkan di sini: `citizen_reports.csv`, `public_alerts.csv`, dan
# `community_feedback.csv`.
#
# **Tidak ada identitas pelapor di mana pun**, termasuk di dalam `description`. Tabel
# `citizen_reports` memang sengaja tidak menyimpan nama, kontak, maupun NIK
# (CLAUDE.md §16, docs/02 §6 U-13, docs/14 §3) — dan keputusan pemilik proyek 1 September
# 2026 menegaskan masyarakat adalah kanal tanpa akun. Deskripsi karena itu berisi
# keterangan **kejadian**, bukan keterangan orang. Dijaga oleh
# `tests/test_seeding_public.py::test_citizen_reports_carry_no_personal_identity`.

#: Jumlah baris tiap berkas. `DEMO` — bukan target operasional.
CITIZEN_REPORT_COUNT = 150
PUBLIC_ALERT_COUNT = 25
COMMUNITY_FEEDBACK_COUNT = 60

#: Bagian laporan yang belum tertaut ke sel grid.
#:
#: `citizen_reports.location_id` nullable justru karena keadaan ini nyata: laporan masuk
#: dengan koordinat bebas, sedangkan grid dummy hanya menutup 33 sel 500 m dari seluruh
#: Jakarta Selatan. Titik di luar sel mana pun **tidak boleh** dipaksa masuk ke sel
#: terdekat — itu akan mengarang lokasi. Baris seperti ini menguji jalur nullable yang
#: sungguh-sungguh ada pada schema (docs/02 §6).
UNMAPPED_REPORT_SHARE = 0.12

#: Rentang tanggal dataset, disamakan dengan `crime_incidents.csv` (2023-01-01..2025-12-31).
#: Diambil dari berkas kejadian saat pembangkitan, bukan ditulis sebagai konstanta,
#: supaya tidak melenceng bila dataset kejadian berubah.

#: Jeda pelaporan: kejadian lebih dulu, laporan menyusul (menit).
REPORT_LAG_MINUTES = (10, 36 * 60)

#: Bagian laporan yang tidak menyebutkan waktu kejadian — pelapor tidak selalu tahu.
#: Kolomnya memang nullable (docs/02 §6).
UNKNOWN_INCIDENT_TIME_SHARE = 0.10

#: Tahapan `status_citizen_report` berurutan (docs/02 §22, config/taxonomy/mappings.yaml).
REPORT_STATUS_STAGES = ("Diterima", "Diverifikasi", "Diteruskan", "Ditangani", "Selesai")

#: Seberapa kuat umur laporan menentukan tahapannya. Sisanya acak, supaya datanya berisik
#: seperti laporan masyarakat yang sebenarnya — bukan tangga yang rapi.
STATUS_AGE_WEIGHT = 0.65


@dataclass(frozen=True)
class ReportCategory:
    """Kategori laporan masyarakat beserta contoh keterangan kejadiannya.

    `name` berstatus **DEMO / PROPOSED**: spesifikasi belum menetapkan daftar kategori
    laporan masyarakat (docs/02 §6). Kalimat pada `descriptions` menerangkan kejadian dan
    **tidak pernah** menyebut orang, nomor, atau tanda pengenal apa pun.
    """

    name: str
    urgency_base: int
    descriptions: tuple[str, ...]


REPORT_CATEGORIES: tuple[ReportCategory, ...] = (
    ReportCategory(
        "Kejahatan Jalanan",
        62,
        (
            "Percobaan penjambretan terhadap pejalan kaki di trotoar dekat perempatan.",
            "Pengendara motor dipepet dari belakang saat melintasi jalan yang minim lampu.",
            "Aksi pemalakan terhadap pengguna jalan pada jam pulang kerja.",
            "Perampasan telepon genggam di pinggir jalan; pelaku langsung melarikan diri.",
        ),
    ),
    ReportCategory(
        "Pencurian Kendaraan",
        70,
        (
            "Sepeda motor hilang dari area parkir warung pada malam hari.",
            "Kunci kendaraan tampak dirusak di parkiran belakang pertokoan.",
            "Mobil kehilangan kaca spion di bahu jalan permukiman.",
            "Sepeda motor dibawa pergi dari halaman rumah tanpa kunci ganda.",
        ),
    ),
    ReportCategory(
        "Tawuran dan Perkelahian Kelompok",
        78,
        (
            "Dua kelompok saling lempar batu di ujung gang menjelang tengah malam.",
            "Perkelahian kelompok pecah setelah keributan di lapangan terbuka.",
            "Kerumunan membawa benda tumpul berkumpul di kolong jalan layang.",
        ),
    ),
    ReportCategory(
        "Keramaian Meresahkan",
        46,
        (
            "Balap liar berlangsung di jalan lurus setiap akhir pekan dini hari.",
            "Kerumunan berkumpul sampai larut malam disertai suara bising.",
            "Miras dikonsumsi terbuka di area parkir yang sepi pengawasan.",
        ),
    ),
    ReportCategory(
        "Kerawanan Lingkungan",
        34,
        (
            "Lampu penerangan jalan mati di sepanjang gang sehingga area menjadi gelap.",
            "Portal permukiman rusak dan tidak dapat ditutup pada malam hari.",
            "Lahan kosong dijadikan tempat berkumpul tanpa penerangan sama sekali.",
            "Pos ronda tidak terpakai dan kaca jendelanya pecah.",
        ),
    ),
    ReportCategory(
        "Gangguan Lalu Lintas",
        28,
        (
            "Parkir liar menutup separuh badan jalan pada jam sibuk.",
            "Kendaraan berhenti di mulut persimpangan sehingga arus tersendat.",
            "Bahu jalan berlubang dan membahayakan pengendara roda dua.",
        ),
    ),
)

#: Penanda tempat pada `location_text` — jenis tempat, bukan alamat dan bukan nama orang.
PLACE_HINTS = (
    "dekat pasar",
    "dekat halte",
    "di jalan utama",
    "di gang permukiman",
    "di area parkir",
    "di kolong jalan layang",
    "dekat taman",
    "di deretan pertokoan",
)

#: Jenis umpan balik masyarakat (config/taxonomy/mappings.yaml -> feedback_type).
FEEDBACK_TYPES = ("Keluhan", "Informasi", "Koreksi", "Apresiasi")

#: Status umpan balik (config/taxonomy/mappings.yaml -> status_community_feedback).
FEEDBACK_STATUSES = ("Baru", "Ditinjau", "Selesai")

#: Status imbauan publik (config/taxonomy/mappings.yaml -> status_public_alert).
PUBLIC_ALERT_ACTIVE = "Active"
PUBLIC_ALERT_RESOLVED = "Resolved"
PUBLIC_ALERT_EXPIRED = "Expired"

#: Imbauan untuk publik. Tidak menyebut grid, satuan, jumlah personel, maupun rencana
#: operasi — hanya kewaspadaan dan langkah yang dapat dilakukan warga (docs/02 §7,
#: CLAUDE.md §24).
PUBLIC_MESSAGE_TEMPLATES: dict[str, str] = {
    "CURANMOR": (
        "Imbauan kewaspadaan pencurian kendaraan bermotor di wilayah {area} pada {window}. "
        "Gunakan kunci ganda, parkir di tempat terang dan terawasi, serta laporkan hal "
        "mencurigakan ke Polsek setempat."
    ),
    "CURAT": (
        "Imbauan kewaspadaan pencurian dengan pemberatan di wilayah {area} pada {window}. "
        "Pastikan pintu dan pagar terkunci, aktifkan kembali ronda lingkungan, serta "
        "laporkan hal mencurigakan ke Polsek setempat."
    ),
    "CURAS": (
        "Imbauan kewaspadaan pencurian dengan kekerasan di wilayah {area} pada {window}. "
        "Hindari jalur sepi dan gelap, jangan menampakkan barang berharga di jalan, serta "
        "laporkan hal mencurigakan ke Polsek setempat."
    ),
    "TAWURAN": (
        "Imbauan kewaspadaan perkelahian kelompok di wilayah {area} pada {window}. "
        "Hindari titik keramaian yang memanas dan segera laporkan kepada Polsek setempat."
    ),
    "KEJAHATAN_JALANAN": (
        "Imbauan kewaspadaan kejahatan jalanan di wilayah {area} pada {window}. "
        "Tetap waspada di jalur sepi, berkendara berkelompok bila memungkinkan, serta "
        "laporkan hal mencurigakan ke Polsek setempat."
    ),
}

_DEFAULT_PUBLIC_MESSAGE = (
    "Imbauan kewaspadaan gangguan kamtibmas di wilayah {area} pada {window}. "
    "Tingkatkan kewaspadaan lingkungan dan laporkan hal mencurigakan ke Polsek setempat."
)


def _moment(value: str) -> datetime:
    """Waktu dari berkas sumber; nilai tanpa offset dibaca sebagai waktu Jakarta (docs/02 K-3).

    Sengaja tidak memakai `csv_source.parse_datetime`: fungsi itu mengubah hasilnya ke UTC,
    sedangkan berkas dummy ditulis kembali dalam waktu lokal `+07:00`. Menormalkan ke UTC di
    sini akan membuat kolom waktu berpindah zona setiap kali data dibangkitkan ulang.
    """
    parsed = datetime.fromisoformat(value.strip())
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=SOURCE_TIMEZONE)


def high_risk_minimum() -> int:
    """Batas bawah kelas risiko HIGH menurut `config/risk/warning-thresholds.yaml`.

    Dibaca dari konfigurasi, tidak ditulis sebagai angka di sini: ambang berstatus
    `DEMO / PROPOSED` (U-01) dan CLAUDE.md §12 melarang menyebarkannya ke banyak tempat.
    """
    classes = yaml.safe_load(THRESHOLDS_FILE.read_text(encoding="utf-8"))["risk_classes"]
    for band in classes:
        if str(band["class"]).upper() == "HIGH":
            return int(band["min"])

    message = "config/risk/warning-thresholds.yaml tidak memuat kelas risiko HIGH"
    raise SeedError(message)


#: Sebaran jam laporan masuk. Malam lebih padat daripada pagi — sesuai jendela waktu yang
#: juga mendominasi dataset kejadian. `DEMO`, bukan hasil pengukuran.
REPORT_HOUR_WEIGHTS: tuple[int, ...] = (
    3, 2, 2, 1, 1, 1, 2, 3, 4, 4, 4, 4,
    5, 5, 5, 6, 7, 9, 12, 13, 12, 10, 8, 5,
)  # fmt: skip

#: Sebaran jenis umpan balik. Informasi tambahan paling sering; apresiasi paling jarang.
FEEDBACK_TYPE_WEIGHTS: tuple[int, ...] = (5, 8, 3, 2)


def _grid_report_weights(risk_rows: list[dict[str, str]]) -> dict[str, int]:
    """Bobot pemilihan wilayah: banyaknya sel risiko berkelas HIGH ke atas per grid.

    Laporan masyarakat memang **lebih sering** datang dari wilayah yang rawan, tetapi
    korelasinya tidak pernah rapi. Bobot 6–18 pada dataset ini hanya menggeser peluang
    sekitar tiga kali lipat, dan dengan 150 laporan atas 33 grid sebaran acaknya masih
    mendominasi. Itu disengaja: data yang cocok sempurna dengan prediksi tidak dapat
    dipercaya saat paparan — ia hanya membuktikan bahwa keduanya dibuat dari satu cetakan.
    """
    minimum = high_risk_minimum()
    weights: dict[str, int] = {}
    for row in risk_rows:
        grid_id = row["grid_id"]
        weights.setdefault(grid_id, 0)
        if int(row["risk_score"]) >= minimum:
            weights[grid_id] += 1

    if not weights:
        message = "risk_scores.csv kosong — bobot wilayah laporan tidak dapat dihitung"
        raise SeedError(message)

    # Setiap grid tetap punya peluang: wilayah tenang pun menerima laporan.
    return {grid_id: max(1, value) for grid_id, value in weights.items()}


def _incident_period(incident_rows: list[dict[str, str]]) -> tuple[date, date]:
    """Rentang tanggal `crime_incidents.csv`, dibaca dari datanya sendiri."""
    days = sorted(row["incident_date"] for row in incident_rows)
    if not days:
        message = "crime_incidents.csv kosong — rentang tanggal laporan tidak dapat ditentukan"
        raise SeedError(message)
    return date.fromisoformat(days[0]), date.fromisoformat(days[-1])


def _build_citizen_reports(
    locations: list[dict[str, str]],
    weights: dict[str, int],
    period: tuple[date, date],
) -> list[dict[str, Any]]:
    first_day, last_day = period
    # Dua hari disisakan supaya `reported_at` (kejadian + jeda pelaporan) tetap berada di
    # dalam rentang dataset, bukan meluber ke tahun berikutnya.
    last_incident_day = last_day - timedelta(days=2)
    span_days = (last_incident_day - first_day).days

    by_grid = {row["grid_id"]: row for row in locations}
    grids = sorted(grid for grid in weights if grid in by_grid)
    grid_weights = [weights[grid] for grid in grids]
    weight_low, weight_high = min(grid_weights), max(grid_weights)
    weight_span = max(1, weight_high - weight_low)

    rows: list[dict[str, Any]] = []
    for index in range(CITIZEN_REPORT_COUNT):
        code = f"RPT-{index + 1:04d}"
        rng = row_rng(code)

        grid_id = rng.choices(grids, weights=grid_weights, k=1)[0]
        location = by_grid[grid_id]

        # `rank` 0 berarti laporan terbaru, 1 berarti tertua. Volumenya dipangkatkan
        # supaya laporan terbaru lebih banyak — kanal pengaduan tumbuh, dan laporan lama
        # lebih jarang terekam ulang. Peringkatnya sendiri tetap seragam, sehingga
        # tahapan penanganan di bawah tidak ikut tergencet ke tahap awal.
        rank = rng.random()
        incident_day = last_incident_day - timedelta(days=int(span_days * rank**2.0))
        hour = rng.choices(range(24), weights=REPORT_HOUR_WEIGHTS, k=1)[0]
        incident_at = datetime(
            incident_day.year,
            incident_day.month,
            incident_day.day,
            hour,
            rng.randrange(60),
            tzinfo=SOURCE_TIMEZONE,
        )
        reported_at = incident_at + timedelta(minutes=rng.randint(*REPORT_LAG_MINUTES))

        category = REPORT_CATEGORIES[rng.randrange(len(REPORT_CATEGORIES))]

        # Tahapan sebagian ditentukan umur laporan, sebagian acak (STATUS_AGE_WEIGHT).
        position = STATUS_AGE_WEIGHT * rank + (1 - STATUS_AGE_WEIGHT) * rng.random()
        stage = min(len(REPORT_STATUS_STAGES) - 1, int(position * len(REPORT_STATUS_STAGES)))

        risk_bump = round(12 * (weights[grid_id] - weight_low) / weight_span)
        urgency = category.urgency_base + risk_bump - 6 + rng.randint(-14, 14)
        # Nilai verifikasi naik seiring tahapan, tetapi rentangnya sengaja bertumpang
        # tindih: laporan yang sudah maju pun tidak selalu terverifikasi kuat.
        verification = 20 + stage * 15 + rng.randint(-18, 18)

        unmapped = rng.random() < UNMAPPED_REPORT_SHARE
        base_lat, base_lon = float(location["latitude"]), float(location["longitude"])
        if unmapped:
            # Digeser 1–3 km sehingga titiknya benar-benar jatuh di luar sel 500 m mana pun.
            offset = rng.uniform(0.009, 0.027)
            angle = rng.uniform(0, 6.283185)
            latitude = base_lat + offset * math.cos(angle)
            longitude = base_lon + offset * math.sin(angle)
            location_text = f"Wilayah {location['kecamatan']}, {rng.choice(PLACE_HINTS)}"
        else:
            latitude = base_lat + rng.uniform(-0.0018, 0.0018)
            longitude = base_lon + rng.uniform(-0.0018, 0.0018)
            location_text = f"Sekitar {location['kelurahan']}, {rng.choice(PLACE_HINTS)}"

        rows.append(
            {
                "report_id": code,
                "reported_at": _iso(reported_at),
                # Sebagian pelapor tidak mengetahui waktu kejadian; kolomnya nullable.
                "incident_time": (
                    "" if rng.random() < UNKNOWN_INCIDENT_TIME_SHARE else _iso(incident_at)
                ),
                "category": category.name,
                "description": category.descriptions[rng.randrange(len(category.descriptions))],
                # Kosong berarti titik laporan belum tertaut ke sel grid mana pun.
                "grid_id": "" if unmapped else grid_id,
                "latitude": f"{latitude:.6f}",
                "longitude": f"{longitude:.6f}",
                "location_text": location_text,
                "urgency_score": str(min(95, max(5, urgency))),
                "verification_score": str(min(100, max(0, verification))),
                "status": REPORT_STATUS_STAGES[stage],
            }
        )

    return rows


def _build_public_alerts(warning_rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    """Imbauan publik atas peringatan dengan jendela waktu paling mutakhir.

    Yang dipilih adalah peringatan **terbaru**, bukan yang paling berat. Kanal publik
    menayangkan imbauan yang masih relevan; imbauan lama tidak diterbitkan ulang hanya
    karena skornya tinggi. Pemilihan ini tetap **keputusan dataset demo**, bukan ambang
    publikasi: siapa yang berwenang mempublikasikan dan severity minimum yang boleh terbit
    belum ditetapkan (U-10, `REQUIRES HUMAN / POLICY APPROVAL`), sehingga tidak ada ambang
    yang ditanam di kode ini.

    Sebagian besar hasilnya berstatus `Expired`. Itu keadaan datanya, bukan cacat
    pembangkit: hampir seluruh peringatan pada dataset dummy jendelanya sudah lewat
    terhadap peringatan termuda. Menyulapnya menjadi `Active` akan membuat layar
    tampak lebih hidup daripada datanya sendiri.
    """
    if not warning_rows:
        message = "early_warnings.csv kosong — imbauan publik tidak dapat dibangkitkan"
        raise SeedError(message)

    # "Sekarang" menurut dataset adalah saat peringatan termuda diterbitkan. Batas jendela
    # tidak dapat dipakai sebagai acuan: jendela justru menunjuk ke depan, dan sebagian
    # peringatan memprediksi hari yang belum tiba.
    now = max(_moment(row["created_at"]) for row in warning_rows)
    ranked = sorted(
        warning_rows,
        key=lambda row: (row["window_end"], int(row["risk_score"]), row["warning_id"]),
        reverse=True,
    )
    selected = sorted(ranked[:PUBLIC_ALERT_COUNT], key=lambda row: row["warning_id"])

    rows: list[dict[str, Any]] = []
    for index, warning in enumerate(selected):
        window_end = _moment(warning["window_end"])
        if warning["status"] == "Resolved":
            # Peringatan sumbernya sudah ditutup, jadi imbauannya ikut ditutup.
            status = PUBLIC_ALERT_RESOLVED
        elif window_end < now:
            # Jendela imbauan sudah lewat sementara peringatannya tidak pernah ditutup.
            status = PUBLIC_ALERT_EXPIRED
        else:
            status = PUBLIC_ALERT_ACTIVE

        # Hanya kecamatan yang disebut ke publik — bukan kelurahan, bukan grid (docs/02 §7).
        area_text = f"Kecamatan {warning['kecamatan']}"
        template = PUBLIC_MESSAGE_TEMPLATES.get(warning["threat_type"], _DEFAULT_PUBLIC_MESSAGE)

        rows.append(
            {
                "public_alert_id": f"PAL-{index + 1:04d}",
                "warning_id": warning["warning_id"],
                "severity": warning["severity"],
                "threat_type": warning["threat_type"],
                "area_text": area_text,
                "time_window": warning["time_window"],
                "window_start": warning["window_start"],
                "window_end": warning["window_end"],
                "status": status,
                "public_message": template.format(
                    area=area_text, window=f"pukul {warning['time_window']} WIB"
                ),
            }
        )

    return rows


def _build_community_feedback(
    report_rows: list[dict[str, Any]], last_day: date
) -> list[dict[str, Any]]:
    limit = datetime(last_day.year, last_day.month, last_day.day, 23, 59, tzinfo=SOURCE_TIMEZONE)
    total_reports = len(report_rows)
    if total_reports < COMMUNITY_FEEDBACK_COUNT:
        message = (
            f"laporan masyarakat hanya {total_reports} baris, "
            f"tidak cukup untuk {COMMUNITY_FEEDBACK_COUNT} umpan balik"
        )
        raise SeedError(message)

    rows: list[dict[str, Any]] = []
    for index in range(COMMUNITY_FEEDBACK_COUNT):
        code = f"FDB-{index + 1:04d}"
        rng = row_rng(code)

        # Laporan yang ditanggapi disebar merata sepanjang daftar, bukan diacak, supaya
        # setiap umpan balik menunjuk laporan yang berbeda tanpa perlu memeriksa tabrakan.
        report = report_rows[index * total_reports // COMMUNITY_FEEDBACK_COUNT]
        reported_at = _moment(str(report["reported_at"]))

        submitted_at = reported_at + timedelta(
            days=rng.randint(1, 21), hours=rng.randint(0, 12), minutes=rng.randrange(60)
        )
        submitted_at = min(submitted_at, limit)

        age_days = (limit - submitted_at).days
        # Umpan balik lama lebih mungkin sudah selesai ditinjau.
        position = 0.6 * min(1.0, age_days / 365) + 0.4 * rng.random()
        status = FEEDBACK_STATUSES[min(len(FEEDBACK_STATUSES) - 1, int(position * 3))]

        rows.append(
            {
                "feedback_id": code,
                "report_id": report["report_id"],
                "feedback_type": rng.choices(FEEDBACK_TYPES, weights=FEEDBACK_TYPE_WEIGHTS, k=1)[0],
                "submitted_at": _iso(submitted_at),
                "status": status,
            }
        )

    return rows


def regenerate_public(directory: Path | None = None) -> dict[str, int]:
    """Menulis ulang citizen_reports.csv, public_alerts.csv, dan community_feedback.csv.

    Deterministik: setiap baris memakai `row_rng(kode)`, sehingga menjalankan ulang
    menghasilkan berkas yang sama persis dan hasilnya tidak bergantung pada urutan
    pemrosesan.

    Dijalankan **setelah** `regenerate()` karena imbauan publik menyalin severity, jenis
    ancaman, dan batas jendela dari `early_warnings.csv` yang baru disesuaikan di sana.
    """
    target_dir = directory or SAMPLE_DATA_DIR

    def read(name: str) -> list[dict[str, str]]:
        with (target_dir / name).open(encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))

    locations = read("locations.csv")
    incidents = read("crime_incidents.csv")
    risk_rows = read("risk_scores.csv")
    warning_rows = read("early_warnings.csv")

    period = _incident_period(incidents)
    weights = _grid_report_weights(risk_rows)

    reports = _build_citizen_reports(locations, weights, period)
    alerts = _build_public_alerts(warning_rows)
    feedback = _build_community_feedback(reports, period[1])

    _write(target_dir / "citizen_reports.csv", reports)
    _write(target_dir / "public_alerts.csv", alerts)
    _write(target_dir / "community_feedback.csv", feedback)

    return {
        "citizen_reports": len(reports),
        "citizen_reports_unmapped": sum(1 for row in reports if not row["grid_id"]),
        "public_alerts": len(alerts),
        "community_feedback": len(feedback),
    }
