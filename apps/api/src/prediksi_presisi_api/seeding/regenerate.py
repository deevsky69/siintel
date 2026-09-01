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

    weights = {key: float(value) for key, value in weights_raw["weights"].items()}
    total = sum(weights.values())
    if abs(total - 1.0) > 1e-9:
        message = f"bobot risk score harus berjumlah 1, saat ini {total}"
        raise SeedError(message)

    return RiskConfig(
        weights_version=str(weights_raw["version"]),
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
