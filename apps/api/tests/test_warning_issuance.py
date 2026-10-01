"""Penerbitan peringatan dini + rekomendasi dari prediksi yang dipublikasikan.

Sampai 1 Oktober 2026 tidak ada kode runtime yang menulis `early_warnings` maupun
`recommendations`; keduanya hanya pernah diisi seeder sintetis. Test di sini menjaga rantai
PREDICTION -> WARNING -> RECOMMENDATION yang kini disambung `services/warning_issuance.py`.
"""

from __future__ import annotations

import itertools
import os
import uuid
from collections.abc import Iterator
from datetime import date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from prediksi_presisi_api.api.deps import get_db
from prediksi_presisi_api.main import app
from prediksi_presisi_api.models import (
    AuditLog,
    EarlyWarning,
    Location,
    Prediction,
    Recommendation,
    Role,
    User,
)
from prediksi_presisi_api.security.passwords import hash_password
from prediksi_presisi_api.services import clock
from prediksi_presisi_api.services import prediction_engine as engine
from prediksi_presisi_api.services import risk_engine as risk
from prediksi_presisi_api.services import warning_issuance as issuance

DATABASE_URL = os.environ.get("DATABASE_URL", "")
PASSWORD = "KataSandiUji#2026"  # noqa: S105
pytestmark = pytest.mark.skipif(not DATABASE_URL, reason="DATABASE_URL tidak diisi")


@pytest.fixture
def session() -> Iterator[Session]:
    db = create_engine(DATABASE_URL, future=True)
    connection = db.connect()
    transaction = connection.begin()
    opened = sessionmaker(bind=connection, expire_on_commit=False)()
    yield opened
    opened.close()
    transaction.rollback()
    connection.close()
    db.dispose()


@pytest.fixture
def client(session: Session) -> Iterator[TestClient]:
    app.dependency_overrides[get_db] = lambda: session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _user(session: Session, role_name: str) -> User:
    role = session.scalar(select(Role).where(Role.role_name == role_name))
    assert role is not None
    user = User(
        code=f"USER-UJI-{uuid.uuid4().hex[:6]}",
        username=f"uji.{uuid.uuid4().hex[:6]}",
        password_hash=hash_password(PASSWORD),
        role_id=role.role_id,
        status="ACTIVE",
        must_change_password=False,
    )
    session.add(user)
    session.flush()
    return user


def _auth(client: TestClient, user: User) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login", json={"username": user.username, "password": PASSWORD}
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


_DAYS = itertools.count()


def _draft(
    session: Session,
    *,
    score: int,
    prediction_date: date = date(2099, 1, 1),
    horizon: str = "24H",
    threat: str = "CURANMOR",
) -> Prediction:
    location = session.scalar(select(Location).order_by(Location.grid_id))
    assert location is not None
    # `uq_predictions_forecast` menolak dua prediksi pada sel+jenis+jendela+horizon+tanggal
    # yang sama — benar untuk sistem, menyulitkan test. Tiap draft memakai hari berbeda.
    day = datetime(2099, 1, 2, 18, 0, tzinfo=clock.JAKARTA) + timedelta(days=next(_DAYS))
    prediction = Prediction(
        code=f"PRD-UJI-{uuid.uuid4().hex[:6]}",
        prediction_date=prediction_date,
        forecast_horizon=horizon,
        threat_type=threat,
        location_id=location.location_id,
        time_window="18:00-23:59",
        window_start=day,
        window_end=day + timedelta(hours=6),
        risk_score=score,
        confidence=40,
        dominant_factors=[
            {"factor": "temporal_factor", "value": 90, "weight": 0.2, "contribution": 18.0},
            {"factor": "historical_factor", "value": 30, "weight": 0.3, "contribution": 9.0},
            {"factor": "confidence_support", "value": 4, "weight": None, "contribution": 0.0},
        ],
        model_version=engine.RULE_VERSION,
        status=engine.STATUS_DRAFT,
    )
    session.add(prediction)
    session.flush()
    return prediction


# ---------------------------------------------------------------------------
# Ambang dan severity dibaca dari config
# ---------------------------------------------------------------------------


def test_severity_comes_from_the_active_threshold_version() -> None:
    thresholds = risk.load_thresholds()
    assert thresholds.minimum_warning_score == 70
    assert thresholds.severity_for(69) is None, "di bawah ambang terbit tidak melahirkan apa pun"
    assert thresholds.severity_for(70) == "WARNING"
    assert thresholds.severity_for(84) == "WARNING"
    assert thresholds.severity_for(85) == "CRITICAL"
    assert thresholds.severity_for(100) == "CRITICAL"


