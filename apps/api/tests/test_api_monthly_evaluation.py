"""Modul 5 mekanisme: cakupan N kelurahan teratas pada bulan sasaran, pembanding historis pada
N dan batas data yang sama, rekap mutu usulan, tinjauan pelaksanaan."""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator
from datetime import date, datetime, time, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from prediksi_presisi_api.api.deps import get_db
from prediksi_presisi_api.main import app
from prediksi_presisi_api.models import CrimeIncident, Location, Role, User
from prediksi_presisi_api.security.passwords import hash_password
from prediksi_presisi_api.services import clock

DATABASE_URL = os.environ.get("DATABASE_URL", "")
PASSWORD = "KataSandiUji#2026"  # noqa: S105
pytestmark = pytest.mark.skipif(not DATABASE_URL, reason="DATABASE_URL tidak diisi")
MONTH = "2033-05"


@pytest.fixture
def session() -> Iterator[Session]:
    engine = create_engine(DATABASE_URL, future=True)
    connection = engine.connect()
    transaction = connection.begin()
    opened = sessionmaker(bind=connection, expire_on_commit=False)()
    yield opened
    opened.close()
    transaction.rollback()
    connection.close()
    engine.dispose()


@pytest.fixture
def client(session: Session) -> Iterator[TestClient]:
    app.dependency_overrides[get_db] = lambda: session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _login(client: TestClient, session: Session, role_name: str) -> dict[str, str]:
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
    token = client.post(
        "/api/v1/auth/login", json={"username": user.username, "password": PASSWORD}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _incident(session: Session, location: Location, day: date) -> None:
    at = datetime.combine(day, time(20, 0), tzinfo=clock.JAKARTA)
    session.add(
        CrimeIncident(
            code=f"INC-UJI-{uuid.uuid4().hex[:8]}",
            incident_type="CURAT",
            occurred_at=at,
            incident_date=day,
            incident_time=time(20, 0),
            time_known=True,
            location_id=location.location_id,
            reported_at=at + timedelta(hours=2),
            status="REPORTED",
        )
    )
    session.flush()


def test_coverage_of_frozen_top_n_and_decision_review(client: TestClient, session: Session) -> None:
    areas = session.scalars(
        select(Location).where(Location.kelurahan.is_not(None)).order_by(Location.kelurahan)
    ).all()
    a, b, c = areas[0], areas[1], areas[2]
    # Dasar (Feb–Apr 2033): A ramai, B sedang → A peringkat 1, B peringkat 2.
    for i in range(6):
        _incident(session, a, date(2033, 2, 3) + timedelta(days=i * 12))
    for i in range(2):
        _incident(session, b, date(2033, 3, 5) + timedelta(days=i * 10))
    analyst = _login(client, session, "Analis Intelkam")
    leader = _login(client, session, "Pimpinan")
    assert (
        client.post("/api/v1/rankings/freeze", json={"month": MONTH}, headers=analyst).status_code
        == 200
    )

    # Aktual Mei 2033: 3 di A, 1 di B, 2 di C (C di luar pilihan).
    for i in range(3):
        _incident(session, a, date(2033, 5, 2 + i))
    _incident(session, b, date(2033, 5, 9))
    for i in range(2):
        _incident(session, c, date(2033, 5, 12 + i))

    before = client.get(f"/api/v1/evaluation/monthly?month={MONTH}", headers=leader)
    assert before.status_code == 200, before.text
    body = before.json()
    assert body["top_n"] == 6 and body["decision"] is None
    frozen = next(m for m in body["methods"] if m["frozen"])
    assert frozen["method"] == "HISTORY_3M" and frozen["mappable_total"] == 6
    assert frozen["selected"][:2] == [a.kelurahan, b.kelurahan]
    assert frozen["covered"] >= 4 and frozen["coverage_pct"] >= 66.0
    comparison = next(m for m in body["methods"] if m["method"] == "HISTORY_12M")
    assert comparison["frozen"] is False and comparison["top_n"] == 6

    # Dengan produk yang ditetapkan Pimpinan pada 1 kelurahan: cakupan keputusan = 3/6.
    base = f"/api/v1/monthly-products/{MONTH}"
    assert (
        client.post("/api/v1/monthly-products", json={"month": MONTH}, headers=analyst).status_code
        == 201
    )
    assert (
        client.post(
            f"{base}/analyst",
            json={
                "items": [
                    {"kelurahan": b.kelurahan, "status": "REJECTED", "reason": "tidak didukung"}
                ]
            },
            headers=analyst,
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"{base}/decide", json={"selected": [{"kelurahan": a.kelurahan}]}, headers=leader
        ).status_code
        == 200
    )

    after = client.get(f"/api/v1/evaluation/monthly?month={MONTH}", headers=leader).json()
    assert after["top_n"] == 1
    assert after["decision"]["covered"] == 3 and after["decision"]["coverage_pct"] == 50.0
    assert after["decision"]["items"][0]["kelurahan"] == a.kelurahan
    assert (
        after["quality"]["analyst"] == {"ACCEPTED": 9, "REVISED": 0, "REJECTED": 1}
        or after["quality"]["analyst"]["REJECTED"] == 1
    )
    assert after["quality"]["reasons"][0]["reason"] == "tidak didukung"
    top1 = next(m for m in after["methods"] if m["frozen"])
    assert top1["top_n"] == 1 and top1["covered"] == 3
