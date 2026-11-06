"""Modul 2–3 mekanisme: peringkat bulanan 65 kelurahan — urutan, seri abjad, batas data,
pembekuan sekali, dan kewenangan."""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator
from datetime import date, datetime, time, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from prediksi_presisi_api.api.deps import get_db
from prediksi_presisi_api.main import app
from prediksi_presisi_api.models import CrimeIncident, Location, Role, User
from prediksi_presisi_api.security.passwords import hash_password
from prediksi_presisi_api.services import clock
from prediksi_presisi_api.services import monthly_ranking as ranking

DATABASE_URL = os.environ.get("DATABASE_URL", "")
PASSWORD = "KataSandiUji#2026"  # noqa: S105
pytestmark = pytest.mark.skipif(not DATABASE_URL, reason="DATABASE_URL tidak diisi")
TARGET = date(2031, 2, 1)  # jauh di depan data apa pun


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


def _incident(
    session: Session,
    location: Location,
    day: date,
    *,
    reported: date | None = None,
    vehicle: bool = True,
) -> None:
    at = datetime.combine(day, time(21, 0), tzinfo=clock.JAKARTA)
    session.add(
        CrimeIncident(
            code=f"INC-UJI-{uuid.uuid4().hex[:8]}",
            incident_type="CURANMOR",
            occurred_at=at,
            incident_date=day,
            incident_time=time(21, 0),
            time_known=True,
            location_id=location.location_id,
            reported_at=datetime.combine(reported or day, time(23, 0), tzinfo=clock.JAKARTA),
            vehicle_object=vehicle,
            status="REPORTED",
        )
    )
    session.flush()


def _areas(session: Session) -> list[Location]:
    rows = session.scalars(
        select(Location).where(Location.kelurahan.is_not(None)).order_by(Location.kelurahan)
    ).all()
    assert len(rows) >= 3
    return list(rows)


def test_ranking_orders_by_three_month_mean_with_alphabetical_ties_and_report_cutoff(
    session: Session,
) -> None:
    areas = _areas(session)
    a, b = areas[0], areas[1]
    # Bulan dasar: Nov 2030 – Jan 2031. A: 6 kejadian; B: 3 kejadian + 1 yang baru dilaporkan
    # setelah batas data (tidak boleh ikut).
    for i in range(6):
        _incident(session, a, date(2030, 11, 5) + timedelta(days=i * 10))
    for i in range(3):
        _incident(session, b, date(2031, 1, 3) + timedelta(days=i))
    _incident(session, b, date(2031, 1, 30), reported=date(2031, 2, 3))

    result = ranking.compute(session, TARGET, "HISTORY_3M", "ALL_3C")
    expected_total = session.scalar(
        select(func.count(func.distinct(Location.kelurahan))).where(Location.kelurahan.is_not(None))
    )
    assert len(result.rows) == expected_total
    assert result.data_cutoff == date(2031, 1, 31)
    assert result.basis_from == date(2030, 11, 1) and result.basis_to == date(2031, 1, 31)
    assert result.rows[0].kelurahan == a.kelurahan and result.rows[0].predicted_count == 2.0
    assert result.rows[1].kelurahan == b.kelurahan and result.rows[1].predicted_count == 1.0
    # Sisanya seri 0 → abjad.
    rest = [row.kelurahan for row in result.rows[2:]]
    assert rest == sorted(rest)
    assert all(row.ikw is not None and row.ikw_category for row in result.rows)
    assert result.rows[0].basis["basis_total"] == 6

    vehicle_only = ranking.compute(session, TARGET, "HISTORY_3M", "VEHICLE")
    assert vehicle_only.rows[0].kelurahan == a.kelurahan


def test_freeze_once_then_read_frozen_and_only_manager_may_freeze(
    client: TestClient, session: Session
) -> None:
    areas = _areas(session)
    _incident(session, areas[2], date(2031, 1, 10))
    admin = _login(client, session, "Administrator")
    leader = _login(client, session, "Pimpinan")

    options = client.get("/api/v1/rankings/options", headers=leader)
    assert options.status_code == 200 and options.json()["default_method"] == "HISTORY_3M"

    preview = client.get("/api/v1/rankings?month=2031-02", headers=leader)
    assert preview.status_code == 200 and preview.json()["frozen"] is False
    assert preview.json()["data"][0]["kelurahan"] == areas[2].kelurahan

    assert (
        client.post(
            "/api/v1/rankings/freeze", json={"month": "2031-02"}, headers=leader
        ).status_code
        == 403
    )
    frozen = client.post("/api/v1/rankings/freeze", json={"month": "2031-02"}, headers=admin)
    assert frozen.status_code == 200, frozen.text
    assert frozen.json()["frozen"] is True and frozen.json()["data_cutoff"] == "2031-01-31"
    assert (
        client.post("/api/v1/rankings/freeze", json={"month": "2031-02"}, headers=admin).status_code
        == 409
    )
    assert (
        client.post(
            "/api/v1/rankings/freeze", json={"month": "2031-02", "method": "MODEL"}, headers=admin
        ).status_code
        == 400
    )

    again = client.get("/api/v1/rankings?month=2031-02", headers=leader).json()
    assert again["frozen"] is True and again["ranking_id"] == frozen.json()["ranking_id"]
    assert "2031-02" in [
        row["target_month"]
        for row in client.get("/api/v1/rankings/options", headers=leader).json()["frozen"]
    ]
