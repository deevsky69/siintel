"""Daftar prediksi menyembunyikan baris VALIDATED kecuali diminta (5 Oktober 2026)."""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator
from datetime import date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from prediksi_presisi_api.api.deps import get_db
from prediksi_presisi_api.main import app
from prediksi_presisi_api.models import Location, Prediction, Role, User
from prediksi_presisi_api.security.passwords import hash_password
from prediksi_presisi_api.services import clock
from prediksi_presisi_api.services import prediction_engine as engine

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


def _headers(client: TestClient, session: Session) -> dict[str, str]:
    role = session.scalar(select(Role).where(Role.role_name == "Administrator"))
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
    response = client.post(
        "/api/v1/auth/login", json={"username": user.username, "password": PASSWORD}
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _prediction(session: Session, status: str, day: date) -> Prediction:
    location = session.scalar(select(Location).order_by(Location.grid_id))
    assert location is not None
    start = datetime.combine(day + timedelta(days=1), datetime.min.time(), tzinfo=clock.JAKARTA)
    row = Prediction(
        code=f"PRD-UJI-{uuid.uuid4().hex[:6]}",
        prediction_date=day,
        forecast_horizon="24H",
        threat_type="CURANMOR",
        location_id=location.location_id,
        time_window="00:00-06:00",
        window_start=start,
        window_end=start + timedelta(hours=6),
        risk_score=50,
        confidence=10,
        dominant_factors=[],
        model_version=engine.RULE_VERSION,
        status=status,
    )
    session.add(row)
    session.flush()
    return row


def test_validated_rows_are_hidden_unless_asked_for(client: TestClient, session: Session) -> None:
    headers = _headers(client, session)
    # VALIDATED yang lebih BARU daripada yang PUBLISHED — persis keadaan setelah evaluasi mundur.
    published = _prediction(session, "PUBLISHED", date(2098, 1, 1))
    validated = _prediction(session, "VALIDATED", date(2098, 6, 1))

    default = client.get("/api/v1/predictions?page_size=200", headers=headers).json()
    codes = {row["code"] for row in default["data"]}
    assert published.code in codes
    assert validated.code not in codes
    assert "VALIDATED" in default["listing_basis"]

    asked = client.get("/api/v1/predictions?status=VALIDATED&page_size=200", headers=headers)
    assert validated.code in {row["code"] for row in asked.json()["data"]}