def test_a_score_inside_the_watch_band_but_below_the_floor_is_not_issued() -> None:
    """Tangga severity dummy-v1 mulai dari 60, ambang terbit 70: 65 punya tingkat, tanpa
    peringatan. Dua ambang itu memang berbeda dan keduanya harus terpenuhi."""
    thresholds = risk.load_thresholds()
    assert any(band.severity == "WATCH" for band in thresholds.severities)
    assert thresholds.severity_for(65) is None


def test_function_rules_are_proposed_and_default_to_samapta() -> None:
    rules = issuance.load_function_rules()
    assert rules.status == "PROPOSED", "siapa yang bertindak belum diputus pemilik proyek"
    assert rules.for_threat("CURANMOR").function == "SAMAPTA"
    assert rules.for_threat("JENIS-TIDAK-DIKENAL").function == rules.default_function
    assert rules.priority_for("WARNING") == "HIGH"
    assert rules.priority_for("CRITICAL") == "URGENT"


# ---------------------------------------------------------------------------
# Publikasi tunggal melahirkan peringatan + rekomendasi
# ---------------------------------------------------------------------------


def test_publishing_a_prediction_above_the_floor_issues_a_warning_and_a_recommendation(
    client: TestClient, session: Session
) -> None:
    draft = _draft(session, score=76)
    headers = _auth(client, _user(session, "Administrator"))

    response = client.post(f"/api/v1/predictions/{draft.code}/publish", headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "PUBLISHED"
    assert body["issuance"]["warnings_issued"] == 1
    assert body["issuance"]["threshold_version"] == risk.load_thresholds().version
    assert body["issuance"]["function_rules_status"] == "PROPOSED"

    warning = session.scalar(
        select(EarlyWarning).where(EarlyWarning.prediction_id == draft.prediction_id)
    )
    assert warning is not None
    assert warning.severity == "WARNING"
    assert warning.status == "ACTIVE"
    assert warning.risk_score == 76 and warning.confidence == 40
    assert warning.threshold_version == risk.load_thresholds().version
    assert (warning.window_start, warning.window_end) == (draft.window_start, draft.window_end)
    assert warning.location_id == draft.location_id

    recommendation = session.scalar(
        select(Recommendation).where(Recommendation.warning_id == warning.warning_id)
    )
    assert recommendation is not None
    assert recommendation.prediction_id == draft.prediction_id
    assert recommendation.recommended_function == "SAMAPTA"
    assert recommendation.priority == "HIGH"
    assert recommendation.status == "PENDING_REVIEW"
    # WHAT, WHERE, WHEN, RISK, CONFIDENCE, WHY — dan penutup yang menyatakan ini usulan.
    text = recommendation.recommendation_text
    assert "CURANMOR" in text and draft.code in text and "76/100" in text and "40%" in text
    assert "18:00-23:59 WIB" in text
    assert "pola jendela waktu" in text, "faktor terkuat diambil dari dominant_factors"
    assert text.endswith(issuance.RECOMMENDATION_CLOSING)


def test_a_critical_score_issues_a_critical_warning_with_urgent_priority(
    client: TestClient, session: Session
) -> None:
    draft = _draft(session, score=91)
    headers = _auth(client, _user(session, "Administrator"))
    response = client.post(f"/api/v1/predictions/{draft.code}/publish", headers=headers)
    assert response.status_code == 200, response.text

    warning = session.scalar(
        select(EarlyWarning).where(EarlyWarning.prediction_id == draft.prediction_id)
    )
    assert warning is not None and warning.severity == "CRITICAL"
    recommendation = session.scalar(
        select(Recommendation).where(Recommendation.warning_id == warning.warning_id)
    )
    assert recommendation is not None and recommendation.priority == "URGENT"


def test_publishing_below_the_floor_issues_nothing_but_still_publishes(
    client: TestClient, session: Session
) -> None:
    draft = _draft(session, score=55)
    headers = _auth(client, _user(session, "Administrator"))
    response = client.post(f"/api/v1/predictions/{draft.code}/publish", headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "PUBLISHED"
    assert body["issuance"]["warnings_issued"] == 0
    assert body["issuance"]["below_threshold"] == 1
    assert "ambang" in body["issuance"]["sample"][0]["reason"]
    assert (
        session.scalar(
            select(EarlyWarning).where(EarlyWarning.prediction_id == draft.prediction_id)
        )
        is None
    )


def test_a_prediction_never_gets_a_second_warning(session: Session) -> None:
    """Lapis kedua: meski dipanggil dua kali, satu prediksi tetap satu peringatan."""
    draft = _draft(session, score=80)
    first = issuance.issue_for_predictions(session, [draft])
    second = issuance.issue_for_predictions(session, [draft])
    assert first.warnings_issued == 1
    assert second.warnings_issued == 0
    assert "sudah memiliki peringatan" in str(second.issued[0].reason)
    total = session.scalar(
        select(EarlyWarning).where(EarlyWarning.prediction_id == draft.prediction_id)
    )
    assert total is not None


def test_codes_are_numbered_by_value_not_by_text(session: Session) -> None:
    """WRN-10000 harus menyusul WRN-9999, bukan WRN-1000."""
    location = session.scalar(select(Location).order_by(Location.grid_id))
    assert location is not None
    tall = _draft(session, score=75)
    session.add(
        EarlyWarning(
            code="WRN-9999",
            prediction_id=tall.prediction_id,
            severity="WARNING",
            threat_type="CURANMOR",
            location_id=location.location_id,
            time_window="18:00-23:59",
            window_start=tall.window_start,
            window_end=tall.window_end,
            risk_score=75,
            status="RESOLVED",
            threshold_version="dummy-v1",
        )
    )
    session.flush()
    fresh = _draft(session, score=75)
    summary = issuance.issue_for_predictions(session, [fresh])
    assert summary.issued[0].warning_code == "WRN-10000"


# ---------------------------------------------------------------------------
# Publikasi massal satu penjalanan
# ---------------------------------------------------------------------------


def test_publish_run_is_a_dry_run_by_default(client: TestClient, session: Session) -> None:
    run_date = date(2098, 6, 1)
    _draft(session, score=72, prediction_date=run_date)
    _draft(session, score=40, prediction_date=run_date)
    headers = _auth(client, _user(session, "Administrator"))
    warnings_before = session.scalar(select(func.count()).select_from(EarlyWarning))

    response = client.post(
        "/api/v1/predictions/publish-run",
        json={"prediction_date": run_date.isoformat(), "horizon": "24H"},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["dry_run"] is True
    assert body["drafts"] == 2 and body["published"] == 0
    assert body["issuance"]["warnings_issued"] == 1
    assert body["issuance"]["below_threshold"] == 1

    assert session.scalar(select(func.count()).select_from(EarlyWarning)) == warnings_before
    assert all(
        row.status == engine.STATUS_DRAFT
        for row in session.scalars(
            select(Prediction).where(Prediction.prediction_date == run_date)
        ).all()
    )


def test_publish_run_publishes_every_draft_of_the_run_and_issues_warnings(
    client: TestClient, session: Session
) -> None:
    run_date = date(2098, 6, 2)
    high = _draft(session, score=88, prediction_date=run_date)
    mid = _draft(session, score=70, prediction_date=run_date, threat="CURAT")
    low = _draft(session, score=12, prediction_date=run_date, threat="CURAS")
    other_run = _draft(session, score=95, prediction_date=date(2098, 6, 3))
    headers = _auth(client, _user(session, "Administrator"))

    response = client.post(
        "/api/v1/predictions/publish-run",
        json={"prediction_date": run_date.isoformat(), "horizon": "24H", "dry_run": False},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["published"] == 3
    assert body["issuance"]["warnings_issued"] == 2
    assert body["issuance"]["recommendations_issued"] == 2

    for row in (high, mid, low):
        session.refresh(row)
        assert row.status == engine.STATUS_PUBLISHED
    session.refresh(other_run)
    assert other_run.status == engine.STATUS_DRAFT, "penjalanan lain tidak disentuh"

    severities = {
        warning.prediction_id: warning.severity
        for warning in session.scalars(
            select(EarlyWarning).where(
                EarlyWarning.prediction_id.in_([high.prediction_id, mid.prediction_id])
            )
        ).all()
    }
    assert severities == {high.prediction_id: "CRITICAL", mid.prediction_id: "WARNING"}

    entry = session.scalar(
        select(AuditLog)
        .where(AuditLog.action == "PUBLISH_PREDICTION", AuditLog.resource_id == f"{run_date}/24H")
        .order_by(AuditLog.timestamp.desc())
    )
    assert entry is not None and entry.detail is not None
    assert entry.detail["warnings_issued"] == 2


def test_publish_run_refuses_a_run_without_drafts(client: TestClient, session: Session) -> None:
    headers = _auth(client, _user(session, "Administrator"))
    response = client.post(
        "/api/v1/predictions/publish-run",
        json={"prediction_date": "2097-01-01", "horizon": "24H", "dry_run": False},
        headers=headers,
    )
    assert response.status_code == 404, response.text


def test_publish_run_requires_the_publish_permission(client: TestClient, session: Session) -> None:
    run_date = date(2098, 6, 4)
    draft = _draft(session, score=90, prediction_date=run_date)
    headers = _auth(client, _user(session, "Pimpinan"))
    response = client.post(
        "/api/v1/predictions/publish-run",
        json={"prediction_date": run_date.isoformat(), "horizon": "24H", "dry_run": False},
        headers=headers,
    )
    assert response.status_code == 403, response.text
    session.refresh(draft)
    assert draft.status == engine.STATUS_DRAFT
