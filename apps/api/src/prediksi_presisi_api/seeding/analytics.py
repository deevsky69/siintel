"""TASK 022 — Seed data analitik: risk_scores, predictions, early_warnings, recommendations.

Data sumber sudah dibangkitkan ulang lebih dulu (lihat `regenerate.py`) agar memenuhi
acceptance A-3 sampai A-6. Modul ini hanya memuatnya, dan memeriksa ulang kesesuaiannya
terhadap `config/risk/` sebelum menyimpan — pemeriksaan yang sama dijalankan dua kali di dua
tempat berbeda, karena data yang tidak koheren pada lapisan ini akan langsung terlihat
sebagai penjelasan (WHY) yang salah di layar.
"""

from __future__ import annotations

import json
import uuid

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from ..models import EarlyWarning, Prediction, Recommendation, RiskScore
from . import csv_source as src
from .crime import location_index
from .errors import SeedError
from .master import SeedSummary
from .regenerate import FACTOR_COLUMNS, RiskConfig, load_risk_config
from .taxonomy import Taxonomy, load_taxonomy


def _check_factor_consistency(row: dict[str, str], config: RiskConfig, where: str) -> None:
    """A-3: faktor harus benar-benar menghasilkan `risk_score` memakai bobot yang berlaku."""
    score = int(row["risk_score"])
    computed = round(sum(config.weights[name] * int(row[name]) for name in FACTOR_COLUMNS))
    if computed != score:
        message = (
            f"{where}: faktor menghasilkan {computed}, sedangkan risk_score tertulis {score}. "
            f"Jalankan pembangkitan ulang data dummy (regenerate) lebih dulu."
        )
        raise SeedError(message)


def seed_risk_scores(session: Session, taxonomy: Taxonomy, summary: SeedSummary) -> None:
    existing = set(session.scalars(select(RiskScore.code)).all())
    locations = location_index(session)
    config = load_risk_config()
    inserted = 0

    for row in src.read_rows("risk_scores.csv"):
        code = src.required_text(row, "risk_score_id", "risk_scores.csv")
        if code in existing:
            continue

        where = f"risk_scores.csv:{code}"
        _check_factor_consistency(row, config, where)

        grid_id = src.required_text(row, "grid_id", where)
        location_id = locations.get(grid_id)
        if location_id is None:
            message = f"{where}: grid_id '{grid_id}' tidak ada pada tabel locations"
            raise SeedError(message)

        session.add(
            RiskScore(
                code=code,
                assessment_date=src.parse_date(
                    src.required_text(row, "assessment_date", where), where
                ),
                location_id=location_id,
                threat_type=src.required_text(row, "threat_type", where),
                time_window=src.text(row, "time_window"),
                window_start=src.parse_datetime(
                    src.required_text(row, "window_start", where), where
                ),
                window_end=src.parse_datetime(src.required_text(row, "window_end", where), where),
                risk_score=int(src.required_text(row, "risk_score", where)),
                risk_class=taxonomy.require("risk_class", src.text(row, "risk_class")),
                historical_factor=src.integer(row, "historical_factor"),
                recent_trend_factor=src.integer(row, "recent_trend_factor"),
                temporal_factor=src.integer(row, "temporal_factor"),
                spatial_factor=src.integer(row, "spatial_factor"),
                context_factor=src.integer(row, "context_factor"),
                weights_version=src.text(row, "weights_version"),
                model_version=src.text(row, "model_version"),
            )
        )
        inserted += 1

    summary.record("risk_scores", inserted, len(existing))


def seed_predictions(session: Session, taxonomy: Taxonomy, summary: SeedSummary) -> None:
    existing = set(session.scalars(select(Prediction.code)).all())
    locations = location_index(session)
    baselines: dict[str, uuid.UUID] = {
        code: risk_score_id
        for code, risk_score_id in session.execute(
            select(RiskScore.code, RiskScore.risk_score_id)
        ).all()
    }
    inserted = 0

    for row in src.read_rows("predictions.csv"):
        code = src.required_text(row, "prediction_id", "predictions.csv")
        if code in existing:
            continue

        where = f"predictions.csv:{code}"
        grid_id = src.required_text(row, "grid_id", where)
        location_id = locations.get(grid_id)
        if location_id is None:
            message = f"{where}: grid_id '{grid_id}' tidak ada pada tabel locations"
            raise SeedError(message)

        raw_factors = src.required_text(row, "dominant_factors", where)
        try:
            dominant_factors = json.loads(raw_factors)
        except json.JSONDecodeError as error:
            message = f"{where}: dominant_factors bukan JSON yang sah"
            raise SeedError(message) from error

        if not dominant_factors:
            # CLAUDE.md §27: prediksi tanpa penjelasan tidak boleh tersimpan.
            message = f"{where}: dominant_factors kosong — prediksi wajib menjelaskan WHY"
            raise SeedError(message)

        baseline_code = src.text(row, "baseline_risk_score_code")

        session.add(
            Prediction(
                code=code,
                prediction_date=src.parse_date(
                    src.required_text(row, "prediction_date", where), where
                ),
                forecast_horizon=src.required_text(row, "forecast_horizon", where).upper(),
                threat_type=src.required_text(row, "threat_type", where),
                location_id=location_id,
                time_window=src.text(row, "time_window"),
                window_start=src.parse_datetime(
                    src.required_text(row, "window_start", where), where
                ),
                window_end=src.parse_datetime(src.required_text(row, "window_end", where), where),
                risk_score=int(src.required_text(row, "risk_score", where)),
                confidence=int(src.required_text(row, "confidence", where)),
                dominant_factors=dominant_factors,
                model_version=src.required_text(row, "model_version", where),
                baseline_risk_score_id=baselines.get(baseline_code) if baseline_code else None,
                status=taxonomy.require("status_prediction", src.text(row, "status")),
            )
        )
        inserted += 1

    summary.record("predictions", inserted, len(existing))


