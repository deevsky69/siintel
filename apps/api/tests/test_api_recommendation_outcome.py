"""Rekomendasi vs kenyataan tahun sasaran (`services/recommendation_outcome.py`).

Fixture sama dengan rencana patroli: batas tampilan 31 Desember 2098, kejadian yang ditanam
pada 2099 hanya terlihat oleh pencocokan.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator
from datetime import UTC, date, datetime, time
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from prediksi_presisi_api.api.deps import get_db
from prediksi_presisi_api.main import app
from prediksi_presisi_api.models import (
    CrimeIncident,
    Location,
    Prediction,
    Recommendation,
    Role,
    User,
)
from prediksi_presisi_api.security.passwords import hash_password
from prediksi_presisi_api.services import recommendation_outcome as outcome
from prediksi_presisi_api.services import visibility

DATABASE_URL = os.environ.get("DATABASE_URL", "")
PASSWORD = "KataSandiUji#2026"  # noqa: S105
pytestmark = pytest.mark.skipif(not DATABASE_URL, reason="DATABASE_URL tidak diisi")
CUTOFF = date(2098, 12, 31)
WIB = ZoneInfo("Asia/Jakarta")


@pytest.fixture
def session(monkeypatch: pytest.MonkeyPatch) -> Iterator[Session]:
    visibility.install()
    monkeypatch.setattr(visibility, "display_cutoff", lambda: CUTOFF)
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


def _kelurahan_location(session: Session, index: int = 0) -> Location:
    rows = session.scalars(
        select(Location).where(Location.kelurahan.is_not(None)).order_by(Location.grid_id)
    ).all()
    assert len(rows) > index
    return rows[index]


def _plant(
    session: Session, location: Location, day: date, hour: int | None, *, count: int = 1
) -> None:
    for _ in range(count):
        session.add(
            CrimeIncident(
                code=f"KJD-UJI-{uuid.uuid4().hex[:6]}",
                incident_type="CURANMOR",
                occurred_at=datetime.combine(day, time(hour=hour or 0), tzinfo=WIB).astimezone(UTC),
                incident_date=day,
                incident_time=None if hour is None else time(hour=hour),
                time_known=hour is not None,
                location_id=location.location_id,
                data_source="UJI",
            )
        )
    session.flush()


def _recommend(session: Session, location: Location, window: str, day: date) -> Recommendation:
    start_hour = int(window[:2])
    window_start = datetime.combine(day, time(hour=start_hour), tzinfo=WIB)
    prediction = Prediction(
        code=f"PRD-UJI-{uuid.uuid4().hex[:6]}",
        prediction_date=day,
        forecast_horizon="24H",
        threat_type="CURANMOR",
        location_id=location.location_id,
        time_window=window,
        window_start=window_start.astimezone(UTC),
        window_end=window_start.replace(hour=min(start_hour + 5, 23), minute=59).astimezone(UTC),
        risk_score=80,
        confidence=70,
        dominant_factors=[],
        model_version="uji",
        status="PUBLISHED",
    )
    session.add(prediction)
    session.flush()
    recommendation = Recommendation(
        code=f"REC-UJI-{uuid.uuid4().hex[:6]}",
        prediction_id=prediction.prediction_id,
        recommended_function="SAMAPTA",
        recommendation_text="uji",
        priority="HIGH",
        status="PENDING_REVIEW",
    )
    session.add(recommendation)
    session.flush()
    return recommendation


def test_time_window_parsing() -> None:
    assert outcome.parse_time_window("00:00-06:00") == (0, 6)
    assert outcome.parse_time_window("18:00-23:59") == (18, 24)
    assert outcome.parse_time_window(None) is None
    assert outcome.parse_time_window("abc") is None


def test_verdicts_follow_place_and_hour(session: Session) -> None:
    aligned_area = _kelurahan_location(session, 0)
    partial_area = _kelurahan_location(session, 1)
    empty_area = _kelurahan_location(session, 2)
    day = date(2099, 1, 1)
    aligned = _recommend(session, aligned_area, "18:00-23:59", day)
    partial = _recommend(session, partial_area, "00:00-06:00", day)
    missing = _recommend(session, empty_area, "12:00-18:00", day)

    # Tempat dan jam terbukti: 3 dari 4 kejadian berjam jatuh pada blok 18-24 (75% >= 25%),
    # satu di antaranya tepat pada jendela harfiah 1 Januari 2099 malam.
    _plant(session, aligned_area, day, 20)
    _plant(session, aligned_area, date(2099, 5, 5), 21, count=2)
    _plant(session, aligned_area, date(2099, 6, 6), 9)
    _plant(session, aligned_area, date(2099, 7, 7), None)  # tanpa jam: tempat saja
    # Tempat terbukti, jam tidak: semua kejadian siang, rekomendasi dini hari.
    _plant(session, partial_area, date(2099, 3, 3), 14, count=2)

    result = outcome.evaluate_recommendations(session, None)
    by_code = {row["code"]: row for row in result["rows"]}

    row = by_code[aligned.code]
    assert row["verdict"] == outcome.VERDICT_ALIGNED
    assert row["literal_window_hit"] is True
    assert row["area_incidents"] == 5 and row["area_unknown_time"] == 1
    assert row["block_incidents"] == 3 and row["block_share_percent"] == 75.0
    assert row["expected_share_percent"] == 25.0
    assert row["area_rank"] == 1 and row["area_rank_of"] == 2

    row = by_code[partial.code]
    assert row["verdict"] == outcome.VERDICT_PARTIAL
    assert row["literal_window_hit"] is False
    assert row["block_incidents"] == 0 and row["block_share_percent"] == 0.0

    row = by_code[missing.code]
    assert row["verdict"] == outcome.VERDICT_NOT_ALIGNED
    assert row["area_incidents"] == 0 and row["area_rank"] is None

    assert result["status"] == "PROPOSED"
    assert result["observed_to"] == "2099-07-07"
    assert result["summary"]["literal_window_hits"] >= 1


def _login(
    client: TestClient, session: Session, role_name: str, polsek: str | None = None
) -> dict[str, str]:
    role = session.scalar(select(Role).where(Role.role_name == role_name))
    assert role is not None
    user = User(
        code=f"USER-UJI-{uuid.uuid4().hex[:6]}",
        username=f"uji.{uuid.uuid4().hex[:6]}",
        password_hash=hash_password(PASSWORD),
        role_id=role.role_id,
        status="ACTIVE",
        must_change_password=False,
        polsek=polsek,
    )
    session.add(user)
    session.flush()
    token = client.post(
        "/api/v1/auth/login", json={"username": user.username, "password": PASSWORD}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_endpoint_requires_a_token_and_honours_polsek_scope(
    client: TestClient, session: Session
) -> None:
    assert client.get("/api/v1/evaluation/recommendations").status_code == 401

    inside = _kelurahan_location(session, 0)
    outside = next(
        row
        for row in session.scalars(
            select(Location).where(Location.kelurahan.is_not(None)).order_by(Location.grid_id)
        ).all()
        if row.polsek != inside.polsek
    )
    own = _recommend(session, inside, "12:00-18:00", date(2099, 1, 1))
    other = _recommend(session, outside, "12:00-18:00", date(2099, 1, 1))

    headers = _login(client, session, "Polsek", polsek=inside.polsek)
    body = client.get("/api/v1/evaluation/recommendations", headers=headers).json()
    codes = {row["code"] for row in body["rows"]}
    assert own.code in codes
    assert other.code not in codes


def test_endpoint_serves_rows_with_their_basis(client: TestClient, session: Session) -> None:
    headers = _login(client, session, "Pimpinan")
    response = client.get("/api/v1/evaluation/recommendations", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "PROPOSED"
    assert "SEJALAN" in body["basis"]
    assert set(body["summary"]) >= {
        "total",
        "aligned",
        "partial",
        "not_aligned",
        "literal_window_hits",
    }
    for row in body["rows"]:
        assert row["verdict"] in {
            outcome.VERDICT_ALIGNED,
            outcome.VERDICT_PARTIAL,
            outcome.VERDICT_NOT_ALIGNED,
            outcome.VERDICT_UNEVALUABLE,
        }
