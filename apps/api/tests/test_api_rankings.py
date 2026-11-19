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
    # IKW (naskah B.4.2) membawa statusnya; yang DITAHAN tidak diterbitkan, bukan dianggap nol.
    for row in result.rows:
        index = row.basis["ikw"]
        assert index["status"] in ("LENGKAP", "SEMENTARA", "DITAHAN")
        assert (row.ikw is None) == (index["status"] == "DITAHAN")
        assert 0 <= index["frequency"] <= 4 and 0 <= index["recurrence"] <= 4
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
    assert options.status_code == 200
    body = options.json()
    # Metode dasar usulan ditentukan penjaga (model bila terbukti lebih tepat, selain itu
    # peta historis) — bergantung pada data, jadi yang diperiksa adalah kesepadanannya.
    assert body["configured_method"] == "MODEL"
    assert body["default_method"] == body["method_choice"]["method"]
    assert body["method_choice"]["reason"]
    assert {m["value"] for m in body["methods"]} == {
        "MODEL",
        "HISTORY_3M",
        "HISTORY_12M",
        "HISTORY_1M",
        "ANNUAL",
    }
    assert body["model"] is not None and "available" in body["model"]

    preview = client.get("/api/v1/rankings?month=2031-02&method=HISTORY_3M", headers=leader)
    assert preview.status_code == 200 and preview.json()["frozen"] is False
    assert preview.json()["data"][0]["kelurahan"] == areas[2].kelurahan

    assert (
        client.post(
            "/api/v1/rankings/freeze",
            json={"month": "2031-02", "method": "HISTORY_3M"},
            headers=leader,
        ).status_code
        == 403
    )
    payload = {"month": "2031-02", "method": "HISTORY_3M"}
    frozen = client.post("/api/v1/rankings/freeze", json=payload, headers=admin)
    assert frozen.status_code == 200, frozen.text
    assert frozen.json()["frozen"] is True and frozen.json()["data_cutoff"] == "2031-01-31"
    assert client.post("/api/v1/rankings/freeze", json=payload, headers=admin).status_code == 409
    assert (
        client.post(
            "/api/v1/rankings/freeze",
            json={"month": "2031-02", "method": "TIDAK_ADA"},
            headers=admin,
        ).status_code
        == 400
    )

    again = client.get("/api/v1/rankings?month=2031-02&method=HISTORY_3M", headers=leader).json()
    assert again["frozen"] is True and again["ranking_id"] == frozen.json()["ranking_id"]
    assert "2031-02" in [
        row["target_month"]
        for row in client.get("/api/v1/rankings/options", headers=leader).json()["frozen"]
    ]


def test_new_comparators_previous_month_and_fixed_annual_map(session: Session) -> None:
    areas = _areas(session)
    a, b = areas[0], areas[1]
    # Bulan sebelumnya (Jan 2031): hanya B. Tiga bulan terakhir: A lebih ramai.
    for i in range(5):
        _incident(session, a, date(2030, 11, 5) + timedelta(days=i * 3))
    for i in range(2):
        _incident(session, b, date(2031, 1, 3) + timedelta(days=i))

    last_month = ranking.compute(session, TARGET, "HISTORY_1M", "VEHICLE")
    assert last_month.rows[0].kelurahan == b.kelurahan and last_month.rows[0].predicted_count == 2.0
    assert last_month.basis_from == date(2031, 1, 1)

    config = ranking.load_config()
    year = ranking.annual_year(config)
    annual = ranking.compute(session, TARGET, "ANNUAL", "VEHICLE")
    assert annual.basis_from == date(year, 1, 1) and annual.basis_to == date(year, 12, 31)
    # Peta tahunan TETAP: kejadian sesudah tahunnya tidak mengubah apa pun.
    assert [r.kelurahan for r in annual.rows] == [
        r.kelurahan for r in ranking.compute(session, date(2032, 6, 1), "ANNUAL", "VEHICLE").rows
    ]
    with pytest.raises(ranking.RankingError):
        ranking.compute(session, date(year, 6, 1), "ANNUAL", "VEHICLE")
