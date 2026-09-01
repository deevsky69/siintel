"""TASK 023 — Seed data operasional: commander_decisions, operational_actions, prediction_actual.

Tiga acceptance criteria ditutup di sini (docs/08 PHASE 3):

- **A-1** `decision_by` menunjuk pengguna yang benar-benar ada;
- **A-8** setiap keputusan `APPROVED`/`MODIFIED` memiliki tindakan, dan tidak ada tindakan
  yang lahir dari keputusan `REJECTED`. Aturan terakhir ditegakkan trigger database, jadi
  data yang melanggarnya akan ditolak PostgreSQL — bukan sekadar tidak lolos review;
- **A-7** evaluasi hanya menyentuh prediksi terbit dan memuat baris `FALSE_NEGATIVE`,
  sehingga recall benar-benar dapat dihitung (CLAUDE.md §26).
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import (
    CommanderDecision,
    CrimeIncident,
    OperationalAction,
    PoliceUnit,
    Prediction,
    PredictionActual,
    Recommendation,
    User,
)
from . import csv_source as src
from .crime import location_index
from .errors import SeedError
from .master import SeedSummary
from .taxonomy import Taxonomy, load_taxonomy


def seed_commander_decisions(session: Session, taxonomy: Taxonomy, summary: SeedSummary) -> None:
    existing = set(session.scalars(select(CommanderDecision.code)).all())
    recommendations = {
        code: recommendation_id
        for code, recommendation_id in session.execute(
            select(Recommendation.code, Recommendation.recommendation_id)
        ).all()
    }
    users = {
        code: user_id for code, user_id in session.execute(select(User.code, User.user_id)).all()
    }
    inserted = 0

    for row in src.read_rows("commander_decisions.csv"):
        code = src.required_text(row, "decision_id", "commander_decisions.csv")
        if code in existing:
            continue

        where = f"commander_decisions.csv:{code}"
        recommendation_code = src.required_text(row, "recommendation_id", where)
        recommendation_id = recommendations.get(recommendation_code)
        if recommendation_id is None:
            message = f"{where}: rekomendasi '{recommendation_code}' tidak ditemukan"
            raise SeedError(message)

        decider_code = src.required_text(row, "decision_by", where)
        decision_by = users.get(decider_code)
        if decision_by is None:
            message = (
                f"{where}: pengguna '{decider_code}' tidak ada pada tabel users. "
                f"Keputusan operasional wajib punya pejabat yang bertanggung jawab."
            )
            raise SeedError(message)

        session.add(
            CommanderDecision(
                code=code,
                recommendation_id=recommendation_id,
                decision_by=decision_by,
                decision=taxonomy.require("decision", src.text(row, "decision")),
                decision_at=src.parse_datetime(src.required_text(row, "decision_at", where), where),
                reason=src.text(row, "reason"),
                modified_text=src.text(row, "modified_text"),
            )
        )
        inserted += 1

    summary.record("commander_decisions", inserted, len(existing))


def seed_operational_actions(session: Session, taxonomy: Taxonomy, summary: SeedSummary) -> None:
    existing = set(session.scalars(select(OperationalAction.code)).all())
    locations = location_index(session)
    decisions = {
        code: decision_id
        for code, decision_id in session.execute(
            select(CommanderDecision.code, CommanderDecision.decision_id)
        ).all()
    }
    units = {
        code: unit_id
        for code, unit_id in session.execute(select(PoliceUnit.code, PoliceUnit.unit_id)).all()
    }
    users = {
        code: user_id for code, user_id in session.execute(select(User.code, User.user_id)).all()
    }
    inserted = 0

    for row in src.read_rows("operational_actions.csv"):
        code = src.required_text(row, "action_id", "operational_actions.csv")
        if code in existing:
            continue

        where = f"operational_actions.csv:{code}"
        decision_code = src.required_text(row, "decision_id", where)
        decision_id = decisions.get(decision_code)
        if decision_id is None:
            message = f"{where}: keputusan '{decision_code}' tidak ditemukan"
            raise SeedError(message)

        creator_code = src.text(row, "created_by")

        session.add(
            OperationalAction(
                code=code,
                decision_id=decision_id,
                unit_id=units[src.required_text(row, "unit_id", where)],
                location_id=locations[src.required_text(row, "grid_id", where)],
                created_by=users.get(creator_code) if creator_code else None,
                start_at=src.parse_datetime(src.required_text(row, "start_at", where), where),
                end_at=(
                    None
                    if src.text(row, "end_at") is None
                    else src.parse_datetime(src.required_text(row, "end_at", where), where)
                ),
                status=taxonomy.require("status_action", src.text(row, "status")),
                result=src.text(row, "result"),
            )
        )
        inserted += 1

    summary.record("operational_actions", inserted, len(existing))


def seed_prediction_actual(session: Session, taxonomy: Taxonomy, summary: SeedSummary) -> None:
    existing = set(session.scalars(select(PredictionActual.code)).all())
    locations = location_index(session)
    predictions = {
        code: prediction_id
        for code, prediction_id in session.execute(
            select(Prediction.code, Prediction.prediction_id)
        ).all()
    }
    incidents = {
        code: incident_id
        for code, incident_id in session.execute(
            select(CrimeIncident.code, CrimeIncident.incident_id)
        ).all()
    }
    inserted = 0

    for row in src.read_rows("prediction_actual.csv"):
        code = src.required_text(row, "evaluation_id", "prediction_actual.csv")
        if code in existing:
            continue

        where = f"prediction_actual.csv:{code}"
        match_type = taxonomy.require("match_type", src.text(row, "match_type"))

        prediction_code = src.text(row, "prediction_id")
        incident_code = src.text(row, "actual_incident_id")
        grid_id = src.text(row, "actual_grid_id")

        if match_type == "FALSE_NEGATIVE" and incident_code is None:
            # Tanpa kejadian yang ditunjuk, false negative tidak dapat ditelusuri
            # dan angka recall kehilangan dasarnya (CLAUDE.md §26).
            message = f"{where}: FALSE_NEGATIVE wajib menunjuk kejadian nyata"
            raise SeedError(message)

        session.add(
            PredictionActual(
                code=code,
                evaluation_date=src.parse_date(
                    src.required_text(row, "evaluation_date", where), where
                ),
                prediction_id=predictions.get(prediction_code) if prediction_code else None,
                actual_incident_id=incidents.get(incident_code) if incident_code else None,
                actual_event=src.required_text(row, "actual_event", where).lower() == "true",
                actual_threat_type=src.text(row, "actual_threat_type"),
                actual_location_id=locations.get(grid_id) if grid_id else None,
                actual_window_start=(
                    None
                    if src.text(row, "actual_window_start") is None
                    else src.parse_datetime(row["actual_window_start"], where)
                ),
                actual_window_end=(
                    None
                    if src.text(row, "actual_window_end") is None
                    else src.parse_datetime(row["actual_window_end"], where)
                ),
                match_type=match_type,
                notes=src.text(row, "notes"),
            )
        )
        inserted += 1

    summary.record("prediction_actual", inserted, len(existing))


def seed_operational_data(session: Session, taxonomy: Taxonomy | None = None) -> SeedSummary:
    """Menjalankan seluruh seed data operasional TASK 023."""
    resolved = taxonomy or load_taxonomy()
    summary = SeedSummary()

    seed_commander_decisions(session, resolved, summary)
    session.flush()
    seed_operational_actions(session, resolved, summary)
    session.flush()
    seed_prediction_actual(session, resolved, summary)

    # Session dibuat dengan `autoflush=False`, sehingga baris terakhir kelompok ini
    # tidak akan terlihat oleh query kelompok berikutnya bila tidak di-flush di sini.
    # Itulah yang membuat `seeding all` gagal di database kosong sementara menjalankan
    # perintah satu per satu berhasil: setiap perintah punya transaksinya sendiri.
    session.flush()

    return summary


__all__ = [
    "seed_commander_decisions",
    "seed_operational_actions",
    "seed_operational_data",
    "seed_prediction_actual",
]