def seed_early_warnings(session: Session, taxonomy: Taxonomy, summary: SeedSummary) -> None:
    existing = set(session.scalars(select(EarlyWarning.code)).all())
    locations = location_index(session)
    predictions = {
        code: prediction_id
        for code, prediction_id in session.execute(
            select(Prediction.code, Prediction.prediction_id)
        ).all()
    }
    inserted = 0

    for row in src.read_rows("early_warnings.csv"):
        code = src.required_text(row, "warning_id", "early_warnings.csv")
        if code in existing:
            continue

        where = f"early_warnings.csv:{code}"
        prediction_code = src.required_text(row, "prediction_id", where)
        prediction_id = predictions.get(prediction_code)
        if prediction_id is None:
            message = f"{where}: prediksi '{prediction_code}' tidak ditemukan"
            raise SeedError(message)

        session.add(
            EarlyWarning(
                code=code,
                prediction_id=prediction_id,
                severity=taxonomy.require("severity", src.text(row, "severity")),
                threat_type=src.required_text(row, "threat_type", where),
                location_id=locations[src.required_text(row, "grid_id", where)],
                time_window=src.text(row, "time_window"),
                window_start=src.parse_datetime(
                    src.required_text(row, "window_start", where), where
                ),
                window_end=src.parse_datetime(src.required_text(row, "window_end", where), where),
                risk_score=int(src.required_text(row, "risk_score", where)),
                confidence=src.integer(row, "confidence"),
                status=taxonomy.require("status_warning", src.text(row, "status")),
                threshold_version=src.text(row, "threshold_version"),
            )
        )
        inserted += 1

    summary.record("early_warnings", inserted, len(existing))


def seed_recommendations(session: Session, taxonomy: Taxonomy, summary: SeedSummary) -> None:
    """Memuat usulan sistem, dan **menyegarkan kalimatnya** pada baris yang sudah ada.

    Seed pada umumnya hanya menambah baris. Untuk `recommendation_text` itu tidak cukup:
    kalimatnya dibangkitkan ulang dari prediksi yang dirujuk setiap kali `regenerate`
    dijalankan, sehingga basis data yang sudah pernah di-seed akan menyimpan kalimat lama
    selamanya sementara berkas sumbernya sudah berubah — persis jenis penyimpangan yang
    membuat layar dan dataset bercerita berbeda.

    Menyegarkannya aman terhadap jejak keputusan: `commander_decisions` menyimpan salinan
    kalimat yang berlaku SAAT keputusan diambil pada `original_recommendation`, jadi
    keputusan lama tetap menunjuk apa yang benar-benar dibaca pejabat waktu itu (U-07).
    """
    existing_rows = {
        code: text
        for code, text in session.execute(
            select(Recommendation.code, Recommendation.recommendation_text)
        ).all()
    }
    existing = set(existing_rows)
    predictions = {
        code: prediction_id
        for code, prediction_id in session.execute(
            select(Prediction.code, Prediction.prediction_id)
        ).all()
    }
    warnings = {
        code: warning_id
        for code, warning_id in session.execute(
            select(EarlyWarning.code, EarlyWarning.warning_id)
        ).all()
    }
    inserted = 0
    refreshed = 0

    for row in src.read_rows("recommendations.csv"):
        code = src.required_text(row, "recommendation_id", "recommendations.csv")
        where = f"recommendations.csv:{code}"
        if code in existing:
            fresh = src.required_text(row, "recommendation_text", where)
            if existing_rows[code] != fresh:
                session.execute(
                    update(Recommendation)
                    .where(Recommendation.code == code)
                    .values(recommendation_text=fresh)
                )
                refreshed += 1
            continue

        prediction_code = src.required_text(row, "prediction_id", where)
        prediction_id = predictions.get(prediction_code)
        if prediction_id is None:
            message = f"{where}: prediksi '{prediction_code}' tidak ditemukan"
            raise SeedError(message)

        warning_code = src.text(row, "warning_id")

        session.add(
            Recommendation(
                code=code,
                prediction_id=prediction_id,
                warning_id=warnings.get(warning_code) if warning_code else None,
                recommended_function=taxonomy.require(
                    "function", src.text(row, "recommended_function")
                ),
                recommendation_text=src.required_text(row, "recommendation_text", where),
                priority=taxonomy.map("priority", src.text(row, "priority")),
                status=taxonomy.require("status_recommendation", src.text(row, "status")),
            )
        )
        inserted += 1

    summary.record("recommendations", inserted, len(existing))
    if refreshed:
        summary.note("recommendations", f"{refreshed} kalimat usulan disegarkan")


def seed_analytics_data(session: Session, taxonomy: Taxonomy | None = None) -> SeedSummary:
    """Menjalankan seluruh seed data analitik TASK 022."""
    resolved = taxonomy or load_taxonomy()
    summary = SeedSummary()

    seed_risk_scores(session, resolved, summary)
    session.flush()
    seed_predictions(session, resolved, summary)
    session.flush()
    seed_early_warnings(session, resolved, summary)
    session.flush()
    seed_recommendations(session, resolved, summary)

    # Session dibuat dengan `autoflush=False`, sehingga baris terakhir kelompok ini
    # tidak akan terlihat oleh query kelompok berikutnya bila tidak di-flush di sini.
    # Itulah yang membuat `seeding all` gagal di database kosong sementara menjalankan
    # perintah satu per satu berhasil: setiap perintah punya transaksinya sendiri.
    session.flush()

    return summary
